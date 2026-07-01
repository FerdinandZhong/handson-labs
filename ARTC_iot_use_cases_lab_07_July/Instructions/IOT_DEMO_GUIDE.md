# IoT Use Cases — Presenter Cheat Sheet

A fast reference for delivering the **ARTC IoT agentic use case** lab. Both use cases share
one story: **an Agent Studio workflow calls a classical ML model to turn an IoT alert into a
work order.**

---

## Recommended demo order

Lead with **UC1** — it is the most tangible (2 agents, single data source, a clean RUL
number). Follow with **UC2** to show multi-source correlation and a 3-agent chain.

| Order | Use case | Why |
|---|---|---|
| 1 | **UC1 — Predictive Maintenance** | Simplest end-to-end: one alert, one model call, one work order |
| 2 | **UC2 — Predictive Quality** | Builds on UC1: classifier + NL-to-SQL + 3-agent investigation |

---

## The one-sentence pitch

> "Streaming sensor data lands in Iceberg; a classical ML model trained on that data is
> served as a REST endpoint; and an Agent Studio workflow calls the model as a tool,
> correlates the lakehouse history, and drafts the maintenance or quality work order —
> autonomously."

---

## Pre-flight checklist

| # | Check | Command / action |
|---|---|---|
| 1 | Iceberg seeded (UC1) | `SELECT COUNT(*) FROM iot_uc1_db.machine_health` → 288 |
| 2 | Iceberg seeded (UC2) | `SELECT COUNT(*) FROM iot_uc2_db.sensor_readings` → 1152 |
| 3 | UC1 model serves | `curl <uc1-app-url>/health` → `rul_regressor`, `loaded:true` |
| 4 | UC2 model serves | `curl <uc2-app-url>/health` → `quality_predictor`, `loaded:true` |
| 5 | Tools registered | RUL Prediction Tool + Quality Prediction Tool point at the app URLs |
| 6 | Workflows imported | UC1 (2 agents) + UC2 (3 agents) from `extra_materials/*/agents.yaml`/`tasks.yaml` |

---

## UC1 — talking points and the money shot

**Inputs:** `machine_id=M02`, `alert_timestamp=2025-06-24T14:30:00Z`, `health_score=38.5`

1. **The alert** — M02's health crashed to 38.5; Z-axis vibration is spiking. "Is this a
   real spindle-bearing failure, and how long do we have?"
2. **The query** — Health Monitor pulls ~60 min of M02 history from Iceberg via NL-to-SQL.
3. **The money shot** — the RUL Prediction Tool returns **6.5 hours, CRITICAL,
   confidence 0.94**. Point out this is a *Random Forest regressor*, not the LLM guessing.
4. **The action** — Maintenance Planner drafts an immediate bearing-replacement work order
   with a downtime window, written to `work_order_M02.json`.

**Backup scenarios:** M03 edge anomaly (HIGH, RUL 18h), M01 tool wear (MEDIUM, RUL 42h).

---

## UC2 — talking points and the money shot

**Inputs:** `machine_id=CNC-01`, `alert_timestamp=2025-06-24T10:15:00Z`,
`defect_rate=0.21`, `risk_level=HIGH`

1. **The alert** — a HIGH defect-rate prediction on the CNC frame-welding station.
2. **Model confirmation** — Alert Triage calls the Quality Prediction Tool; XGBoost returns
   `defect_rate≈0.22, HIGH`. Confirms the alert is real, routes the investigation.
3. **The money shot** — Root-Cause Investigator pivots `sensor_readings` and finds
   **vibration and temperature rising together**, correlated with `WELD-001` defects in
   `quality_events` → **worn welding tip**. Multi-source correlation in action.
4. **The action** — Recommendation Agent drafts a production-stop + tool-change work order,
   written to `work_order_CNC-01.json`.

**Backup scenarios:** PAINT-01 humidity drift (MEDIUM → HVAC), BAT-01 thermal anomaly
(INVESTIGATE → cooling inspection).

---

## Common questions

| Question | Answer |
|---|---|
| "Is the prediction the LLM?" | No — it's a trained scikit-learn/XGBoost model served as a REST endpoint. The agent *calls* it. |
| "Where does the training data come from?" | The same Iceberg tables, seeded deterministically (`seed=42`) from the bundled CSVs. |
| "Is this production-ready?" | The pattern is. The demo data is synthetic and scoped to one 8–12h shift for a clean story. |
| "Could it write back to the real MES?" | UC2's work-order JSON is designed for MES write-back via Kafka/NiFi (pre-built layer, out of demo scope). |
| "What if the model endpoint is down?" | The tool returns a clear error string; the agent reports it rather than hallucinating a number. |

---

## Reset between runs

The workflows are read-only against Iceberg and write only Artifact Files, so no reset is
needed between Test sessions. To re-seed from scratch, re-run
`generate_demo_data_uc*.py` → `create_impala_tables_uc*.py` → `load_data_to_impala_uc*.py`.

---

## Source of truth

Workshop materials are maintained in the **SP_hol** repository under
`extra_materials/iot_use_cases/` and synced to
`Handson_labs/ARTC_iot_use_cases_lab_07_July/` for delivery.
