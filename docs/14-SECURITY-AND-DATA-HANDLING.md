# 14 — Security and Data Handling

## Intended deployment boundary

Local use is single-user. The public Docker demo adds an optional access-code prompt in the Streamlit UI, but it has no user accounts, API authentication contract, tenant isolation, or production security controls. The container binds FastAPI to loopback and publishes only Streamlit. Do not present it as a secure enterprise legal platform.

## Data flow and disclosure

- Uploaded files are parsed and indexed in local ChromaDB under ignored `data/`.
- The disclosure text and retrieved excerpts are sent to the configured Gemini API for generation.
- The app must show this data-handling notice before analysis.
- When `DEMO_MODE=true`, the UI displays a public-demo warning that text goes to Gemini and only fictional material should be used.
- Use fictional samples in demos. Do not submit confidential or client material without permission and an approved data-handling basis.
- Do not persist full analysis reports by default. Exports are initiated by the user.

## Threats and controls

| Risk | MVP control |
|---|---|
| API key committed or shown | `.env` ignored by Git; `.env.example` contains placeholders; health endpoint reveals only whether a key is configured |
| Prompt injection inside a patent document | Treat passages as untrusted data; comparison prompt disallows following document instructions; no tools or external actions are exposed to Gemini |
| Hallucinated citation | Validate every cited chunk ID against the current claim's retrieved IDs and enrich metadata from ChromaDB |
| Oversized or malicious file | Enforce file-size and type allow-lists before parsing; surface safe errors |
| Public-demo resource abuse | Demo container caps requests at four claims and 2 MB per file; uploads are disabled unless `DEMO_ALLOW_UPLOADS=true` |
| Unwanted public UI access | Optional `ACCESS_CODE` blocks disclosure extraction and analysis in the UI; it is not API authentication, so the API binds to container loopback |
| Scanned PDF mistaken for searchable | Detect empty extraction and report that OCR is unsupported |
| Local corpus accidentally committed | Ignore `data/`, environment files, caches, and local exports |
| Unsupported legal conclusion | Label all findings as human-review triage and display scope/uncertainty limitations |

## Enterprise deployment note

The MVP sends disclosure text to the public Gemini API, which is acceptable only for fictional or public material. Unfiled invention disclosures are highly confidential. In a company setting the model call would run on approved infrastructure inside the organisation's own environment (for example a tenant-hosted model service), with access control and logging. Because the SDK is isolated in one module, this is a provider swap, not a redesign. Say this explicitly when presenting the project.

## Secrets

Read secrets only from environment-backed settings. Never put Gemini keys in source, prompts, logs, generated reports, screenshots, or chat attachments. The API returns a `gemini_configured` boolean only.

For a Space, store `GEMINI_API_KEY` and optional `ACCESS_CODE` as Space secrets, and set `GEMINI_MODEL`/`DEMO_MODE` as variables. The image excludes `.env`, local Chroma data, local exports, caches and `examples/real/`. Only the fictional synthetic corpus is included and seeded into an empty store. `DEMO_ALLOW_UPLOADS` should remain false unless public uploads are intentionally enabled.

## Legal and research limits

The app compares only uploaded material. Search similarity does not establish legal relevance, priority date, claim construction, infringement, novelty, or patentability. The output is not legal advice. Analysts should review original documents and consult qualified counsel for legal decisions.

