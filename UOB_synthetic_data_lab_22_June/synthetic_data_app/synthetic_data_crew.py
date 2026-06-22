#!/usr/bin/env python3
"""
D3 Synthetic Data — Agentic pipeline (CrewAI).

Five agents handle schema analysis, generation strategy, evaluation strategy,
script authoring, and script verification. After the crew produces READY scripts,
After the crew produces READY scripts (timestamped per run, e.g.
generate_synthetic_data_20250621_193045.py), a CmlJobTool dispatches CML Jobs.

Architecture:
    FastAPI /agent/kickoff
        → run_crew_async() (background thread)
            → 5-agent sequential CrewAI crew
                → [Agent 1: Schema Scanner] ImpalaQueryTool
                → [Agent 2: Generation Strategist] (LLM only)
                → [Agent 3: Evaluation Strategist] (LLM only)
                → [Agent 4: Code Writer] WriteFileTool
                → [Agent 5: Script Verifier] ReadFileTool → CmlJobTool (if READY)

Requirements:
    pip install crewai crewai-tools fastapi uvicorn impyla thrift-sasl requests
"""

from __future__ import annotations

import json
import os
import time
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests
import urllib3
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Config — all values from env vars so the module is side-effect free
# ---------------------------------------------------------------------------

IMPALA_HOST = os.getenv("IMPALA_HOST", "")
IMPALA_PORT = int(os.getenv("IMPALA_PORT", "443"))
IMPALA_USER = os.getenv("IMPALA_USER", "")
IMPALA_PASS = os.getenv("IMPALA_PASS", "")
IMPALA_DB   = os.getenv("IMPALA_DB", "pf_usecase")

LLM_API_BASE_URL = (
    os.getenv("LLM_API_BASE_URL")
    or os.getenv("CAI_BASE_URL")
    or os.getenv("CAI_URL")
    or ""
)
LLM_MODEL = os.getenv("LLM_MODEL") or os.getenv("CAI_MODEL", "gpt-4o")

# CAI Workbench credentials for CmlJobTool — resolved at call time via _get_cml_credentials()

RUNTIME_IMAGE = (
    "docker.repository.cloudera.com/cloudera/cdsw/"
    "ml-runtime-pbj-jupyterlab-python3.11-standard:2026.04.1-b7"
)

try:
    _APP_DIR = Path(__file__).resolve().parent
except NameError:
    _APP_DIR = Path(os.environ.get("CDSW_PROJECT_ROOT", "/home/cdsw"))

DEFAULT_OUTPUT_SCRIPTS_DIR = os.environ.get(
    "OUTPUT_SCRIPTS_DIR", f"{os.environ.get('CDSW_PROJECT_ROOT', '/home/cdsw')}/generated_scripts"
)

PIPELINE_STAGES = [
    {"id": "scanner",    "label": "Schema Scanner",   "role_hint": "scanner"},
    {"id": "gen_strat",  "label": "Gen Strategist",   "role_hint": "generation strategist"},
    {"id": "eval_strat", "label": "Eval Strategist",  "role_hint": "evaluation strategist"},
    {"id": "writer",     "label": "Code Writer",      "role_hint": "script writer"},
    {"id": "verifier",   "label": "Verifier + Jobs",  "role_hint": "reviewer"},
]


def _detect_stage(agent_str: str) -> int:
    """Map an agent role string to its 0-based PIPELINE_STAGES index."""
    low = agent_str.lower()
    checks = [
        ("scanner", 0), ("generation strategist", 1), ("evaluation strategist", 2),
        ("script writer", 3), ("code writer", 3), ("verifier", 4), ("reviewer", 4),
    ]
    for keyword, idx in checks:
        if keyword in low:
            return idx
    return -1


# Maps top-level Python module names → pip package names for auto-detection.
_MODULE_TO_PACKAGE: dict[str, str] = {
    "faker":          "faker",
    "sdv":            "sdv>=1.0",   # pin v1.x — load_demo and sdv.tabular removed in v1.0
    "pandas":         "pandas",
    "numpy":          "numpy",
    "scipy":          "scipy",
    "sklearn":        "scikit-learn",
    "matplotlib":     "matplotlib",
    "seaborn":        "seaborn",
    "ydata_profiling":"ydata-profiling",
    "impala":         "impyla",
    "thrift":         "thrift-sasl",
}


def _build_install_preamble(script_content: str) -> str:
    """Return a CML job bootstrap block injected before every generated script.

    The block does two things:
    1. pip-installs packages detected from the script's import statements, with
       a --target fallback for stale-NFS environments (Errno 116).
    2. Patches sys.argv from well-known CML job environment variables so that
       argparse scripts receive --manifest / --output / --report etc. even when
       the job is launched without explicit CLI arguments.
    """
    import re
    seen: list[str] = []
    for line in script_content.splitlines():
        m = re.match(r'^\s*(?:import|from)\s+([\w.]+)', line)
        if m:
            top = m.group(1).split('.')[0]
            pkg = _MODULE_TO_PACKAGE.get(top)
            if pkg and pkg not in seen:
                seen.append(pkg)

    parts = [
        "# --- CML job bootstrap (auto-injected by dispatch_cml_job) ---",
        "import subprocess as _b_sub, sys as _b_sys, os as _b_os",
    ]

    if seen:
        pkg_repr = ", ".join(f'"{p}"' for p in seen)
        parts += [
            f"_b_pkgs = [{pkg_repr}]",
            "print('Installing: ' + ', '.join(_b_pkgs), flush=True)",
            "try:",
            "    _b_sub.check_call([_b_sys.executable, '-m', 'pip', 'install',",
            "                       '-q', '--no-cache-dir', *_b_pkgs])",
            "except Exception as _b_pip_err:",
            "    # Fallback: install to a project-local dir (avoids stale NFS .local/)",
            "    print(f'Standard pip failed ({_b_pip_err}); retrying with --target...', flush=True)",
            "    _b_tgt = '/home/cdsw/.cml_deps'",
            "    _b_os.makedirs(_b_tgt, exist_ok=True)",
            "    _b_sub.check_call([_b_sys.executable, '-m', 'pip', 'install',",
            "                       '-q', '--no-cache-dir', '--target', _b_tgt, *_b_pkgs])",
            "    if _b_tgt not in _b_sys.path:",
            "        _b_sys.path.insert(0, _b_tgt)",
            "print('Package installation complete.', flush=True)",
        ]

    # Reset sys.argv to strip Jupyter kernel args (-f /tmp/jupyter/kernel-*.json
    # and other ipykernel_launcher flags) that cause argparse "unrecognized arguments".
    # Then inject our known CML job env vars as proper CLI flags.
    parts += [
        "_b_sys.argv = [_b_sys.argv[0]]  # drop Jupyter/ipykernel runtime args",
        "_b_argmap = {",
        "    'MANIFEST_PATH': '--manifest', 'OUTPUT_DIR': '--output',",
        "    'SYNTHETIC_DIR': '--synthetic', 'REPORT_PATH': '--report',",
        "    'ROWS': '--rows', 'SEED': '--seed', 'TARGET_TABLES': '--tables',",
        "}",
        "for _b_k, _b_f in _b_argmap.items():",
        "    _b_v = _b_os.environ.get(_b_k, '')",
        "    if _b_v:",
        "        _b_sys.argv += [_b_f, _b_v]",
        "# --- end bootstrap ---",
        "",
        "",
    ]
    return "\n".join(parts)


