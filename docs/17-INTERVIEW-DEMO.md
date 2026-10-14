# 17 — Interview Demo

## One-minute project description

> IP Lens: AI Agent Platform for Patent & Prior-Art Analysis is a human-review aid for comparing a technology disclosure with documents in an uploaded corpus. LangGraph coordinates per-claim retrieval and comparison; FastAPI exposes the workflow; ChromaDB stores local embeddings; Gemini structures disclosures and compares claim elements; Streamlit presents the findings. Python validates citations and calculates the triage score. It is not legal advice or a patentability decision.

The redesigned page opens with the four-step workflow, shows system status in the sidebar, and guides a reviewer through Corpus, Invention disclosure, Analysis and Results. **Live demo backup:** `https://huggingface.co/spaces/<HF_USERNAME>/ip-lens` *(placeholder until published; check for cold starts before use).* The local two-terminal setup remains the primary fallback.

## Demo flow

1. Start FastAPI on port 8001 and Streamlit in a second terminal using [`16-LOCAL-RUNNING.md`](./16-LOCAL-RUNNING.md). Confirm API/Gemini status in the System sidebar.
2. In Corpus, upload the five synthetic `examples/synthetic_prior_art_*.txt` documents and review the passage count and ingestion table. The container demo seeds these automatically.
3. In Invention disclosure, paste [`../examples/demo_disclosure.md`](../examples/demo_disclosure.md). Explain that the text goes to Gemini and only fictional or public material should be entered.
4. Extract candidate claims, review and edit them. [`../examples/demo_claims.json`](../examples/demo_claims.json) has four prepared claims and IDs for repeatable API requests.
5. In Analysis, describe the v1/v2 prompt selector and leave v2 selected, then run the analysis.
6. In Results, inspect the overview metrics and status legend, then trace a claim's shared/missing elements and citation to its filename, page and similarity. Show limitations and JSON/Markdown downloads.
7. If the public Space is asleep or unavailable, use the local two-terminal setup. The live link is a backup, not a dependency for the walkthrough.

## What to emphasize

- Only `evidence` findings contribute to the score. Missing evidence is never presented as a Low band.
- The score uses `round(0.65 * max_claim_coverage + 0.35 * best_cited_retrieval_similarity)` and is not a probability or legal conclusion.
- Retrieval covers only the uploaded corpus, and prompt coverage judgments vary between runs.
- Prompt v2 is the workflow/API default; v1 remains selectable. The recorded held-out claims were easy single-feature matches and do not demonstrate generalization.
- The public Gemini API receives the disclosure and retrieved excerpts. The demo is unsuitable for confidential material.
- The public container uses synthetic prior-art text, caps requests at four claims and 2 MB per uploaded file, and disables uploads unless explicitly enabled. `ACCESS_CODE` gates the UI only; it is not general API authentication.

## Questions to prepare for

**Why multiple agents?** Disclosure structuring and claim comparison are separate model tasks with different structured outputs. Retrieval, label mapping, citation validation and scoring remain Python code.

**How do you know it works?** Show the retrieval and v1/v2 measurements in [`EVALUATION.md`](./EVALUATION.md), explain that the labeled sets are small, and distinguish consistency from correctness.

**Does it determine novelty?** No. It is a research aid over the selected uploaded corpus, not an exhaustive search or legal analysis.

**Could this process confidential disclosures?** Not with the public Gemini API configuration. The SDK integration is isolated in `backend/app/services/gemini.py` so an approved provider can replace it.

**What would you build next?** Evaluate on harder held-out claims and a closely related corpus before changing retrieval or claiming improved comparison quality.
