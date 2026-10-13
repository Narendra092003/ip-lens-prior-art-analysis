"""Create stable, page-bounded overlapping chunks from extracted documents."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from backend.app.config import Settings, get_settings
from backend.app.services.documents import ExtractedDocument, Language


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    document_id: str
    chunk_id: str
    original_filename: str
    display_title: str
    page_number: int
    chunk_index: int
    language: Language
    text: str


@dataclass(frozen=True, slots=True)
class ChunkedDocument:
    document_id: str
    chunks: tuple[DocumentChunk, ...]


def chunk_document(
    document: ExtractedDocument,
    file_content: bytes,
    *,
    settings: Settings | None = None,
) -> ChunkedDocument:
    """Chunk only indexable pages, using original bytes for a stable document ID."""
    active_settings = settings or get_settings()
    if active_settings.chunk_overlap >= active_settings.chunk_size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")

    document_id = "doc_" + hashlib.sha256(file_content).hexdigest()
    chunks: list[DocumentChunk] = []
    for page in document.pages:
        if not page.included_in_index:
            continue
        page_parts = _split_page(
            page.text,
            chunk_size=active_settings.chunk_size,
            chunk_overlap=active_settings.chunk_overlap,
        )
        for chunk_index, text in enumerate(page_parts):
            chunk_key = f"{document_id}:{page.page_number}:{chunk_index}".encode("utf-8")
            chunk_id = "chunk_" + hashlib.sha256(chunk_key).hexdigest()
            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    chunk_id=chunk_id,
                    original_filename=document.source_filename,
                    display_title=document.display_title,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    language=page.language,
                    text=text,
                )
            )

    return ChunkedDocument(document_id=document_id, chunks=tuple(chunks))


def _split_page(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split one page, preferring whitespace at both chunk boundaries."""
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        limit = min(start + chunk_size, len(normalized))
        end = limit
        if limit < len(normalized):
            # Avoid undersized chunks while allowing breaks at natural word boundaries.
            earliest_break = start + chunk_size // 2
            whitespace = normalized.rfind(" ", earliest_break, limit)
            if whitespace < 0:
                whitespace = normalized.find(" ", limit)
            if whitespace >= 0:
                end = whitespace

        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(normalized):
            break

        next_start = max(start + 1, end - chunk_overlap)
        # Keep the beginning of a chunk on a word boundary where possible.
        next_space = normalized.find(" ", next_start, end)
        if next_space >= 0:
            next_start = next_space + 1
        start = next_start

    return chunks
