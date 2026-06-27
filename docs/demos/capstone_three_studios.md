# Capstone — All Three Studios

This capstone chains **all three** Cloudera AI studios into a single Agent Studio
workflow. **Synthetic Data Studio (SDS)** manufactures a privacy-safe source corpus,
**RAG Studio** ingests and serves it as a knowledge base, and **Agent Studio**
orchestrates the whole run end-to-end — generating ground truth, querying RAG, and
scoring retrieval + generation quality.

It is the natural composition of the other two demos: Demo A
([Agent ⇄ RAG](agent_rag_demo.md)) evaluates a RAG system against ground truth, and
Demo B ([Agent ⇄ SDS](agent_synthetic_demo.md)) produces synthetic data. Here SDS's
output becomes the document that RAG indexes — so you can stand up and evaluate a RAG
chatbot **without ever touching real customer data**.

!!! note "Tools used"
    Both integration tools ship with this lab under `tools/`:
    [`rag_studio_tool`](../tools/rag_studio_tool.md) (actions `upload_document`, `query`)
    and [`synthetic_data_studio_tool`](../tools/synthetic_data_studio_tool.md)
    (action `generate`), plus the built-in `write_to_shared_pdf` for report artifacts.

## Workflow Overview

A **6-task sequential** Agent Studio workflow:

1. **Generate Synthetic Corpus** — SDS produces synthetic records/passages; write them to a source PDF.
2. **Generate Ground Truth** — read the synthetic corpus, produce Q&A pairs.
3. **Verify Quality** — validate and score the Q&A pairs.
4. **Ingest into RAG** — upload the synthetic corpus to a RAG Studio knowledge base.
5. **Query RAG** — run the validated questions against the knowledge base.
6. **Evaluate Results** — LLM-as-judge on retrieval + generation; emit a final report.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                  CAPSTONE — THREE-STUDIO SEQUENTIAL WORKFLOW (Agent Studio orchestrates)        │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                │
│   ┌─ SYNTHETIC DATA STUDIO ─┐   ┌──── AGENT STUDIO ────┐   ┌── RAG STUDIO ──┐   ┌─ AGENT STUDIO ─┐│
│   │                         │   │                      │   │                │   │                ││
│   │  ┌────────┐             │   │ ┌────────┐ ┌────────┐│   │  ┌────────┐    │   │ ┌────────┐     ││
│   │  │ TASK 1 │             │   │ │ TASK 2 │ │ TASK 3 ││   │  │ TASK 4 │    │   │ │ TASK 5 │     ││
│   │  │Generate│────────────────▶│ │Generate│▶│ Verify ││──▶│  │ Ingest │────────▶│ Query  │     ││
│   │  │ Synth. │  corpus PDF  │   │ │Ground  │ │Quality ││   │  │into RAG│    │   │ │  RAG   │     ││
│   │  │ Corpus │             │   │ │ Truth  │ │        ││   │  │  (KB)  │    │   │ └───┬────┘     ││
│   │  └───┬────┘             │   │ └────────┘ └────────┘│   │  └────────┘    │   │     │          ││
│   └──────┼──────────────────┘   └──────────────────────┘   └────────────────┘   │     ▼          ││
│          │                                                                       │ ┌────────┐     ││
│          ▼ synthetic_data_studio_tool                            rag_studio_tool │ │ TASK 6 │     ││
│      POST /synthesis/freeform        upload_document ──────────────────────────▶│ │Evaluate│     ││
│                                      query ─────────────────────────────────────│ │Results │     ││
│                                                                                  │ └────────┘     ││
│                                                                                  └────────────────┘│
│                                                                                                │
│  Agents:  1 Synthetic Corpus Builder → 2 Q&A Generator → 3 Q&A Verifier →                       │
│           4 RAG Document Uploader → 5 RAG Query Specialist → 6 RAG Evaluation Analyst           │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

