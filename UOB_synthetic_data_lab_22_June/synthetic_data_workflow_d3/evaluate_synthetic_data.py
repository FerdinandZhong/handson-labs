#!/usr/bin/env python3
"""
Reference evaluator produced by the Direction 3 (code-generation) synthetic data
workflow. Validates generated CSVs against the schema manifest and produces a
fidelity scorecard, a referential-integrity verdict, and a PII-leakage scan.

Run:
    python evaluate_synthetic_data.py \
        --manifest schema_manifest.sample.json \
        --synthetic ./synthetic_output \
        --report ./eval_report.md

Dependencies:
    pip install pandas numpy scipy
    # Optional rich HTML profile report:
    #   pip install ydata-profiling

Checks per table:
  - Schema fidelity      : all manifest columns present, types parseable.
  - Distribution fidelity: numeric mean within 20% of profiled avg;
                           top categorical values overlap the profiled top values.
  - Null-rate fidelity   : per-column null% within 20 points of profiled null_rate.
  - Referential integrity: every child FK value exists in the parent key pool.
  - PII leakage          : regex scan for SG NRIC / phone / email patterns.

A table fails overall if any single check fails. Scores 0-100 per table; the
dataset is ML-ready only if all tables pass.
"""

import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# SG personal-data leakage patterns.
NRIC_RE = re.compile(r"\b[STFG]\d{7}[A-Z]\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# SG mobile/landline: a standalone 8-digit number (optionally +65 / 65 with a
# separator). The separator is required on the prefix so we do not flag longer
# synthetic numeric strings (e.g. 10-digit account numbers) as phone numbers.
SG_PHONE_RE = re.compile(r"\b(?:\+65[\s-]?|65[\s-])?[689]\d{7}\b")

# Manifest roles that are deliberately synthetic surrogates — never real PII, so
# they are excluded from the leakage scan to avoid false positives.
SYNTHETIC_SURROGATE_ROLES = {"cif_id", "account_no", "txn_id"}


def _load_csv(path: str) -> Optional[pd.DataFrame]:
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, dtype=str, keep_default_na=True)


