# Synthetic Data Pipeline — CAI Application

CAI Application (FastAPI) exposing **two execution modes**:

| Mode | Endpoints | When to use |
|---|---|---|
| **Deterministic** (`/pipeline/*`) | `scan`, `generate`, `evaluate`, `all` | Scripts already exist; fast, no LLM |
| **Agentic** (`/agent/*`) | `kickoff`, `kickoff/sync`, `status`, `events` | New database or schema; LLM crew authors scripts then dispatches CML Jobs |

Mirrors the [`nl_to_sql_agent`](../nl_to_sql_agent/) deploy pattern.

## Architecture

```
deploy_app.py (CAI Job)  →  registers Application
run_app.py (CAI App)     →  pip install + uvicorn
synthetic_data_api.py    →  /pipeline/* + /agent/*
synthetic_data_crew.py   →  CrewAI 5-agent crew (agentic mode)
run_pipeline.py          →  ../synthetic_data_workflow_d3/ (deterministic mode)
```

```
/agent/kickoff
    → synthetic_data_crew.py (background thread)
        → Agent 1 (Schema Scanner): ImpalaQueryTool — DESCRIBE + FK validation
        → Agent 2 (Generation Strategist): LLM reasons → strategy_map JSON
        → Agent 3 (Evaluation Strategist): LLM reasons → evaluation_plan JSON
        → Agent 4 (Code Writer): WriteFileTool → generate + evaluate scripts
        → Agent 5 (Script Verifier): ReadFileTool → verify → CmlJobTool
            → CML Job: generate_synthetic_data_<timestamp>.py
            → CML Job: evaluate_synthetic_data_<timestamp>.py
```

## Deploy

1. Copy `synthetic_data_app/` and `synthetic_data_workflow_d3/` into your CAI project root.

2. Set **Project → Environment Variables**:

### Deterministic mode (always required)

| Variable | Example |
|---|---|
| `IMPALA_HOST` | Impala CDW hostname |
| `IMPALA_USER` / `IMPALA_PASS` | Workload credentials |
| `IMPALA_DB` | `pf_usecase` |
| `PIPELINE_DIR` | `/home/cdsw/synthetic_data_workflow_d3` |
| `MANIFEST_PATH` | `/home/cdsw/artifacts/schema_manifest.json` |
| `OUTPUT_DIR` | `/home/cdsw/artifacts/synthetic_output` |
| `REPORT_PATH` | `/home/cdsw/artifacts/eval_report.md` |

### Agentic mode (required for `/agent/*`)

| Variable | Example |
|---|---|
| `LLM_API_BASE_URL` | `https://api.openai.com/v1` (OpenAI) or Cloudera AI Inference `/v1` URL |
| `LLM_API_KEY` | OpenAI API key (`sk-...`) or CAII key |
| `LLM_MODEL` | `gpt-4o` |
| `CAI_WORKBENCH_HOST` | `https://ml-xxxx.cloudera.site` |
| `CAI_WORKBENCH_API_KEY` | Workbench API v2 key (or auto-set `CDSW_APIV2_KEY`) |
| `CDSW_PROJECT_ID` | Auto-set on CAI Workbench (optional manual override) |
| `OUTPUT_SCRIPTS_DIR` | `/home/cdsw/generated_scripts` |

> **Deprecated aliases** (still read by the crew): `CAI_BASE_URL`, `CAI_URL`, `CAI_API_KEY`, `CAI_MODEL`.

3. Create a **Job** running `deploy_app.py` (Python 3.11, PBJ standard runtime).

4. Open the Application URL — the UI shows both pipelines.

## API reference

### Deterministic (`/pipeline/*`)

| Endpoint | Method | Body | Description |
|---|---|---|---|
| `/pipeline/scan` | POST | `PipelineRequest` | Build schema manifest from Impala |
| `/pipeline/generate` | POST | `PipelineRequest` | Generate synthetic CSVs |
| `/pipeline/evaluate` | POST | `PipelineRequest` | Scorecard with `--strict` |
| `/pipeline/all` | POST | `PipelineRequest` | scan → generate → evaluate |
| `/pipeline/all/async` | POST | `PipelineRequest` | Same, non-blocking + event polling |
| `/pipeline/status` | GET | — | Current pipeline run state |
| `/api/workflow/events` | GET | `?since=<ts>` | Event log |
| `/artifacts/report` | GET | — | Download eval_report.md |

### Agentic (`/agent/*`)

| Endpoint | Method | Body | Description |
|---|---|---|---|
| `/agent/kickoff` | POST | `AgentPipelineRequest` | Start crew async (returns run_id) |
| `/agent/kickoff/sync` | POST | `AgentPipelineRequest` | Run crew synchronously |
| `/agent/status` | GET | — | Crew state: idle \| running |
| `/agent/events` | GET | `?since=<ts>` | Crew step/log event stream |

`AgentPipelineRequest` fields: `target_database`, `target_tables`, `rows_per_table`, `seed`,
`output_scripts_dir`, `output_data_dir`, `report_path`, `manifest_path`.

### Agentic curl example

```bash
# Start crew for a new database — database-agnostic
curl -X POST "$APP_URL/agent/kickoff" \
  -H "Content-Type: application/json" \
  -d '{
    "target_database": "my_custom_db",
    "target_tables": "all",
    "rows_per_table": 1000,
    "seed": 42,
    "output_scripts_dir": "/home/cdsw/generated_scripts"
  }'

# Poll events
curl "$APP_URL/agent/events?since=0"
```

### Deterministic curl example

```bash
curl -X POST "$APP_URL/pipeline/all" \
  -H "Content-Type: application/json" \
  -d '{"target_tables": "eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d", "rows": 1000, "seed": 42}'
```

## Local test (no CAI)

```bash
# Deterministic — no LLM needed
cd synthetic_data_workflow_d3
pip install -r requirements.txt
python run_pipeline.py generate --manifest schema_manifest.sample.json \
  --target-tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d \
  --output /home/cdsw/artifacts/synthetic_output --rows 1000 --seed 42
python run_pipeline.py evaluate --manifest schema_manifest.sample.json \
  --output /home/cdsw/artifacts/synthetic_output --report /home/cdsw/artifacts/eval_report.md \
  --target-tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d --strict

# Agentic — set env vars then:
cd synthetic_data_app
pip install -r requirements.txt
python synthetic_data_crew.py --database pf_usecase --tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d
```

## CML Jobs (without Application)

See [`../synthetic_data_workflow_d3/CML_JOBS.md`](../synthetic_data_workflow_d3/CML_JOBS.md)
for standalone Job definitions.
