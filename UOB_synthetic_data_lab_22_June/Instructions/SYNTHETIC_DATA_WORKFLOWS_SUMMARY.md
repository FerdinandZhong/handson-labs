# Synthetic Data Generation — Four Workflow Summary

Quick reference for all workshop directions: **D1**, **D2**, **D2.5**, and **D3**.

**Use case:** Generate PII-free synthetic training data that mirrors the `pf_usecase`
Impala lakehouse (73 tables across BWC, RBK, REM, AMH, BRM, PIB, RLP, SSS) while
preserving schema shape, referential integrity, and statistical fidelity — without
exporting real customer or transactional data.

---

## At a glance

| | **D1** | **D2** | **D2.5** | **D3** |
|---|---|---|---|---|
| **Name** | Purely Agent Studio | Agent Studio + SDS | Agent Studio script authoring | Production pipeline |
| **Where it runs** | Agent Studio UI | Agent Studio UI + SDS CAI app | Agent Studio UI only | CAI Workbench (`run_pipeline.py`, CAI Application) |
| **Agents / steps** | 5 agents, 5 tasks | 4 agents, 4 tasks | 4 agents, 4 tasks | 3 deterministic steps; **5 agents** in agentic mode |
| **LLM at runtime** | Yes (all agents) | Yes (agents + SDS judge) | Yes (authoring only) | Optional — agentic mode only |
| **Primary output** | CSV files per table | JSON rows per table | Python scripts + manifest | CSV files + evaluation report |
| **Executes generation?** | Yes — in workflow | Yes — via SDS API | **No** — stops at scripts | Yes — scripts / CML Jobs |
| **FK enforcement** | Agent 4 CSV overwrite | Prompt-constrained (best-effort) | Encoded in generated scripts | Deterministic `pandas` code |
| **Typical row volume** | 100–10k (scoped) | ≤ 25 per SDS call (demo) | N/A (no rows produced) | Unlimited (`--rows`, batch Jobs) |
| **Hands-on lab** | [D1 workflow](synthetic_data_d1_workflow.md) | [D2 workflow](synthetic_data_d2_workflow.md) | [D2.5 workflow](synthetic_data_d2_5_workflow.md) | [D3 workflow](synthetic_data_d3_workflow.md) |

---

## Common artefacts

Every direction ultimately aims to produce some combination of:

| Artefact | D1 | D2 | D2.5 | D3 |
|---|---|---|---|---|
| Schema manifest (`schema_manifest.json`) | ✓ (in-session JSON) | ✓ | ✓ (Artifact Files) | ✓ (scan step) |
| Synthetic data files | CSV | JSON | — (scripts only) | CSV |
| Evaluation report | Per-table scorecard | SDS 1–5 row scores | — (eval script only) | Markdown scorecard |
| Generation / eval code | — | — | `generate_*.py`, `evaluate_*.py` | Bundled + agent-authored scripts |

**Workflow inputs (Agent Studio directions):** `{target_tables}`, `{database}`, `{rows_per_table}` (D1/D2/D2.5); D2.5 also uses `{seed}`.

---

## Direction 1 — Purely Agent Studio

**Goal:** Build a complete synthetic-data pipeline entirely inside Agent Studio — no
Synthetic Data Studio, no external generation service, no compiled Python pipeline.

```
Scan → Map FKs → Generate CSVs → Patch FK columns → Evaluate
```

| Step | Agent | Tools | Output |
|---|---|---|---|
| 1. Schema profile | Schema Analyst | `iceberg-mcp-server` | Column types, stats, PII flags |
| 2. Relationships | Relationship Mapper | `iceberg-mcp-server` | FK map, generation order |
| 3. Generate | Synthetic Data Generator | Artifact Files, `csv_reader` | `/synthetic_output/<table>_synthetic.csv` |
| 4. FK integrity | Integrity Linker | Artifact Files, `csv_reader` | Patched CSVs + validation report |
| 5. Quality | Quality Evaluator | Artifact Files, `csv_reader` | Statistical scorecard |

