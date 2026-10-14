# 17 — Interview Demo

## One-minute project description

> IP Lens is a local, evidence-linked prior-art research prototype. It retrieves from documents uploaded to its corpus, compares reviewed claims with selected passages, validates citations in Python, and presents a report for human review. LangGraph coordinates the workflow; FastAPI exposes it; ChromaDB stores local embeddings; Gemini structures disclosures and compares claims; Streamlit presents the evidence. Its score is an unvalidated triage heuristic, not legal advice or a patentability decision.

## Demo flow

1. Start the API and Streamlit using [`16-LOCAL-RUNNING.md`](./16-LOCAL-RUNNING.md); show the research-aid notice and corpus count.
2. Upload `examples/synthetic_prior_art_01.txt` through `_05.txt` and point out page, drawing, and language ingestion counts.
3. Paste `examples/demo_disclosure.md` into Disclosure and extract candidate claims.
4. Review/edit the claims. `examples/demo_claims.json` contains the prepared texts and IDs for a reproducible API request.
5. Leave v2 selected, run analysis, and trace a finding to its filename, page, and excerpt. Explain the four statuses: Evidence, No evidence, No supporting passage, and Unsupported.
6. Show the analysis settings, Python-calculated score components, limitations, duration, and JSON/Markdown download buttons.
7. Open [`EVALUATION.md`](./EVALUATION.md) and `../outputs/prompt_comparison.md` for the measured retrieval and prompt-comparison results, including their limitations.

## What to emphasize

- The user reviews claims before analysis; supplied claim IDs are retained by the API.
- Only `evidence` findings contribute to the score. Missing evidence is never presented as a Low band.
- The score uses `round(0.65 * max_claim_coverage + 0.35 * best_cited_retrieval_similarity)` and is not a probability or legal conclusion.
- Retrieval covers only the uploaded corpus, and prompt coverage judgments vary between runs.
- Prompt v2 is the workflow/API default; v1 remains selectable. The current held-out comparison claims were easy single-feature matches and do not demonstrate generalization.
- The public Gemini API receives the disclosure and retrieved excerpts. The demo is unsuitable for confidential material; an approved private provider would be needed.

## Questions to prepare for

**Why multiple agents?** Disclosure structuring and claim comparison are separate model tasks with different structured outputs. Retrieval, label mapping, citation validation, and scoring remain Python code.

**How do you know it works?** Show the retrieval and v1/v2 measurements, explain that the labeled sets are small, and distinguish consistency from correctness.

**Does it determine novelty?** No. It is a research aid over the selected uploaded corpus, not an exhaustive search or legal analysis.

**Could this process confidential disclosures?** Not with the public Gemini API configuration. The SDK integration is isolated in `backend/app/services/gemini.py` so an approved provider can replace it.

**What would you build next?** Evaluate on harder held-out claims and a closely related corpus before changing retrieval or claiming improved comparison quality.
