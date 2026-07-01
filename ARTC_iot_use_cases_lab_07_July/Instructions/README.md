# IoT Agentic Use Cases — Instructions

Hands-on lab walkthroughs and reference docs for the **ARTC IoT use cases — 07 July 2025**
workshop.

| Document | Purpose |
|---|---|
| [**IOT_USE_CASES_SUMMARY.md**](IOT_USE_CASES_SUMMARY.md) | Two-use-case comparison — **start here** |
| [**IOT_DEMO_GUIDE.md**](IOT_DEMO_GUIDE.md) | Presenter cheat sheet |
| [uc1_predictive_maintenance_workflow.md](uc1_predictive_maintenance_workflow.md) | UC1 — Predictive Maintenance (2 agents + RUL model) |
| [uc2_predictive_quality_workflow.md](uc2_predictive_quality_workflow.md) | UC2 — Predictive Quality (3 agents + defect model) |

Agent/task YAML specs live under `../extra_materials/uc1_predictive_maintenance/` and
`../extra_materials/uc2_predictive_quality/`.

> **The shared pattern:** Agent Studio agents orchestrate a **classical ML model**
> (scikit-learn / XGBoost) served as a CAI Application REST endpoint. The LLM reasons and
> drafts the work order; the ML model makes the numeric prediction. See
> [IOT_USE_CASES_SUMMARY.md § The shared pattern](IOT_USE_CASES_SUMMARY.md#the-shared-pattern-agents--a-classical-ml-model).

## Code and data (lab root)

| Resource | Path |
|---|---|
| UC1 demo data + Impala seed scripts | [`../uc1_demo_data/`](../uc1_demo_data/) |
| UC2 demo data + Impala seed scripts | [`../uc2_demo_data/`](../uc2_demo_data/) |
| UC1 RUL model (train / serve / tool / deploy) | [`../iot_uc1_model/`](../iot_uc1_model/) |
| UC2 quality model (train / serve / tool / deploy) | [`../iot_uc2_model/`](../iot_uc2_model/) |
