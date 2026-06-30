# Agent Studio

Cloudera AI Agent Studio is the **orchestration layer** for every demo in this lab. It
lets you build, run, and iterate on multi-agent AI workflows entirely through a guided UI —
no framework code required.

---

## What Agent Studio does

Agent Studio wraps the CrewAI engine behind a point-and-click workflow builder. You define
a sequential pipeline of agents and tasks; Agent Studio routes each task's output to the
next task as context, calls the right tools, and streams live logs to the Test panel as
the run progresses.

Key capabilities used in this lab:

- **Sequential workflows** — tasks execute in a fixed order; each task receives the
  outputs of whichever prior tasks you wire as context.
- **Tools Catalog** — register custom Python tools (packaged as `tool.py` + `UserParameters`)
  or MCP servers. Both types appear identically in the agent editor.
- **MCP servers** — `iceberg-mcp-server` exposes Impala schema discovery
  (`get_schema`, `execute_query`) as MCP tools; agents pick them up without any extra code.
- **Input variables** — declare workflow-level variables (e.g. `{target_tables}`,
  `{rows_per_table}`) once; Agent Studio substitutes them at run time and validates that
  every `{word}` in agent/task text has a corresponding variable.
- **Artifact Files** — a shared virtual filesystem within a workflow run; agents can read
  and write files (CSV, JSON, plain text) visible in the Test panel.

---

## Building a workflow

1. **Create workflow** — click *Agentic Workflows → Create Workflow*. Select **Sequential**
   as the process type. Toggle *Is Conversational* **off** for pipeline-style runs.
2. **Add input variables** — declare every placeholder used in agent and task text.
   Only declared variables may appear in `{curly braces}`; undeclared ones cause a
   `Template variable not found` error at run time.
3. **Create agents** — for each agent provide four fields:

   | Field | Purpose |
   |---|---|
   | **Name** | Display label; also how context wiring references the agent |
   | **Role** | One-line professional identity used in the system prompt |
   | **Backstory** | Paragraph-length persona; shapes reasoning and tool-calling style |
   | **Goal** | What this agent must produce; scopes its decision-making |

4. **Attach tools** — after creating an agent, add MCP tool instances or custom tools
   from the Tools Catalog. Set any `UserParameters` (API keys, endpoints) here.
5. **Create tasks** — for each task provide:

   | Field | Purpose |
   |---|---|
   | **Description** | Detailed instructions; may reference `{workflow_variables}` |
   | **Expected Output** | JSON or prose template; tells the LLM what shape to return |
   | **Context** | Which prior tasks' outputs this task receives as additional context |

6. **Save and run** — open the *Test* panel, fill in run-time input values, and click
   **Run**. The Logs tab streams every tool call, MCP request, and LLM turn in real time.

---

## Tools Catalog

The Tools Catalog stores reusable tool definitions at the Agent Studio level (not per
workflow). Two registration paths:

**Custom Python tool** — upload or point to a directory containing `tool.py`. The file
must expose `UserParameters` (a Pydantic model for static config such as API keys and
endpoints) and `ToolParameters` (per-call arguments). Agent Studio renders both as
editable forms in the workflow editor.

**MCP server** — provide a server name, command, and connection arguments. Agent Studio
launches the server process and exposes its tools to any agent in any workflow. The
`iceberg-mcp-server` used in the synthetic-data demos is registered this way.

---

## How Agent Studio drives the three lab demos

| Demo | What Agent Studio orchestrates |
|---|---|
| **Demo A — RAG** | Single or multi-agent workflow querying RAG Studio knowledge bases via `rag_studio_tool` |
| **Demo B — Synthetic Data** | Four-agent pipeline: schema scan → prompt build → SDS generation → SDS evaluation via `synthetic_data_studio_tool` |
| **Capstone — Three Studios** | Combined workflow spanning RAG query, synthetic generation, and evaluation in one run |

In all three demos, Agent Studio acts as the **central coordinator**: it supplies input
variables, routes context between tasks, calls the appropriate tools, and surfaces results
in the Test panel — while RAG Studio and Synthetic Data Studio remain separate CAI
Applications that only receive API calls.

---

## Demos in this lab

- [Demo A — Agent + RAG](../demos/agent_rag_demo.md)
- [Demo B — Agent + Synthetic Data](../demos/agent_synthetic_demo.md)
- [Capstone — Three Studios](../demos/capstone_three_studios.md)
