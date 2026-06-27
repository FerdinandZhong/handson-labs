# UOB AI Studios Lab

Welcome to the hands-on lab demonstrating how Cloudera's three AI studios work
**together**. Agent Studio is the orchestrator; RAG Studio serves knowledge bases;
Synthetic Data Studio manufactures privacy-safe data. This lab shows them combined in
two focused demos and one end-to-end capstone.

## The three studios

| Studio | Role in this lab | Guide |
|--------|------------------|-------|
| **Agent Studio** | Orchestrates sequential multi-agent workflows; calls every tool | [Agent Studio](studios/agent_studio.md) |
| **RAG Studio** | Ingests documents into knowledge bases and answers queries | [RAG Studio](studios/rag_studio.md) |
| **Synthetic Data Studio** | Generates and evaluates privacy-safe synthetic data | [Synthetic Data Studio](studios/synthetic_data_studio.md) |

## The demos

| Demo | Studios linked | What it shows |
|------|----------------|---------------|
| [**Demo A — Agent + RAG**](demos/agent_rag_demo.md) | Agent ⇄ RAG | A 5-task workflow that generates ground-truth Q&A, uploads a document to RAG Studio, queries it, and scores retrieval + generation quality. |
| [**Demo B — Agent + Synthetic Data**](demos/agent_synthetic_demo.md) | Agent ⇄ SDS | A 4-task workflow that discovers a lakehouse schema, generates synthetic rows via SDS, enforces FK integrity, and scores quality with an LLM judge. |
| [**Capstone — All Three**](demos/capstone_three_studios.md) | Agent ⇄ SDS ⇄ RAG | A 6-task workflow where SDS manufactures a synthetic corpus, RAG ingests it, and Agent Studio evaluates the resulting RAG chatbot — no real data required. |

## How the studios link

```
  Synthetic Data Studio  ──generate──▶  (synthetic corpus)  ──upload──▶  RAG Studio
            ▲                                                                │
            │                                                              query
            └──────────────── Agent Studio orchestrates ───────────────────┘
                         (ground truth · verification · evaluation)
```

- **Demo A** exercises the right side of the diagram (Agent ⇄ RAG).
- **Demo B** exercises the left side (Agent ⇄ SDS).
- **The Capstone** connects all three into one loop.

## Integration tools

Both custom Agent Studio tools ship with this lab under `tools/` and are documented here:

- [RAG Studio Tool](tools/rag_studio_tool.md) — `query`, `upload_document`, and more.
- [Synthetic Data Studio Tool](tools/synthetic_data_studio_tool.md) — `generate`, `evaluate`.

## Deep-dive: the Synthetic Data Lab

For the full four-direction synthetic-data curriculum (Agent Studio only, Agent + SDS,
script authoring, and the production CML Jobs pipeline), see the
[Synthetic Data Lab](synthetic_data_lab/SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md).

---

Ready to begin? Start with [Agent Studio](studios/agent_studio.md), then run
[Demo A](demos/agent_rag_demo.md).