The workflow crosses **two external integration surfaces** — SDS (generate) and RAG
Studio (upload + query) — with Agent Studio sequencing every step and the LLM doing the
ground-truth and evaluation reasoning in between.

---

## Task Definitions

### Task 1: Generate Synthetic Corpus

**Description:**
Use the `synthetic_data_studio_tool` with action `generate` to produce a set of
privacy-safe synthetic records or passages for the chosen domain (e.g. a synthetic
banking product FAQ, synthetic customer service notes, or synthetic policy summaries).
Drive generation from a short topic/schema description supplied in the `{domain_prompt}`
input variable. Then use the `write_to_shared_pdf` tool with `output_file` set to
`"synthetic_corpus.pdf"` and `markdown_content` containing the generated content,
formatted with headings and sections, to create the source document that RAG Studio
will ingest. No real customer data is read at any point.

**Expected Output:**
A JSON object containing:

- `corpus_summary`: number of synthetic items generated and the domain/topic
- `synthetic_items`: array of generated records/passages (each with an `id` and `text`)
- `pdf_artifact`: object with `status`, `file_path`, `file_name` (`synthetic_corpus.pdf`)

**Success Criteria:**

- SDS returns the requested synthetic content with no PII from any real source
- A well-formed `synthetic_corpus.pdf` is written via `write_to_shared_pdf`
- The corpus has enough breadth (≥ 8 distinct items/sections) to support diverse questions

---

### Task 2: Generate Ground Truth

**Description:**
Read the synthetic corpus produced in Task 1 (the `synthetic_corpus.pdf`, or the
`synthetic_items` text passed in context) and generate a comprehensive set of
question-answer pairs that serve as the ground-truth dataset for evaluating the RAG
system. The Q&A pairs must be diverse, covering different question types and difficulty
levels. Use the `write_to_shared_pdf` tool with `output_file` set to
`"qa_pairs_report.pdf"` to create a visual report of the pairs.

**Expected Output:**
A JSON object containing 5–10 Q&A pairs:

- `document_name`: `"synthetic_corpus.pdf"`
- `qa_pairs`: array of objects, each with `id`, `question`, `answer`, `type`
  (factual/reasoning/summarization/comparison), `source_reference`

**Success Criteria:**

- Minimum 5, maximum 10 Q&A pairs generated
- At least 2 different question types represented
- All answers are verifiable from the synthetic corpus
- Output is valid JSON

---

### Task 3: Verify Quality

**Description:**
Review and validate the Q&A pairs from Task 2 against the synthetic corpus to ensure
they meet quality standards. Verify each answer is factually accurate and grounded in
the corpus, assess clarity/completeness/difficulty classification, filter out
low-quality pairs, and assign quality scores. Use the `write_to_shared_pdf` tool with
`output_file` set to `"qa_verification_report.pdf"` to report the results.

**Expected Output:**
A JSON validation report containing:

- `validation_summary`: total pairs, approved count, flagged count, overall quality score, question-type coverage
- `validated_pairs`: each pair plus `quality_score` (0–1), `status` (`approved`/`flagged`), `issues`
- `recommendations`: improvement suggestions if needed

**Success Criteria:**

- Every Q&A pair from Task 2 is evaluated and scored
- Approved pairs have quality score ≥ 0.8
- At least 5 approved pairs available for downstream tasks

---

### Task 4: Ingest into RAG

**Description:**
Use the `rag_studio_tool` with action `upload_document` and `file_path` set to the
generated `synthetic_corpus.pdf` to upload the synthetic corpus to the configured RAG
Studio knowledge base. Ensure the document is successfully ingested and ready for
retrieval queries. This makes the synthetic corpus searchable by the RAG system.

**Expected Output:**
A JSON status report containing:

- `status`: `"success"` or `"failure"`
- `knowledge_base_name`, `knowledge_base_id`
- `document_name`: `"synthetic_corpus.pdf"`
- `message`, `timestamp`

