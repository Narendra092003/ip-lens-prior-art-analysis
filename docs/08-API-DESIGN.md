# 08 — API Design

## API conventions

- Use Pydantic contracts for JSON requests and responses.
- Return safe, actionable errors; do not expose stack traces, local paths, secrets, or raw provider payloads.
- Process multipart uploads independently so one failed file does not hide successful files.
- FastAPI exposes its OpenAPI page at `/docs` during local development.

## Endpoint summary

| Method and path | Input | Successful response |
|---|---|---|
| `GET /health` | None | Status and `gemini_configured` boolean; never the key |
| `GET /api/corpus` | None | Indexed passage count and storage/embedding mode |
| `POST /api/documents` | Multipart `files[]` | Per-file successes and failures, including passage and skipped-page counts |
| `POST /api/disclosures/extract` | Disclosure text | Summary and candidate claims for user review |
| `POST /api/analyses` | Disclosure, reviewed claims, optional `top_k` and `prompt_version` | Validated report and JSON/Markdown exports |

## Analysis request

`reviewed_claims` accepts plain strings, which receive sequential IDs such as `claim-1`, or objects `{ "claim_id": "…", "text": "…" }`, whose IDs are retained. Duplicate IDs are rejected. `prompt_version` is `v1` or `v2` and defaults to `v2`; `top_k` is optional and defaults to the configured value (4, maximum 10).

```json
{
  "disclosure_text": "The original disclosure text.",
  "reviewed_claims": [
    {"claim_id": "claim-a", "text": "A system comprising …"},
    "A dependent claim …"
  ],
  "prompt_version": "v2",
  "top_k": 4
}
```

The response contains the validated `AnalysisReport` and both exports generated from that same report object. Reports are not persisted to disk by default. Full contracts are in [`13-DATA-MODEL-AND-REPORTS.md`](./13-DATA-MODEL-AND-REPORTS.md) and `backend/app/schemas.py`.

## Validation and errors

- Uploads accept PDF, TXT, and Markdown. Each file has a configured size limit (25 MB by default); individual extraction/indexing failures are returned in the upload response.
- Analysis request validation, duplicate claim IDs, and exceeding `MAX_CLAIMS` return HTTP 400.
- Missing Gemini configuration returns 503. Disclosure extraction maps Gemini rate limiting to 429; analysis provider errors, including rate limits, use a safe 502 response.
- Empty, unreadable, scanned-only, unsupported, and all-excluded-language documents return a per-file error reason.
- Never return credentials, prompt text, disclosure contents, raw provider details, or temporary file paths.
