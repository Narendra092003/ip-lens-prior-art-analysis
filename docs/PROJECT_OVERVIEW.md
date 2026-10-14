# IP Lens: AI Agent Platform for Patent & Prior-Art Analysis

IP Lens is a human-review aid for comparing a technology disclosure with a user-provided corpus. It extracts page-aware text from searchable PDF, TXT and Markdown documents, structures a disclosure into candidate claims, retrieves passages for each reviewed claim, and returns a cited novelty-risk triage report. It is not legal advice or a patentability decision, and it does not search external patent databases.

## User workflow and interface

The Streamlit page presents a four-step workflow, a System sidebar, and four numbered sections:

1. **Corpus:** upload supported files and inspect indexing results and the indexed-passage count. Drawing pages and pages outside the configured language filter are skipped.
2. **Invention disclosure:** paste a disclosure, ask Gemini to propose a summary and candidate claims, then edit the claims before analysis. The UI warns that text is sent to Gemini.
3. **Analysis:** choose prompt v1 or v2 and run per-claim retrieval and comparison.
4. **Results:** review score components, one status per claim, shared and missing elements, validated source citations, limitations and JSON/Markdown downloads.

The optional public-demo notice, access-code gate, four-claim cap and two-megabyte per-file cap are controlled by `DEMO_MODE`, `ACCESS_CODE` and `DEMO_ALLOW_UPLOADS`. They are inactive when unset. The public container sets `MAX_CLAIMS=4` and `MAX_UPLOAD_MB=2`; uploads stay disabled unless explicitly enabled.

## Components and code boundaries

| Component | Implementation | Responsibility |
|---|---|---|
| Streamlit UI | `frontend/streamlit_app.py` | Presentation, user input and HTTP requests to FastAPI. It imports no backend services. |
| Presentation helpers | `frontend/report_display.py` | Human-readable statuses and overlap-aware citation excerpt grouping. |
| Demo controls | `frontend/demo_controls.py` | Pure checks for access code, demo claim count and upload size/availability. |
| API | `backend/app/api.py`, `backend/app/main.py` | Health, corpus count, ingestion, disclosure extraction and analysis routes. |
| Configuration/contracts | `backend/app/config.py`, `backend/app/schemas.py` | Environment settings and validated request/report models. |
| Ingestion | `backend/app/services/documents.py`, `ingestion.py`, `chunking.py` | PDF/TXT/Markdown text extraction, page metadata, language checks, drawing-page filtering and page-bounded chunks. |
| Retrieval | `backend/app/services/vector_store.py`, `retrieval.py` | Local ChromaDB storage and per-claim similarity filtering. |
| Model boundary | `backend/app/services/gemini.py`, `claim_comparison.py` | Gemini disclosure structuring and claim comparison with versioned prompts. |
| Workflow | `backend/app/workflow.py` | LangGraph claim routing, timing and report assembly coordination. |
| Report | `backend/app/services/reports.py` | Citation validation, score calculation and JSON/Markdown export. |

Python validates model-returned passage labels against the retrieved passages, assigns finding statuses, calculates coverage and the risk score, and assembles the report. Gemini does not select arbitrary corpus records or calculate the aggregate score.

## API endpoints

| Method and path | Purpose |
|---|---|
| `GET /health` | Returns service status and whether Gemini is configured; it never returns the API key. |
| `GET /api/corpus` | Returns passage count and local ChromaDB storage/embedding modes. |
| `POST /api/documents` | Accepts multiple PDF, TXT or Markdown files and returns per-file indexing results and failures. |
| `POST /api/disclosures/extract` | Accepts disclosure text and returns an invention summary with candidate claims. |
| `POST /api/analyses` | Accepts disclosure text, optional summary, reviewed claims and optional retrieval/prompt settings; returns the validated report and both exports. |

Analysis claims may be plain strings or `{ "claim_id": "…", "text": "…" }` objects. The API accepts prompt versions `v1` and `v2`, defaulting to `v2`; `top_k` is optional. Duplicate claim IDs, invalid requests and over-limit claim counts return HTTP 400. Missing Gemini configuration returns 503. Disclosure extraction maps Gemini rate limits to 429; analysis provider errors, including rate limits, return a safe 502. The API does not persist reports by default.

## Current settings and defaults

Defaults below come from `backend/app/config.py` and the analysis request schema. Environment values can override them.

| Setting | Default | Meaning |
|---|---:|---|
| `API_BASE_URL` | `http://127.0.0.1:8001` | URL used by Streamlit to call FastAPI. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model used by model-backed steps. |
| `MAX_UPLOAD_MB` | 25 | Maximum upload size per file. |
| `MAX_CLAIMS` | 10 | Maximum reviewed claims accepted by the API. |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 1200 / 180 | Text chunking parameters. |
| `DEFAULT_TOP_K` | 4 | Maximum retrieved passages requested per claim by default. |
| `MIN_SIMILARITY` | 50 | Minimum converted 0–100 similarity for a useful passage. |
| `INDEX_LANGUAGES` | `en` | Languages accepted by default. Supported values are `en`, `de`, `fr` and `unknown`. |
| `DEMO_MODE` | false | Shows the public-demo warning and applies UI demo limits when enabled. |
| `ACCESS_CODE` | unset | Optional UI gate for disclosure extraction and analysis. |
| `DEMO_ALLOW_UPLOADS` | false | Enables file uploads in demo mode only when explicitly true. |

The public container runs the API on `127.0.0.1:8001` and Streamlit on `0.0.0.0:7860`. Local development uses two terminals: FastAPI on port 8001 and Streamlit in the second terminal. The root `.env.example` sets the UI's API URL to port 8001.

## Finding statuses and score

| Status | Meaning |
|---|---|
| `evidence` | At least one useful retrieved passage was cited and validated. |
| `no_supporting_passage` | Useful passages were retrieved, but none was cited as support. |
| `no_evidence` | No passage met `MIN_SIMILARITY`; the model comparison is skipped. |
| `unsupported` | The model returned citations that could not be validated against retrieved passages. |

For v2, Python derives claim coverage from per-element judgments. The aggregate risk score is `round(0.65 * max_claim_coverage + 0.35 * best_cited_retrieval_similarity)`. Bands are Low (0–34), Moderate (35–69) and High (70–100). If there is no validated evidence finding, the score is null and the risk band is **Not scored**. This is a triage heuristic over the indexed corpus, not a probability of novelty or infringement.

## Deployment and evaluation

`Dockerfile` installs dependencies from `uv.lock`, preloads ChromaDB's default embedding model, runs as a non-root user and exposes Streamlit on port 7860. `deploy/start.sh` seeds an empty corpus from the five fictional `examples/synthetic_prior_art_*.txt` files, starts the internal API, waits for `/health`, then starts Streamlit. The GitHub Actions workflow runs the test suite before pushing deployment sources to a Hugging Face Space.

The recorded retrieval and v1/v2 comparison results, methodology and limits are in [`EVALUATION.md`](EVALUATION.md). They are small-sample observations, not evidence of legal accuracy or generalization.

## Limitations

Search covers only uploaded or seeded documents. OCR is not implemented, drawing-page detection is heuristic, language filtering can exclude relevant documents, and model judgments can vary. Disclosure text and retrieved excerpts go to Gemini. The public demo is for fictional material only; its access code is a UI gate rather than enterprise authentication. Human reviewers must inspect the source documents and make any legal assessment.
