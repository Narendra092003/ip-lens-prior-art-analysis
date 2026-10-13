# IP Lens

IP Lens is a local research aid for comparing an invention disclosure with patent documents supplied by the user. It is designed to retrieve relevant passages, organize claim-level evidence, and prepare a provisional novelty-risk triage report for human review.

The project is under phased development. This starter repository currently defines the Python environment, configuration, and API data contracts; the application workflow is not yet complete.

## Planned stack

- Python 3.11 or later, managed with [uv](https://docs.astral.sh/uv/)
- FastAPI for the service API
- Streamlit for the interface
- ChromaDB with local embeddings for the uploaded corpus
- LangGraph for the analysis workflow
- Gemini through the official `google-genai` SDK

## Setup

Install Python 3.11+ and uv, then run:

```powershell
uv sync
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env` to enable Gemini features. Never commit `.env` or put confidential disclosures in this demo: disclosure text and retrieved passages are sent to the configured Gemini API when model-backed analysis is implemented.

Start the API from the project root with:

```powershell
uv run uvicorn backend.app.main:app --reload
```

Ingest all supported documents in a folder (for example, the real-patent demo set) with:

```powershell
uv run python scripts/ingest_folder.py examples/real
```

In a second terminal, start the Streamlit interface with:

```powershell
uv run streamlit run frontend/streamlit_app.py
```

## Scope and limitations

IP Lens will search only documents uploaded to its local corpus. Its score is an unvalidated triage heuristic, not a probability, patentability decision, or legal opinion. Analysts must review the source documents and consult qualified counsel for legal decisions. Use fictional or public material for demonstrations.

See [PROJECT_SPECIFICATION.md](PROJECT_SPECIFICATION.md) for the complete scope and [docs/19-BUILD-ORDER.md](docs/19-BUILD-ORDER.md) for the phased implementation plan.
