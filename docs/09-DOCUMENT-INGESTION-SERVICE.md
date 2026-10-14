# 09 — Document Ingestion Service

## Responsibility

Convert a supported upload into searchable, page-aware chunks with source metadata. Supported formats are searchable PDF, TXT, and Markdown; DOCX is not supported. The service does not OCR scanned pages or make legal judgments.

## Processing path

1. Check file extension and per-file size before parsing.
2. Decode text or extract searchable PDF text page by page.
3. Skip near-empty PDF pages with fewer than 50 non-whitespace characters. Also skip likely drawing sheets when a sheet marker or figure label occurs with fewer than 40 real words; these increase the drawing-page skip count.
4. Normalize text, retain page boundaries, tag each page `en`, `de`, `fr`, or `unknown` using stopwords, and mark whether its language is selected for indexing.
5. Split included pages into overlapping chunks using `CHUNK_SIZE` and `CHUNK_OVERLAP`; chunks never cross page boundaries.
6. Assign a content-derived document ID and stable chunk IDs, then replace existing chunks for that document before indexing.
7. Return passage count, drawing pages skipped, language-excluded page count, or a clear per-file failure.

`INDEX_LANGUAGES` defaults to `en`. If all pages are excluded by this setting, ingestion reports “no pages in the selected index languages.” Excluded-language pages are not counted as drawing pages. PDFs with no usable text layer are reported as scanned/unsearchable; OCR is not implemented.

## Page and source rules

| Format | Page marker behavior |
|---|---|
| PDF | 1-based physical PDF page number |
| TXT / Markdown | Page 1 unless form-feed characters explicitly separate pages |

Retain the original filename and a safe display title. Every chunk stays within one source page so its page citation remains valid. Do not treat filenames as trusted patent identifiers.

## Chunking defaults

Defaults are 1,200 characters and 180 characters of overlap, configured through settings. Whitespace is preferred as a chunk boundary where practical. Re-indexing identical file content replaces its prior chunk set rather than increasing the count.

## Bulk ingestion

`uv run python scripts/ingest_folder.py examples/real` processes supported files in a folder through the same extraction, chunking, and vector-store service used by the API. It prints per-file progress and a final summary; temporary uploads are not retained.

## Manual review checklist

- Each indexed chunk resolves to its filename and physical/source page.
- Drawing pages and excluded languages contribute to their separate counts.
- Re-uploading identical content does not create duplicates.
- TXT/Markdown and PDF failures provide readable reasons.
- A scanned PDF is clearly reported as unsupported because OCR is unavailable.