**Strengths:** Full Agent Studio workshop; teaches schema profiling, FK reasoning, and
data quality evaluation interactively.

**Limits:** Row generation is LLM-driven (slower, less reproducible than code); scoped
volumes for workshop runs.

**YAML import:** `extra_materials/synthetic_data_workflow_d1/agents.yaml` + `tasks.yaml`

---

## Direction 2 — Agent Studio + Synthetic Data Studio (SDS)

**Goal:** Use Agent Studio to orchestrate **Cloudera Synthetic Data Studio** — a deployed
CAI Application — for row generation and LLM-as-judge evaluation.

```
Scan → Build prompts → SDS generate (FK order) → SDS evaluate
```

| Step | Agent | Tools | Output |
|---|---|---|---|
| 1. Scan | Schema & Relationship Scanner | `iceberg-mcp-server` | Schema manifest + FK map |
| 2. Prompts | Prompt Builder | LLM only | `schema_json`, `sample_values_json`, prompts |
| 3. Generate | SDS Generation Orchestrator | `synthetic_data_studio_tool` | JSON rows per table |
| 4. Evaluate | SDS Evaluation Collator | `synthetic_data_studio_tool` | 1–5 quality scores per row |

**Strengths:** Showcases SDS integration; built-in quality scoring; good for demos.

**Limits:** SDS demo mode caps rows per call (~25); FK consistency is prompt-guided,
not guaranteed like D1 CSV patching or D3 code.

**Prerequisite:** Deploy SDS CAI app + register `synthetic_data_studio_tool` in Agent Studio.

**YAML import:** `extra_materials/synthetic_data_workflow_d2/agents.yaml` + `tasks.yaml`

---

## Direction 2.5 — Agent Studio script authoring (D3 pipeline, no execution)

**Goal:** Same logical pipeline as **D3 agentic mode (Agents 1–4)**, but runs in
Agent Studio and **stops after writing Python scripts** — no script execution, no CML Jobs.

```
Scan → Generation strategy → Evaluation strategy → Write scripts  ← STOP
```

| Step | Agent | Tools | Output |
|---|---|---|---|
| 1. Scan | Schema and Relationship Scanner | `iceberg-mcp-server`, Artifact Files | `schema_manifest.json` |
| 2. Plan generation | Python Generation Strategist | LLM only | Strategy JSON (faker / SDV) |
| 3. Plan evaluation | Statistical Evaluation Strategist | LLM only | Evaluation plan JSON |
| 4. Write scripts | Python Script Writer | Artifact Files | Timestamped `generate_*.py`, `evaluate_*.py` |

**Strengths:** Learn the D3 agentic design interactively; inspect and edit scripts
before anything runs; no CAI Application deployment required.

**Limits:** Produces no CSV data or eval report by itself — hand off to D3 deterministic
mode after downloading artifacts.

**Not included:** Agent 5 (verifier + CML dispatch), CAI Workbench MCP, CrewAI app.

**YAML import:** `extra_materials/synthetic_data_workflow_d2_5/agents.yaml` + `tasks.yaml`

---

## Direction 3 — Production pipeline (deterministic + agentic)

**Goal:** Production path for **ML training data** — scan Impala, generate CSVs at scale,
evaluate statistically, optionally automate the full loop with a CrewAI crew.

### Deterministic mode (no LLM)

| Step | Script | Trigger | Output |
|---|---|---|---|
| 1. Scan | `describe_to_manifest.py` | `run_pipeline.py scan` | `schema_manifest.json` |
| 2. Generate | `generate_synthetic_data.py` | `run_pipeline.py generate` | CSV per table |
| 3. Evaluate | `evaluate_synthetic_data.py` | `run_pipeline.py evaluate` | `eval_report.md` |

Runs via CLI, CML Jobs, or CAI Application `/pipeline/*` endpoints. Fully reproducible
with `--seed`.

### Agentic mode (CrewAI — 5 agents)

Same first four steps as D2.5, plus:

| Step | Agent | Tools | Output |
|---|---|---|---|
| 5. Verify + run | Script Verifier | CmlJobTool, Artifact Files | Executes scripts; CSVs + report |

