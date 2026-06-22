# Synthetic Data Generation — Demo Guide & Status

Companion to [`SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md`](SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md)
(four-direction comparison). This guide tracks what is built and how to demo each
direction. All four directions target PII-free synthetic data that mirrors the
`pf_usecase` lakehouse (73 tables across BWC, RBK, REM, AMH, BRM, PIB, RLP, SSS)
for ML training.

**How we build:** workflows are created **manually in the Agent Studio UI** — not via
`crewai_yaml_importer`. The `agents.yaml` and `tasks.yaml` files in each direction
folder are version-control specs; the hands-on labs contain full copy-paste blocks for
Name, Role, Backstory, Goal (agents) and Description, Expected Output (tasks).

---

## Current status

| Direction | What it is | Artefacts | Demo-ready |
|---|---|---|---|
| **D1 — Agent Studio only** | 5-agent LLM pipeline (profile → map → generate → link → evaluate) | `extra_materials/synthetic_data_workflow_d1/` YAML | ✅ Build in UI & run (needs `iceberg-mcp-server`) |
| **D2 — Agent Studio + SDS** | Agent Studio orchestrates SDS generate/eval (demo mode) | `extra_materials/synthetic_data_workflow_d2/` YAML, `synthetic_data_studio_tool/` | ✅ Tool built; needs SDS app + UI workflow |
| **D2.5 — Script authoring** | 4-agent Agent Studio pipeline; stops at Python scripts (no execution) | `extra_materials/synthetic_data_workflow_d2_5/` YAML | ✅ Build in UI & run |
| **D3 — CML Jobs + CAI App** | Deterministic + agentic CrewAI; scan → generate → evaluate at scale | `synthetic_data_workflow_d3/` + `synthetic_data_app/` | ✅ Deterministic verified; agentic needs LLM creds |

Shared prerequisite for D1/D2/D2.5 schema discovery: **`iceberg-mcp-server`** against
`pf_usecase` (same Impala gateway credentials as `synthetic_data_workflow_d3/test_impala_connection.py`).

---

## Production vs workshop — tell the audience clearly

| Direction | Workshop / demo? | Production ML training? |
|---|---|---|
| **D1** | ✅ Yes — learn Agent Studio CSV pipeline | ❌ No — LLM generation, partial wide-table schema, session artefacts |
| **D2** | ✅ Yes — showcase SDS integration live | ❌ No — 25-row demo cap, prompt FK, LLM judge |
| **D2.5** | ✅ Yes — learn script authoring interactively | ❌ No — produces scripts only, no CSV output |
| **D3** | ✅ Yes — run offline demo with sample manifest | ✅ **Yes** — deterministic CML Jobs, full schema, `--strict` eval |

When an attendee asks *"Which direction do we use for real model training?"* the answer is
always **D3 deterministic**. D1/D2/D2.5 teach **how** the pipeline thinks; D3 **ships** the data.