def _prepare_crew_inputs(inputs: dict) -> dict:
    """Add run timestamp and timestamped script filenames for this crew run."""
    prepared = dict(inputs)
    ts = prepared.get("run_timestamp") or datetime.now().strftime("%Y%m%d_%H%M%S")
    prepared["run_timestamp"] = ts

    gen_name = prepared.get("gen_script_name") or f"generate_synthetic_data_{ts}.py"
    eval_name = prepared.get("eval_script_name") or f"evaluate_synthetic_data_{ts}.py"
    prepared["gen_script_name"] = gen_name
    prepared["eval_script_name"] = eval_name

    scripts_dir = prepared.get("output_scripts_dir", DEFAULT_OUTPUT_SCRIPTS_DIR)
    prepared["gen_script_path"] = str(Path(scripts_dir) / gen_name)
    prepared["eval_script_path"] = str(Path(scripts_dir) / eval_name)

    prepared.setdefault(
        "manifest_path",
        str(Path(scripts_dir) / "schema_manifest.json"),
    )
    return prepared


def _get_cml_credentials() -> tuple[str, str, str]:
    """Read Workbench API credentials from the current process environment."""
    host = (
        os.getenv("CAI_WORKBENCH_HOST")
        or os.getenv("CDSW_DOMAIN")
        or ""
    )
    if host and not host.startswith(("http://", "https://")):
        host = f"https://{host}"
    api_key = os.getenv("CAI_WORKBENCH_API_KEY") or os.getenv("CDSW_APIV2_KEY") or ""
    project_id = os.getenv("CDSW_PROJECT_ID") or os.getenv("CAI_WORKBENCH_PROJECT_ID") or ""
    return host, api_key, project_id


def _cml_credentials_status() -> str:
    host, api_key, project_id = _get_cml_credentials()
    parts = [
        f"host={'set' if host else 'MISSING'}",
        f"api_key={'set' if api_key else 'MISSING'}",
        f"project_id={'set' if project_id else 'MISSING'}",
    ]
    return ", ".join(parts)


def _job_dispatch_status(result: str) -> str:
    upper = result.upper()
    if "FINISHED WITH STATUS: SUCCEEDED" in upper or "STATUS: SUCCEEDED" in upper:
        return "SUCCEEDED"
    if result.startswith("ERROR") or "FAILED" in upper:
        return "FAILED"
    return "NOT_DISPATCHED"


def _get_api_key() -> str:
    return (
        os.getenv("LLM_API_KEY")
        or os.getenv("CAI_API_KEY")
        or os.getenv("CDP_TOKEN", "")
    )


# ---------------------------------------------------------------------------
# LLM factory (same pattern as nl_to_sql_crew.py)
# ---------------------------------------------------------------------------

def make_llm():
    from crewai import LLM
    api_key = _get_api_key()
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_API_BASE"] = LLM_API_BASE_URL
    return LLM(
        model=f"openai/{LLM_MODEL}",
        base_url=LLM_API_BASE_URL,
        api_key=api_key,
    )


# ---------------------------------------------------------------------------
# Tool: ImpalaQueryTool — run SQL against the configured Impala CDW endpoint
# ---------------------------------------------------------------------------

class ImpalaQueryInput(BaseModel):
    sql: str = Field(description="SQL query to execute against Impala")


class ImpalaQueryTool:
    """Thin wrapper so it can be instantiated as a CrewAI BaseTool."""

    name: str = "impala_query"
    description: str = (
        "Execute a SQL query against Impala and return results as a formatted table. "
        "Use for DESCRIBE, SHOW TABLES, COUNT(*), GROUP BY top-N, and JOIN validation queries."
    )

    def _run_raw(self, sql: str) -> str:
        try:
            from impala.dbapi import connect  # type: ignore
            t0 = time.monotonic()
            conn = connect(
                host=IMPALA_HOST, port=IMPALA_PORT,
                use_ssl=True, use_http_transport=True,
                http_path="cliservice", auth_mechanism="PLAIN",
                user=IMPALA_USER, password=IMPALA_PASS,
            )
            cur = conn.cursor()
            cur.execute(f"USE {IMPALA_DB}")
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            elapsed = int((time.monotonic() - t0) * 1000)
            cur.close()
            conn.close()

            lines = [f"DURATION : {elapsed} ms", f"ROWS     : {len(rows)}", ""]
            if cols:
                widths = [max(len(c), max((len(str(r[i])) for r in rows), default=0))
                          for i, c in enumerate(cols)]
                header = "| " + " | ".join(c.ljust(w) for c, w in zip(cols, widths)) + " |"
                sep    = "|-" + "-|-".join("-" * w for w in widths) + "-|"
                lines += [header, sep]
                for row in rows:
                    lines.append("| " + " | ".join(str(v).ljust(w) for v, w in zip(row, widths)) + " |")
            return "\n".join(lines)

        except ImportError:
            return "ERROR: impyla not installed — cannot run live queries"
        except Exception as exc:
            return f"ERROR: {exc}"


