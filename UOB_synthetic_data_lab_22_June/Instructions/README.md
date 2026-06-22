# Synthetic Data Generation — Instructions

Hands-on lab walkthroughs and reference docs for the **22 June 2026** workshop.

| Document | Purpose |
|---|---|
| [**SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md**](SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md) | Four-direction comparison — **start here** |
| [**SYNTHETIC_DATA_DEMO_GUIDE.md**](SYNTHETIC_DATA_DEMO_GUIDE.md) | Presenter cheat sheet |
| [synthetic_data_d1_workflow.md](synthetic_data_d1_workflow.md) | D1 — Purely Agent Studio (5 agents) |
| [synthetic_data_d2_workflow.md](synthetic_data_d2_workflow.md) | D2 — Agent Studio + SDS |
| [synthetic_data_d2_5_workflow.md](synthetic_data_d2_5_workflow.md) | D2.5 — Script authoring (no execution) |
| [synthetic_data_d3_workflow.md](synthetic_data_d3_workflow.md) | D3 — Production pipeline + CAI Application |

Agent/task YAML specs live under `../extra_materials/synthetic_data_workflow_d*/`.

> **Production ML training data:** only [D3](synthetic_data_d3_workflow.md) (deterministic CML Jobs).
> D1, D2, and D2.5 are workshop directions — see
> [SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md § Why only D3 is suitable for production](SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md#why-only-d3-is-suitable-for-production).

## Code and ops docs (project root)

| Resource | Path |
|---|---|
| D3 CML Jobs | [`../synthetic_data_workflow_d3/CML_JOBS.md`](../synthetic_data_workflow_d3/CML_JOBS.md) |
| D3 agentic plan | [`../synthetic_data_workflow_d3/D3_AGENTIC_REDESIGN_PLAN.md`](../synthetic_data_workflow_d3/D3_AGENTIC_REDESIGN_PLAN.md) |
| D3 CAI Application | [`../synthetic_data_app/`](../synthetic_data_app/) |
