# 08 — API Design

## API conventions

- Use Pydantic request and response models for every JSON endpoint.
- Keep response shapes stable and avoid returning stack traces, local paths, or secrets.
- Return actionable client errors for malformed input and file errors; return a service error when Gemini is unavailable.
- Use one request per analysis. The MVP does not require accounts, streaming, background jobs, or pagination.
- FastAPI should expose its OpenAPI page at `/docs` during local development.

## Endpoint summary

| Method and path | Input | Successful response |
|---|---|---|
| `GET /health` | None | API status and a `gemini_configured` boolean; never the key |
| `GET /api/corpus` | None | Indexed document/passage counts and storage mode |
| `POST /api/documents` | Multipart `files[]` | Per-file success/failure, document IDs, passage counts |
| `POST /api/disclosures/extract` | JSON disclosure text | Summary and candidate claims for user review |
| `POST /api/analyses` | Disclosure, reviewed claims, optional `top_k` | Claim findings, validated evidence, score, limitations |

## Request examples

### Upload documents

```http
POST /api/documents
Content-Type: multipart/form-data

files: prior_art.pdf
files: second_document.txt
```

### Structure a disclosure

```json
{
  "disclosure_text": "A synthetic description of the invention for the demo."
}
```

### Analyze user-reviewed claims

```json
{
  "disclosure_text": "The original disclosure text.",
  "reviewed_claims": [
    "A system comprising ...",
    "The system of claim 1, wherein ..."
  ],
  "top_k": 4
}
```

The exact response fields are defined in [`13-DATA-MODEL-AND-REPORTS.md`](./13-DATA-MODEL-AND-REPORTS.md) and the Pydantic schemas.

## Validation and errors

- Unsupported extension or media type: clear client error identifying the rejected file.
- File above the configured default of 25 MB: reject it before reading the whole file into memory.
- Empty, unreadable, or text-free scanned PDF: return a per-file extraction failure with a helpful reason.
- Invalid disclosure, empty claims, or `top_k` outside 1–10: validation error.
- Gemini key missing when a model call is required: service error that names the missing configuration key, never its value.
- Provider timeout or invalid structured output: service error with a safe message; do not return invented fallback content.

For multi-file uploads, process each file independently so one failure does not conceal successful indexing of other files. Do not leak absolute paths or raw exception details in public responses.