def _make_impala_tool():
    """Return a CrewAI-compatible BaseTool wrapping ImpalaQueryTool."""
    from crewai.tools import BaseTool

    _impl = ImpalaQueryTool()

    class _ImpalaBaseTool(BaseTool):
        name: str = _impl.name
        description: str = _impl.description
        args_schema: type[BaseModel] = ImpalaQueryInput

        def _run(self, sql: str) -> str:
            return _impl._run_raw(sql)

    return _ImpalaBaseTool()


# ---------------------------------------------------------------------------
# Tool: WriteFileTool — write generated script content to disk
# ---------------------------------------------------------------------------

class WriteFileInput(BaseModel):
    path: str = Field(description="Absolute or relative path for the file to write")
    content: str = Field(description="Full text content to write to the file")


def _make_write_file_tool(scripts_dir: str):
    from crewai.tools import BaseTool

    class _WriteFileTool(BaseTool):
        name: str = "write_file"
        description: str = (
            "Write text content to a file at the given path. "
            "Use this to save generated Python scripts to disk."
        )
        args_schema: type[BaseModel] = WriteFileInput

        def _run(self, path: str, content: str) -> str:
            target = Path(path) if os.path.isabs(path) else Path(scripts_dir) / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Written {len(content)} chars to {target}"

    return _WriteFileTool()


# ---------------------------------------------------------------------------
# Tool: ReadFileTool — read a script file back for verification
# ---------------------------------------------------------------------------

class ReadFileInput(BaseModel):
    path: str = Field(description="Path of the file to read")


def _make_read_file_tool(scripts_dir: str):
    from crewai.tools import BaseTool

    class _ReadFileTool(BaseTool):
        name: str = "read_file"
        description: str = "Read and return the full text content of a file."
        args_schema: type[BaseModel] = ReadFileInput

        def _run(self, path: str) -> str:
            target = Path(path) if os.path.isabs(path) else Path(scripts_dir) / path
            if not target.is_file():
                return f"ERROR: file not found: {target}"
            return target.read_text(encoding="utf-8")

    return _ReadFileTool()


# ---------------------------------------------------------------------------
# Tool: CmlJobTool — upload scripts and dispatch CML Jobs via CDSW API v2
# ---------------------------------------------------------------------------

class CmlJobInput(BaseModel):
    script_path: str = Field(description="Path to the Python script to run as a CML Job")
    job_name: str = Field(description="Unique name for the CML Job")
    env_overrides: str = Field(
        default="{}",
        description="JSON string of additional environment variables for the job",
    )
    # cpu and memory are intentionally NOT exposed to the LLM — hardcoded in dispatch_cml_job
    # to prevent the model from requesting absurd values (e.g. memory=8192 GB).


_JOB_CPU = 2      # vCPU — not exposed to LLM to prevent over-allocation
_JOB_MEMORY = 8   # GB   — not exposed to LLM to prevent over-allocation


def dispatch_cml_job(
    script_path: str,
    job_name: str,
    env_overrides: str = "{}",
    log_fn: Optional[Callable] = None,
) -> str:
    """Upload a script and run it as a CML Job. Returns a human-readable status string."""

    def _log(msg: str) -> None:
        if log_fn:
            log_fn(msg)

    host, api_key, project_id = _get_cml_credentials()

    if not all([host, api_key, project_id]):
        msg = (
            "CmlJobTool: missing CAI_WORKBENCH_HOST / CAI_WORKBENCH_API_KEY / "
            "CDSW_PROJECT_ID — scripts have been written to disk "
            "but jobs were NOT dispatched. Run them manually with run_pipeline.py."
        )
        _log(msg)
        return msg

    try:
        env_dict = json.loads(env_overrides)
    except json.JSONDecodeError:
        env_dict = {}

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    session.trust_env = False
    session.verify = False
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    script_file = Path(script_path)
    if not script_file.is_file():
        return f"ERROR: script not found at {script_path}"

    # Inject a pip-install preamble so the job self-heals missing packages.
    script_content = script_file.read_text(encoding="utf-8")
    preamble = _build_install_preamble(script_content)
    upload_bytes = (preamble + script_content).encode("utf-8")
    if preamble:
        n_pkgs = preamble.count('"') // 2  # each package name has two quotes in _pkgs = [...]
        _log(f"Injecting pip preamble into {script_file.name} ({n_pkgs} package(s) detected)...")
    else:
        _log(f"No installable packages detected in {script_file.name}; uploading as-is.")

    upload_url = f"{host}/api/v2/projects/{project_id}/files"
    target_name = f"generated_scripts/{script_file.name}"
    _log(f"Uploading {script_file.name} ({len(upload_bytes):,} bytes) to project files...")
    # Pass the target path as the files= key so requests sets multipart/form-data
    # correctly. Content-Type: None removes the session-level application/json header
    # so requests can inject the boundary parameter automatically.
    resp = session.put(
        upload_url,
        files={target_name: (script_file.name, upload_bytes, "text/plain")},
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": None,
        },
    )
    if resp.status_code not in (200, 201, 202, 204):
        return f"ERROR uploading script: {resp.status_code} {resp.text[:200]}"
    _log(f"Upload OK ({resp.status_code}). Creating CML job '{job_name}'...")

    jobs_url = f"{host}/api/v2/projects/{project_id}/jobs"
    job_config = {
        "name": job_name,
        "script": target_name,
        "kernel": "python3",
        "cpu": _JOB_CPU,
        "memory": _JOB_MEMORY,
        "runtime_identifier": RUNTIME_IMAGE,
        "environment": env_dict,
    }
    resp = session.post(jobs_url, json=job_config)
    if resp.status_code not in (200, 201):
        return f"ERROR creating job: {resp.status_code} {resp.text[:200]}"
    job_id = resp.json().get("id", "")
    _log(f"Job '{job_name}' created (id={job_id}). Starting run...")

    runs_url = f"{host}/api/v2/projects/{project_id}/jobs/{job_id}/runs"
    resp = session.post(runs_url, json={})
    if resp.status_code not in (200, 201):
        return f"ERROR starting job run: {resp.status_code} {resp.text[:200]}"
    run_id = resp.json().get("id", "")
    _log(f"Run {run_id} started. Polling every 15s (max 30 min)...")

    poll_url = f"{runs_url}/{run_id}"
    deadline = time.time() + 1800
    poll_start = time.time()
    last_status = ""
    poll_n = 0
    while time.time() < deadline:
        time.sleep(15)
        poll_n += 1
        resp = session.get(poll_url)
        if resp.status_code != 200:
            return f"ERROR polling job run: {resp.status_code}"
        status = resp.json().get("status", "UNKNOWN")
        elapsed = int(time.time() - poll_start)
        if status != last_status:
            _log(f"[{job_name}] status → {status} ({elapsed}s elapsed)")
            last_status = status
        elif poll_n % 4 == 0:  # heartbeat every ~60 s even if status unchanged
            _log(f"[{job_name}] still {status}... ({elapsed}s elapsed)")
        if status not in ("STARTING", "RUNNING", "SCHEDULING"):
            return f"Job {job_name} finished with status: {status}"

    return f"Job {job_name} timed out after 30 minutes"


