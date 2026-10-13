# 19 — Build Order and 5-Day Plan

Section 12 of [`../PROJECT_SPECIFICATION.md`](../PROJECT_SPECIFICATION.md) is authoritative if this summary ever differs.

## Timeline

| Day | Date | Phases | Goal for the day |
|---|---|---|---|
| 0 | Tue 13 Oct (evening) | Setup | Tools installed, Gemini key works, workspace opened |
| 1 | Wed 14 Oct | 1–5 | Documents become searchable chunks in ChromaDB |
| 2 | Thu 15 Oct | 6–8 | Upload works end to end through FastAPI and Streamlit |
| 3 | Fri 16 Oct | 9–12 | Gemini structures a disclosure and compares one claim |
| 4 | Sat 17 Oct | 13–16 | **Full demo works end to end** (the cut line) |
| 5 | Sun 18 Oct | 17 | Evaluation numbers, tests, README, GitHub |
| Buffer | Mon 19 – Tue 20 Oct | — | Catch up, rehearse the demo, read your own code |
| Interview | Wed 21 Oct, 14:00 | — | — |

Plan for about 6–8 focused hours per day. If a day runs over, use the buffer days rather than skipping a phase.

## Day 0 — Setup (tonight, about 1 hour)

- Follow [`07-GETTING-STARTED.md`](./07-GETTING-STARTED.md): install Python 3.11+, `uv`, Git and VS Code.
- Create a Gemini API key, put it in `.env`, and confirm one test call works.
- Create a GitHub repository for the project.
- Download 5–8 published, text-searchable patent PDFs on agricultural machinery (for example tractor transmissions, implement control, precision farming) from Google Patents or Espacenet. Note each publication number and URL for `examples/REAL_PATENTS.md`.

## Day 1 — Wednesday: ingestion and storage

| Phase | Build | Done when |
|---:|---|---|
| 1 | Scaffold, `pyproject.toml`, `.gitignore`, `.env.example`, README stub | Folder tree matches the spec; no secrets committed |
| 2 | Settings and Pydantic schemas | Settings load from `.env`; key never appears in output |
| 3 | TXT/Markdown and PDF extraction | A real patent PDF produces page-numbered text; a scanned PDF gives a clear error |
| 4 | Page-aware chunking | Chunks never cross a page and keep their metadata |
| 5 | Persistent ChromaDB service | Index, replace, count and search work, and survive a restart |

**Also today:** write 3–4 synthetic prior-art documents and the demo disclosure, so you can test search immediately.

## Day 2 — Thursday: API and upload screen

| Phase | Build | Done when |
|---:|---|---|
| 6 | FastAPI `GET /health` and `GET /api/corpus` | Both return safe status in the browser at `/docs` |
| 7 | `POST /api/documents` | Multiple files upload with per-file success or failure |
| 8 | Streamlit Corpus screen | You can upload from the UI and see the passage count |

**Also today:** hand-label the retrieval set (`examples/eval/retrieval_labels.json`, 10–15 claims). Label it now, before you tune anything.

## Day 3 — Friday: the two model agents

| Phase | Build | Done when |
|---:|---|---|
| 9 | Gemini client with `structure_disclosure()` and `compare_claim()` | One module, Pydantic in and out, clear errors for missing key or timeout |
| 10 | Disclosure extraction route and UI | Claims appear and can be edited before analysis |
| 11 | Per-claim retrieval | Each claim gets its own threshold-filtered results |
| 12 | Claim comparison with `claim_compare_v1` | One claim returns shared/missing elements and cited chunk IDs |

## Day 4 — Saturday: workflow and results (cut line)

| Phase | Build | Done when |
|---:|---|---|
| 13 | LangGraph workflow with per-node timing | All claims run, including the no-evidence branch |
| 14 | Citation validation and risk score in Python | Unknown IDs are discarded; no evidence gives `Not scored` |
| 15 | `POST /api/analyses` and JSON/Markdown export | Both exports come from the same validated report |
| 16 | Results screen | Findings, evidence with filename and page, score parts and downloads are visible |

**By tonight the full demo must work end to end on synthetic and real documents.** This is the most important milestone of the week.

## Day 5 — Sunday: evidence and polish

| Task | Done when |
|---|---|
| `scripts/evaluate_retrieval.py` | Recall@1, Recall@4 and threshold counts printed and copied into `docs/EVALUATION.md` |
| `claim_compare_v2.md` and `scripts/compare_prompts.py` | v1 vs v2 table with schema-valid rate, discarded citations and reviewer notes |
| Timing | Median and maximum time of 5 demo runs recorded |
| Focused tests | Extraction, chunking, citation validation, scoring, request validation |
| README and architecture diagram | Someone else could set it up and understand it |
| GitHub | Final push; repository history shows one commit per phase |

## If you fall behind

Cut in this order, from first to last:

1. Stretch goals (DOCX, second provider, screen recording).
2. Markdown export (keep JSON).
3. Prompt v2 comparison (keep v1, and do not use the word "benchmarked").
4. Some of the focused tests (keep citation validation and scoring tests).

**Never cut:** citation validation, the `Not scored` behaviour, the Python-calculated score, or the retrieval evaluation. These are what make the project credible.

## Working agreement for each phase

1. Ask the AI coding assistant to inspect the workspace, state the phase goal, and list the files it will touch.
2. Keep changes limited to that phase.
3. Run the phase's "done when" check yourself.
4. **Explain-it check:** before moving on, explain out loud in two or three sentences what each new file does and why. If you can't, ask the assistant to walk you through it until you can. In the interview you must be able to explain any file.
5. Commit to Git with a clear message, such as `Phase 5: persistent ChromaDB service`.

Do not skip ahead, and do not let a model replace reviewed claims, citations or score logic.
