#!/usr/bin/env python3
"""
Impyla connection test for CDP Impala (Knox gateway, HTTP + SSL + PLAIN auth).

Checks:
  1. impyla import
  2. Connect + open session
  3. SELECT 1
  4. USE <database>
  5. SHOW TABLES
  6. Optional row/column spot-check on --tables

Usage:
    export IMPALA_HOST=hue-impala-gateway.example.cloudera.site
    export IMPALA_USER=myuser
    export IMPALA_PASS='mypassword'
    export IMPALA_DB=pf_usecase

    python test_impala_connection.py

    python test_impala_connection.py \\
        --host hue-impala-gateway.datalake.bdqdgc.c0.cloudera.site \\
        --user qishuai --password '...' --database pf_usecase \\
        --tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg

Dependencies:
    pip install impyla thrift-sasl
"""

from __future__ import annotations

import argparse
import os
import sys
import time


def _ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def _info(msg: str) -> None:
    print(f"         {msg}")


def connect(host: str, port: int, user: str, password: str):
    from impala.dbapi import connect

    return connect(
        host=host,
        port=port,
        use_ssl=True,
        use_http_transport=True,
        http_path="cliservice",
        auth_mechanism="PLAIN",
        user=user,
        password=password,
    )


def run(host: str, port: int, user: str, password: str, database: str,
        tables: list[str], list_all_tables: bool) -> int:
    print("=" * 60)
    print("  Impyla — Impala CDW connection test")
    print("=" * 60)

    print("\n[1] Config")
    _info(f"Host : {host}:{port}")
    _info(f"User : {user}")
    _info(f"Pass : {'*' * len(password) if password else '(not set)'}")
    _info(f"DB   : {database}")
    _info("SSL  : yes   Transport: HTTP   Auth: PLAIN")

    print("\n[2] Package")
    try:
        import impala  # noqa: F401
        _ok(f"impyla installed (impala=={impala.__version__})")
    except ImportError as exc:
        _fail(f"impyla not installed: {exc}")
        _info("Run: pip install impyla thrift-sasl")
        return 1

    print("\n[3] Connect")
    try:
        t0 = time.monotonic()
        conn = connect(host, port, user, password)
        ms = int((time.monotonic() - t0) * 1000)
        _ok(f"Session opened ({ms} ms)")
    except Exception as exc:
        _fail(f"Connection failed: {exc}")
        return 1

    cur = conn.cursor()
    failed = False

    print("\n[4] Ping")
    try:
        t0 = time.monotonic()
        cur.execute("SELECT 1")
        row = cur.fetchone()
        ms = int((time.monotonic() - t0) * 1000)
        _ok(f"SELECT 1 → {row[0]}  ({ms} ms)")
    except Exception as exc:
        _fail(f"Ping failed: {exc}")
        failed = True

    print(f"\n[5] USE {database}")
    try:
        cur.execute(f"USE {database}")
        _ok(f"Switched to {database}")
    except Exception as exc:
        _fail(f"USE failed: {exc}")
        cur.close()
        conn.close()
        return 1

    print("\n[6] SHOW TABLES")
    all_tables: list[str] = []
    try:
        t0 = time.monotonic()
        cur.execute("SHOW TABLES")
        all_tables = [r[0] for r in cur.fetchall()]
        ms = int((time.monotonic() - t0) * 1000)
        _ok(f"{len(all_tables)} table(s)  ({ms} ms)")
        show = all_tables if list_all_tables else all_tables[:20]
        for name in show:
            _info(name)
        if not list_all_tables and len(all_tables) > 20:
            _info(f"... and {len(all_tables) - 20} more (use --list-all-tables)")
    except Exception as exc:
        _fail(f"SHOW TABLES failed: {exc}")
        failed = True

    if tables:
        print("\n[7] Table spot-check")
        table_set = set(all_tables)
        for table in tables:
            if table not in table_set:
                _fail(f"{table}: not found in {database}")
                failed = True
                continue
            try:
                t0 = time.monotonic()
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                rows = cur.fetchone()[0]
                cur.execute(f"DESCRIBE {table}")
                cols = len([r for r in cur.fetchall() if r[0] and not str(r[0]).startswith("#")])
                ms = int((time.monotonic() - t0) * 1000)
                _ok(f"{table:<35} {rows:>8,} rows  {cols:>4} cols  ({ms} ms)")
            except Exception as exc:
                _fail(f"{table}: {exc}")
                failed = True

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    if failed:
        print("  Done — one or more checks failed.")
        print("=" * 60)
        return 1
    print("  Done — all checks passed.")
    print("=" * 60)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Test impyla connection to Impala CDW")
    parser.add_argument("--host", default=os.getenv("IMPALA_HOST", ""))
    parser.add_argument("--port", type=int, default=int(os.getenv("IMPALA_PORT", "443")))
    parser.add_argument("--user", default=os.getenv("IMPALA_USER", ""))
    parser.add_argument("--password", default=os.getenv("IMPALA_PASS", os.getenv("IMPALA_PASSWORD", "")))
    parser.add_argument("--database", "--db", dest="database",
                        default=os.getenv("IMPALA_DB", "pf_usecase"))
    parser.add_argument("--tables", default="",
                        help="Comma-separated tables to COUNT/DESCRIBE spot-check")
    parser.add_argument("--list-all-tables", action="store_true",
                        help="Print every table from SHOW TABLES (default: first 20)")
    args = parser.parse_args()

    if not args.host:
        print("Error: --host or IMPALA_HOST is required", file=sys.stderr)
        sys.exit(1)
    if not args.user:
        print("Error: --user or IMPALA_USER is required", file=sys.stderr)
        sys.exit(1)

    tables = [t.strip() for t in args.tables.split(",") if t.strip()]
    sys.exit(run(args.host, args.port, args.user, args.password,
                 args.database, tables, args.list_all_tables))


if __name__ == "__main__":
    main()