def _make_cml_job_tool():
    from crewai.tools import BaseTool

    class _CmlJobTool(BaseTool):
        name: str = "cml_job"
        description: str = (
            "Create and run a CML Job on CAI Workbench for the given script. "
            "Uploads the script, creates the job, starts a job run, polls until complete, "
            "and returns the final status (SUCCEEDED or FAILED)."
        )
        args_schema: type[BaseModel] = CmlJobInput

        def _run(self, script_path: str, job_name: str,
                 env_overrides: str = "{}") -> str:
            return dispatch_cml_job(script_path, job_name, env_overrides)

    return _CmlJobTool()


# ---------------------------------------------------------------------------
# Build agents
# ---------------------------------------------------------------------------

def _build_scanner(llm, impala_tool, write_tool) -> "Agent":
    from crewai import Agent
    return Agent(
        role="Schema and Relationship Scanner",
        goal=(
            "Profile every target table in the {target_database} database, infer "
            "foreign-key relationships and generation order, and produce a complete "
            "schema_manifest.json that the code-writing agent uses to write generation scripts."
        ),
        backstory=(
            "You are an expert data analyst who reads database schemas via SQL queries. "
            "You run DESCRIBE, COUNT(*), GROUP BY top-N on categorical columns, and "
            "MIN/MAX/AVG only on columns whose DESCRIBE type is numeric or timestamp "
            "(never AVG on strings). You flag PII-risk columns by name "
            "patterns (id, cif, name, email, phone, addr, mobile, nric) and infer FK "
            "relationships from column-name overlaps and naming conventions. You never "
            "export real data values — only aggregated statistics and representative codes. "
            "You work with any database schema, not just banking schemas."
        ),
        tools=[impala_tool, write_tool],
        llm=llm,
        verbose=True,
    )


def _build_gen_strategist(llm) -> "Agent":
    from crewai import Agent
    return Agent(
        role="Python Generation Strategist",
        goal=(
            "Map each table to the most suitable Python generation approach (faker, "
            "SDV GaussianCopulaSynthesizer, SDV PARSynthesizer — v1.x API only) "
            "and identify special column rules."
        ),
        backstory=(
            "You are a synthetic data engineer. For lookup/reference tables you use faker "
            "with manual code-description pairs. For customer/account masters you use "
            "SDV GaussianCopulaSynthesizer (sdv.single_table). For time-series transaction "
            "tables you use SDV PARSynthesizer (sdv.sequential) to preserve temporal patterns. "
            "IMPORTANT: you ONLY use the SDV v1.x API. Never use load_demo, "
            "sdv.tabular, or SingleTablePreset — those were removed in SDV v1.0. "
            "Correct imports: from sdv.single_table import GaussianCopulaSynthesizer; "
            "from sdv.sequential import PARSynthesizer. "
            "You also specify when faker.providers.bank, .person, or .address are needed, "
            "and when Luhn-valid card numbers or SWIFT BIC codes are required. You produce a "
            "generation strategy JSON that is database-agnostic — valid for any schema."
        ),
        llm=llm,
        verbose=True,
    )


def _build_eval_strategist(llm) -> "Agent":
    from crewai import Agent
    return Agent(
        role="Statistical Evaluation Strategist",
        goal=(
            "Design the statistical test plan for validating the generated synthetic data "
            "against the schema manifest."
        ),
        backstory=(
            "You are a statistician who validates synthetic data fidelity. You select "
            "KS tests for numeric distributions, chi-squared for categoricals, Pearson "
            "correlation diffs for multi-column relationships, pandas null-rate comparison, "
            "pandas.merge for FK completeness, regex scans for PII leakage (NRIC, phone, "
            "email), and temporal coherence checks (no future dates, created < updated). "
            "You produce an evaluation plan JSON specifying which tests apply to which "
            "table types, valid for any schema."
        ),
        llm=llm,
        verbose=True,
    )


