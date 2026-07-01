# IoT Agentic Use Cases — Two-Use-Case Summary

Quick reference for both workshop use cases: **UC1 — Predictive Maintenance** and
**UC2 — Predictive Quality Management**.

**Theme:** In both labs, **CAI Agent Studio agents orchestrate a classical ML model**
(served as a CAI Application REST endpoint) to turn an IoT alert in the Iceberg lakehouse
into an actionable work order. The LLM reasons and explains; a scikit-learn / XGBoost model
makes the prediction.

---

## At a glance

| | **UC1 — Predictive Maintenance** | **UC2 — Predictive Quality** |
|---|---|---|
| **Industry** | CNC machining shop | Bike manufacturing line |
| **Goal** | Predict machine failure before it happens | Predict defects before they leave the station |
| **Iceberg DB** | `iot_uc1_db` | `iot_uc2_db` |
| **Sensor scope** | 3-axis vibration (per machine) | Vibration, temp, sound, humidity, pressure, voltage |
| **Data sources** | Single OPC-UA stream | 3 sources unified (sensor + events + MES) |
| **ML model** | RandomForest **RUL regressor** | XGBoost **defect-rate regressor + risk classifier** |
| **ML output** | `rul_hours`, `risk_level`, `confidence` | `defect_rate`, `risk_level`, `confidence` |
| **Agents** | 2 (Health Monitor → Maintenance Planner) | 3 (Triage → Root-Cause → Recommendation) |
| **Custom tool** | RUL Prediction Tool | Quality Prediction Tool + NL-to-SQL Tool |
| **Intervention** | Maintenance work order | Production stop / rework / environmental adjustment |
| **Hands-on lab** | [UC1 workflow](uc1_predictive_maintenance_workflow.md) | [UC2 workflow](uc2_predictive_quality_workflow.md) |

---

## The shared pattern: agents + a classical ML model

Both use cases follow the same four-layer pattern. Only the model and the agent chain differ.

```
   Iceberg lakehouse            CAI Application              Agent Studio
   (seeded demo data)           (trained ML model)           (orchestration)
   ┌──────────────┐  train      ┌──────────────┐  REST       ┌──────────────┐
   │ sensor /     │ ──────────► │ *.pkl model  │ ◄────────── │ Prediction   │
   │ health tables│             │ POST /predict│             │ Tool → Agents│
   └──────────────┘             └──────────────┘             └──────┬───────┘
          ▲                                                          │
          │ NL-to-SQL queries (iceberg-mcp-server)                   │
          └──────────────────────────────────────────────────────────┘
                                                                      ▼
                                                          Work order JSON + narrative
```

| Layer | What it does | UC1 | UC2 |
|---|---|---|---|
| **Storage** | Seeded Iceberg tables the agents query | `vibration_readings`, `machine_health`, `rul_predictions` | `sensor_readings`, `quality_events`, `quality_predictions` |
| **Model** | Classical ML served as a REST endpoint | `iot_uc1_model/` RUL regressor | `iot_uc2_model/` regressor + classifier |
| **Tool** | Wraps the REST endpoint for Agent Studio | RUL Prediction Tool | Quality Prediction Tool |
| **Agents** | Investigate, predict, act | 2-agent chain | 3-agent chain |

> **Why a classical ML model and not the LLM?** RUL and defect-rate prediction are
> numeric regression/classification problems with labelled training data. A Random Forest
> or XGBoost model is accurate, fast, cheap, and reproducible — the right tool for the
> prediction. The LLM's job is to orchestrate the query, call the model, interpret the
> result, and draft the human-facing work order.

---

## UC1 — Predictive Maintenance (CNC Machining)

**Goal:** Turn a `machine_health` alert into a prioritised maintenance work order.

```
Alert → Health Monitor (query + RUL model) → Maintenance Planner (work order)
```

| Step | Agent | Tools | Output |
|---|---|---|---|
| 1. Assess | Health Monitor | `iceberg-mcp-server`, RUL Prediction Tool | Severity + RUL + evidence |
| 2. Plan | Maintenance Planner | Artifact Files | Work order JSON + fleet narrative |

**Demo anchors:** M02 spindle bearing CRITICAL (RUL 6.5h), M03 edge anomaly HIGH (RUL 18h),
M01 tool wear MEDIUM.

**YAML import:** `extra_materials/uc1_predictive_maintenance/agents.yaml` + `tasks.yaml`

---

## UC2 — Predictive Quality Management (Bike Manufacturing)

**Goal:** Turn a `quality_predictions` alert into a corrective action + MES work-order update.

```
Alert → Triage (model confirm) → Root-Cause (multi-source) → Recommendation (action)
```

| Step | Agent | Tools | Output |
|---|---|---|---|
| 1. Triage | Alert Triage | Quality Prediction Tool, `iceberg-mcp-server` | Severity + source routing |
| 2. Investigate | Root-Cause Investigator | NL-to-SQL Tool, `iceberg-mcp-server` | Root-cause hypothesis + evidence |
| 3. Recommend | Recommendation Agent | Artifact Files | Corrective action + work order JSON |

**Demo anchors:** CNC-01 frame welding crisis HIGH, PAINT-01 humidity drift MEDIUM,
BAT-01 battery thermal anomaly INVESTIGATE.

**YAML import:** `extra_materials/uc2_predictive_quality/agents.yaml` + `tasks.yaml`

---

## Choosing where to start

| Question | Use case |
|---|---|
| Simplest agentic + ML demo (2 agents, single data source)? | **UC1** |
| Multi-source correlation + 3-agent investigation chain? | **UC2** |
| Show a regression model (RUL hours) inside an agent? | **UC1** |
| Show a classifier (risk level) + NL-to-SQL across tables? | **UC2** |

---

## Suggested workshop progression

| Session | Use case | Outcome |
|---|---|---|
| 1 | **UC1** | Understand seed → train → serve → tool → 2-agent workflow |
| 2 | **UC2** | Extend to 3 agents, multi-source correlation, classifier + NL-to-SQL |

---

## Documentation index

| Document | Purpose |
|---|---|
| [IOT_USE_CASES_SUMMARY.md](IOT_USE_CASES_SUMMARY.md) | This page — two-use-case comparison |
| [IOT_DEMO_GUIDE.md](IOT_DEMO_GUIDE.md) | Presenter cheat sheet |
| [uc1_predictive_maintenance_workflow.md](uc1_predictive_maintenance_workflow.md) | UC1 hands-on lab |
| [uc2_predictive_quality_workflow.md](uc2_predictive_quality_workflow.md) | UC2 hands-on lab |

---

## Source of truth

Workshop materials are maintained in the **SP_hol** repository under
`extra_materials/iot_use_cases/` and synced to
`Handson_labs/ARTC_iot_use_cases_lab_07_July/` for delivery.
