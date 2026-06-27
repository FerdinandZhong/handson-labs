# Synthetic Data Studio

Cloudera Synthetic Data Studio (SDS) is a deployed CAI Application that exposes a REST
API for prompt-driven synthetic data generation and LLM-as-judge quality evaluation.
In this lab, Agent Studio orchestrates SDS via the `synthetic_data_studio_tool` custom
tool — SDS never touches Impala directly; it only receives the prompts and schema
definitions that Agent Studio builds.

---

## Generation technique — freeform

SDS uses a `technique: "freeform"` approach: you supply a natural-language prompt
describing column rules, distributions, and PII-surrogate conventions, and SDS asks an
LLM to produce a JSON array of row objects. Key properties of this technique:

- **Prompt-driven column scope** — SDS generates exactly the columns described in
  `schema_json`. If a column is not in the prompt, it will not appear in the output.
  This is by design, not a bug.
- **FK constraint injection** — referential integrity is enforced by listing allowed
  parent-pool values directly in the prompt (e.g. *"Column `cfcif` MUST use only values
  from this list: [...]"*). The LLM is asked to comply; compliance is reliable for
  10–100 rows but is best-effort, not deterministic.
- **PII surrogates** — PII-flagged columns receive synthetic surrogate IDs
  (e.g. `SYN-CIF-000001`) rather than realistic personal data.

---

## Evaluate endpoint — LLM-as-judge scoring

`POST /synthesis/evaluate_freeform` reads a JSON row file from the **SDS application's
own filesystem** (not the Agent Studio host) and scores each row 1–5 using an LLM rubric:

| Score | Meaning |
|---|---|
| 1 | Wrong columns, invalid types, or obvious real PII leaked |
| 2 | Columns present but multiple type/range/category violations |
| 3 | Schema-compliant and mostly plausible; minor realism or PII concerns |
| 4 | Strong schema compliance, SG banking realism, diverse values, safe surrogates |
| 5 | Excellent on all criteria; clearly synthetic, production-demo quality |

A `dataset_ready_for_training: true` verdict from the evaluate endpoint means the data
passes the SDS rubric in a demo context. It does **not** certify column parity,
statistical fidelity, or programmatic FK integrity — for those use Direction 3
(`evaluate_synthetic_data.py` with KS tests and chi-square gates).

---

## Synchronous vs batch mode

SDS exposes two execution paths:

| Mode | How it works | When to use |
|---|---|---|
| **Synchronous** | Rows are generated inside the HTTP request and returned in the response body | Interactive demos, 25–100 rows per table |
| **Batch** | SDS creates an async CML Job and returns a job ID immediately; data is written later | Large-scale production generation (thousands+ rows) |

**Direction 2 (this lab) uses the synchronous path only.** Agent Studio tasks run
sequentially and cannot pause mid-pipeline to poll a background CML Job. Batch mode
requires a separate workflow in the SDS UI and is outside the scope of the Agent Studio
integration.

---

## Demo-mode row cap

The `synthetic_data_studio_tool` enforces `DEMO_MODE_MAX_ROWS = 500` as a safety ceiling
on each synchronous SDS call. The practical reliable range for live demos is **25–100
rows per table** — above ~100 rows synchronous HTTP timeout becomes a risk depending on
SDS server load. The default `rows_per_table` in the D2 workflow is `10` (for the fastest
demos) or `25` (for a more populated FK chain).

For training-scale data (10 k–100 k+ rows), use Direction 3 CML Jobs.

---

## Two-filesystem architecture

Agent Studio and Synthetic Data Studio run as **separate CAI Applications on separate
hosts**. They do not share a filesystem. When `synthetic_data_studio_tool` calls generate:

- A local JSON copy is written to `/synthetic_output/<table>_synthetic.json` on the
  **Agent Studio host** — useful for debugging.
- SDS writes its own export file on the **SDS host** and returns `eval_import_path`
  (e.g. `freeform_data_gpt-4o-mini_<ts>_test.json`).

The evaluate call must use `eval_import_path` — the SDS-side path. Passing the Agent
Studio `output_path` to evaluate returns a 404 Not Found from SDS.

---

## Next steps

- Run the synthetic data demo: [Demo B — Agent + Synthetic Data](../demos/agent_synthetic_demo.md)
- Full synthetic data lab: [Synthetic Data Workflows Summary](../synthetic_data_lab/SYNTHETIC_DATA_WORKFLOWS_SUMMARY.md)
- Register the tool in Agent Studio: [Synthetic Data Studio Tool](../tools/synthetic_data_studio_tool.md)