def _build_code_writer(llm, write_tool) -> "Agent":
    from crewai import Agent
    return Agent(
        role="Python Script Writer",
        goal=(
            "Write two complete, executable, fixed-seed Python scripts with the exact "
            "timestamped filenames specified in your task, implementing the generation "
            "and evaluation strategies. Save them to {output_scripts_dir} using write_file."
        ),
        backstory=(
            "You are a senior Python engineer who writes clean, reproducible data "
            "pipelines. You embed the GENERATION_ORDER and STRATEGY_MAP from the "
            "strategy tasks, implement per-table generator functions, enforce FK "
            "relationships using pandas, and produce an evaluation script with "
            "statistical tests and a Markdown report. Your scripts run as standalone "
            "CML Jobs — no agent involvement at execution time. Both scripts have "
            "argparse CLIs with --manifest, --rows, --output, --seed, --report flags, "
            "and each argument uses os.getenv() as its default so the script works "
            "when launched as a CML Job with environment variables instead of CLI flags. "
            "You write schema-agnostic scripts that read all configuration from the "
            "manifest JSON at runtime. "
            "CRITICAL SDV API rules (SDV v1.x only — older APIs were removed): "
            "1. Import: from sdv.single_table import GaussianCopulaSynthesizer  "
            "   NOT from sdv.tabular import GaussianCopula or SingleTablePreset. "
            "2. Import: from sdv.sequential import PARSynthesizer  "
            "   NOT from sdv.timeseries import PARSynthesizer. "
            "3. NEVER use 'from sdv import load_demo' or any sdv.demo module. "
            "4. Fit: synthesizer.fit(real_df); Sample: synthesizer.sample(num_rows=N). "
            "5. For SDV you must create a Metadata object: "
            "   from sdv.metadata import SingleTableMetadata; "
            "   metadata = SingleTableMetadata(); metadata.detect_from_dataframe(df). "
            "If SDV integration is complex, fall back to faker-only generation. "
            "PYTHON SYNTAX RULE (Python 3.11): never put a backslash inside an "
            "f-string expression — it raises SyntaxError. When an f-string needs a "
            "quoted dict key, use single quotes inside the double-quoted f-string, "
            "e.g. f\"Unknown library: {strategy['library']}\" — and NEVER the "
            "backslash-escaped form f\"...{strategy[\\\"library\\\"]}...\". "
            "Alternatively, assign the lookup to a local variable on the previous "
            "line and reference that bare variable name inside the f-string."
        ),
        tools=[write_tool],
        llm=llm,
        verbose=True,
    )


def _build_verifier(llm, read_tool, cml_tool) -> "Agent":
    from crewai import Agent
    return Agent(
        role="Code Quality Reviewer",
        goal=(
            "Read both generated scripts back, verify syntax and completeness, "
            "and — if verdict is READY — dispatch CML Jobs via cml_job tool to "
            "run the generate script followed by the evaluate script."
        ),
        backstory=(
            "You are a meticulous code reviewer. You check that GENERATION_ORDER "
            "covers every table in the schema manifest, that child FK columns reference "
            "the correct parent pools, that both scripts have argparse entrypoints "
            "with os.getenv() defaults, and that imports match used libraries. "
            "You flag problems with line references. "
            "SDV API check (blocker — set verdict NEEDS_FIXES if any of these appear): "
            "'from sdv import load_demo', 'from sdv.tabular import', "
            "'from sdv.timeseries import', 'SingleTablePreset', 'sdv.demo'. "
            "Correct SDV v1.x imports are: sdv.single_table.GaussianCopulaSynthesizer, "
            "sdv.sequential.PARSynthesizer, sdv.metadata.SingleTableMetadata. "
            "After confirming READY, use the cml_job tool to dispatch "
            "two CML Jobs: one for generation, one for evaluation."
        ),
        tools=[read_tool, cml_tool],
        llm=llm,
        verbose=True,
    )


# ---------------------------------------------------------------------------
# Build tasks
# ---------------------------------------------------------------------------