def check_schema(df: pd.DataFrame, columns: List[Dict[str, Any]],
                 table: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    expected = {c["name"] for c in columns}
    actual = set(df.columns)
    missing = sorted(expected - actual)
    if missing:
        return {"pass": False, "partial": False, "missing_columns": missing}

    # Wide table: only columns_to_populate required for PASS; full list = PARTIAL ok
    wide = next((w for w in manifest.get("wide_tables", []) if w.get("table") == table), None)
    if wide:
        ctp = wide.get("columns_to_populate", [])
        if isinstance(ctp, list) and ctp:
            must_have = set(ctp)
            missing_pop = sorted(must_have - actual)
            if missing_pop:
                return {"pass": False, "partial": False, "missing_columns": missing_pop}
            defaulted = len(expected - must_have)
            if defaulted > 0:
                return {"pass": True, "partial": True,
                        "note": f"{len(must_have)} populated / {defaulted} defaulted (wide table)"}
    return {"pass": True, "partial": False, "missing_columns": []}


def check_distribution(df: pd.DataFrame, columns: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues: List[str] = []
    for col in columns:
        name = col["name"]
        if name not in df.columns:
            continue
        if col.get("avg") is not None:
            numeric = pd.to_numeric(df[name], errors="coerce").dropna()
            if len(numeric) >= 500:
                gen_mean = float(numeric.mean())
                ref = float(col["avg"])
                if ref and abs(gen_mean - ref) / abs(ref) > 0.20:
                    issues.append(f"{name}: mean {gen_mean:.1f} vs profiled {ref:.1f} (>20%)")
        elif col.get("top_values"):
            gen_top = set(df[name].dropna().value_counts().head(3).index.tolist())
            ref_top = set(map(str, col["top_values"][:3]))
            if gen_top and not (gen_top & ref_top):
                issues.append(f"{name}: top values {gen_top} disjoint from profiled {ref_top}")
    return {"pass": not issues, "partial": False, "issues": issues}


def check_distribution_scipy(df: pd.DataFrame, columns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Optional scipy-enhanced distribution sanity checks."""
    try:
        from scipy import stats  # noqa: F401
    except ImportError:
        return {"pass": True, "issues": [], "skipped": "scipy not installed"}

    issues: List[str] = []
    for col in columns:
        name = col["name"]
        if name not in df.columns:
            continue
        if col.get("avg") is not None:
            numeric = pd.to_numeric(df[name], errors="coerce").dropna()
            if len(numeric) >= 8 and numeric.nunique() <= 1 and col.get("max") != col.get("min"):
                issues.append(f"{name}: constant numeric despite profiled range")
        elif col.get("top_values") and len(col["top_values"]) >= 2:
            observed = df[name].dropna().value_counts()
            if len(observed) >= 2:
                ref = col["top_values"][: min(5, len(col["top_values"]))]
                gen_top = set(observed.head(5).index.astype(str))
                if not (gen_top & set(map(str, ref))):
                    issues.append(f"{name}: no overlap with profiled top values")
    return {"pass": not issues, "issues": issues}


def check_null_rate(df: pd.DataFrame, columns: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues: List[str] = []
    n = max(len(df), 1)
    for col in columns:
        name = col["name"]
        if name not in df.columns or col.get("null_rate") is None:
            continue
        gen_null = df[name].isna().mean()
        if abs(gen_null - float(col["null_rate"])) > 0.20:
            issues.append(f"{name}: null% {gen_null:.2f} vs profiled {col['null_rate']:.2f}")
    return {"pass": not issues, "issues": issues}


def check_pii(df: pd.DataFrame, columns: List[Dict[str, Any]]) -> Dict[str, Any]:
    hits: List[str] = []
    skip = {c["name"] for c in columns
            if (c.get("role") or "").lower() in SYNTHETIC_SURROGATE_ROLES}
    for col in df.columns:
        if col in skip:
            continue
        series = df[col].dropna().astype(str)
        sample = series.head(2000)
        for value in sample:
            if NRIC_RE.search(value) or EMAIL_RE.search(value) or SG_PHONE_RE.search(value):
                hits.append(f"{col}: '{value}'")
                break
    return {"pass": not hits, "hits": hits[:10]}


def check_fk(child_df: pd.DataFrame, child_col: str,
             parent_df: pd.DataFrame, parent_col: str) -> Dict[str, Any]:
    if child_col not in child_df.columns or parent_col not in parent_df.columns:
        return {"pass": False, "orphans": -1, "note": "FK column missing"}
    pool = set(parent_df[parent_col].dropna().astype(str))
    child_vals = child_df[child_col].dropna().astype(str)
    orphans = int((~child_vals.isin(pool)).sum())
    return {"pass": orphans == 0, "orphans": orphans}


def score_table(checks: Dict[str, Dict[str, Any]]) -> int:
    weights = {"schema": 30, "distribution": 25, "null_rate": 15, "pii": 20, "fk": 10}
    score = 0
    for key, weight in weights.items():
        if key not in checks:
            score += weight  # not applicable -> full credit
        elif checks[key].get("pass"):
            score += weight
    return score


def run(manifest_path: str, synthetic_dir: str, report_path: str,
        use_scipy: bool = False, only_tables: Optional[List[str]] = None) -> bool:
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    tables = manifest.get("tables", {})
    if only_tables:
        tables = {k: v for k, v in tables.items() if k in only_tables}
    relationships = manifest.get("relationships", [])
    loaded: Dict[str, pd.DataFrame] = {}

    for table in tables:
        df = _load_csv(os.path.join(synthetic_dir, f"{table}_synthetic.csv"))
        if df is not None:
            loaded[table] = df

    lines: List[str] = ["# Synthetic Data Evaluation Report", ""]
    lines.append(f"- Manifest: `{manifest_path}`")
    lines.append(f"- Synthetic dir: `{synthetic_dir}`")
    lines.append(f"- Tables found: {len(loaded)} / {len(tables)}")
    lines.append("")
    lines.append("| Table | Score | Cols(gen/manifest) | Schema | Distrib | Null | PII | FK | Verdict |")
    lines.append("|---|---|---|---|---|---|---|---|---|")

    all_pass = True
    passed = 0

    for table, profile in tables.items():
        df = loaded.get(table)
        if df is None:
            lines.append(f"| {table} | 0 | - | MISSING | - | - | - | - | FAIL |")
            all_pass = False
            continue

        columns = profile.get("columns", [])
        col_coverage = f"{len(df.columns)}/{len(columns)}"
        schema_result = check_schema(df, columns, table, manifest)
        checks: Dict[str, Dict[str, Any]] = {
            "schema": schema_result,
            "distribution": check_distribution(df, columns),
            "null_rate": check_null_rate(df, columns),
            "pii": check_pii(df, columns),
        }
        if use_scipy:
            scipy_result = check_distribution_scipy(df, columns)
            if not scipy_result.get("pass"):
                checks["distribution"]["pass"] = False
                checks["distribution"]["issues"] = (
                    checks["distribution"].get("issues", []) + scipy_result.get("issues", [])
                )

        for rel in relationships:
            if rel["child_table"] == table and rel["parent_table"] in loaded:
                checks["fk"] = check_fk(df, rel["child_column"],
                                        loaded[rel["parent_table"]], rel["parent_column"])

        score = score_table(checks)
        hard_fail = any(
            not c.get("pass") for k, c in checks.items()
            if not (k == "schema" and c.get("partial"))
        )
        verdict = "PASS" if not hard_fail else "FAIL"
        if verdict == "PASS":
            passed += 1
        else:
            all_pass = False

        def mark(key: str) -> str:
            if key not in checks:
                return "n/a"
            c = checks[key]
            if key == "schema" and c.get("partial"):
                return "PARTIAL"
            return "PASS" if c.get("pass") else "FAIL"

        lines.append(
            f"| {table} | {score} | {col_coverage} | {mark('schema')} | {mark('distribution')} | "
            f"{mark('null_rate')} | {mark('pii')} | {mark('fk')} | {verdict} |"
        )

        for key, result in checks.items():
            detail = (result.get("issues") or result.get("hits")
                      or result.get("missing_columns") or result.get("note"))
            if detail:
                lines.append(f"  - {table} / {key}: {detail}")

    lines.append("")
    lines.append(f"**Overall:** {passed}/{len(tables)} tables passed. "
                 f"Dataset ready for ML training: **{'YES' if all_pass else 'NO'}**.")
    lines.append("")
    lines.append("Schema PARTIAL on wide tables (populated + NULL-defaulted columns) does not fail the table.")

    report = "\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(report_path)) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report + "\n")

    print(report)
    print(f"\nReport written to {report_path}")
    return all_pass


def main() -> None:
    import sys
    parser = argparse.ArgumentParser(description="Evaluate synthetic data fidelity, PII safety, and FK integrity.")
    parser.add_argument("--manifest", default="schema_manifest.sample.json", help="Path to schema_manifest.json")
    parser.add_argument("--synthetic", default="./synthetic_output", help="Directory containing generated CSVs")
    parser.add_argument("--report", default="./eval_report.md", help="Output report path (Markdown)")
    parser.add_argument("--tables", default="", help="Comma-separated subset to evaluate (default: all in manifest)")
    parser.add_argument("--use-scipy", action="store_true", help="Run additional scipy distribution checks")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with code 1 if any table FAILs (for CML Job signaling)")
    args = parser.parse_args()
    only = [t.strip() for t in args.tables.split(",") if t.strip()] or None
    ok = run(args.manifest, args.synthetic, args.report, use_scipy=args.use_scipy, only_tables=only)
    if args.strict and not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
