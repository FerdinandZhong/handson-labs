#!/usr/bin/env python3
"""
CAI Application entry point — Synthetic Data Pipeline API.

Bootstraps dependencies and starts FastAPI via uvicorn in a background thread
(same pattern as nl_to_sql_agent/run_app.py — avoids Jupyter asyncio conflict).

Two modes served by synthetic_data_api.py:
  /pipeline/*  — deterministic subprocess mode (no LLM)
  /agent/*     — agentic mode (CrewAI + LLM, requires LLM_API_BASE_URL + LLM_API_KEY)
"""

import asyncio
import os
import subprocess
import sys
import threading


PROJECT_ROOT = "/home/cdsw"
DEFAULT_APP_DIR = f"{PROJECT_ROOT}/synthetic_data_app"
DEFAULT_PIPELINE_DIR = f"{PROJECT_ROOT}/synthetic_data_workflow_d3"


def _resolve_app_dir() -> str:
    """Locate synthetic_data_app/ — __file__ is undefined in CAI Jupyter kernels."""
    try:
        candidate = os.path.dirname(os.path.abspath(__file__))
        if os.path.isfile(os.path.join(candidate, "synthetic_data_api.py")):
            return candidate
    except NameError:
        pass

    for candidate in (
        os.environ.get("APP_DIR"),
        os.path.join(os.environ.get("CDSW_PROJECT_ROOT", PROJECT_ROOT), "synthetic_data_app"),
        DEFAULT_APP_DIR,
    ):
        if not candidate:
            continue
        path = os.path.abspath(candidate)
        if os.path.isfile(os.path.join(path, "synthetic_data_api.py")):
            return path

    raise RuntimeError(
        f"Could not locate synthetic_data_api.py under {DEFAULT_APP_DIR}. "
        "Sync synthetic_data_app/ into the project or set APP_DIR."
    )


def _pip_install(app_dir: str, *args: str) -> None:
    """Install packages without upgrading CAI runtime pins (see constraints-cai.txt)."""
    cmd = [sys.executable, "-m", "pip", "install", "-q", "--upgrade-strategy", "only-if-needed"]
    constraint = os.path.join(app_dir, "constraints-cai.txt")
    if os.path.isfile(constraint):
        cmd.extend(["-c", constraint])
    cmd.extend(args)
    subprocess.run(cmd, check=False)


def run_server() -> None:
    app_dir = _resolve_app_dir()
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    print("Installing dependencies...")
    req_file = os.path.join(app_dir, "requirements.txt")
    if os.path.isfile(req_file):
        _pip_install(app_dir, "-r", req_file)
    else:
        _pip_install(
            app_dir,
            "fastapi", "uvicorn[standard]", "requests",
            "crewai>=0.80.0", "crewai-tools",
            "impyla", "thrift-sasl",
        )

    # pydantic/crewai need typing_extensions>=4.13 (Sentinel); install without deps.
    _pip_install(app_dir, "--no-deps", "typing_extensions>=4.13")

    pipeline_dir = os.environ.get("PIPELINE_DIR", DEFAULT_PIPELINE_DIR)
    pipeline_req = os.path.join(pipeline_dir, "requirements.txt")
    if os.path.isfile(pipeline_req):
        _pip_install(app_dir, "-r", pipeline_req)

    print("Dependencies ready.")

    # Fix typing_extensions shadowing on PBJ runtime (same workaround as nl_to_sql)
    import site
    user_site = site.getusersitepackages()
    if user_site and os.path.isdir(user_site):
        if user_site in sys.path:
            sys.path.remove(user_site)
        sys.path.insert(0, user_site)

    for _name in list(sys.modules):
        if _name == "typing_extensions" or _name.startswith(("pydantic", "pydantic_core")):
            del sys.modules[_name]

    from synthetic_data_api import app  # noqa: E402
    import uvicorn

    host = os.environ.get("CDSW_APP_HOST", "127.0.0.1")
    port = int(os.environ.get("CDSW_APP_PORT", 8080))
    model = os.environ.get("LLM_MODEL") or os.environ.get("CAI_MODEL", "not configured")
    llm_base = (
        os.environ.get("LLM_API_BASE_URL")
        or os.environ.get("CAI_BASE_URL")
        or os.environ.get("CAI_URL", "not configured")
    )
    cwb_host = os.environ.get("CAI_WORKBENCH_HOST", "not configured")

    print("=" * 60)
    print("  Synthetic Data Pipeline — CAI Application")
    print("=" * 60)
    print(f"  App dir         : {app_dir}")
    print(f"  Host            : {host}:{port}")
    print(f"  Pipeline dir    : {pipeline_dir}")
    print(f"  LLM endpoint    : {llm_base}")
    print(f"  LLM model       : {model}")
    print(f"  Workbench host  : {cwb_host}")
    print(f"  Manifest        : {os.environ.get('MANIFEST_PATH', '/home/cdsw/artifacts/schema_manifest.json')}")
    print("-" * 60)
    print("  /pipeline/*  — deterministic subprocess mode")
    print("  /agent/*     — agentic CrewAI mode (requires LLM config)")
    print("=" * 60)

    config = uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)

    def _serve() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())

    thread = threading.Thread(target=_serve, daemon=False)
    thread.start()
    thread.join()


def main() -> None:
    run_server()


if __name__ == "__main__":
    main()
