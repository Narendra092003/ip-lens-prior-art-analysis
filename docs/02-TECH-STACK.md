# 02 — Tech Stack

## At a glance

| Layer | Choice | Responsibility |
|---|---|---|
| Language | Python 3.12 repository pin (`.python-version`; package metadata supports 3.11–3.13) | API, services, workflow, evaluation |
| Workflow | LangGraph `StateGraph` | Explicit, typed analysis steps and conditional routing |
| API | FastAPI + Uvicorn | Upload, extraction, analysis, corpus-status endpoints |
| Vector store | ChromaDB persistent local client | Store and retrieve page-aware document chunks |
| Generative model | Official `google-genai` SDK with Gemini | Disclosure structuring and evidence-bounded claim comparison |
| UI | Streamlit | Redesigned workflow and results; calls FastAPI over HTTP without importing backend services |
| Validation | Pydantic | API contracts and structured model-output validation |
| File parsing | `pypdf`, Python text decoding | Searchable PDF, TXT, and Markdown extraction; DOCX is unsupported |
| Dependency manager | `uv` with committed `uv.lock` | Reproducible local environment and dependency resolution |

## Why these choices fit the MVP

- **FastAPI** makes a small typed API and automatic OpenAPI documentation available without a separate gateway.
- **LangGraph** makes the multi-step analysis path visible and reviewable as a state graph. It is used for orchestration rather than as a label for every helper function.
- **ChromaDB** keeps the uploaded corpus and vector index on the local machine for this single-user MVP.
- **Gemini** performs language-heavy tasks. Python owns thresholds, source metadata, citation validation, and final arithmetic.
- **Streamlit** keeps the interface simple while the portfolio project focuses on the backend workflow and evidence trail.
- **`uv`** manages the Python environment from a project file and lockfile; the setup guide explains how to prepare it on Windows.

## Boundaries

The embedding function is local to ChromaDB; corpus text is not sent to a separate embedding service. The disclosure and retrieved excerpts are sent to the configured Gemini API for generation. The UI must say this before a user submits sensitive text. The Gemini SDK stays behind one backend client module so prompt, timeout, and provider-error handling are not duplicated in routes or Streamlit. That module exposes task functions with the project's own Pydantic types, so the provider can be replaced (for example by a model hosted inside a company tenant) without touching the workflow.

## Deployment

The Python 3.12 Docker image installs the locked dependencies with `uv`, preloads ChromaDB's default embedding model, and runs as a non-root user. The API binds to loopback port 8001; Streamlit is exposed on port 7860. An empty container corpus is seeded only from the synthetic prior-art text files.

## Dependency policy

Declare supported dependency ranges in `pyproject.toml`, resolve exact versions into `uv.lock`, and record important compatibility decisions in the repository. Do not invent version numbers in the specification. Before implementation, check the official documentation for the current SDK and LangGraph APIs and then lock the chosen versions.

## Official documentation

- [Python](https://docs.python.org/3/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)
- [ChromaDB Python reference](https://docs.trychroma.com/reference/python)
- [Gemini API libraries](https://ai.google.dev/gemini-api/docs/libraries)
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output)
- [Streamlit](https://docs.streamlit.io/)
- [`uv` project guide](https://docs.astral.sh/uv/guides/projects/)