**Success Criteria:**

- Upload completes without errors and is confirmed by the RAG Studio API
- The knowledge base is correctly identified
- Document is queryable (allow time for chunking + embedding)

---

### Task 5: Query RAG

**Description:**
For each approved question from the validated Q&A pairs, use the `rag_studio_tool` with
action `query` and the `query` parameter set to the question text. Execute all queries
against the RAG Studio knowledge base and collect both the RAG-generated answers and the
retrieved source chunks for each query.

**Expected Output:**
A JSON object with `query_results`: an array of objects, each with `id`, `question`,
`ground_truth_answer`, `rag_answer`, `retrieved_chunks`, `question_type`.

**Success Criteria:**

- All approved Q&A pairs are queried
- Each query returns a RAG-generated answer and its retrieved chunks
- No query timeouts or API errors
- Results retain traceability to the original Q&A pair IDs

---

### Task 6: Evaluate Results

**Description:**
Perform a comprehensive evaluation of RAG performance by comparing RAG outputs against
the ground-truth answers. Apply retrieval and generation metrics, generate per-question
scores and overall summary statistics, and use the `write_to_shared_pdf` tool with
`output_file` set to `"capstone_evaluation_report.pdf"` to produce the final report.

**Expected Output:**
A JSON evaluation report containing:

- `evaluation_summary`: `total_questions`, `avg_context_relevance`, `avg_faithfulness`,
  `avg_answer_relevance`, `avg_semantic_similarity`, `avg_correctness`
- `detailed_results`: per-question scores + reasoning
- `recommendations`: actionable insights, including whether the synthetic corpus was
  sufficient for high-quality retrieval

**Success Criteria:**

- All query results from Task 5 are evaluated against all five metrics
- Scores are within range (0–1) with reasoning for each
- Summary statistics are correctly aggregated
- The report closes the loop: synthetic data → RAG → measurable quality

---

## Agent Definitions

### Agent 1: Synthetic Corpus Builder

| Attribute | Value |
|-----------|-------|
| **Name** | Synthetic Corpus Builder |
| **Role** | Privacy-Safe Source Data Generator |

**Backstory:**
You specialize in producing realistic but entirely synthetic content for testing AI
systems. You understand that demonstrating a RAG pipeline on real customer documents is
often impossible for privacy and compliance reasons, so you manufacture a faithful
stand-in: synthetic passages that read like the real domain but contain no real PII.
Your corpus is the foundation the rest of the pipeline depends on.

**Goal:**

1. Read the `{domain_prompt}` describing the desired corpus (domain, topics, style).
2. Call `synthetic_data_studio_tool` (action `generate`) to produce synthetic items.
3. Format the items into a structured document and write `synthetic_corpus.pdf` via `write_to_shared_pdf`.
4. Output a JSON summary of what was generated and the PDF artifact path.

**Output Format:**
```json
{
  "corpus_summary": {"domain": "retail banking FAQ", "item_count": 10},
  "synthetic_items": [{"id": 1, "text": "..."}],
  "pdf_artifact": {"status": "success", "file_path": "/.../synthetic_corpus.pdf", "file_name": "synthetic_corpus.pdf"}
}
```

---

### Agent 2: Q&A Generator

| Attribute | Value |
|-----------|-------|
| **Name** | Q&A Generator |
| **Role** | Ground Truth Dataset Creator |

**Backstory:**
You are an expert at reading documents and formulating diverse, high-quality question-
answer pairs that thoroughly test a RAG system's retrieval and generation. You know that
good evaluation needs a spread of question types — from simple factual lookups to
reasoning, summarization, and comparison.

**Goal:**

1. Read the synthetic corpus produced by Agent 1.
2. Generate 5–10 Q&A pairs spanning factual, reasoning, summarization, and comparison types.
3. Write a `qa_pairs_report.pdf` and output the pairs as JSON for downstream tasks.