Full rationale: [SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md § Why only D3 is suitable for production](SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md#why-only-d3-is-suitable-for-production).

---

## Building workflows in Agent Studio (UI)

1. **Create a workflow** in Agent Studio → **Sequential** process type.
2. **Set input variables** (see per-direction hands-on lab).
3. **Create agents** — paste Name, Role, Backstory, Goal from the lab or YAML.
4. **Attach tools** per the lab (MCP instances and custom tools in Tools Catalog first).
5. **Create tasks** — paste Description and Expected Output; wire **context** links.
6. **Save and run** with suggested starter inputs from the lab.

| Direction | Agents | Tasks | Hands-on lab |
|---|---|---|---|
| D1 | 5 | 5 | [`synthetic_data_d1_workflow.md`](synthetic_data_d1_workflow.md) |
| D2 | 4 | 4 | [`synthetic_data_d2_workflow.md`](synthetic_data_d2_workflow.md) |
| D2.5 | 4 | 4 | [`synthetic_data_d2_5_workflow.md`](synthetic_data_d2_5_workflow.md) |
| D3 (workshop) | 5 | 5 | [`synthetic_data_d3_workflow.md`](synthetic_data_d3_workflow.md) § Optional D2.5 |

---

## Direction 1 — pure Agent Studio

**Lab:** [`synthetic_data_d1_workflow.md`](synthetic_data_d1_workflow.md)

**Tools:** `iceberg-mcp-server` (Agents 1–2), Artifact Files Read/Write Tool + `csv_reader` (Agents 3–5).

**Run inputs (scoped first run):**

| Variable | Value |
|---|---|
| `target_tables` | `eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d` |
| `rows_per_table` | `100` |
| `database` | `pf_usecase` |

**Best for:** Agent Studio workshop — FK patch via CSV overwrite, statistical evaluation.
Not reproducible at production scale; use D3 for full column parity.

---

## Direction 2 — Agent Studio + Synthetic Data Studio

**Lab:** [`synthetic_data_d2_workflow.md`](synthetic_data_d2_workflow.md) — read **Understand the Limitations** first.

**Positioning:** Stakeholder / SDS showcase demo, not a training data pipeline. Row cap
≤25 per SDS call (demo mode). For ML training data, use D3.

**Run inputs (demo):**

| Variable | Value |
|---|---|
| `target_tables` | `eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d` |
| `rows_per_table` | `10` |
| `database` | `pf_usecase` |

**What to show:**

1. Task 1 — `relationships` JSON with two FK edges
2. Task 3 — `fk_pools_keys` in generation log; JSON files side by side
3. Spot-check FK values across tables
4. Task 4 — SDS evaluation scores ≥ 3.5/5; `dataset_ready_for_training: true`

---

## Direction 2.5 — Agent Studio script authoring

**Lab:** [`synthetic_data_d2_5_workflow.md`](synthetic_data_d2_5_workflow.md)

**Positioning:** Same logical pipeline as D3 agentic Agents 1–4; **stops after writing**
timestamped `generate_*.py` and `evaluate_*.py` + `schema_manifest.json`. No CML Jobs,
no script execution in the workflow.

**Run inputs:**

| Variable | Value |
|---|---|
| `target_tables` | `eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d` |
| `rows_per_table` | `100` |
| `database` | `pf_usecase` |
| `seed` | `42` |

**What to show:**

1. Task 1 — manifest written via Artifact Files
2. Tasks 2–3 — strategy JSON in task output
3. Task 4 — both timestamped `.py` files in Artifact Files tab
4. Hand off to D3 deterministic to run the scripts

---

## Direction 3 — CML Jobs + CAI Application

**Lab:** [`synthetic_data_d3_workflow.md`](synthetic_data_d3_workflow.md)

| Mode | When to use |
|---|---|
| **Deterministic** | Scripts exist; fast; reproducible; no LLM |
| **Agentic** | New database; CrewAI authors scripts + dispatches Jobs |

### Quick local demo (sample manifest, no Impala)

```bash
cd synthetic_data_workflow_d3
pip install -r requirements.txt

python run_pipeline.py generate \
  --manifest schema_manifest.sample.json \
  --target-tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d \
  --rows 1000 --seed 42 --output ./artifacts/synthetic_output

python run_pipeline.py evaluate \
  --manifest schema_manifest.sample.json \
  --output ./artifacts/synthetic_output \
  --report ./artifacts/eval_report.md \
  --target-tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d \
  --strict --use-scipy
```

Expected: **3/3 PASS** on scoped tables; `eda_rbk_tltx_d` schema **PARTIAL** (wide-table NULL defaults).

### Production on CAI Workbench

1. Set `IMPALA_*`, `TARGET_TABLES`, `MANIFEST_PATH`, `OUTPUT_DIR`, `REPORT_PATH`.
2. Run CML Jobs — see [`../synthetic_data_workflow_d3/CML_JOBS.md`](../synthetic_data_workflow_d3/CML_JOBS.md).
3. Optional: deploy CAI Application via `synthetic_data_app/deploy_app.py`.

### Agentic mode (new database)

```bash
curl -X POST "$APP_URL/agent/kickoff" \
  -H "Content-Type: application/json" \
  -d '{"target_database": "pf_usecase", "target_tables": "eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d", "rows_per_table": 1000}'
curl "$APP_URL/agent/events?since=0"
```

---

## Recommended demo flow

1. **D3 first** — run deterministic pipeline; show CSVs + PASS scorecard (most tangible).
2. **D2.5** (optional) — show Agent Studio authoring the same scripts interactively.
3. **D1** — five-agent CSV pipeline against live `pf_usecase` schema.
4. **D2** — SDS integration demo with ≤25 rows and LLM-as-judge scores.

See [`SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md`](SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md) for
when to choose each direction.