def _build_tasks(agents: list, inputs: dict) -> list:
    from crewai import Task

    scanner, gen_strat, eval_strat, writer, verifier = agents

    t_scan = Task(
        description=(
            f"Profile the tables [{inputs['target_tables']}] in database "
            f"[{inputs['target_database']}]. For each table:\n"
            "1. Run DESCRIBE <table> — collect EVERY column name, type, nullable.\n"
            "2. Run SELECT COUNT(*) to get row count.\n"
            "3. For key columns (ids, dates, amounts, currencies, codes): run "
            "   GROUP BY top-20 for string/varchar columns; MIN/MAX/AVG only for "
            "   numeric/timestamp types from DESCRIBE (skip AVG on strings).\n"
            "4. Flag PII-risk columns by name patterns.\n"
            "5. Infer FK relationships from column-name matches; validate with JOIN COUNT queries.\n"
            "6. For wide tables (>200 cols), list columns_to_populate as column names.\n\n"
            "Write the complete schema_manifest.json to "
            f"[{inputs.get('output_scripts_dir', DEFAULT_OUTPUT_SCRIPTS_DIR)}/"
            "schema_manifest.json] using the write_file tool."
        ),
        expected_output=(
            'Confirmation that schema_manifest.json was written via write_file, plus '
            'a summary of tables profiled, FK relationships, and generation_order. '
            'columns_to_populate must be a list of column names, not an integer.'
        ),
        agent=scanner,
    )

    t_gen = Task(
        description=(
            "Using the schema manifest from the scan task, plan the Python generation "
            "approach for each table category:\n"
            "- Lookup: faker + manual code-description pairs\n"
            "- Master/account (small-medium row count, PII columns): "
            "  faker or SDV GaussianCopulaSynthesizer (sdv.single_table, v1.x API)\n"
            "- Transaction (large row count, timestamps, amounts): "
            "  SDV PARSynthesizer (sdv.sequential, v1.x API)\n"
            "- Other: faker with appropriate providers\n\n"
            "Identify special column rules: Luhn card numbers, SWIFT BIC, surrogate IDs, "
            "locale-specific names/addresses. Output a generation strategy JSON."
        ),
        expected_output=(
            'A generation strategy JSON: {"strategy_map": [{"table": "<name>", '
            '"category": "lookup|master|account|transaction", "library": '
            '"faker|sdv_preset|sdv_par", "providers": [...], '
            '"special_columns": [{"column": "<c>", "rule": "<rule>"}]}]}'
        ),
        agent=gen_strat,
        context=[t_scan],
    )

    t_eval = Task(
        description=(
            "Using the schema manifest from the scan task, design the evaluation test "
            "plan specifying which statistical tests apply to each table type:\n"
            "- Numeric columns: KS test (scipy.stats.ks_2samp or kstest)\n"
            "- Categorical columns: chi-squared test (scipy.stats.chisquare)\n"
            "- Multi-column: Pearson correlation matrix diff\n"
            "- Null rates: absolute difference per column\n"
            "- FK integrity: pandas merge orphan count\n"
            "- PII leakage: regex scan (NRIC, phone, email)\n"
            "- Temporal: no future dates, created < updated where applicable\n\n"
            "Output an evaluation plan JSON."
        ),
        expected_output=(
            'An evaluation plan JSON: {"evaluation_plan": [{"table": "<name>", '
            '"tests": ["ks", "chi2", "null_rate", "fk_integrity", "pii_regex"]}]}'
        ),
        agent=eval_strat,
        context=[t_scan],
    )

    gen_name = inputs["gen_script_name"]
    eval_name = inputs["eval_script_name"]
    gen_script = inputs["gen_script_path"]
    eval_script = inputs["eval_script_path"]
    run_ts = inputs["run_timestamp"]
    scripts_dir = inputs.get("output_scripts_dir", DEFAULT_OUTPUT_SCRIPTS_DIR)
    manifest = inputs["manifest_path"]

    t_code = Task(
        description=(
            f"Write two complete Python scripts to [{scripts_dir}] using write_file.\n\n"
            f"1. [{gen_name}] — generation script:\n"
            "- Reads schema_manifest.json at runtime (--manifest flag)\n"
            "- Embeds GENERATION_ORDER and STRATEGY_MAP from the generation strategy\n"
            "- Per-table generator functions using faker/SDV per strategy\n"
            "- FK enforcement: sample child FK values from parent key pools\n"
            "- Wide-table parity: all manifest columns present; only columns_to_populate "
            "  are actively synthesised; others get NULL/type-default\n"
            "- argparse CLI: --manifest, --rows, --output, --tables, --seed\n\n"
            f"2. [{eval_name}] — evaluation script:\n"
            "- Implements tests from the evaluation plan\n"
            "- Reports Cols(gen/manifest) per table\n"
            "- Produces Markdown scorecard; optional HTML via ydata-profiling\n"
            "- PASS/FAIL FK integrity, PII scan, ML readiness summary\n"
            "- argparse CLI: --manifest, --synthetic, --report, --strict\n"
            "  (--strict exits 1 if any table FAILs, for CML Job signaling)\n\n"
            "Both scripts must have if __name__ == '__main__' entrypoints. "
            "Pin dependencies in a header comment. Scripts must be database-agnostic "
            "— they read all schema logic from the manifest JSON at runtime.\n\n"
            "IMPORTANT — CML Job compatibility: use os.getenv() as the default for every "
            "argparse argument so that CML job environment variables are picked up "
            "automatically when CLI flags are not provided. Example pattern:\n"
            "  import os\n"
            "  parser.add_argument('--manifest', default=os.getenv('MANIFEST_PATH', ''))\n"
            "  parser.add_argument('--output',   default=os.getenv('OUTPUT_DIR', ''))\n"
            "  parser.add_argument('--synthetic', default=os.getenv('SYNTHETIC_DIR', ''))\n"
            "  parser.add_argument('--report',   default=os.getenv('REPORT_PATH', ''))\n"
            "  parser.add_argument('--rows',     type=int, default=int(os.getenv('ROWS', '1000')))\n"
            "  parser.add_argument('--seed',     type=int, default=int(os.getenv('SEED', '42')))\n\n"
            f"You MUST call write_file twice with paths [{gen_script}] and [{eval_script}]. "
            "Do not claim files were written unless write_file returned success for both."
        ),
        expected_output=(
            f"write_file confirmations for {gen_name} and {eval_name} "
            f"in {scripts_dir}."
        ),
        agent=writer,
        context=[t_scan, t_gen, t_eval],
    )

    output_dir = inputs.get("output_data_dir", "/home/cdsw/synthetic_output")
    report_path = inputs.get("report_path", "/home/cdsw/artifacts/eval_report.md")
    rows = inputs.get("rows_per_table", 1000)
    seed = inputs.get("seed", 42)

    gen_env = json.dumps({
        "MANIFEST_PATH": manifest,
        "OUTPUT_DIR": output_dir,
        "ROWS": str(rows),
        "SEED": str(seed),
    })
    eval_env = json.dumps({
        "MANIFEST_PATH": manifest,
        "SYNTHETIC_DIR": output_dir,
        "REPORT_PATH": report_path,
    })

    t_verify = Task(
        description=(
            f"Read both generated scripts at [{gen_script}] and [{eval_script}] "
            "using the read_file tool. Verify:\n"
            "1. Syntax correctness (no obvious errors)\n"
            "2. All imports match libraries actually used in the code\n"
            "3. GENERATION_ORDER covers every table in the schema manifest\n"
            "4. Child FK column generators reference the correct parent pool variables\n"
            "5. The evaluation script tests cover all table types\n"
            "6. Both scripts have argparse CLIs and __main__ entrypoints\n\n"
            "Produce a verification JSON with 'verdict': 'READY' or 'NEEDS_FIXES'.\n\n"
            "If verdict is READY:\n"
            f"  - Dispatch a CML Job named 'd3-generate-{run_ts}' for [{gen_script}] "
            f"with env {gen_env}\n"
            f"  - Wait for it to complete, then dispatch 'd3-evaluate-{run_ts}' for [{eval_script}] "
            f"with env {eval_env}\n"
            "Use the cml_job tool for both. If CML credentials are missing, "
            "report that scripts are ready for manual execution."
        ),
        expected_output=(
            'A verification JSON: {"verification": {"syntax_ok": true, '
            '"imports_complete": true, "generation_order_covers_all_tables": true, '
            '"fk_wiring_correct": true, "entrypoints_present": true}, '
            '"issues": [], "verdict": "READY|NEEDS_FIXES", '
            '"job_dispatch": {"generate": "SUCCEEDED|FAILED|NOT_DISPATCHED", '
            '"evaluate": "SUCCEEDED|FAILED|NOT_DISPATCHED"}}'
        ),
        agent=verifier,
        context=[t_code],
    )

    return [t_scan, t_gen, t_eval, t_code, t_verify]


