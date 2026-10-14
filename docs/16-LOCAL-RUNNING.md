# 16 — Running Locally

Use the repository's Python 3.12 pin and `uv` from the project root. Local development uses two terminals, with FastAPI on port 8001 so it does not clash with applications on port 8000.

## Configure

```powershell
uv sync
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env`. `GEMINI_MODEL` defaults to `gemini-2.5-flash`. Other settings include `API_BASE_URL` (default `http://127.0.0.1:8001`), `CHROMA_PATH`, `MAX_UPLOAD_MB` (25), `MAX_CLAIMS` (10), `CHUNK_SIZE` (1200), `CHUNK_OVERLAP` (180), `DEFAULT_TOP_K` (4), `MIN_SIMILARITY` (50) and `INDEX_LANGUAGES` (English by default). Keep `.env` private and ignored by Git.

Demo variables are optional: `DEMO_MODE=true` shows the public-demo banner, `ACCESS_CODE` asks for a code before extraction or analysis, and `DEMO_ALLOW_UPLOADS=true` enables uploads in demo mode. With these variables unset, local behavior and the API limits remain unchanged.

## Terminal 1: start the API

```powershell
uv run uvicorn backend.app.main:app --reload --port 8001
```

Check `http://127.0.0.1:8001/health`; open `http://127.0.0.1:8001/docs` for the API explorer.

## Terminal 2: start Streamlit

```powershell
uv run streamlit run frontend/streamlit_app.py
```

Open the local URL printed by Streamlit. The UI talks to FastAPI over HTTP using `API_BASE_URL`. Upload searchable PDF, TXT or Markdown files from the Corpus section. The System sidebar shows API/Gemini status and the indexed passage count.

## Bulk ingest and synthetic demo

Upload the five `examples/synthetic_prior_art_*.txt` documents in the UI for the fictional demo. Paste `examples/demo_disclosure.md`, review or edit the claims, choose v2, run analysis and inspect the findings/exports. `examples/demo_claims.json` contains four prepared claims and IDs for reproducible API requests.

For folder-based ingestion, create `examples/real/`, place your own supported documents there, then run:

```powershell
New-Item -ItemType Directory -Force examples/real
uv run python scripts/ingest_folder.py examples/real
```

Files in `examples/real/` are ignored by Git and are excluded from the Docker image.

## Run the container

From the project root:

```powershell
docker build -t ip-lens .
docker run -p 7860:7860 --env-file .env ip-lens
```

Open `http://localhost:7860`. The container automatically enables demo mode, seeds an empty store with the synthetic documents, starts the API on container loopback port 8001, waits for `/health`, and then starts Streamlit on port 7860. It exits if either process exits. The API is not published outside the container. Demo mode caps the API at four claims and 2 MB per file; uploads require `DEMO_ALLOW_UPLOADS=true`.

## Troubleshooting

| Symptom | Check |
|---|---|
| Wrong folder | Run commands from the repository root, next to `pyproject.toml` and `uv.lock`. |
| Port 8001 already in use | Stop the existing process or choose a different API port and set the same `API_BASE_URL`. |
| Streamlit cannot reach the API | Confirm terminal 1 is still running and `API_BASE_URL` is `http://127.0.0.1:8001`. |
| Gemini unavailable | Check `GEMINI_API_KEY` and `GEMINI_MODEL`; do not paste the key into logs or chat. |
| Rate limit/provider failure | Wait briefly and retry. Disclosure extraction returns a rate-limit response; analysis reports provider failure safely. |
| Space is sleeping | Free-tier Spaces may cold-start; wait for it to wake, then reload. |
| Corpus disappears | Check that `CHROMA_PATH` points to the local project `data/` directory; container storage may be ephemeral. |

Disclosure text and retrieved excerpts are sent to Gemini. Use only fictional or public material. Scanned PDFs are unsupported because OCR is not implemented.
