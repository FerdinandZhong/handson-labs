#!/usr/bin/env python3
"""
FastAPI wrapper for the D3 synthetic data pipeline.

Two execution modes:
  /pipeline/*  — deterministic subprocess mode (run_pipeline.py, no LLM)
  /agent/*     — agentic mode (synthetic_data_crew.py, CrewAI + LLM)

The agentic mode is database-agnostic: the LLM crew discovers the schema,
authors generation and evaluation scripts, then dispatches CML Jobs via
CmlJobTool. Use /pipeline/* when scripts are already generated and ready.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
DEFAULT_PIPELINE_DIR = APP_DIR.parent / "synthetic_data_workflow_d3"
PROJECT_ROOT = os.environ.get("CDSW_PROJECT_ROOT", "/home/cdsw")

app = FastAPI(title="Synthetic Data Pipeline", version="2.0.0")

_events: List[Dict[str, Any]] = []
_status: Dict[str, Any] = {"state": "idle", "last_command": None, "exit_code": None}
_lock = threading.Lock()

# Lazy import for crew module (avoids crewai import at startup if not needed)
_crew_module = None


def _get_crew_module():
    global _crew_module
    if _crew_module is None:
        try:
            import importlib
            import sys
            sys.path.insert(0, str(APP_DIR))
            _crew_module = importlib.import_module("synthetic_data_crew")
        except ImportError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Agentic mode unavailable: {exc}. Install crewai and crewai-tools.",
            )
    return _crew_module


class PipelineRequest(BaseModel):
    target_tables: str = Field(
        default="eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d",
    )
    rows: int = 1000
    seed: int = 42
    validate_fks: bool = True
    profile_stats: bool = True
    use_scipy: bool = True
    strict: bool = True
    batch_prefix: str = ""


class AgentPipelineRequest(BaseModel):
    target_database: str = Field(
        default="pf_usecase",
        description="Impala database name — any database the crew can DESCRIBE",
    )
    target_tables: str = Field(
        default="all",
        description="Comma-separated table names, or 'all'",
    )
    rows_per_table: int = 1000
    seed: int = 42
    output_scripts_dir: str = Field(
        default=f"{PROJECT_ROOT}/generated_scripts",
        description="Directory where the crew writes the generated Python scripts",
    )
    output_data_dir: str = Field(
        default=f"{PROJECT_ROOT}/synthetic_output",
        description="Directory for generated CSV files (used by CML Jobs)",
    )
    report_path: str = Field(
        default=f"{PROJECT_ROOT}/artifacts/eval_report.md",
        description="Path for the evaluation report",
    )
    manifest_path: str = Field(
        default="",
        description="Override path for schema_manifest.json (defaults to <output_scripts_dir>/schema_manifest.json)",
    )


def _pipeline_dir() -> Path:
    return Path(os.environ.get("PIPELINE_DIR", str(DEFAULT_PIPELINE_DIR)))


def _env_overrides(req: Optional[PipelineRequest] = None) -> Dict[str, str]:
    env = os.environ.copy()
    env.setdefault("MANIFEST_PATH", f"{PROJECT_ROOT}/artifacts/schema_manifest.json")
    env.setdefault("OUTPUT_DIR", f"{PROJECT_ROOT}/artifacts/synthetic_output")
    env.setdefault("REPORT_PATH", f"{PROJECT_ROOT}/artifacts/eval_report.md")
    env.setdefault("IMPALA_DB", "pf_usecase")
    if req:
        env["TARGET_TABLES"] = req.target_tables
        env["ROWS"] = str(req.rows)
        env["SEED"] = str(req.seed)
    return env


def _emit(event_type: str, message: str, **extra: Any) -> None:
    with _lock:
        _events.append({
            "id": str(uuid.uuid4()),
            "ts": time.time(),
            "type": event_type,
            "message": message,
            **extra,
        })


def _run_pipeline_command(command: str, req: Optional[PipelineRequest] = None) -> int:
    pipeline = _pipeline_dir()
    script = pipeline / "run_pipeline.py"
    if not script.is_file():
        raise HTTPException(status_code=500, detail=f"Pipeline not found: {script}")

    args = [sys.executable, str(script), command]
    if req:
        if req.validate_fks and command in ("scan", "all"):
            args.append("--validate-fks")
        if req.profile_stats and command in ("scan", "all"):
            args.append("--profile-stats")
        if req.use_scipy and command in ("evaluate", "all"):
            args.append("--use-scipy")
        if req.strict and command in ("evaluate", "all"):
            args.append("--strict")
        if req.batch_prefix and command == "generate":
            args.extend(["--batch-prefix", req.batch_prefix])

    env = _env_overrides(req)
    _emit("start", f"Running: {' '.join(args)}", command=command)

    proc = subprocess.Popen(
        args, cwd=str(pipeline), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            _emit("log", line, command=command)
    proc.wait()
    _emit("done", f"Exit code {proc.returncode}", command=command, exit_code=proc.returncode)
    return proc.returncode or 0


def _run_async(command: str, req: PipelineRequest) -> str:
    run_id = str(uuid.uuid4())

    def _worker() -> None:
        with _lock:
            _status.update({"state": "running", "last_command": command, "run_id": run_id})
        rc = _run_pipeline_command(command, req)
        with _lock:
            _status.update({"state": "idle", "exit_code": rc})

    threading.Thread(target=_worker, daemon=True).start()
    return run_id


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    static = APP_DIR / "static" / "index.html"
    if static.is_file():
        return HTMLResponse(static.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Synthetic Data Pipeline API</h1><p>See /docs</p>")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "pipeline_dir": str(_pipeline_dir())}


@app.get("/pipeline/status")
def pipeline_status() -> Dict[str, Any]:
    with _lock:
        return dict(_status)


@app.get("/api/workflow/events")
def workflow_events(since: float = 0) -> Dict[str, Any]:
    with _lock:
        filtered = [e for e in _events if e["ts"] >= since]
    return {"events": filtered}


@app.post("/pipeline/scan")
def pipeline_scan(req: PipelineRequest) -> Dict[str, Any]:
    rc = _run_pipeline_command("scan", req)
    if rc != 0:
        raise HTTPException(status_code=500, detail=f"scan failed with exit code {rc}")
    return {"status": "ok", "manifest": os.environ.get("MANIFEST_PATH", f"{PROJECT_ROOT}/artifacts/schema_manifest.json")}


@app.post("/pipeline/generate")
def pipeline_generate(req: PipelineRequest) -> Dict[str, Any]:
    rc = _run_pipeline_command("generate", req)
    if rc != 0:
        raise HTTPException(status_code=500, detail=f"generate failed with exit code {rc}")
    return {"status": "ok", "output_dir": os.environ.get("OUTPUT_DIR", f"{PROJECT_ROOT}/artifacts/synthetic_output")}


@app.post("/pipeline/evaluate")
def pipeline_evaluate(req: PipelineRequest) -> Dict[str, Any]:
    rc = _run_pipeline_command("evaluate", req)
    if rc != 0:
        raise HTTPException(status_code=500, detail=f"evaluate failed with exit code {rc}")
    return {"status": "ok", "report": os.environ.get("REPORT_PATH", f"{PROJECT_ROOT}/artifacts/eval_report.md")}


@app.post("/pipeline/all")
def pipeline_all(req: PipelineRequest) -> Dict[str, Any]:
    rc = _run_pipeline_command("all", req)
    if rc != 0:
        raise HTTPException(status_code=500, detail=f"pipeline failed with exit code {rc}")
    return {
        "status": "ok",
        "manifest": os.environ.get("MANIFEST_PATH"),
        "output_dir": os.environ.get("OUTPUT_DIR"),
        "report": os.environ.get("REPORT_PATH"),
    }


@app.post("/pipeline/all/async")
def pipeline_all_async(req: PipelineRequest) -> Dict[str, str]:
    run_id = _run_async("all", req)
    return {"run_id": run_id, "status": "started"}


@app.get("/artifacts/report")
def get_report() -> FileResponse:
    path = os.environ.get("REPORT_PATH", f"{PROJECT_ROOT}/artifacts/eval_report.md")
    pipeline = _pipeline_dir()
    full = (pipeline / path).resolve() if not os.path.isabs(path) else Path(path)
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Report not found — run pipeline first")
    return FileResponse(full, media_type="text/markdown", filename=full.name)


# ---------------------------------------------------------------------------
# Agentic pipeline endpoints (/agent/*)
# ---------------------------------------------------------------------------

@app.post("/agent/kickoff")
def agent_kickoff(req: AgentPipelineRequest) -> Dict[str, str]:
    """
    Start the agentic D3 pipeline in a background thread.
    The crew will:
      1. Scan the target database schema via Impala
      2. Plan generation and evaluation strategies
      3. Write Python scripts to output_scripts_dir
      4. Verify scripts and dispatch CML Jobs if CAI_WORKBENCH_* vars are set
    Returns run_id for polling /agent/events and /agent/status.
    """
    crew_mod = _get_crew_module()
    inputs: Dict[str, Any] = {
        "target_database": req.target_database,
        "target_tables": req.target_tables,
        "rows_per_table": req.rows_per_table,
        "seed": req.seed,
        "output_scripts_dir": req.output_scripts_dir,
        "output_data_dir": req.output_data_dir,
        "report_path": req.report_path,
    }
    if req.manifest_path:
        inputs["manifest_path"] = req.manifest_path
    run_id = crew_mod.run_crew_async(inputs)
    return {"run_id": run_id, "status": "started"}


@app.post("/agent/kickoff/sync")
def agent_kickoff_sync(req: AgentPipelineRequest) -> Dict[str, Any]:
    """Synchronous agent run — blocks until the crew completes. Suitable for short runs."""
    crew_mod = _get_crew_module()
    inputs: Dict[str, Any] = {
        "target_database": req.target_database,
        "target_tables": req.target_tables,
        "rows_per_table": req.rows_per_table,
        "seed": req.seed,
        "output_scripts_dir": req.output_scripts_dir,
        "output_data_dir": req.output_data_dir,
        "report_path": req.report_path,
    }
    if req.manifest_path:
        inputs["manifest_path"] = req.manifest_path
    result = crew_mod.run_crew(inputs)
    return {"status": "completed", "result": result[:2000]}


@app.get("/agent/status")
def agent_status() -> Dict[str, Any]:
    """Return current crew state: idle | running, last event, run_id."""
    crew_mod = _get_crew_module()
    return crew_mod.get_crew_status()


@app.get("/agent/events")
def agent_events(since: float = 0) -> Dict[str, Any]:
    """Return crew event log entries since the given timestamp."""
    crew_mod = _get_crew_module()
    return {"events": crew_mod.get_crew_events(since)}


static_dir = APP_DIR / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
