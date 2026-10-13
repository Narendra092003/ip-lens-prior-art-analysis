# 16 — Running Locally

This is the reference run procedure after implementation. Initial editor and dependency setup is in [`07-GETTING-STARTED.md`](./07-GETTING-STARTED.md).

## Configuration

Create `.env` from `.env.example` after the configuration phase. Common settings include `GEMINI_API_KEY`, `GEMINI_MODEL`, `API_BASE_URL`, `CHROMA_PATH`, `MAX_UPLOAD_MB`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `DEFAULT_TOP_K`, and `MIN_SIMILARITY`. Keep `.env` private and ignored by Git.

## Start the API

From the project root, open a terminal and run:

```powershell
uv run uvicorn backend.app.main:app --reload --port 8000
```

Check `http://localhost:8000/health` and `http://localhost:8000/docs`.

## Start the Streamlit UI

Open a second terminal in the project root and run:

```powershell
uv run streamlit run frontend/streamlit_app.py
```

Open the local address printed by Streamlit. The UI should explain when the corpus is empty or Gemini is not configured.

## Reproducible demo

1. Upload the clearly labeled synthetic patent documents.
2. Enter the synthetic disclosure and review/edit its claims.
3. Run the analysis and inspect each excerpt/citation.
4. Confirm the score explanation and limitations.
5. Download JSON and Markdown.
6. Restart the API and check that the corpus remains indexed.

## Troubleshooting

| Symptom | Check |
|---|---|
| API does not start | Confirm `uv sync` completed and the working directory is the project root. |
| Streamlit cannot reach API | Check the API terminal and `API_BASE_URL`. |
| Gemini error | Check `.env`, model configuration, network access, and provider error message; never paste the key into support chat. |
| Corpus disappears on restart | Check `CHROMA_PATH` points to persistent local storage under `data/`. |
| No useful evidence | Verify a document indexed successfully and explain that search covers only the uploaded corpus. |

