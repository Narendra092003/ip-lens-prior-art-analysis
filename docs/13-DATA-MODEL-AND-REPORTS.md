# 13 — Data Model and Reports

## Core records

| Record | Key fields |
|---|---|
| Indexed document | Content-derived `document_id`, filename, display title, passage count, skipped drawing pages, language-excluded pages |
| Passage/chunk | `chunk_id`, `document_id`, page number, chunk index, language, text, embedding metadata |
| Reviewed claim | Stable `claim_id`, text, user order/index |
| Claim finding | Claim ID/text, one of four evidence statuses, coverage if assessed, useful passage count, best retrieval similarity, shared/missing elements, assessment, uncertainty, citations |
| Citation | Chunk/document IDs, title, filename, page, excerpt, retrieval similarity |
| Analysis report | Analysis ID, timestamp, summary, reviewed claims, score/band/components, analysis settings, findings, durations, limitations |

Analysis requests accept plain claim strings (assigned `claim-1`, `claim-2`, …) or `{ "claim_id", "text" }` objects that preserve caller IDs. Duplicate IDs are rejected. `prompt_version` accepts `v1` or `v2`, defaulting to v2. JSON keeps machine-readable status values.

## Finding statuses

| Code | Meaning | Coverage/citations |
|---|---|---|
| `evidence` | At least one retrieved passage was cited and validated for this claim | Coverage and validated citations present |
| `no_evidence` | No passage reached `MIN_SIMILARITY` | No coverage or citations |
| `no_supporting_passage` | Useful passages were compared, but the model cited none | No coverage or citations; comparison elements retained |
| `unsupported` | All model citation references failed to map to supplied passages | No coverage or citations |

Only `evidence` findings contribute to risk scoring.

## Analysis settings and exports

Each report records comparison prompt version, Gemini model, `MIN_SIMILARITY`, `top_k`, and corpus passage count at analysis time. The report also records per-node durations in milliseconds. JSON and Markdown exports are generated from the same validated report object; reports are not written to disk by the API by default.

Markdown includes settings, total duration in seconds, human-readable status names and explanations, score components, limitations, and citations. Citation excerpts are shortened to about 400 characters for Markdown only. Overlapping citations from the same document/page are combined for display with a note; JSON preserves every citation and its full excerpt.

## Deterministic triage score

For evidence findings with validated citations:

```text
risk_score = round(0.65 * max_claim_coverage + 0.35 * best_cited_retrieval_similarity)
```

Coverage and similarity are 0–100. The bands are Low 0–34, Moderate 35–69, and High 70–100. If there is no `evidence` finding, `risk_score` is null and `risk_band` is `Not scored`; non-evidence findings never contribute. The score is an unvalidated triage heuristic over the uploaded corpus, not a probability or legal conclusion. Model coverage judgments can vary between runs.

## Human-readable Markdown report

The Markdown export contains the summary; score, components, and formula; settings; per-claim text, status, coverage, shared/missing elements, and citations with filename, page, similarity, and excerpt; total duration; and limitations. It ends with a human-review aid, not legal advice statement. The JSON export retains the complete validated report without display-only excerpt shortening or citation merging.
