# 09 — Document Ingestion Service

## Responsibility

Turn a user-uploaded, searchable patent document into page-aware text chunks with stable source metadata. The service handles PDF, TXT, and Markdown. DOCX is a stretch goal. It does not OCR scanned pages or make legal judgments.

## Processing path

1. Validate allowed extension and file size before parsing.
2. Decode text formats safely and extract text page-by-page from PDF.
3. Normalize whitespace while preserving page boundaries and meaningful punctuation.
4. Detect empty or text-free input and return a useful error.
5. Divide each page into overlapping chunks using configured size and overlap.
6. Assign stable document/chunk IDs and attach metadata.
7. Ask the vector-store service to replace any existing chunks for the same document ID, then index the new chunks.

## Page and source rules

| Format | Page marker behavior |
|---|---|
| PDF | 1-based physical PDF page number |
| TXT / Markdown | Page 1 unless form-feed characters explicitly separate pages |
| DOCX (stretch goal) | Page 1 unless explicit page breaks indicate later pages; do not claim Word-rendered pagination accuracy |

Retain the original uploaded filename and a safe display title. Every chunk stays within one source page so its page citation remains valid.

## Chunk metadata

Each indexed chunk carries at least `document_id`, `chunk_id`, `original_filename`, `display_title`, `page_number`, `chunk_index`, and `text`. Add a content hash for stable duplicate detection/replacement. Do not treat the filename as a trusted patent identifier.

## Chunking defaults

Start with approximately 1,200 characters and 180 characters of overlap, configurable through settings. Do not split across two pages. Keep enough context for claim comparison, and avoid duplicated leading/trailing text growing without bound.

## Replacement and errors

Uploading a file with the same stable content/document identity replaces its previous chunks instead of duplicating them. Report per-file success or failure. Errors should distinguish unsupported type, size limit, unreadable content, empty text, and a scanned-only PDF. Avoid storing raw temporary upload files after processing.

## Real patent PDFs

Published patent PDFs from Google Patents or Espacenet are usually text-searchable, but some older ones are scanned images. Test each file before the demo; if extraction is empty, the app must report it as unsupported (no OCR) rather than indexing nothing silently. Patent PDFs often have two-column layouts, so check a few extracted pages by eye.

## Manual review checklist

- Each chunk resolves to its source filename and page.
- A long page yields overlapping chunks without crossing into the next page.
- Re-uploading the same file does not increase the corpus count through duplicates.
- TXT/Markdown and PDF extraction failures give readable messages.
- A scanned PDF without an OCR layer is clearly reported as unsupported by this MVP.

