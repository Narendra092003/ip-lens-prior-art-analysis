# 16 — Running Locally

The repository pins Python 3.12 in `.python-version`; use `uv` from the project root. The package metadata accepts Python 3.11–3.13, while the reproducible local setup uses the 3.12 pin.

## Configure

```powershell
uv sync
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env`. `GEMINI_MODEL` selects the provider model. Other common settings include `API_BASE_URL`, `CHROMA_PATH`, `MAX_UPLOAD_MB`, `MAX_CLAIMS`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `DEFAULT_TOP_K`, `MIN_SIMILARITY` (default 50), and `INDEX_LANGUAGES` (default English). Keep `.env` private and ignored by Git.

## Start the API

From the project root:

```powershell
uv run uvicorn backend.app.main:app --reload --port 8000
```

Check `http://localhost:8000/health` and open `http://localhost:8000/docs` for the interactive API.

## Start the Streamlit UI

In a second terminal:

```powershell
uv run streamlit run frontend/streamlit_app.py
```

The interface calls FastAPI over HTTP. Upload searchable PDF, TXT, or Markdown files through Corpus; status information shows API/Gemini availability and indexed passage count.

## Bulk ingestion and demo

To ingest supported files from a folder through the same service as the API:

```powershell
uv run python scripts/ingest_folder.py examples/real
```

For the fictional demo, upload the five `examples/synthetic_prior_art_*.txt` files in the UI. Paste `examples/demo_disclosure.md` into Disclosure, then review the extracted claims or use the texts in `examples/demo_claims.json`. Choose v2 (the default), run analysis, and inspect findings and exports. The API preserves supplied claim IDs when claims are sent as `{ "claim_id", "text" }` objects.

## Troubleshooting

| Symptom | Check |
|---|---|
| API does not start | Confirm `uv sync` completed and the terminal is in the project root. |
| Streamlit cannot reach API | Check the API process and `API_BASE_URL`. |
| Gemini unavailable | Check model/key configuration and the safe provider error; never share the key. |
| Corpus disappears on restart | Check `CHROMA_PATH` points to project-root persistent storage. |
| No useful evidence | Confirm files indexed and check the recorded threshold. Search covers only the uploaded corpus. |
| German document rejected | Default `INDEX_LANGUAGES` is English; configure selected languages if appropriate. |

The public Gemini API receives disclosure text and retrieved excerpts. Do not use confidential invention material with this configuration. Scanned PDFs are unsupported because OCR is not implemented.
