# 05 — Flow Walkthrough

This fictional example illustrates the data path. Names and text below are synthetic and do not describe a real filing.

## Example input

The researcher uploads `synthetic-cooling-prior-art.pdf` and enters a disclosure about a battery cooling plate that adjusts coolant flow using measurements from multiple cell zones. Gemini proposes candidate claims; the user edits and approves two claims.

## Upload path

1. Streamlit sends the file to `POST /api/documents`.
2. FastAPI checks its type and size. The PDF parser extracts searchable text with physical page numbers.
3. The chunker creates page-bounded passages, for example `chunk_8d2…`, page 4, from `synthetic-cooling-prior-art.pdf`.
4. The vector-store service stores the passage, source metadata, and local embedding in persistent ChromaDB.
5. The API returns a document ID, indexed passage count, and any per-file error.

## Analysis path

1. Streamlit sends the disclosure and user-reviewed claims to `POST /api/analyses`.
2. LangGraph starts with typed state containing the analysis ID, reviewed claims, configuration, and an initially empty result list.
3. For Claim 1, retrieval searches ChromaDB and removes passages below `MIN_SIMILARITY`.
4. If evidence remains, the comparison step receives Claim 1 and only those passages. It returns shared elements, missing elements, uncertainty, a coverage estimate, and proposed chunk IDs.
5. Python checks that each proposed chunk ID belongs to Claim 1's retrieved set. It attaches the trusted filename, page, title, and excerpt from the store.
6. The graph repeats the retrieval/comparison path for Claim 2. If no useful evidence exists, application code returns a no-evidence result without calling Gemini.
7. Python computes the score using only claims with valid evidence. If none have valid citations, the result is `Not scored` with a null numeric score.
8. FastAPI returns the report; Streamlit renders the same report and makes JSON/Markdown downloads available.

## Illustrative claim finding

```json
{
  "claim_id": "claim_01",
  "shared_elements": ["coolant flow is adjusted in response to temperature measurements"],
  "missing_elements": ["the passage does not describe independent sensing for each cell zone"],
  "coverage_estimate": 54,
  "assessment": "Partial overlap in the general feedback-control concept.",
  "uncertainty": "The passage uses broad system language; inspect the full source context.",
  "citations": ["chunk_8d2f…"]
}
```

The percentage is a model-produced comparison estimate, not a measured legal conclusion. A user must be able to open the source excerpt and judge the comparison.

## Failure paths to show

- Unsupported or unreadable upload: report that file's failure without discarding successful files in the same request.
- Gemini unavailable: return an actionable service error; do not silently invent model output.
- No passage above threshold: show no-evidence and `Not scored` when no claim has a valid citation.
- Model cites an unknown chunk: discard the citation and report the remaining validated evidence only.

