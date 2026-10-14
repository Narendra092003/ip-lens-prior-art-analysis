# Design Changes — IP Lens: AI Agent Platform for Patent & Prior-Art Analysis

The original architecture is unchanged: two Gemini-backed agents, deterministic retrieval, citation validation and scoring in Python, coordinated by LangGraph. These changes make the scope fit a 5-day build and make every portfolio claim provable.

| # | Change | Why | Where |
|---|---|---|---|
| 1 | DOCX extraction moved to a stretch goal | Saves time; PDF and TXT/Markdown cover the demo and evaluation | Spec §2, §2a, §5, §6, §8, §10, §12; docs 01, 02, 08, 09 |
| 2 | Added a small real-patent demo set (5–8 published PDFs, downloaded manually, listed in `examples/REAL_PATENTS.md`, not committed) | "Patent documents" becomes true without adding patent-office APIs; agricultural machinery patents fit the target role | Spec §2, §11; docs 01, 09, 17 |
| 3 | Evaluation includes Recall@1/@4 on 15 labeled claims, threshold counts, and repeated v1/v2 comparison; five-run end-to-end timing remains uncollected | Provides collected retrieval and prompt-consistency measurements without implying a timing benchmark | Spec §9, §10, §12; docs 11, 15 |
| 4 | Added `claim_compare_v2.md` and `scripts/compare_prompts.py` | A concrete before/after prompt improvement to discuss | Spec §9, §11; doc 11 |
| 5 | Per-node durations returned with reports; UI and Markdown show summed analysis duration | Any speed claim must be measured, not assumed | Spec §4, §6; doc 12 |
| 6 | Model-provider boundary: one module, two task functions, project-owned Pydantic types | Shows how confidential disclosures could use an approved in-company model | Spec §4, §10; docs 02, 11, 14 |
| 7 | Enterprise deployment note on confidential data | Public API use is only acceptable for fictional or public material | Doc 14 |
| 8 | One Git commit per phase | Repository history documents how the project was built | Spec §9; doc 19 |
| 9 | 5-day plan with a cut line, cut order and daily explain-it check | Interview on 21 October 2026 | Doc 19 |
| 10 | Interview guidance: honest answers on AI-assisted building, confidentiality and speed; claims allowed only once evidence exists | Prevents over-claiming | Doc 17 |
| 11 | Fixed broken reference `docs/00-DOCUMENTATION-INDEX.md` → `docs/00-README.md` | The file did not exist | Spec header |
| 12 | Raised default `MIN_SIMILARITY` from 35 to 50 after the labeled threshold sweep | 50 was the lowest tested threshold at which both no-answer queries returned no passage; this is an indicative calibration | Spec §5; docs 10, 16; `docs/EVALUATION.md` |
| 13 | Skip near-empty PDF pages and likely drawing sheets using marker/word-count heuristics | Patent drawing sheets add figure-label noise; skipped pages are counted separately | Spec §5; doc 09 |
| 14 | Tag pages `en`, `de`, `fr`, or `unknown`; index only selected `INDEX_LANGUAGES` and reject documents with no selected-language pages | The evaluated corpus includes German-language publications that the English-only default cannot index | Spec §5; doc 09 |
| 15 | Add `scripts/ingest_folder.py` for folder-based bulk ingestion through the shared service | Reuses API ingestion behavior and summarizes successes, failures, skipped drawings, and language exclusions | Spec §11; docs 09, 16 |
| 16 | Distinguish `evidence`, `no_evidence`, `no_supporting_passage`, and `unsupported` | Separates retrieval absence, a comparison with no supporting citation, and invalid model references | Spec §5; docs 08, 12, 13 |
| 17 | Use prompt passage labels and map them to retrieved chunk IDs in Python | Prevents the model from inventing source IDs and keeps citation validation tied to the current claim | Spec §4–5; docs 04, 11, 12 |
| 18 | Make prompt v2 the workflow/API default, compute its element coverage in Python, and retain v1 as a selectable comparison | The seven-case comparison had lower mean coverage spread and no claim-reference elements for v2; the sample is small and does not establish accuracy | Spec §4, §6, §9; docs 11, 17; `docs/EVALUATION.md` |
| 19 | Add analysis settings and preserve supplied claim IDs; shorten Markdown excerpts and combine overlapping same-page display citations | Makes runs auditable and Markdown easier to scan while JSON retains full, separate citation data | Spec §6; doc 13 |
| 20 | Retry transient Gemini errors at most twice and record per-node workflow durations in reports | Bounds provider retry time and makes the comparison stage duration visible without claiming a separate provider-call timing log | Spec §4, §6; doc 12 |
| 21 | Pin the reproducible local Python runtime to 3.12 in `.python-version` | Gives the setup and test procedure one consistent interpreter while package metadata remains compatible with 3.11–3.13 | Spec §8; docs 02, 16, 19 |
| 22 | Refresh the front page and selected supporting documentation; add `.gitattributes` with LF text handling and binary PDF treatment | Aligns project setup, workflow explanations, phase status, and cross-platform line-ending behavior with the implementation | README; selected docs 02–19; `.gitattributes` |
| 23 | Redesign the Streamlit page with a four-step overview, System sidebar, numbered workflow sections, consistent claim-status colors, result metrics, and a restrained theme | Makes the analysis flow and evidence easier for an internal reviewer to scan while keeping all API access over HTTP | `frontend/streamlit_app.py`; `.streamlit/config.toml`; docs 03–05, 14, 17 |
| 24 | Set the local API URL default and two-terminal instructions to port 8001 | Avoids conflicts with other local projects using port 8000 and keeps the UI/API configuration aligned | `backend/app/config.py`; `.env.example`; README; docs 07, 16 |
| 25 | Add a Python 3.12 Docker deployment with loopback-only API on 8001, Streamlit on 7860, build-time Chroma embedding preload, and synthetic-only empty-corpus seeding | Provides a reproducible public showcase without placing real patent PDFs or local data in the image | `Dockerfile`; `.dockerignore`; `deploy/start.sh`; `scripts/seed_demo_corpus.py` |
| 26 | Add opt-in public-demo warning, optional UI access-code gate, four-claim and 2 MB upload limits, and upload opt-in | Limits the public demo to fictional, small inputs; unset variables preserve local behavior | `backend/app/config.py`; `frontend/demo_controls.py`; `frontend/streamlit_app.py`; tests |
| 27 | Add a test-before-deploy Hugging Face workflow and Space metadata header; document the deployment, screenshot, setup, and evaluation limits | Makes deployment repeatable and keeps the GitHub README unchanged by the CI-only front-matter step | `.github/workflows/deploy-hf.yml`; `deploy/hf_space_header.md`; README; docs |

## Not changed (deliberately)

- No patent-office crawling or public patent APIs. Out of scope for 5 days and not needed to demonstrate the workflow.
- No OCR. Scanned PDFs are reported as unsupported.
- The 65/35 triage score remains an unvalidated heuristic and is labelled as such.
