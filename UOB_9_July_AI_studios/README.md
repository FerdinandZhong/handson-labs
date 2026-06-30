# UOB AI Studios Lab (9 July 2026)

A hands-on lab demonstrating how **Cloudera AI Agent Studio**, **RAG Studio**, and
**Synthetic Data Studio (SDS)** interoperate. It contains two focused linkage demos plus
a three-studio capstone, and a full MkDocs-Material documentation site ready to publish
on GitHub Pages.

## What's inside

| Path | Contents |
|------|----------|
| `docs/` | The MkDocs site source (Home, Studios, Demos, Synthetic Data Lab, Tools) |
| `docs/demos/` | The three demo workflow designs (Agent+RAG, Agent+SDS, Capstone) |
| `docs/synthetic_data_lab/` | The ported four-direction synthetic-data curriculum (D1–D3) |
| `tools/` | The two custom Agent Studio tools: `rag_studio_tool/`, `synthetic_data_studio_tool/` |
| `extra_materials/` | Agent/task YAML specs for the demos |
| `mkdocs.yml` | MkDocs-Material configuration and navigation |
| `.github/workflows/ci.yml` | GitHub Action that deploys the site to GitHub Pages on push to `main` |

## The demos

- **Demo A — Agent ⇄ RAG Studio:** generate ground-truth Q&A → upload to a RAG knowledge base → query → evaluate retrieval + generation.
- **Demo B — Agent ⇄ Synthetic Data Studio:** discover schema → build prompts → generate synthetic rows via SDS → score quality.
- **Capstone — All three:** SDS generates a synthetic corpus → RAG ingests it → Agent Studio evaluates the RAG chatbot end-to-end.

## Local development

```bash
cd UOB_9_July_AI_studios
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
mkdocs serve                       # http://127.0.0.1:8000
```

Build static files (strict mode catches broken links):

```bash
mkdocs build --strict
```

## Publishing to GitHub Pages

1. Push this folder to its own GitHub repository.
2. Edit `mkdocs.yml` — set `site_url`, `repo_url`, and `repo_name` to your repository.
3. On push to `main`, the `deploy-docs` GitHub Action runs `mkdocs gh-deploy --force`,
   publishing to the `gh-pages` branch. Enable GitHub Pages (source: `gh-pages`) in repo settings.

## Tools setup

Both tools are registered in the **Agent Studio Tools Catalog** before building the
workflows. See [`docs/tools/rag_studio_tool.md`](docs/tools/rag_studio_tool.md) and
[`docs/tools/synthetic_data_studio_tool.md`](docs/tools/synthetic_data_studio_tool.md)
for parameters and registration steps.
