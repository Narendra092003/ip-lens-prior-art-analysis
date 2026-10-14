# 06 — Project Structure

The repository separates Streamlit presentation, FastAPI routes, backend services, scripts, tests and documentation. The UI calls the API over HTTP and does not import backend services.

```text
IP-Lens-Project/
├── .github/workflows/deploy-hf.yml
├── .streamlit/config.toml
├── backend/app/
│   ├── api.py, config.py, main.py, schemas.py, workflow.py
│   ├── prompts/
│   └── services/
├── deploy/
│   ├── hf_space_header.md
│   └── start.sh
├── docs/
├── examples/
│   ├── demo_claims.json
│   ├── demo_disclosure.md
│   └── synthetic_prior_art_*.txt
├── frontend/
│   ├── demo_controls.py
│   ├── report_display.py
│   └── streamlit_app.py
├── scripts/
│   ├── compare_prompts.py
│   ├── evaluate_retrieval.py
│   ├── ingest_folder.py
│   └── seed_demo_corpus.py
├── tests/
├── Dockerfile
├── README.md
├── PROJECT_SPECIFICATION.md
├── pyproject.toml
└── uv.lock
```

Runtime `data/`, `outputs/`, `.env`, `.venv/`, caches and `examples/real/` are local/ignored. The two synthetic Markdown reports under `outputs/` are explicit README-linked exceptions.

## Dependency direction

```text
Streamlit --HTTP--> FastAPI routes --> workflow/services --> ChromaDB or Gemini
                          |                                  |
                          +-------- Pydantic contracts ------+
```

Routes validate and delegate. Services own parsing, chunking, retrieval, Gemini calls or report assembly. LangGraph coordinates analysis. Streamlit renders API responses and its pure frontend helpers; it does not import backend services.

## Files to understand first

| File | Why it matters |
|---|---|
| `backend/app/config.py` | Environment-backed runtime settings, including optional demo flags |
| `backend/app/schemas.py` | API and report contracts |
| `backend/app/api.py` | HTTP routes and error mappings |
| `backend/app/services/ingestion.py` | Shared file ingestion service |
| `backend/app/services/vector_store.py` | Persistent ChromaDB boundary |
| `backend/app/workflow.py` | LangGraph state and node wiring |
| `backend/app/services/reports.py` | Citation validation, scoring and report exports |
| `frontend/streamlit_app.py` | User-facing workflow and HTTP calls |
| `deploy/start.sh` | Container seed, API health wait and process supervision |

## Repository hygiene

Never commit `.env`, `.venv/`, Chroma data, caches or real patent files. Keep synthetic documents clearly labeled. The image excludes local state and `examples/real/`; it contains only the committed fictional demo corpus.
