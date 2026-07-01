# ARTC IoT Agentic Use Cases Lab — 07 July 2025

Hands-on lab covering **two industrial IoT use cases** where a **CAI Agent Studio workflow
orchestrates a classical ML model** (served as a CAI Application) to turn a sensor alert in
the Iceberg lakehouse into an actionable work order.

- **UC1 — Predictive Maintenance** (CNC machining): vibration → RUL regression → maintenance work order
- **UC2 — Predictive Quality Management** (bike manufacturing): multi-sensor → defect classifier → corrective action

---

## Quick start — where to begin

| Audience | Start here |
|---|---|
| **Overview — both use cases** | [`Instructions/IOT_USE_CASES_SUMMARY.md`](Instructions/IOT_USE_CASES_SUMMARY.md) |
| **Presenter / demo walkthrough** | [`Instructions/IOT_DEMO_GUIDE.md`](Instructions/IOT_DEMO_GUIDE.md) |
| **Workshop participant — UC1** (2-agent maintenance workflow + RUL model) | [`Instructions/uc1_predictive_maintenance_workflow.md`](Instructions/uc1_predictive_maintenance_workflow.md) |
| **Workshop participant — UC2** (3-agent quality workflow + defect model) | [`Instructions/uc2_predictive_quality_workflow.md`](Instructions/uc2_predictive_quality_workflow.md) |

---

## The pattern

Both use cases teach the same architecture — **agents orchestrate, a classical ML model predicts:**

```
Iceberg (seeded demo data)  →  train  →  ML model (*.pkl)  →  CAI Application REST endpoint
                                                                      ▲
                                                                      │ called as a tool
                                              Agent Studio workflow ──┘  →  work order JSON
```

> The prediction (RUL hours, defect rate, risk level) comes from a **scikit-learn /
> XGBoost** model — not the LLM. The LLM queries the lakehouse, calls the model, interprets
> the result, and drafts the work order. See the
> [summary](Instructions/IOT_USE_CASES_SUMMARY.md) for the full comparison.

---

## Project layout

```
ARTC_iot_use_cases_lab_07_July/
│
├── Instructions/                          ← Hands-on lab walkthroughs (all markdown here)
│   ├── IOT_USE_CASES_SUMMARY.md           ★ Two-use-case comparison (start here)
│   ├── IOT_DEMO_GUIDE.md                  Presenter cheat sheet
│   ├── uc1_predictive_maintenance_workflow.md
│   └── uc2_predictive_quality_workflow.md
│
├── images/                                ← Architecture diagrams embedded by Instructions
│   ├── uc1_predictive_maintenance/architecture.png
│   └── uc2_predictive_quality/architecture.png
│
├── extra_materials/                       ← Agent/task YAML (CrewAI import)
│   ├── uc1_predictive_maintenance/        agents.yaml + tasks.yaml (2 agents)
│   └── uc2_predictive_quality/            agents.yaml + tasks.yaml (3 agents)
│
├── uc1_demo_data/                         ← UC1 CSVs + generator + Impala seed scripts
├── uc2_demo_data/                         ← UC2 CSVs + generator + Impala seed scripts
├── iot_uc1_model/                         ← UC1 RUL model: train, serve (FastAPI), tool, deploy
└── iot_uc2_model/                         ← UC2 quality model: train, serve (FastAPI), tool, deploy
```

---

## End-to-end setup (per use case)

Each use case is built in five moves. Full detail is in the workflow docs.

| Step | UC1 | UC2 |
|---|---|---|
| 1. Seed Iceberg | `uc1_demo_data/` scripts → `iot_uc1_db` | `uc2_demo_data/` scripts → `iot_uc2_db` |
| 2. Train model | `iot_uc1_model/train_rul_model.py` | `iot_uc2_model/train_quality_model.py` |
| 3. Serve + deploy | `iot_uc1_model/{run_app,deploy_app}.py` | `iot_uc2_model/{run_app,deploy_app}.py` |
| 4. Register tool | `iot_uc1_model/tool.py` (RUL Prediction Tool) | `iot_uc2_model/tool.py` (Quality Prediction Tool) |
| 5. Build workflow | Import `extra_materials/uc1_predictive_maintenance/*.yaml` | Import `extra_materials/uc2_predictive_quality/*.yaml` |

---

## ML model quick start

```bash
# UC1 — RUL regressor
cd iot_uc1_model
pip install -r requirements.txt
python train_rul_model.py          # → rul_model.pkl
python run_app.py                  # → POST /predict, GET /health on :8080

# UC2 — defect-rate regressor + risk classifier
cd iot_uc2_model
pip install -r requirements.txt
python train_quality_model.py      # → quality_regressor.pkl, quality_classifier.pkl
python run_app.py                  # → POST /predict, GET /health on :8080
```

Deploy each as a CAI Application with `deploy_app.py` (run as a CAI Job), then register the
matching `tool.py` in Agent Studio pointed at the app URL.

---

## Impala connection parameters

| Parameter | Value |
|---|---|
| Host | `hue-impala-gateway.datalake.bdqdgc.c0.cloudera.site` |
| Port | `443` |
| Auth | LDAP / PLAIN + SSL + HTTP (`http_path=cliservice`) |
| Database | `iot_uc1_db` (UC1) / `iot_uc2_db` (UC2) |
| User / Password | Provided by instructor |

---

## Diagrams

Architecture PNGs are pre-rendered under `images/`. Mermaid sources live in the **SP_hol**
repository under `extra_materials/iot_use_cases/architecture_diagrams.md`.

---

## Source of truth

Workshop materials are maintained in the **SP_hol** repository under
`extra_materials/iot_use_cases/` and synced here for delivery.