**Output Format:**
```json
{
  "document_name": "synthetic_corpus.pdf",
  "qa_pairs": [
    {"id": 1, "question": "...", "answer": "...", "type": "factual", "source_reference": "Item 3"}
  ]
}
```

---

### Agent 3: Q&A Verifier

| Attribute | Value |
|-----------|-------|
| **Name** | Q&A Verifier |
| **Role** | Ground Truth Quality Assurance Specialist |

**Backstory:**
You have a keen eye for subtle errors in datasets. You know that a flawed Q&A pair
produces misleading evaluation results, so you rigorously validate each pair against the
source corpus before it proceeds.

**Goal:**

1. Validate each Q&A pair against the synthetic corpus for accuracy, clarity, completeness, and type match.
2. Assign a quality score (0–1) and flag issues.
3. Write a `qa_verification_report.pdf` and output the validation report as JSON, with ≥ 5 approved pairs.

**Output Format:**
```json
{
  "validation_summary": {"total_pairs": 10, "approved": 8, "flagged": 2, "overall_quality_score": 0.86},
  "validated_pairs": [{"id": 1, "quality_score": 0.95, "status": "approved", "issues": []}],
  "recommendations": ["..."]
}
```

---

### Agent 4: RAG Document Uploader

| Attribute | Value |
|-----------|-------|
| **Name** | RAG Document Uploader |
| **Role** | RAG Knowledge Base Manager |

**Backstory:**
You manage documents in the RAG Studio knowledge base. You ensure the synthetic corpus
is properly uploaded and indexed before any evaluation queries run, and you verify the
upload succeeded.

**Goal:**

1. Receive the `synthetic_corpus.pdf` path from Agent 1.
2. Use `rag_studio_tool` (action `upload_document`) to upload it to the configured knowledge base.
3. Verify and report the upload status.

**Tool:** `rag_studio_tool` (action `upload_document`)

**Output Format:**
```json
{
  "status": "success",
  "knowledge_base_name": "...",
  "knowledge_base_id": "...",
  "document_name": "synthetic_corpus.pdf",
  "message": "Document uploaded successfully",
  "timestamp": "2026-07-09T10:30:00Z"
}
```

---

### Agent 5: RAG Query Specialist

| Attribute | Value |
|-----------|-------|
| **Name** | RAG Query Specialist |
| **Role** | RAG System Tester and Response Collector |

**Backstory:**
You systematically query the RAG system with each ground-truth question and meticulously
record both the generated answers and the retrieved context chunks — the raw material the
evaluator needs to assess retrieval and generation separately.

**Goal:**

1. Receive the approved Q&A pairs from Agent 3.
2. For each question, call `rag_studio_tool` (action `query`) and collect the answer + retrieved chunks.
3. Output the compiled results, preserving Q&A pair IDs.

**Tool:** `rag_studio_tool` (action `query`)

**Output Format:**
```json
{
  "query_results": [
    {"id": 1, "question": "...", "ground_truth_answer": "...", "rag_answer": "...", "retrieved_chunks": ["..."], "question_type": "factual"}
  ]
}
```

---

### Agent 6: RAG Evaluation Analyst

| Attribute | Value |
|-----------|-------|
| **Name** | RAG Evaluation Analyst |
| **Role** | RAG Quality Assessment Specialist |

**Backstory:**
You evaluate RAG performance using established metrics, assessing both whether retrieval
found relevant context and whether generation produced accurate, faithful answers. You
use LLM-as-judge techniques combined with semantic analysis for objective scoring.

**Goal:**
Evaluate each query result on five metrics, each scored 0–1:

- **Context Relevance** — are the retrieved chunks relevant to the question?
- **Faithfulness** — is the answer grounded in the retrieved context?
- **Answer Relevance** — does the answer address the question?
- **Semantic Similarity** — how close is the RAG answer to ground truth?
- **Correctness** — is the answer factually correct vs ground truth?

