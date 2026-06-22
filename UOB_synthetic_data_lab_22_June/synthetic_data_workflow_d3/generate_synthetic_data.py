#!/usr/bin/env python3
"""
Reference generator produced by the Direction 3 (code-generation) synthetic data
workflow. Reads a schema_manifest.json (written by the Schema & Relationship Scan
task) and emits one referentially-consistent, PII-free CSV per table.

Run:
    python generate_synthetic_data.py \
        --manifest schema_manifest.sample.json \
        --rows 1000 --output ./synthetic_output --seed 42

Dependencies:
    pip install faker pandas numpy
    # Production upgrade path for higher-fidelity distributions / time-series:
    #   pip install sdv   (SDV SingleTablePreset for masters, PARSynthesizer for txns)

Design:
  1. Load schema profile + relationship map from the manifest.
  2. For each table in GENERATION_ORDER (parents before children):
       a. Generate columns per type/role rules (PII -> synthetic surrogates).
       b. Enforce FK columns by sampling from already-generated parent key pools.
  3. Write each table to <output>/<table>_synthetic.csv.

No real data is ever read here: generation is driven purely by aggregated statistics
in the manifest, with a fixed seed for reproducibility.

Full-schema / wide-table parity:
  The output has column parity with the source table when the manifest lists every
  column (name + type + nullable) for that table. Every column in a table's `columns`
  list is emitted to the CSV. A table may optionally appear in the manifest's
  `wide_tables` list with `columns_to_populate` to control which columns are actively
  synthesised vs filled with type-valid NULL/default:

      "wide_tables": [
        {"table": "eda_rbk_tltx_d", "total_columns": 896,
         "columns_to_populate": ["txn_id", "acct_no", "txn_amt", ...]}
      ]

  - `columns_to_populate` as a list of names: those columns are synthesised; all other
    columns listed for the table are filled with NULL (nullable) or a type default.
  - `columns_to_populate` as an integer N: the first N columns (manifest order) are
    synthesised; the rest are defaulted.
  - omitted: every column is synthesised.

  For true column parity, Task 1 must emit the FULL column list per table (all 896 for
  eda_rbk_tltx_d), not a subset. This script generates exactly the columns it is given.
"""

import argparse
import json
import os
import random
import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from faker import Faker
except ImportError:  # pragma: no cover - faker is a hard dependency at run time
    Faker = None

# Optional SDV upgrade (Phase 3): pip install sdv
_SDV_AVAILABLE = False
try:
    from sdv.single_table import SingleTablePreset  # type: ignore  # noqa: F401
    from sdv.sequential import PARSynthesizer  # type: ignore  # noqa: F401
    _SDV_AVAILABLE = True
except ImportError:
    pass


# --------------------------------------------------------------------------- #
# Per-column generation primitives
# --------------------------------------------------------------------------- #

def _gen_cif_ids(n: int) -> List[str]:
    return [f"SYN-CIF-{i:08d}" for i in range(1, n + 1)]


def _gen_account_numbers(n: int, rng: random.Random) -> List[str]:
    """Unique random 10-digit numeric strings."""
    pool = set()
    while len(pool) < n:
        pool.add("".join(str(rng.randint(0, 9)) for _ in range(10)))
    return list(pool)


def _gen_names(n: int, faker: Optional[Any], rng: random.Random) -> List[str]:
    if faker is not None:
        suffixes = ["Pte Ltd", "Holdings", "Enterprises", "Trading", "Capital"]
        return [f"{faker.last_name()} {rng.choice(suffixes)}" for _ in range(n)]
    stems = ["Sunrise", "Harbour", "Orchard", "Marina", "Sentosa", "Jurong"]
    suffixes = ["Holdings Pte Ltd", "Trading Co", "Capital", "Enterprises"]
    return [f"{rng.choice(stems)} {rng.choice(suffixes)}" for _ in range(n)]


def _gen_categorical(n: int, top_values: List[str], rng: random.Random) -> List[str]:
    # Zipf-ish weighting so earlier (more frequent) values dominate, like real data.
    weights = [1.0 / (i + 1) for i in range(len(top_values))]
    total = sum(weights)
    weights = [w / total for w in weights]
    return list(np.random.choice(top_values, size=n, p=weights))