Triggered via CAI Application `/agent/kickoff`. Auto-dispatches CML Jobs when Workbench
credentials are configured.

**Strengths:** Scale to full 73-table lakehouse via batch CML Jobs; bit-reproducible
deterministic runs; end-to-end automation in agentic mode.

**Limits:** Requires CAI Workbench project setup; agentic mode needs LLM + Workbench API
credentials.

**Key paths:**

| Resource | Path |
|---|---|
| Pipeline scripts | `synthetic_data_workflow_d3/` |
| CAI Application | `synthetic_data_app/` |
| CML Job definitions | `synthetic_data_workflow_d3/CML_JOBS.md` |

---

## How the directions relate

```
                    ┌─────────────────────────────────────────┐
                    │         pf_usecase Impala schema         │
                    └─────────────────┬───────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
   ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
   │     D1      │            │     D2      │            │    D2.5     │
   │ Agent Studio│            │ Agent Studio│            │ Agent Studio│
   │  → CSV      │            │  → SDS JSON │            │  → .py only │
   └─────────────┘            └─────────────┘            └──────┬──────┘
                                                                │
                                                                │ download scripts
                                                                ▼
                                                         ┌─────────────┐
                                                         │     D3      │
                                                         │ deterministic│
                                                         │  → CSV      │
                                                         │ agentic     │
                                                         │  → auto-run │
                                                         └─────────────┘
```

- **D1** and **D2** are self-contained Agent Studio workshops with different generation backends.
- **D2.5** mirrors D3 agentic Agents 1–4 — a teaching step before production.
- **D3 deterministic** runs existing scripts (bundled or agent-authored from D2.5).
- **D3 agentic** is D2.5 + Agent 5 + CML dispatch in one automated crew.

---

## Choosing a direction

| Question | Recommended direction |
|---|---|
| First Agent Studio workshop — learn schema + FK + CSV generation? | **D1** |
| Demo Cloudera Synthetic Data Studio integration? | **D2** |
| Learn D3 agentic design without deploying the CAI app? | **D2.5** |
| Scripts already exist and you need reproducible CSV output? | **D3 deterministic** |
| New database, unknown schema, full automation? | **D3 agentic** |
| Need 73-table scale-out via parallel CML Jobs? | **D3** |
| Want to review agent-authored code before any execution? | **D2.5**, then **D3 deterministic** |

---

## Suggested workshop progression

| Session | Direction | Outcome |
|---|---|---|
| 1 | **D1** | Understand Impala profiling, FK order, CSV generation in Agent Studio |
| 2 | **D2** | See SDS as an external generation service orchestrated by agents |
| 3 | **D2.5** | Author `generate_*.py` + `evaluate_*.py` + manifest interactively |
| 4 | **D3** | Run scripts at production scale; deploy CAI Application; optional agentic mode |

Participants who skip D2.5 can go directly to **D3 agentic** for end-to-end automation,
or **D3 deterministic** if using the bundled reference scripts.

---

## Documentation index

| Document | Purpose |
|---|---|
| [SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md](SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md) | This page — four-direction comparison |
| [synthetic_data_d1_workflow.md](synthetic_data_d1_workflow.md) | D1 hands-on lab |
| [synthetic_data_d2_workflow.md](synthetic_data_d2_workflow.md) | D2 hands-on lab |
| [synthetic_data_d2_5_workflow.md](synthetic_data_d2_5_workflow.md) | D2.5 hands-on lab |
| [synthetic_data_d3_workflow.md](synthetic_data_d3_workflow.md) | D3 hands-on lab |
| [SYNTHETIC_DATA_DEMO_GUIDE.md](SYNTHETIC_DATA_DEMO_GUIDE.md) | Presenter cheat sheet |

---

## Source of truth

Workshop materials are maintained in the **SP_hol** repository under
`instructions/synthetic_data_generation/` and synced to
`Handson_labs/UOB_synthetic_data_lab_22_June/Instructions/` for delivery.