def _pipeline_job_env(inputs: dict) -> tuple[str, str]:
    scripts_dir = inputs.get("output_scripts_dir", DEFAULT_OUTPUT_SCRIPTS_DIR)
    manifest = inputs.get(
        "manifest_path",
        str(Path(scripts_dir) / "schema_manifest.json"),
    )
    output_dir = inputs.get("output_data_dir", "/home/cdsw/synthetic_output")
    report_path = inputs.get("report_path", "/home/cdsw/artifacts/eval_report.md")
    rows = inputs.get("rows_per_table", 1000)
    seed = inputs.get("seed", 42)
    gen_env = json.dumps({
        "MANIFEST_PATH": manifest,
        "OUTPUT_DIR": output_dir,
        "ROWS": str(rows),
        "SEED": str(seed),
    })
    eval_env = json.dumps({
        "MANIFEST_PATH": manifest,
        "SYNTHETIC_DIR": output_dir,
        "REPORT_PATH": report_path,
    })
    return gen_env, eval_env


def auto_dispatch_pipeline_jobs(
    inputs: dict,
    log_fn: Optional[Callable] = None,
) -> Dict[str, str]:
    """Dispatch generate/evaluate CML jobs when scripts exist on disk."""

    def _log(msg: str, etype: str = "dispatch") -> None:
        if log_fn:
            log_fn(etype, msg)

    gen_script = Path(inputs.get("gen_script_path", ""))
    eval_script = Path(inputs.get("eval_script_path", ""))
    run_ts = inputs.get("run_timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
    status: Dict[str, str] = {
        "generate": "NOT_DISPATCHED",
        "evaluate": "NOT_DISPATCHED",
        "gen_script": str(gen_script),
        "eval_script": str(eval_script),
    }

    if not gen_script.is_file():
        status["reason"] = f"Missing {gen_script}"
        _log(f"Script not found: {gen_script}", "error")
        return status
    if not eval_script.is_file():
        status["reason"] = f"Missing {eval_script}"
        _log(f"Script not found: {eval_script}", "error")
        return status

    host, api_key, project_id = _get_cml_credentials()
    if not all([host, api_key, project_id]):
        reason = (
            "Missing CML credentials — set CAI_WORKBENCH_HOST (or CDSW_DOMAIN), "
            "CAI_WORKBENCH_API_KEY (or CDSW_APIV2_KEY), and CDSW_PROJECT_ID"
        )
        status["reason"] = reason
        _log(reason, "error")
        return status

    _log(f"Scripts verified on disk. Starting CML job dispatch for run {run_ts}...")
    gen_env, eval_env = _pipeline_job_env(inputs)

    gen_result = dispatch_cml_job(
        str(gen_script), f"d3-generate-{run_ts}", gen_env,
        log_fn=lambda m: _log(m, "dispatch"),
    )
    status["generate"] = _job_dispatch_status(gen_result)
    status["generate_detail"] = gen_result[:300]
    _log(f"Generate job finished: {status['generate']}")

    if status["generate"] == "SUCCEEDED":
        _log("Generate succeeded. Dispatching evaluate job...")
        eval_result = dispatch_cml_job(
            str(eval_script), f"d3-evaluate-{run_ts}", eval_env,
            log_fn=lambda m: _log(m, "dispatch"),
        )
        status["evaluate"] = _job_dispatch_status(eval_result)
        status["evaluate_detail"] = eval_result[:300]
        _log(f"Evaluate job finished: {status['evaluate']}")
    else:
        status["evaluate"] = "NOT_DISPATCHED"
        status["evaluate_detail"] = "Skipped because generate job did not succeed"
        _log("Evaluate job skipped (generate did not succeed).", "error")

    return status


# ---------------------------------------------------------------------------
# Crew factory
# ---------------------------------------------------------------------------

def build_crew(
    inputs: dict,
    step_callback: Optional[Callable] = None,
    task_callback: Optional[Callable] = None,
) -> "Crew":
    from crewai import Crew, Process

    llm          = make_llm()
    impala_tool  = _make_impala_tool()
    scripts_dir  = inputs.get("output_scripts_dir", DEFAULT_OUTPUT_SCRIPTS_DIR)
    write_tool   = _make_write_file_tool(scripts_dir)
    read_tool    = _make_read_file_tool(scripts_dir)
    cml_tool     = _make_cml_job_tool()

    agents = [
        _build_scanner(llm, impala_tool, write_tool),
        _build_gen_strategist(llm),
        _build_eval_strategist(llm),
        _build_code_writer(llm, write_tool),
        _build_verifier(llm, read_tool, cml_tool),
    ]
    tasks = _build_tasks(agents, inputs)

    return Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        step_callback=step_callback,
        task_callback=task_callback or step_callback,
    )


# ---------------------------------------------------------------------------
# Synchronous entry point
# ---------------------------------------------------------------------------

def run_crew(inputs: dict) -> str:
    """Run the crew synchronously and return the final output string."""
    inputs = _prepare_crew_inputs(inputs)
    crew = build_crew(inputs)
    result = crew.kickoff(inputs=inputs)
    dispatch = auto_dispatch_pipeline_jobs(inputs)
    return f"{result}\n\njob_dispatch: {json.dumps(dispatch)}"


# ---------------------------------------------------------------------------
# Async wrapper (for FastAPI background thread)
# ---------------------------------------------------------------------------

_crew_events: List[Dict[str, Any]] = []
_crew_status: Dict[str, Any] = {"state": "idle", "run_id": None, "last_event": None}
_crew_lock = threading.Lock()


def _crew_emit(event_type: str, message: str, **extra: Any) -> None:
    with _crew_lock:
        _crew_events.append({
            "id": str(uuid.uuid4()),
            "ts": time.time(),
            "type": event_type,
            "message": str(message)[:2000],
            **extra,
        })
        _crew_status["last_event"] = message[:200]


