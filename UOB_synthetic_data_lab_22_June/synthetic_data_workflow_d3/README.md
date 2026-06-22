# Direction 3 — Synthetic Data Pipeline

Production path for ML training data. Two execution modes share the same CAI Application.

| Mode | Entry point | LLM at runtime? |
|---|---|---|
| **Deterministic** | `run_pipeline.py` / `/pipeline/*` | No |
| **Agentic** | `synthetic_data_crew.py` / `/agent/*` | Yes (CrewAI) |

## Files in this folder

| File | Purpose |
|---|---|
| `describe_to_manifest.py` | Scan Impala → `schema_manifest.json` |
| `generate_synthetic_data.py` | Deterministic generation |
| `evaluate_synthetic_data.py` | FK, PII, distribution checks |
| `run_pipeline.py` | CLI orchestrator |
| `schema_manifest.sample.json` | Sample manifest for local demo |
| `CML_JOBS.md` | CML Job definitions |
| `D3_AGENTIC_REDESIGN_PLAN.md` | Agentic mode design |

## Workshop-only YAML (not production runtime)

`agents.yaml` and `tasks.yaml` are for an **optional Agent Studio workshop** only.
Production uses `../synthetic_data_app/synthetic_data_crew.py` (agentic) or the Python
scripts above as CML Jobs (deterministic).

## Documentation

| Doc | Path |
|---|---|
| D3 hands-on lab | [`../../Instructions/synthetic_data_d3_workflow.md`](../../Instructions/synthetic_data_d3_workflow.md) |
| CAI Application | [`../synthetic_data_app/README.md`](../synthetic_data_app/README.md) |

Diagram PNGs for instruction embeds: `../../images/synthetic_data_workflow_d3/`

## Quick local demo

Run from this folder or copy scripts locally. Sample outputs are generated on first run
under `artifacts/`.

```bash
pip install -r requirements.txt

python run_pipeline.py generate \
  --manifest schema_manifest.sample.json \
  --target-tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d \
  --rows 1000 --seed 42 --output /home/cdsw/artifacts/synthetic_output

python run_pipeline.py evaluate \
  --manifest schema_manifest.sample.json \
  --output /home/cdsw/artifacts/synthetic_output \
  --report /home/cdsw/artifacts/eval_report.md \
  --tables eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d \
  --strict
```
