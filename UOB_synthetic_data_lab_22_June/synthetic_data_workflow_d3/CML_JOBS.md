# D3 CML Jobs — Synthetic Data Pipeline

Run these as **Jobs** in CAI Workbench. All scripts live under
`synthetic_data_workflow_d3/`.

## Two execution modes

| Mode | Entry point | When to use |
|---|---|---|
| **Deterministic** (this doc) | `run_pipeline.py` | Scripts exist; no LLM; reproducible |
| **Agentic** | `synthetic_data_app/synthetic_data_crew.py` | New/unknown database; LLM discovers schema + writes scripts |

For the agentic mode see [`D3_AGENTIC_REDESIGN_PLAN.md`](D3_AGENTIC_REDESIGN_PLAN.md) and [`../synthetic_data_app/README.md`](../synthetic_data_app/README.md).
The CML Jobs below apply to the deterministic mode.

## Architecture diagrams

| Figure | PNG | Mermaid source |
|---|---|---|
| **Agentic pipeline** (CrewAI + CML dispatch) | `agentic_architecture.png` | `agentic_architecture.mmd` |
| Production pipeline (deterministic) | `architecture.png` | `architecture.mmd` |
| Hybrid overview (workshop + Jobs + App) | `hybrid_overview.png` | `hybrid_overview.mmd` |
| CAI Application layer | `cai_application.png` | `cai_application.mmd` |
| FK generation order | `fk_generation_order.png` | `fk_generation_order.mmd` |

Re-render: `./render_mermaid.sh` (requires `npx @mermaid-js/mermaid-cli`).

Set **Project → Settings → Environment Variables** before first run:

| Variable | Example | Used by |
|---|---|---|
| `IMPALA_HOST` | `your-impala-host` | scan |
| `IMPALA_USER` | workload user | scan |
| `IMPALA_PASS` | workload password | scan |
| `IMPALA_DB` | `pf_usecase` | scan |
| `TARGET_TABLES` | `eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d` | all |
| `ROWS` | `1000` | generate |
| `SEED` | `42` | generate |
| `MANIFEST_PATH` | `/home/cdsw/artifacts/schema_manifest.json` | all |
| `OUTPUT_DIR` | `/home/cdsw/artifacts/synthetic_output` | generate, evaluate |
| `REPORT_PATH` | `/home/cdsw/artifacts/eval_report.md` | evaluate |

**Kernel:** Python 3.11  
**Runtime:** `ml-runtime-pbj-jupyterlab-python3.11-standard:2026.04.1-b7` (or current PBJ standard)

Install deps on first run (or add to job preamble):

```bash
pip install -r synthetic_data_workflow_d3/requirements.txt
```

---

## Job definitions

### `d3-scan` — Schema manifest builder

| Setting | Value |
|---|---|
| **Script** | `synthetic_data_workflow_d3/run_pipeline.py` |
| **Arguments** | `scan --validate-fks --profile-stats` |
| **Resources** | 2 CPU / 8 GB |
| **Artifact** | `$MANIFEST_PATH` |

Uses live Impala (`IMPALA_*` env vars). For offline mode, use a describe dump directory:

```bash
python run_pipeline.py scan --describe-dir ./describe_dumps
```

---

### `d3-generate` — Synthetic CSV generation

| Setting | Value |
|---|---|
| **Script** | `synthetic_data_workflow_d3/run_pipeline.py` |
| **Arguments** | `generate` |
| **Depends on** | `d3-scan` (manifest must exist) |
| **Artifact** | `$OUTPUT_DIR/*.csv` |

Scoped demo (3-table FK chain):

```bash
export TARGET_TABLES=eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d
export ROWS=1000
export SEED=42
python run_pipeline.py generate
```

---

### `d3-evaluate` — Quality scorecard

| Setting | Value |
|---|---|
| **Script** | `synthetic_data_workflow_d3/run_pipeline.py` |
| **Arguments** | `evaluate --strict --use-scipy` |
| **Depends on** | `d3-generate` |
| **Artifact** | `$REPORT_PATH` |
| **Exit code** | Non-zero if any table FAILs (`--strict`) |

---

### `d3-all` — End-to-end demo Job

| Setting | Value |
|---|---|
| **Script** | `synthetic_data_workflow_d3/run_pipeline.py` |
| **Arguments** | `all --validate-fks --profile-stats --strict --use-scipy` |
| **Resources** | 4 CPU / 16 GB (scoped 3-table demo) |

One-shot command for workshops:

```bash
cd synthetic_data_workflow_d3
pip install -r requirements.txt

export TARGET_TABLES=eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d
export ROWS=1000
export SEED=42
export MANIFEST_PATH=/home/cdsw/artifacts/schema_manifest.json
export OUTPUT_DIR=/home/cdsw/artifacts/synthetic_output
export REPORT_PATH=/home/cdsw/artifacts/eval_report.md

python run_pipeline.py all --validate-fks --profile-stats --strict
```

---

## Phase 3 scale-out — batched generate Jobs

For full `pf_usecase` (73 tables), run **parallel generate Jobs** by source-system prefix:

| Job | `--batch-prefix` | Tables (approx.) |
|---|---|---|
| `d3-generate-bwc` | `eda_bwc_` | BWC master/account |
| `d3-generate-rbk` | `eda_rbk_` | RBK transactions |
| `d3-generate-rem` | `eda_rem_` | Remittance |
| `d3-generate-amh` | `eda_amh_` | AMH gateway |
| `d3-generate-other` | (run remaining prefixes) | BRM, PIB, RLP, SSS |

Example:

```bash
python run_pipeline.py generate --batch-prefix eda_bwc_
python run_pipeline.py generate --batch-prefix eda_rbk_
```

All batches write to the same `$OUTPUT_DIR`. Run `d3-evaluate` once after all batches complete.

Store versioned manifests:

```bash
MANIFEST_PATH=/home/cdsw/artifacts/manifests/pf_usecase_$(date +%Y%m%d).json
python run_pipeline.py scan --validate-fks
```

---

## Local acceptance test (no Impala)

```bash
cd synthetic_data_workflow_d3
pip install -r requirements.txt

python run_pipeline.py generate \
  --manifest schema_manifest.sample.json \
  --rows 1000 --seed 42 \
  --output /home/cdsw/artifacts/synthetic_output \
  --target-tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d

python run_pipeline.py evaluate \
  --manifest schema_manifest.sample.json \
  --output /home/cdsw/artifacts/synthetic_output \
  --report /home/cdsw/artifacts/eval_report.md \
  --target-tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d \
  --strict
```

Expected: **3/3 PASS**, tltx schema **PARTIAL** (wide-table NULL defaults).
