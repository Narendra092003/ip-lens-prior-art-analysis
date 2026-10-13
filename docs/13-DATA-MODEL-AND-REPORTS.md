# 13 — Data Model and Reports

## Core records

| Record | Key fields |
|---|---|
| Document | `document_id`, original filename, display title, content hash, indexed timestamp |
| Passage/chunk | `chunk_id`, `document_id`, page number, chunk index, text, embedding metadata |
| Reviewed claim | `claim_id`, claim text, user order/index |
| Claim finding | claim ID/text, coverage estimate, shared elements, missing elements, assessment, uncertainty, citations |
| Citation | chunk ID, document ID, source title, filename, page, excerpt, retrieval-similarity value |
| Analysis report | analysis ID, timestamp, disclosure summary, reviewed claims, score/band/components, findings, limitations |

Use stable IDs within stored documents and one analysis. Timestamps are ISO 8601 UTC strings in API/export data. File paths on the user's machine are never part of public citations.

## Report example

```json
{
  "analysis_id": "analysis_…",
  "created_at": "2026-10-13T12:00:00Z",
  "invention_summary": "A concise summary for reviewer context.",
  "reviewed_claims": ["A system comprising …"],
  "risk_score": 57,
  "risk_band": "Moderate",
  "score_components": {
    "max_claim_coverage": 60,
    "best_cited_retrieval_similarity": 52,
    "formula": "round(0.65 * coverage + 0.35 * similarity)"
  },
  "claims": [],
  "limitations": "This is a triage aid over the uploaded corpus, not legal advice."
}
```

When no claim has a valid citation, `risk_score` is JSON `null`, `risk_band` is `Not scored`, and score components explain that evidence was insufficient. Never substitute zero and call it Low risk.

## Deterministic triage heuristic

For claims with at least one valid citation:

```text
risk_score = round(0.65 * max_claim_coverage + 0.35 * best_cited_retrieval_similarity)
```

Both inputs range from 0 to 100. `max_claim_coverage` is the highest model comparison estimate among evidence-backed claims. `best_cited_retrieval_similarity` is the highest converted similarity among valid report citations. Bands: Low 0–34, Moderate 35–69, High 70–100. The score is an unvalidated heuristic until evaluated on a labeled corpus.

## Exports

Generate JSON and Markdown from the same validated report object so the UI and downloads cannot disagree. The Markdown report should include the corpus limitation, score formula, claim-by-claim findings, source/page/excerpt citations, and uncertainty. Escape user-provided text appropriately in Markdown.