Then write `capstone_evaluation_report.pdf` and output the full report as JSON.

**Output Format:**
```json
{
  "evaluation_summary": {
    "total_questions": 8,
    "avg_context_relevance": 0.85,
    "avg_faithfulness": 0.90,
    "avg_answer_relevance": 0.88,
    "avg_semantic_similarity": 0.82,
    "avg_correctness": 0.84
  },
  "detailed_results": [{"id": 1, "scores": {"context_relevance": 0.9}, "reasoning": "..."}],
  "recommendations": ["..."]
}
```

---

## Workflow Summary

| Stage | Studio | Task | Agent | Tool | Output |
|-------|--------|------|-------|------|--------|
| 1 | Synthetic Data Studio | Generate Synthetic Corpus | Synthetic Corpus Builder | `synthetic_data_studio_tool` (generate) + `write_to_shared_pdf` | `synthetic_corpus.pdf` |
| 2 | Agent Studio | Generate Ground Truth | Q&A Generator | LLM + `write_to_shared_pdf` | 5–10 Q&A pairs |
| 3 | Agent Studio | Verify Quality | Q&A Verifier | LLM + `write_to_shared_pdf` | Validated Q&A pairs |
| 4 | RAG Studio | Ingest into RAG | RAG Document Uploader | `rag_studio_tool` (upload_document) | Upload confirmation |
| 5 | RAG Studio | Query RAG | RAG Query Specialist | `rag_studio_tool` (query) | RAG answers + chunks |
| 6 | Agent Studio | Evaluate Results | RAG Evaluation Analyst | LLM-as-judge + `write_to_shared_pdf` | Evaluation report |

## Run Inputs

| Variable | Example | Notes |
|----------|---------|-------|
| `domain_prompt` | `"Retail banking product FAQ: accounts, cards, loans, fees"` | Describes the synthetic corpus to generate |
| `corpus_items` | `10` | How many synthetic items SDS should produce (keep small for a live demo) |
| `knowledge_base_name` | `capstone_synthetic_kb` | Target RAG Studio knowledge base (create it first) |

## Required Tools

| Tool | Actions used | Where to configure |
|------|--------------|--------------------|
| [`synthetic_data_studio_tool`](../tools/synthetic_data_studio_tool.md) | `generate` | Agent Studio Tools Catalog (SDS base URL + API key) |
| [`rag_studio_tool`](../tools/rag_studio_tool.md) | `upload_document`, `query` | Agent Studio Tools Catalog (RAG Studio base URL + API key + KB name) |
| `write_to_shared_pdf` | — | Built-in artifact writer for the PDF reports |

## Usage Notes

1. **Create the knowledge base first** in RAG Studio (`knowledge_base_name` above) before running.
2. **Allow indexing time** after Task 4 — chunking + embedding is not instantaneous; the
   first queries in Task 5 may need a short wait/verification.
3. **Keep `corpus_items` small** for a live demo — SDS synchronous generation is bounded by
   HTTP timeout (see the [Synthetic Data Studio overview](../studios/synthetic_data_studio.md)).
4. **Interpreting the evaluation** (Task 6): high context relevance + low correctness points
   to a generation issue; low context relevance points to a retrieval/ingestion issue.
5. **Why this matters:** the capstone proves you can stand up and *measure* a RAG chatbot on
   a realistic corpus while keeping real customer data entirely out of the loop — the core
   value of combining all three studios.

## Related

- [Demo A — Agent ⇄ RAG Studio](agent_rag_demo.md) — the RAG evaluation half, on a real document.
- [Demo B — Agent ⇄ Synthetic Data Studio](agent_synthetic_demo.md) — the synthetic generation half.
- [Agent Studio](../studios/agent_studio.md) · [RAG Studio](../studios/rag_studio.md) · [Synthetic Data Studio](../studios/synthetic_data_studio.md)
