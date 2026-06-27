# RAG Studio Tool

The RAG Studio Tool (`tools/rag_studio_tool/tool.py`) is a custom Agent Studio tool that
lets agents interact with a deployed Cloudera RAG Studio application via its REST API.
Agents use it to query knowledge bases, upload documents, inspect sessions, and retrieve
chat history with quality evaluations — all without writing any HTTP code in the workflow.

---

## Supported actions

| Action | Description |
|---|---|
| `query` | Send a natural-language question to a knowledge base and return the answer with source citations. Creates and tears down a temporary session automatically. |
| `upload_document` | Upload a local file into the configured knowledge base (multipart POST to the RAG Studio data-source files endpoint). |
| `list_knowledge_bases` | List all knowledge bases (data sources) available in RAG Studio, including document count and embedding model. |
| `get_sessions` | List all existing RAG sessions with their IDs, names, data sources, and inference models. |
| `get_chat_history` | Retrieve the full message history for a session, including per-turn relevance and faithfulness evaluations. Requires `session_id`. |

---

## UserParameters

Set these once per tool registration in the Agent Studio Tools Catalog. They apply to
every agent that uses this tool instance.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `base_url` | `str` | — | Base URL of the RAG Studio application, e.g. `https://ragstudio-xxx.cloudera.site` |
| `api_key` | `str` | — | Bearer token for RAG Studio authentication (`CDSW_APIV2_KEY` or CDP JWT) |
| `knowledge_base_name` | `str` | — | Name of the default knowledge base to query or upload into (case-insensitive partial match supported) |
| `project_id` | `int` | `1` | Project ID used when creating query sessions |
| `inference_model` | `str` | `None` | Inference model for response generation, e.g. `gpt-4o`. Omit to use RAG Studio's default. |
| `response_chunks` | `int` | `5` | Number of retrieved chunks returned per query |
| `timeout_seconds` | `int` | `60` | HTTP timeout in seconds |

---

## Registering in the Tools Catalog

1. In Agent Studio, go to **Tools Catalog → Add Tool**.
2. Set the tool path to `tools/rag_studio_tool/` (the directory containing `tool.py`).
3. Agent Studio reads `UserParameters` and renders them as an editable form.
4. Fill in `base_url`, `api_key`, and `knowledge_base_name`. Adjust `project_id` and
   `inference_model` as needed for your deployment.
5. Save and attach the tool to any agent in a workflow.

At run time, the agent calls the tool by setting `action` to one of the values above. For
`query`, also set `query` (the question string). For `upload_document`, set `file_path`
(absolute path on the Agent Studio host). For `get_chat_history`, set `session_id`.

---

## Used by

- [Demo A — Agent + RAG](../demos/agent_rag_demo.md)
- [Capstone — Three Studios](../demos/capstone_three_studios.md)
