# 06 — Project Structure

The application is a single Python repository with a Streamlit UI, a FastAPI backend, and a numbered documentation set. Keep the planning docs separate from runtime data and secrets.

## Target repository layout

```text
IP-Lens-Project/
├── README.md
├── PROJECT_SPECIFICATION.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── backend/
│   └── app/
│       ├── main.py
│       ├── api.py
│       ├── config.py
│       ├── schemas.py
│       ├── workflow.py
│       ├── prompts/
│       │   ├── disclosure_extract_v1.md
│       │   └── claim_compare_v1.md
│       └── services/
│           ├── documents.py
│           ├── chunking.py
│           ├── vector_store.py
│           ├── retrieval.py
│           ├── gemini.py
│           ├── claim_comparison.py
│           └── reports.py
├── frontend/
│   └── streamlit_app.py
├── examples/
│   ├── demo_disclosure.md
│   └── synthetic_prior_art_01.txt
├── docs/
│   ├── 00-README.md … 19-BUILD-ORDER.md
│   ├── PORTFOLIO_DEMO.md
│   └── EVALUATION.md
├── scripts/
│   └── evaluate_retrieval.py
├── tests/
│   ├── unit/
│   └── integration/
├── data/                 # local Chroma files; ignored by Git
└── outputs/              # optional local report exports; ignored by Git
```

## Dependency direction

```text
Streamlit → FastAPI routes → application/workflow → services → ChromaDB or Gemini
                                      ↓
                              Pydantic contracts
```

Routes validate and delegate. Services own parsing, chunking, retrieval, Gemini calls, or report assembly. The LangGraph workflow coordinates them. Streamlit calls the API and renders its response; it does not import backend services directly.

## Files to understand first

| File | Why it matters |
|---|---|
| `PROJECT_SPECIFICATION.md` | Scope, contracts, build order, and acceptance criteria |
| `backend/app/config.py` | All environment-backed settings and safe defaults |
| `backend/app/schemas.py` | Shared API and report data shapes |
| `backend/app/services/documents.py` | Parsing and source/page metadata |
| `backend/app/services/vector_store.py` | Persistent ChromaDB boundary |
| `backend/app/workflow.py` | LangGraph state and node wiring |
| `backend/app/services/reports.py` | Citation validation and deterministic scoring |
| `frontend/streamlit_app.py` | User-facing workflow |

## Repository hygiene

`.env`, `.venv/`, `data/`, generated exports, caches, and IDE files must be ignored. Commit `.env.example`, never a key. Keep synthetic sample documents clearly marked as fictional. Store prompts as versioned files so a prompt change can be reviewed and evaluated independently from application logic.