def _gen_amounts(n: int, lo: float, hi: float, avg: Optional[float]) -> List[float]:
    """Log-normal values clipped into the observed [lo, hi] range."""
    lo = float(lo or 0.0)
    hi = float(hi if hi is not None else max(lo + 1.0, 1.0))
    target_mean = float(avg) if avg else (lo + hi) / 4.0
    target_mean = max(target_mean, 1.0)
    sigma = 0.9
    mu = np.log(target_mean) - (sigma ** 2) / 2.0
    vals = np.random.lognormal(mean=mu, sigma=sigma, size=n)
    vals = np.clip(vals, lo, hi)
    return [round(float(v), 2) for v in vals]


def _gen_timestamps(n: int, min_dt: str, max_dt: str) -> List[str]:
    start = pd.Timestamp(min_dt or "2015-01-01")
    end = pd.Timestamp(max_dt or "2024-12-31")
    span = max((end - start).days, 1)
    offsets = np.random.randint(0, span + 1, size=n)
    return [(start + pd.Timedelta(days=int(o))).strftime("%Y-%m-%d") for o in offsets]


def _apply_null_rate(values: List[Any], null_rate: float, rng: random.Random) -> List[Any]:
    if not null_rate:
        return values
    return [None if rng.random() < null_rate else v for v in values]


# --------------------------------------------------------------------------- #
# Table generation
# --------------------------------------------------------------------------- #

def generate_column(col: Dict[str, Any], n: int, faker: Optional[Any],
                    rng: random.Random) -> List[Any]:
    name = col.get("name", "")
    ctype = (col.get("type") or "string").lower()
    role = (col.get("role") or "").lower()
    lname = name.lower()
    null_rate = float(col.get("null_rate") or 0.0)

    if role == "cif_id" or "cif" in lname:
        return _gen_cif_ids(n)
    if role == "account_no" or "acct_no" in lname or "account" in lname:
        return _gen_account_numbers(n, rng)
    if role == "txn_id" or lname.endswith("txn_id") or lname == "txn_id":
        return [f"SYN-TXN-{i:010d}" for i in range(1, n + 1)]
    if col.get("pii_risk") and ctype == "string" and not col.get("top_values"):
        return _apply_null_rate(_gen_names(n, faker, rng), null_rate, rng)
    if col.get("top_values"):
        return _apply_null_rate(_gen_categorical(n, col["top_values"], rng), null_rate, rng)
    if ctype in ("decimal", "double", "float", "int", "bigint"):
        vals = _gen_amounts(n, col.get("min", 0.0), col.get("max", 1000.0), col.get("avg"))
        return _apply_null_rate(vals, null_rate, rng)
    if ctype in ("timestamp", "date"):
        vals = _gen_timestamps(n, col.get("min"), col.get("max"))
        return _apply_null_rate(vals, null_rate, rng)

    # Generic fallback string code.
    vals = [f"{name[:3].upper()}-{rng.randint(1000, 9999)}" for _ in range(n)]
    return _apply_null_rate(vals, null_rate, rng)


_NUMERIC_TYPES = ("decimal", "double", "float", "int", "bigint", "smallint", "tinyint")


def _default_value(col: Dict[str, Any]) -> Any:
    """Type-valid placeholder for a column that is present but not actively populated.

    Nullable columns get NULL; non-nullable columns get a benign type default so the
    column stays type-valid for downstream loads.
    """
    if col.get("nullable", True):
        return None
    ctype = (col.get("type") or "string").lower()
    if ctype in _NUMERIC_TYPES:
        return 0
    if ctype in ("timestamp", "date"):
        return "1970-01-01"
    if ctype == "boolean":
        return False
    return "NA"


def _resolve_populate_columns(table: str, manifest: Dict[str, Any],
                              all_names: List[str]) -> set:
    """Which columns to actively synthesise for this table.

    Driven by the manifest `wide_tables` entry. Returns the full set when the table is
    not listed (i.e. populate everything).
    """
    for entry in manifest.get("wide_tables", []):
        if entry.get("table") != table:
            continue
        ctp = entry.get("columns_to_populate")
        if isinstance(ctp, list) and ctp:
            return {name for name in ctp if name in all_names}
        if isinstance(ctp, int) and ctp > 0:
            return set(all_names[:ctp])
    return set(all_names)


