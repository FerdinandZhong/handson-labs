# Synthetic Data Studio Tool

The Synthetic Data Studio Tool (`tools/synthetic_data_studio_tool/tool.py`) is a custom
Agent Studio tool that lets agents call a deployed Cloudera Synthetic Data Studio (SDS)
application via its REST API. Agents use it to generate prompt-driven synthetic JSON rows
and to score generated rows with an LLM-as-judge evaluator — the two core operations in
the Direction 2 synthetic data pipeline.

---

## Supported actions

| Action | SDS endpoint | Description |
|---|---|---|
| `generate` | `POST /synthesis/freeform` | Produce synthetic JSON rows for one table. Builds the generation prompt from `schema_json`, `sample_values_json`, FK constraints, and `custom_prompt`. Writes a local copy to `output_path` and returns `eval_import_path` (the SDS-side file path required by `evaluate`). |
| `evaluate` | `POST /synthesis/evaluate_freeform` | Score each row in a previously generated file 1–5 using an LLM-as-judge rubric. Reads `import_path` from the **SDS filesystem** — pass `eval_import_path` from the `generate` response, not the Agent Studio local `output_path`. |

---

## UserParameters

Set these once per tool registration in the Agent Studio Tools Catalog.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sds_base_url` | `str` | — | Base URL of the Synthetic Data Studio application, e.g. `https://synthetic-data-generator-xxx.cloudera.site` |
| `api_key` | `str` | — | `CDSW_APIV2_KEY` / CDP JWT used as Bearer auth to the SDS app |
| `model_id` | `str` | `gpt-4o-mini` | Model ID passed through to SDS for generation and evaluation |
| `inference_type` | `str` | `openai` | SDS inference backend: `openai`, `openai_compatible`, `CAII`, `aws_bedrock`, or `gemini` |
| `caii_endpoint` | `str` | `""` | Required when `inference_type` is `CAII` or `openai_compatible`. Leave empty for direct OpenAI access. |
| `timeout_seconds` | `int` | `300` | HTTP timeout in seconds. Generation can be slow for larger row counts. |

> **Note:** Do not set `inference_type: CAII` when targeting OpenAI. CAII authenticates
> with a CDP token, not an OpenAI key. Use `inference_type: openai` and set
> `OPENAI_API_KEY` in the SDS application's environment variables.

---

## Demo-mode row cap and output directory

The tool enforces `DEMO_MODE_MAX_ROWS = 500` as a safety ceiling on each synchronous
generate call. Rows above this cap are silently capped with a warning returned in the
tool response. For live demos, `rows_per_table = 10` or `25` is recommended.

Generated JSON files are written to `DEFAULT_OUTPUT_DIR = /synthetic_output` on the
Agent Studio host by default (e.g. `/synthetic_output/eda_bwc_cfmast_d_sg_synthetic.json`).
Override with the `output_path` tool parameter.

---

## Registering in the Tools Catalog

1. In Agent Studio, go to **Tools Catalog → Add Tool**.
2. Set the tool path to `tools/synthetic_data_studio_tool/` (the directory containing
   `tool.py`).
3. Agent Studio reads `UserParameters` and renders them as an editable form.
4. Fill in `sds_base_url`, `api_key`, `model_id`, and `inference_type`. Set
   `timeout_seconds` to `300` or higher for generation calls.
5. Save and attach the tool to agents that perform generation (Agent 3) and evaluation
   (Agent 4) in the D2 workflow.

Both agents in the D2 pipeline share the same tool registration. The `action` field in
each task's tool call (`generate` vs `evaluate`) determines which SDS endpoint is called.

---

## Used by

- [Demo B — Agent + Synthetic Data](../demos/agent_synthetic_demo.md)
- [Capstone — Three Studios](../demos/capstone_three_studios.md)
