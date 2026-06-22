# Cloudera AI Hands-On Labs

This repository contains hands-on lab materials for Cloudera AI (CAI) workshops. Each sub-folder corresponds to a specific lab event and includes step-by-step instructions and supporting assets.

## Labs

| Lab | Date | Description |
|-----|------|-------------|
| [UOB Synthetic Data Lab](UOB_synthetic_data_lab_22_June/) | 22 June 2026 | **Latest** — four-direction synthetic data generation for ML training: Agent Studio workshops (D1, D2, D2.5) and production pipeline (D3 CML Jobs + CAI Application). Includes workflow summary, presenter demo guide, D3 deterministic/agentic modes, and SDS integration tool. |
| [UOB Hands-On Lab](UOB_handson_lab_14_May/) | 14 May 2026 | Building agentic workflows with Agent Studio — tools, MCP servers, and a memory-enabled invoice parser |

## Structure

Each lab folder follows a similar layout. The synthetic data lab (22 June) is more extensive:

```
<lab_name>/
├── Instructions/       # Step-by-step markdown guides
├── images/             # Diagram PNGs referenced by the instructions
├── extra_materials/    # Agent/task YAML (where applicable)
└── <code folders>/     # Pipeline scripts, CAI apps, custom tools (where applicable)
```

See each lab's README for its full layout.

## About

These labs are designed for participants with access to a Cloudera AI environment. They cover practical use of **Cloudera AI Agent Studio** and **CAI Workbench**, including:

- Building sequential multi-agent workflows in Agent Studio
- Registering MCP servers (`iceberg-mcp-server`) and custom tools in the Tools Catalog
- Generating PII-free synthetic training data from Impala lakehouse schemas
- Running production-scale pipelines via CML Jobs and CAI Applications
- Integrating Cloudera Synthetic Data Studio (SDS) as an external generation service