def generate_table(table: str, profile: Dict[str, Any], n_rows: int,
                   faker: Optional[Any], rng: random.Random,
                   table_type: str, populate_cols: Optional[set] = None) -> pd.DataFrame:
    columns = profile.get("columns", [])
    # Lookup tables are small: cap to the number of known categories or 200.
    if table_type == "lookup":
        cat_col = next((c for c in columns if c.get("top_values")), None)
        n_rows = min(n_rows, len(cat_col["top_values"]) if cat_col else 200)

    data: Dict[str, List[Any]] = {}
    for col in columns:
        name = col["name"]
        if populate_cols is None or name in populate_cols:
            data[name] = generate_column(col, n_rows, faker, rng)
        else:
            # Present for schema parity, but filled with type-valid NULL/default.
            data[name] = [_default_value(col)] * n_rows
    return pd.DataFrame(data)


def enforce_fk(child_df: pd.DataFrame, child_col: str,
               parent_df: pd.DataFrame, parent_col: str,
               rng: random.Random) -> pd.DataFrame:
    """Replace child FK values with samples from the parent key pool (with replacement)."""
    pool = parent_df[parent_col].dropna().unique().tolist()
    if not pool:
        return child_df
    child_df[child_col] = [rng.choice(pool) for _ in range(len(child_df))]
    return child_df


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def run(manifest_path: str, rows: int, output_dir: str, seed: int,
        only_tables: Optional[List[str]], batch_prefix: str = "") -> None:
    rng = random.Random(seed)
    np.random.seed(seed)
    faker = None
    if Faker is not None:
        # Prefer an SG-realistic locale; fall back if the installed faker lacks it.
        for locale in ("en_SG", "en_US"):
            try:
                faker = Faker(locale)
                break
            except AttributeError:
                continue
        if faker is not None:
            Faker.seed(seed)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    os.makedirs(output_dir, exist_ok=True)
    tables = manifest.get("tables", {})
    order = manifest.get("generation_order", [])
    relationships = manifest.get("relationships", [])

    generated: Dict[str, pd.DataFrame] = {}

    for entry in order:
        table = entry["table"]
        if batch_prefix and not table.startswith(batch_prefix):
            continue
        if only_tables and table not in only_tables:
            continue
        if table not in tables:
            print(f"  [skip] {table}: not in manifest tables")
            continue

        t0 = time.monotonic()
        all_names = [c["name"] for c in tables[table].get("columns", [])]
        populate_cols = _resolve_populate_columns(table, manifest, all_names)
        df = generate_table(table, tables[table], rows, faker, rng,
                            entry.get("type", "child"), populate_cols)

        # Enforce every FK whose child is this table and whose parent is already built.
        for rel in relationships:
            if rel["child_table"] != table:
                continue
            parent = rel["parent_table"]
            if parent in generated and rel["child_column"] in df.columns:
                df = enforce_fk(df, rel["child_column"], generated[parent],
                                rel["parent_column"], rng)

        generated[table] = df
        out_path = os.path.join(output_dir, f"{table}_synthetic.csv")
        df.to_csv(out_path, index=False)
        elapsed = int((time.monotonic() - t0) * 1000)
        defaulted = len(all_names) - len(populate_cols)
        fill_note = f" ({len(populate_cols)} populated / {defaulted} defaulted)" if defaulted else ""
        print(f"  [ok] {table:<28} {len(df):>6} rows x {len(df.columns)} cols{fill_note}  "
              f"({elapsed} ms) -> {out_path}")

    print(f"\nDone. {len(generated)} table(s) written to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PII-free synthetic data from a schema manifest.")
    parser.add_argument("--manifest", default="schema_manifest.sample.json",
                        help="Path to schema_manifest.json")
    parser.add_argument("--rows", type=int, default=1000, help="Rows per table (lookup tables auto-capped)")
    parser.add_argument("--output", default="./synthetic_output", help="Output directory for CSVs")
    parser.add_argument("--tables", default="", help="Comma-separated subset of tables (default: all)")
    parser.add_argument("--batch-prefix", default="",
                        help="Only generate tables whose names start with this prefix (e.g. eda_bwc_)")
    parser.add_argument("--use-sdv", action="store_true",
                        help="Use SDV when installed (SingleTablePreset / PARSynthesizer)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    if args.use_sdv and not _SDV_AVAILABLE:
        print("Warning: --use-sdv requested but sdv is not installed; using faker/numpy path")

    only = [t.strip() for t in args.tables.split(",") if t.strip()] or None

    print("=" * 64)
    print("  Synthetic Data Generator (Direction 3 reference script)")
    if _SDV_AVAILABLE:
        print("  SDV: available (pass --use-sdv to enable when strategy_map is wired)")
    print("=" * 64)
    run(args.manifest, args.rows, args.output, args.seed, only, args.batch_prefix)


if __name__ == "__main__":
    main()