def run_crew_async(inputs: dict) -> str:
    """Start the crew in a background thread. Returns run_id."""
    run_id = str(uuid.uuid4())

    def _worker() -> None:
        prepared = _prepare_crew_inputs(inputs)
        with _crew_lock:
            _crew_status.update({"state": "running", "run_id": run_id})

        _crew_emit(
            "start",
            f"Crew started — database={prepared.get('target_database')} "
            f"tables={prepared.get('target_tables')}",
            run_id=run_id,
        )
        _crew_emit(
            "info",
            f"Scripts: {prepared['gen_script_name']} | {prepared['eval_script_name']}",
            run_id=run_id,
        )
        _crew_emit("info", f"CML credentials: {_cml_credentials_status()}", run_id=run_id)

        # Announce stage 0 as running so the UI can light it up immediately.
        _crew_emit(
            "stage", PIPELINE_STAGES[0]["label"],
            stage_index=0, status="running", run_id=run_id,
        )

        def _step_cb(step_output: Any) -> None:
            """Called after each agent tool-use step."""
            tool = getattr(step_output, "tool", None)
            tool_input = getattr(step_output, "tool_input", None)
            result = getattr(step_output, "result", None)

            if tool:
                inp = str(tool_input)[:120] if tool_input else ""
                res = str(result)[:120] if result else ""
                _crew_emit(
                    "step", f"[{tool}] {inp}",
                    tool=tool, result_preview=res, run_id=run_id,
                )
                # Detect script writes so the UI can display the file path.
                if tool == "write_file":
                    path = ""
                    if isinstance(tool_input, dict):
                        path = tool_input.get("path", "")
                    elif isinstance(tool_input, str):
                        try:
                            path = json.loads(tool_input).get("path", "")
                        except Exception:
                            pass
                    if not path and result:
                        # Parse "Written N chars to /some/path"
                        for part in str(result).split(" to "):
                            if part.strip().startswith("/"):
                                path = part.strip()
                                break
                    if path:
                        _crew_emit("script", path, path=path, run_id=run_id)
            else:
                _crew_emit("step", str(step_output)[:300], run_id=run_id)

        def _task_cb(task_output: Any) -> None:
            """Called after each task completes."""
            agent = str(getattr(task_output, "agent", ""))
            raw = str(getattr(task_output, "raw", task_output))
            stage_idx = _detect_stage(agent)

            _crew_emit(
                "task", f"{agent}: {raw[:400]}",
                agent=agent, stage_index=stage_idx, run_id=run_id,
            )

            # Advance the stage tracker.
            if stage_idx >= 0:
                _crew_emit(
                    "stage", PIPELINE_STAGES[stage_idx]["label"],
                    stage_index=stage_idx, status="done", run_id=run_id,
                )
                next_idx = stage_idx + 1
                if next_idx < len(PIPELINE_STAGES):
                    _crew_emit(
                        "stage", PIPELINE_STAGES[next_idx]["label"],
                        stage_index=next_idx, status="running", run_id=run_id,
                    )

        # Heartbeat thread — emits an "info" event every 30 s while the crew
        # is active so the UI never goes silent during long LLM thinking phases.
        _hb_stop = threading.Event()
        _crew_start_ts = time.time()

        def _heartbeat() -> None:
            while not _hb_stop.wait(30):
                elapsed = int(time.time() - _crew_start_ts)
                with _crew_lock:
                    last = _crew_status.get("last_event", "")[:80]
                _crew_emit(
                    "info",
                    f"Agent still working... ({elapsed}s elapsed) — last: {last}",
                    run_id=run_id,
                )

        hb_thread = threading.Thread(target=_heartbeat, daemon=True)
        hb_thread.start()

        try:
            crew = build_crew(prepared, step_callback=_step_cb, task_callback=_task_cb)
            result = crew.kickoff(inputs=prepared)

            _crew_emit("info", "Crew finished. Starting job dispatch...", run_id=run_id)
            dispatch = auto_dispatch_pipeline_jobs(
                prepared,
                log_fn=lambda etype, msg: _crew_emit(etype, msg, run_id=run_id),
            )
            _crew_emit("dispatch", json.dumps(dispatch), dispatch=dispatch, run_id=run_id)
            _crew_emit(
                "done",
                f"Pipeline complete. Generate={dispatch.get('generate')} "
                f"Evaluate={dispatch.get('evaluate')}",
                run_id=run_id, status="completed",
            )
            with _crew_lock:
                _crew_status.update({
                    "state": "idle",
                    "result": str(result)[:500],
                    "job_dispatch": dispatch,
                    "gen_script_name": prepared["gen_script_name"],
                    "eval_script_name": prepared["eval_script_name"],
                })
        except Exception as exc:  # noqa: BLE001
            _crew_emit("error", str(exc), run_id=run_id, status="failed")
            with _crew_lock:
                _crew_status.update({"state": "idle", "error": str(exc)[:300]})
        finally:
            _hb_stop.set()  # stop the heartbeat thread

    threading.Thread(target=_worker, daemon=True).start()
    return run_id


def get_crew_events(since: float = 0) -> List[Dict[str, Any]]:
    with _crew_lock:
        return [e for e in _crew_events if e["ts"] >= since]


def get_crew_status() -> Dict[str, Any]:
    with _crew_lock:
        return dict(_crew_status)


# ---------------------------------------------------------------------------
# CLI entry point for local testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run D3 synthetic data crew")
    parser.add_argument("--database", default="pf_usecase")
    parser.add_argument("--tables", default="all")
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scripts-dir", default=DEFAULT_OUTPUT_SCRIPTS_DIR)
    parser.add_argument("--output-dir", default="/home/cdsw/synthetic_output")
    parser.add_argument("--report", default="/home/cdsw/artifacts/eval_report.md")
    args = parser.parse_args()

    _inputs = {
        "target_database": args.database,
        "target_tables": args.tables,
        "rows_per_table": args.rows,
        "seed": args.seed,
        "output_scripts_dir": args.scripts_dir,
        "output_data_dir": args.output_dir,
        "report_path": args.report,
    }
    print(run_crew(_inputs))
