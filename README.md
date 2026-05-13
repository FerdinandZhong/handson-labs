# Cloudera AI Hands-On Labs

This repository contains hands-on lab materials for Cloudera AI (CAI) workshops. Each sub-folder corresponds to a specific lab event and includes step-by-step instructions and supporting screenshots.

## Labs

| Lab | Date | Description |
|-----|------|-------------|
| [UOB Hands-On Lab](UOB_handson_lab_14_May/) | 14 May 2026 | Building agentic workflows with Agent Studio — tools, MCP servers, and a memory-enabled invoice parser |

## Structure

Each lab folder follows this layout:

```
<lab_name>/
├── Instructions/       # Step-by-step markdown guides
└── images/             # Screenshots referenced by the instructions
```

## About

These labs are designed for participants with access to a Cloudera AI environment. They cover practical use of **Cloudera AI Agent Studio** to build production-grade agentic workflows, including:

- Creating and registering custom tools in the Tools Catalog
- Deploying vector databases and registering MCP servers
- Building hierarchical, conversational multi-agent workflows
- Configuring cross-session memory with LightMem + ChromaDB
