#!/usr/bin/env python3
"""
Convert a live Impala DESCRIBE dump into a schema_manifest.json ready for
generate_synthetic_data.py and evaluate_synthetic_data.py.

Two input modes
---------------
1. Live Impala connection (needs impyla):

    python describe_to_manifest.py \
        --host <impala-host> --user <workload-user> --password <workload-pass> \
        --database pf_usecase \
        --tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d \
        --wide-threshold 200 \
        --output schema_manifest.json

2. Pre-saved DESCRIBE text files (no live DB needed):

    # Save one file per table named <table>.describe.txt containing the
    # tab/pipe-delimited output of: DESCRIBE pf_usecase.<table>
    python describe_to_manifest.py \
        --describe-dir ./describe_dumps \
        --database pf_usecase \
        --wide-threshold 200 \
        --output schema_manifest.json

Output
------
A schema_manifest.json with:
- Full column list per table (name, type, nullable — schema parity).
- wide_tables entry for any table exceeding --wide-threshold columns, with
  columns_to_populate pre-filled with the first --populate-cols semantic columns
  (you can edit the list before running the generator).
- Placeholder relationships inferred from column-name conventions (BWC: cfcif,
  RBK: acct_no, REM: txn_ref_no, AMH: msg_ref_no). Review and adjust before use.

Dependencies
------------
Live mode:  pip install impyla thrift-sasl
Text mode:  stdlib only
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# PII heuristics
# ---------------------------------------------------------------------------

PII_PATTERNS = re.compile(
    r"cif|custid|name|addr|email|phone|mobile|nric|passport|dob|birth",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# FK convention map: source-system prefix -> (parent_table_fragment, key_column)
# ---------------------------------------------------------------------------

FK_CONVENTIONS: List[Tuple[str, str]] = [
    ("cfcif",      "eda_bwc_cfmast_d_sg"),   # CIF — customer master
    ("acct_no",    "eda_bwc_cfacct_d_sg"),   # account FK (confirm via JOIN validation)
    ("cfanos",     "eda_bwc_cfacct_d_sg"),   # alternate account key stem
    ("txn_ref_no", "eda_rem_tf"),             # remittance reference
    ("msg_ref_no", "eda_amh_gtw"),            # AMH gateway message
]

# Account-key candidates probed when linking transaction → account tables.
ACCOUNT_FK_CANDIDATES = ["acct_no", "cfanos", "tlxtno", "account_no", "acct_id"]

# Columns we always want in columns_to_populate for each table type.
SEMANTIC_CORE: Dict[str, List[str]] = {
    "master":      ["cfcif", "cfbrnn", "cfname", "cfcost", "cfopen_dt"],
    "account":     ["acct_no", "cfcif", "acct_type", "bal_amt", "ccy", "status"],
    "transaction": ["txn_id", "acct_no", "txn_amt", "ccy", "txn_dt", "txn_type",
                    "status", "branch_cd", "channel_cd", "dr_cr_ind"],
    "lookup":      [],   # small tables — populate everything
    "unknown":     [],
}


# ---------------------------------------------------------------------------
# Impala type helpers
# ---------------------------------------------------------------------------

def _normalise_type(raw: str) -> str:
    t = raw.strip().lower()
    if t.startswith("decimal"):
        return "decimal"
    if t.startswith("varchar") or t.startswith("char"):
        return "string"
    if t in ("int", "integer", "bigint", "smallint", "tinyint",
             "float", "double", "boolean", "string", "timestamp", "date"):
        return t
    return "string"


def _is_nullable(raw: str) -> bool:
    if not raw:
        return True
    return "not null" not in raw.lower()


def _pii_risk(name: str) -> bool:
    return bool(PII_PATTERNS.search(name))


# ---------------------------------------------------------------------------
# Parse DESCRIBE output
# ---------------------------------------------------------------------------

def _parse_describe_text(text: str) -> List[Dict[str, Any]]:
    """Parse the text output of DESCRIBE <table> into a column list.

    Handles tab-delimited, pipe-delimited, or space-aligned output.
    Lines starting with '#' (partition info) are ignored.
    """
    columns = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Try common delimiters.
        for sep in ("\t", "|", "  "):
            parts = [p.strip() for p in line.split(sep) if p.strip()]
            if len(parts) >= 2:
                break
        if len(parts) < 2:
            continue
        name, dtype = parts[0], parts[1]
        nullable_hint = parts[2] if len(parts) > 2 else ""
        columns.append({
            "name": name,
            "type": _normalise_type(dtype),
            "nullable": _is_nullable(nullable_hint),
            "pii_risk": _pii_risk(name),
            "top_values": None,
            "min": None,
            "max": None,
            "avg": None,
            "null_rate": 0.0,
        })
    return columns


# ---------------------------------------------------------------------------
# Classify table type
# ---------------------------------------------------------------------------

def _classify_table(table: str, row_count: int, columns: List[Dict]) -> str:
    has_timestamp = any(c["type"] in ("timestamp", "date") for c in columns)
    has_amount = any("amt" in c["name"] or "bal" in c["name"] for c in columns)
    if row_count < 1000 and not has_timestamp:
        return "lookup"
    if row_count > 100_000 and has_timestamp and has_amount:
        return "transaction"
    if any(c["name"] in ("cfcif", "cif_id") for c in columns):
        if not any("acct" in c["name"] for c in columns):
            return "master"
        return "account"
    return "unknown"


# ---------------------------------------------------------------------------
# Infer FK relationships
# ---------------------------------------------------------------------------

def _infer_relationships(tables: Dict[str, Dict]) -> List[Dict[str, str]]:
    rels = []
    seen_pairs: set = set()
    for child_table, profile in tables.items():
        child_cols = {c["name"] for c in profile["columns"]}
        for fk_col, parent_fragment in FK_CONVENTIONS:
            if fk_col not in child_cols:
                continue
            parent = next(
                (t for t in tables if parent_fragment in t and t != child_table),
                None,
            )
            if parent is None:
                continue
            parent_cols = {c["name"] for c in tables[parent]["columns"]}
            if fk_col in parent_cols:
                key = (parent, child_table, fk_col)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                rels.append({
                    "parent_table": parent,
                    "parent_column": fk_col,
                    "child_table": child_table,
                    "child_column": fk_col,
                    "confidence": "inferred_name_match",
                    "validated_count": None,
                    "note": "Validate with JOIN COUNT (--validate-fks)",
                })

    # Probe transaction → account joins when exact name match failed.
    for child_table, profile in tables.items():
        ttype = _classify_table(child_table, profile["row_count"], profile["columns"])
        if ttype != "transaction" and "tltx" not in child_table:
            continue
        child_cols = {c["name"] for c in profile["columns"]}
        parent = next((t for t in tables if "cfacct" in t), None)
        if not parent:
            continue
        parent_cols = {c["name"] for c in tables[parent]["columns"]}
        for cand in ACCOUNT_FK_CANDIDATES:
            if cand in child_cols and cand in parent_cols:
                key = (parent, child_table, cand)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                rels.append({
                    "parent_table": parent,
                    "parent_column": cand,
                    "child_table": child_table,
                    "child_column": cand,
                    "confidence": "probed_account_key",
                    "validated_count": None,
                    "note": "Probed account-key candidate — confirm with JOIN COUNT",
                })
                break
    return rels


# ---------------------------------------------------------------------------
# Build columns_to_populate for wide tables
# ---------------------------------------------------------------------------

def _columns_to_populate(table: str, columns: List[Dict], table_type: str,
                         max_cols: int, relationships: List[Dict]) -> List[str]:
    """Return a suggested columns_to_populate list for a wide table.

    Always includes: FK columns (from relationships), PK/ID columns, and the
    semantic core for the table type. Then fills up to max_cols with profiled
    (non-null stats) columns.
    """
    fk_cols = {r["parent_column"] for r in relationships if r["parent_table"] == table}
    fk_cols |= {r["child_column"] for r in relationships if r["child_table"] == table}

    id_cols = {c["name"] for c in columns
               if c["name"].endswith("_id") or c["name"].endswith("_no")
               or c.get("role") in ("cif_id", "account_no", "txn_id")}

    core = set(SEMANTIC_CORE.get(table_type, []))
    must_have = fk_cols | id_cols | core

    # Prioritise profiled columns (have top_values or numeric stats).
    profiled = [c["name"] for c in columns
                if c.get("top_values") or c.get("avg") is not None]

    populate = list(dict.fromkeys(
        [c["name"] for c in columns if c["name"] in must_have] +
        profiled
    ))[:max_cols]

    return populate


# ---------------------------------------------------------------------------
# FK validation + column profiling (live Impala)
# ---------------------------------------------------------------------------

def _validate_relationships(cur, database: str,
                            relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    validated = []
    for rel in relationships:
        parent = rel["parent_table"]
        child = rel["child_table"]
        pcol = rel["parent_column"]
        ccol = rel["child_column"]
        sql = (
            f"SELECT COUNT(DISTINCT a.{pcol}) FROM {database}.{parent} a "
            f"INNER JOIN {database}.{child} b ON a.{pcol} = b.{ccol}"
        )
        try:
            cur.execute(sql)
            count = cur.fetchone()[0]
            rel = dict(rel)
            rel["validated_count"] = int(count)
            rel["confidence"] = "high" if count > 0 else "invalid_join"
            if count == 0:
                rel["note"] = f"JOIN returned 0 — column pair {pcol}/{ccol} may be wrong"
            validated.append(rel)
            status = "ok" if count > 0 else "FAIL"
            print(f"    FK validate {parent}.{pcol} -> {child}.{ccol}: {count:,} [{status}]")
        except Exception as exc:  # noqa: BLE001
            rel = dict(rel)
            rel["validated_count"] = None
            rel["confidence"] = "validation_error"
            rel["note"] = str(exc)[:200]
            validated.append(rel)
            print(f"    FK validate {parent}.{pcol} -> {child}.{ccol}: ERROR ({exc})")
    return validated


def _profile_column_stats(cur, database: str, table: str,
                          columns: List[Dict[str, Any]],
                          max_cols: int = 30) -> List[Dict[str, Any]]:
    """Add MIN/MAX/AVG or top-N stats to semantic columns (live mode only)."""
    semantic = [
        c for c in columns
        if any(k in c["name"].lower() for k in ("id", "no", "date", "amt", "ccy", "status", "type", "code"))
        or c.get("pii_risk")
    ][:max_cols]
    updated = {c["name"]: dict(c) for c in columns}
    for col in semantic:
        name = col["name"]
        ctype = col["type"]
        try:
            if ctype in ("decimal", "double", "float", "int", "bigint"):
                cur.execute(
                    f"SELECT MIN(`{name}`), MAX(`{name}`), AVG(`{name}`) "
                    f"FROM {database}.{table} WHERE `{name}` IS NOT NULL"
                )
                row = cur.fetchone()
                if row:
                    updated[name]["min"] = float(row[0]) if row[0] is not None else None
                    updated[name]["max"] = float(row[1]) if row[1] is not None else None
                    updated[name]["avg"] = float(row[2]) if row[2] is not None else None
            elif ctype == "string":
                cur.execute(
                    f"SELECT `{name}`, COUNT(*) AS freq FROM {database}.{table} "
                    f"WHERE `{name}` IS NOT NULL GROUP BY `{name}` "
                    f"ORDER BY freq DESC LIMIT 20"
                )
                rows = cur.fetchall()
                if rows:
                    updated[name]["top_values"] = [str(r[0]) for r in rows[:20]]
        except Exception:  # noqa: BLE001
            continue
    return [updated[c["name"]] for c in columns]


# ---------------------------------------------------------------------------
# Live Impala mode
# ---------------------------------------------------------------------------

def _describe_via_impala(host: str, port: int, user: str, password: str,
                         database: str, tables: List[str],
                         wide_threshold: int, populate_cols: int,
                         validate_fks: bool = False,
                         profile_stats: bool = False,
                         ) -> Dict[str, Any]:
    try:
        from impala.dbapi import connect  # type: ignore
    except ImportError:
        sys.exit("impyla not installed. Run: pip install impyla thrift-sasl")

    conn = connect(host=host, port=port, use_ssl=True, use_http_transport=True,
                   http_path="cliservice", auth_mechanism="PLAIN",
                   user=user, password=password)
    cur = conn.cursor()
    cur.execute(f"USE {database}")

    if not tables or tables == ["all"]:
        cur.execute("SHOW TABLES")
        tables = [r[0] for r in cur.fetchall()]
        print(f"Discovered {len(tables)} tables in {database}")

    result: Dict[str, Dict] = {}
    for table in tables:
        print(f"  DESCRIBE {database}.{table} ...", end=" ", flush=True)
        cur.execute(f"DESCRIBE {database}.{table}")
        raw = cur.fetchall()
        columns = []
        for row in raw:
            name = row[0].strip()
            dtype = row[1].strip() if len(row) > 1 else "string"
            nullable = row[2].strip() if len(row) > 2 else ""
            if not name or name.startswith("#"):
                continue
            columns.append({
                "name": name,
                "type": _normalise_type(dtype),
                "nullable": _is_nullable(nullable),
                "pii_risk": _pii_risk(name),
                "top_values": None, "min": None, "max": None,
                "avg": None, "null_rate": 0.0,
            })
        cur.execute(f"SELECT COUNT(*) FROM {database}.{table}")
        row_count = cur.fetchone()[0]
        if profile_stats and columns:
            columns = _profile_column_stats(cur, database, table, columns)
        print(f"{len(columns)} cols, {row_count:,} rows")
        result[table] = {"row_count": row_count, "columns": columns}

    manifest = _assemble_manifest(database, result, wide_threshold, populate_cols)
    if validate_fks and manifest["relationships"]:
        print("\n  Validating FK relationships ...")
        manifest["relationships"] = _validate_relationships(
            cur, database, manifest["relationships"]
        )
    cur.close()
    conn.close()
    return manifest


# ---------------------------------------------------------------------------
# Text-file mode
# ---------------------------------------------------------------------------

def _describe_via_files(describe_dir: str, database: str,
                        wide_threshold: int, populate_cols: int) -> Dict[str, Any]:
    result: Dict[str, Dict] = {}
    for fname in sorted(os.listdir(describe_dir)):
        if not fname.endswith(".describe.txt"):
            continue
        table = fname.replace(".describe.txt", "")
        path = os.path.join(describe_dir, fname)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        columns = _parse_describe_text(text)
        print(f"  {table}: {len(columns)} columns from {fname}")
        result[table] = {"row_count": 0, "columns": columns}

    return _assemble_manifest(database, result, wide_threshold, populate_cols)


# ---------------------------------------------------------------------------
# Assemble manifest
# ---------------------------------------------------------------------------

def _assemble_manifest(database: str, tables: Dict[str, Dict],
                       wide_threshold: int, populate_cols: int) -> Dict[str, Any]:
    relationships = _infer_relationships(tables)

    generation_order = []
    wide_tables = []
    lookup_tables = []
    master_tables = []
    transaction_tables = []

    for table, profile in tables.items():
        cols = profile["columns"]
        row_count = profile["row_count"]
        ttype = _classify_table(table, row_count, cols)

        # Build FK dependency list.
        parents = list(dict.fromkeys(
            r["parent_table"] for r in relationships if r["child_table"] == table
        ))
        fk_col = next(
            (r["child_column"] for r in relationships if r["child_table"] == table),
            None,
        )
        entry: Dict[str, Any] = {
            "table": table, "type": ttype, "depends_on": parents,
        }
        if fk_col:
            entry["fk"] = fk_col
        generation_order.append(entry)

        if ttype == "lookup":
            lookup_tables.append(table)
        elif ttype in ("master", "account"):
            master_tables.append(table)
        elif ttype == "transaction":
            transaction_tables.append(table)

        if len(cols) > wide_threshold:
            pop = _columns_to_populate(table, cols, ttype, populate_cols, relationships)
            wide_tables.append({
                "table": table,
                "total_columns": len(cols),
                "columns_to_populate": pop,
            })

    # Simple topological sort: tables with no parents first.
    ordered = []
    remaining = list(generation_order)
    placed = set()
    for _ in range(len(remaining) + 1):
        if not remaining:
            break
        for entry in list(remaining):
            if all(p in placed for p in entry["depends_on"]):
                ordered.append(entry)
                placed.add(entry["table"])
                remaining.remove(entry)

    ordered.extend(remaining)  # any unresolvable cycles appended at end

    return {
        "database": database,
        "tables": tables,
        "generation_order": ordered,
        "relationships": relationships,
        "lookup_tables": lookup_tables,
        "master_tables": master_tables,
        "transaction_tables": transaction_tables,
        "wide_tables": wide_tables,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert DESCRIBE output to schema_manifest.json for D3 generator/evaluator."
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--describe-dir", metavar="DIR",
                     help="Directory of *.describe.txt files (text mode, no DB needed)")
    src.add_argument("--host", help="Impala host (live mode)")

    parser.add_argument("--port", type=int, default=443, help="Impala port (default 443)")
    parser.add_argument("--user", help="Impala workload username")
    parser.add_argument("--password", help="Impala workload password")
    parser.add_argument("--database", default="pf_usecase", help="Impala database")
    parser.add_argument("--tables", "--target-tables", dest="tables", default="all",
                        help="Comma-separated table list, or 'all' (live mode only)")
    parser.add_argument("--wide-threshold", type=int, default=200,
                        help="Column count threshold for wide_tables entry (default 200)")
    parser.add_argument("--populate-cols", type=int, default=50,
                        help="Max columns to actively synthesise in wide tables (default 50)")
    parser.add_argument("--validate-fks", action="store_true",
                        help="Run JOIN COUNT queries to validate inferred FK relationships")
    parser.add_argument("--profile-stats", action="store_true",
                        help="Profile MIN/MAX/AVG and top-N on semantic columns (live mode)")
    parser.add_argument("--output", default="schema_manifest.json",
                        help="Output path for schema_manifest.json")
    args = parser.parse_args()

    print("=" * 60)
    print("  describe_to_manifest — D3 schema manifest builder")
    print("=" * 60)

    if args.describe_dir:
        manifest = _describe_via_files(
            args.describe_dir, args.database,
            args.wide_threshold, args.populate_cols,
        )
    else:
        if not args.user or not args.password:
            sys.exit("--user and --password are required for live mode")
        tables = [t.strip() for t in args.tables.split(",") if t.strip()]
        manifest = _describe_via_impala(
            args.host, args.port, args.user, args.password,
            args.database, tables, args.wide_threshold, args.populate_cols,
            validate_fks=args.validate_fks,
            profile_stats=args.profile_stats,
        )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    n_tables = len(manifest["tables"])
    n_rels = len(manifest["relationships"])
    n_wide = len(manifest["wide_tables"])
    print(f"\n[ok] {n_tables} table(s), {n_rels} inferred FK(s), {n_wide} wide table(s)")
    print(f"[ok] Manifest written to {args.output}")
    if manifest["relationships"]:
        print("\nInferred FK relationships (review before running generator):")
        for r in manifest["relationships"]:
            print(f"  {r['parent_table']}.{r['parent_column']}"
                  f" -> {r['child_table']}.{r['child_column']}"
                  f"  [{r.get('confidence','')}]")
    if manifest["wide_tables"]:
        print("\nWide tables (edit columns_to_populate as needed):")
        for w in manifest["wide_tables"]:
            print(f"  {w['table']}: {w['total_columns']} total, "
                  f"{len(w['columns_to_populate'])} to populate")
    print("\nNext steps:")
    print("  1. Review wide_tables[].columns_to_populate — confirm the FK join")
    print("     column is in the list (check with DESCRIBE and a JOIN COUNT query).")
    print("  2. Run: python generate_synthetic_data.py --manifest", args.output)
    print("  3. Run: python evaluate_synthetic_data.py --manifest", args.output)


if __name__ == "__main__":
    main()
