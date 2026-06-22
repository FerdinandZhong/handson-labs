# UOB Synthetic Data Generation Lab — 22 June 2026

Hands-on lab covering **four complementary directions** for generating PII-free
synthetic training data from the `pf_usecase` Impala lakehouse.

---

## Quick start — where to begin

| Audience | Start here |
|---|---|
| **Overview — all four directions** | [`Instructions/SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md`](Instructions/SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md) |
| **Presenter / demo walkthrough** | [`Instructions/SYNTHETIC_DATA_DEMO_GUIDE.md`](Instructions/SYNTHETIC_DATA_DEMO_GUIDE.md) |
| **Workshop participant — D1** (build five-agent pipeline in Agent Studio) | [`Instructions/synthetic_data_d1_workflow.md`](Instructions/synthetic_data_d1_workflow.md) |
| **Workshop participant — D2** (Agent Studio + Synthetic Data Studio integration) | [`Instructions/synthetic_data_d2_workflow.md`](Instructions/synthetic_data_d2_workflow.md) |
| **Workshop participant — D2.5** (Agent Studio script authoring — D3 pipeline, no execution) | [`Instructions/synthetic_data_d2_5_workflow.md`](Instructions/synthetic_data_d2_5_workflow.md) |
| **Workshop participant — D3** (deterministic CML Jobs + optional CAI Application) | [`Instructions/synthetic_data_d3_workflow.md`](Instructions/synthetic_data_d3_workflow.md) |

---

## Direction comparison

See **[`Instructions/SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md`](Instructions/SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md)** for the full four-direction comparison.

> **Production ML training data:** only **D3** (deterministic CML Jobs + `--strict` evaluation).
> D1, D2, and D2.5 are Agent Studio workshops — they do not meet production requirements
> for volume, schema parity, reproducibility, or CI-gatable quality gates.

---

## Project layout

```
UOB_synthetic_data_lab_22_June/
│
├── Instructions/                     ← Hands-on lab walkthroughs (all markdown here)
│   ├── SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md  ★ Four-direction comparison (start here)
│   ├── SYNTHETIC_DATA_DEMO_GUIDE.md         Presenter cheat sheet
│   ├── synthetic_data_d1_workflow.md
│   ├── synthetic_data_d2_workflow.md
│   ├── synthetic_data_d2_5_workflow.md
│   └── synthetic_data_d3_workflow.md
│
├── images/                           ← PNG diagrams embedded by Instructions
│   ├── synthetic_data_workflow_d1/
│   ├── synthetic_data_workflow_d2/
│   ├── synthetic_data_workflow_d2_5/
│   └── synthetic_data_workflow_d3/
│
├── extra_materials/                  ← Agent/task YAML only (no duplicate markdown specs)
│   ├── synthetic_data_workflow_d1/
│   └── synthetic_data_workflow_d2/
│
├── synthetic_data_workflow_d3/       ← D3 pipeline scripts
├── synthetic_data_app/               ← D3 CAI Application
└── synthetic_data_studio_tool/       ← D2 custom Agent Studio tool
```

---

## D3 — CML Jobs quick start

### Prerequisites

1. CAI Workbench project with Python 3.11 runtime
2. Impala CDW credentials
3. Install dependencies:

```bash
cd synthetic_data_workflow_d3
pip install -r requirements.txt
```

### Test Impala connection

```bash
cd synthetic_data_workflow_d3

export IMPALA_HOST=hue-impala-gateway.datalake.bdqdgc.c0.cloudera.site
export IMPALA_USER=<workload_user>
export IMPALA_PASS=<workload_password>
export IMPALA_DB=pf_usecase

python test_impala_connection.py
# Expected: all checks passed — N tables in pf_usecase
```

### Local offline demo (no live Impala)

Uses the bundled `schema_manifest.sample.json` — no credentials needed:

```bash
cd synthetic_data_workflow_d3

python run_pipeline.py generate \
  --manifest schema_manifest.sample.json \
  --target-tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d \
  --rows 1000 --seed 42 \
  --output /home/cdsw/artifacts/synthetic_output

python run_pipeline.py evaluate \
  --manifest schema_manifest.sample.json \
  --output /home/cdsw/artifacts/synthetic_output \
  --report /home/cdsw/artifacts/eval_report.md \
  --target-tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d \
  --strict
```

Expected: **3/3 PASS**, `eda_rbk_tltx_d` schema **PARTIAL** (wide-table defaults, normal).

### Live Impala end-to-end

```bash
cd synthetic_data_workflow_d3

export TARGET_TABLES=eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d
export ROWS=1000
export SEED=42
export MANIFEST_PATH=/home/cdsw/artifacts/schema_manifest.json
export OUTPUT_DIR=/home/cdsw/artifacts/synthetic_output
export REPORT_PATH=/home/cdsw/artifacts/eval_report.md

python run_pipeline.py all --validate-fks --profile-stats --strict
```

### CML Jobs (production)

See [`synthetic_data_workflow_d3/CML_JOBS.md`](synthetic_data_workflow_d3/CML_JOBS.md) for
full Job definitions (`d3-scan`, `d3-generate`, `d3-evaluate`, `d3-all`).

### CAI Application (optional UI)

See [`synthetic_data_app/README.md`](synthetic_data_app/README.md) and
[`Instructions/synthetic_data_d3_workflow.md`](Instructions/synthetic_data_d3_workflow.md) § "CAI Application — step-by-step launch"
for the deploy guide.

**Agentic mode** (`/agent/*`) requires OpenAI-compatible LLM env vars:

| Variable | Example |
|---|---|
| `LLM_API_BASE_URL` | `https://api.openai.com/v1` |
| `LLM_API_KEY` | `sk-...` |
| `LLM_MODEL` | `gpt-4o` |
| `PIPELINE_DIR` | `/home/cdsw/synthetic_data_workflow_d3` |

Also set `CAI_WORKBENCH_HOST`, `CAI_WORKBENCH_API_KEY`, and `CDSW_PROJECT_ID`
if you want the crew to auto-dispatch CML Jobs after script generation.

---

## Diagrams

All diagram PNGs are pre-rendered under `images/`. Mermaid sources and render
scripts are intentionally omitted from the audience repo to keep it lightweight.

---

## Impala connection parameters

| Parameter | Value |
|---|---|
| Host | `hue-impala-gateway.datalake.bdqdgc.c0.cloudera.site` |
| Port | `443` |
| Auth | PLAIN + SSL + HTTP (`http_path=cliservice`) |
| Database | `pf_usecase` |
| User / Password | Provided by instructor |
