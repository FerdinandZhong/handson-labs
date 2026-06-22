#!/usr/bin/env python3
"""
D3 synthetic data pipeline — single CLI for CML Jobs and local runs.

Subcommands:
  scan      Build schema_manifest.json (live Impala or describe text files)
  generate  Emit referentially-consistent CSVs from a manifest
  evaluate  Score synthetic output; non-zero exit on FAIL (--strict)
  all            scan → generate → evaluate in one Job
  batch-generate Run generate for each pf_usecase source-system prefix (73-table scale-out)

Examples:
  python run_pipeline.py all \\
    --target-tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d \\
    --rows 1000 --seed 42 \\
    --manifest ./artifacts/schema_manifest.json \\
    --output ./artifacts/synthetic_output \\
    --report ./artifacts/eval_report.md

  # Text-file scan (no live DB):
  python run_pipeline.py scan \\
    --describe-dir ./describe_dumps \\
    --manifest ./artifacts/schema_manifest.json

Environment variables (used when CLI flags omitted):
  IMPALA_HOST, IMPALA_USER, IMPALA_PASS, IMPALA_DB
  TARGET_TABLES, ROWS, SEED, MANIFEST_PATH, OUTPUT_DIR, REPORT_PATH
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# Source-system prefixes for parallel CML generate Jobs (full pf_usecase).
BATCH_PREFIXES = [
    "eda_bwc_", "eda_rbk_", "eda_rem_", "eda_amh_",
    "eda_brm_", "eda_pib_", "eda_rlp_", "eda_sss_",
]


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _run_script(script: str, args: list[str]) -> int:
    cmd = [sys.executable, str(SCRIPT_DIR / script), *args]
    print(f"\n>>> {' '.join(cmd)}\n")
    return subprocess.call(cmd)


def cmd_scan(ns: argparse.Namespace) -> int:
    args = ["--output", ns.manifest, "--database", ns.database,
            "--wide-threshold", str(ns.wide_threshold),
            "--populate-cols", str(ns.populate_cols)]
    if ns.validate_fks:
        args.append("--validate-fks")
    if ns.profile_stats:
        args.append("--profile-stats")

    tables = ns.target_tables or _env("TARGET_TABLES", "all")
    if ns.describe_dir:
        args.extend(["--describe-dir", ns.describe_dir])
    else:
        host = ns.host or _env("IMPALA_HOST")
        user = ns.user or _env("IMPALA_USER")
        password = ns.password or _env("IMPALA_PASS")
        if not host:
            print("Error: --host or IMPALA_HOST required for live scan", file=sys.stderr)
            return 1
        if not user or not password:
            print("Error: --user/--password or IMPALA_USER/IMPALA_PASS required", file=sys.stderr)
            return 1
        args.extend([
            "--host", host, "--user", user, "--password", password,
            "--tables", tables,
        ])
        if ns.port:
            args.extend(["--port", str(ns.port)])

    os.makedirs(os.path.dirname(os.path.abspath(ns.manifest)) or ".", exist_ok=True)
    return _run_script("describe_to_manifest.py", args)


def cmd_generate(ns: argparse.Namespace) -> int:
    os.makedirs(ns.output, exist_ok=True)
    args = [
        "--manifest", ns.manifest,
        "--rows", str(ns.rows),
        "--output", ns.output,
        "--seed", str(ns.seed),
    ]
    tables = ns.target_tables or _env("TARGET_TABLES")
    if tables:
        args.extend(["--tables", tables])
    if getattr(ns, "batch_prefix", ""):
        args.extend(["--batch-prefix", ns.batch_prefix])
    return _run_script("generate_synthetic_data.py", args)


def cmd_evaluate(ns: argparse.Namespace) -> int:
    os.makedirs(os.path.dirname(os.path.abspath(ns.report)) or ".", exist_ok=True)
    args = [
        "--manifest", ns.manifest,
        "--synthetic", ns.output,
        "--report", ns.report,
    ]
    if getattr(ns, "use_scipy", False):
        args.append("--use-scipy")
    if getattr(ns, "strict", False):
        args.append("--strict")
    tables = ns.target_tables or _env("TARGET_TABLES")
    if tables:
        args.extend(["--tables", tables])
    return _run_script("evaluate_synthetic_data.py", args)


def cmd_batch_generate(ns: argparse.Namespace) -> int:
    prefixes = [p.strip() for p in ns.batch_prefixes.split(",") if p.strip()] if ns.batch_prefixes else BATCH_PREFIXES
    last_rc = 0
    for prefix in prefixes:
        print(f"\n{'=' * 60}\n  Batch generate: {prefix}\n{'=' * 60}")
        ns.batch_prefix = prefix
        rc = cmd_generate(ns)
        if rc != 0:
            last_rc = rc
            if ns.fail_fast:
                return rc
    return last_rc


def cmd_all(ns: argparse.Namespace) -> int:
    rc = cmd_scan(ns)
    if rc != 0:
        return rc
    rc = cmd_generate(ns)
    if rc != 0:
        return rc
    return cmd_evaluate(ns)


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--manifest", default=_env("MANIFEST_PATH", "/home/cdsw/artifacts/schema_manifest.json"))
    p.add_argument("--output", default=_env("OUTPUT_DIR", "/home/cdsw/artifacts/synthetic_output"))
    p.add_argument("--report", default=_env("REPORT_PATH", "/home/cdsw/artifacts/eval_report.md"))
    p.add_argument("--database", default=_env("IMPALA_DB", "pf_usecase"))
    p.add_argument("--target-tables", default="",
                   help="Comma-separated tables (alias: --tables in scan)")
    p.add_argument("--rows", type=int, default=int(_env("ROWS", "1000") or "1000"))
    p.add_argument("--seed", type=int, default=int(_env("SEED", "42") or "42"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="D3 synthetic data pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Build schema manifest")
    _add_common(p_scan)
    p_scan.add_argument("--describe-dir", help="Directory of *.describe.txt files")
    p_scan.add_argument("--host", help="Impala host (live mode)")
    p_scan.add_argument("--port", type=int, default=443)
    p_scan.add_argument("--user", help="Impala workload user")
    p_scan.add_argument("--password", help="Impala workload password")
    p_scan.add_argument("--wide-threshold", type=int, default=200)
    p_scan.add_argument("--populate-cols", type=int, default=50)
    p_scan.add_argument("--validate-fks", action="store_true",
                        help="Validate inferred FKs with JOIN COUNT queries")
    p_scan.add_argument("--profile-stats", action="store_true",
                        help="Profile MIN/MAX/AVG and top-N on semantic columns")
    p_scan.set_defaults(func=cmd_scan)

    p_gen = sub.add_parser("generate", help="Generate synthetic CSVs")
    _add_common(p_gen)
    p_gen.add_argument("--batch-prefix", default="",
                       help="Only tables whose names start with this prefix (Phase 3 scale-out)")
    p_gen.set_defaults(func=cmd_generate)

    p_batch = sub.add_parser("batch-generate",
                             help="Generate by source-system prefix (parallel Job pattern)")
    _add_common(p_batch)
    p_batch.add_argument("--batch-prefixes", default="",
                         help=f"Comma-separated prefixes (default: {','.join(BATCH_PREFIXES)})")
    p_batch.add_argument("--fail-fast", action="store_true",
                         help="Stop on first prefix failure")
    p_batch.set_defaults(func=cmd_batch_generate)

    p_eval = sub.add_parser("evaluate", help="Evaluate synthetic output")
    _add_common(p_eval)
    p_eval.add_argument("--use-scipy", action="store_true", help="Run scipy KS/chi² checks")
    p_eval.add_argument("--strict", action="store_true",
                        help="Exit 1 if any table FAILs (for CML Job signaling)")
    p_eval.set_defaults(func=cmd_evaluate)

    p_all = sub.add_parser("all", help="scan → generate → evaluate")
    _add_common(p_all)
    p_all.add_argument("--describe-dir", help="Directory of *.describe.txt files")
    p_all.add_argument("--host", help="Impala host (live mode)")
    p_all.add_argument("--port", type=int, default=443)
    p_all.add_argument("--user")
    p_all.add_argument("--password")
    p_all.add_argument("--wide-threshold", type=int, default=200)
    p_all.add_argument("--populate-cols", type=int, default=50)
    p_all.add_argument("--validate-fks", action="store_true")
    p_all.add_argument("--profile-stats", action="store_true")
    p_all.add_argument("--batch-prefix", default="",
                       help="Only tables whose names start with this prefix")
    p_all.add_argument("--use-scipy", action="store_true")
    p_all.add_argument("--strict", action="store_true")
    p_all.set_defaults(func=cmd_all)

    return parser


def main() -> None:
    parser = build_parser()
    ns = parser.parse_args()
    rc = ns.func(ns)
    sys.exit(rc)


if __name__ == "__main__":
    main()
