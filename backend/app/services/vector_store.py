"""Persistent local ChromaDB storage for patent passage chunks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from backend.app.config import Settings, get_settings
from backend.app.services.chunking import ChunkedDocument, DocumentChunk

COLLECTION_NAME = "patent_chunks"
_BATCH_SIZE = 500


@dataclass(frozen=True, slots=True)
class SearchResult:
    chunk_id: str
    text: str
    metadata: dict[str, str | int | float | bool]
    distance: float


class VectorStore:
    """A persistent Chroma collection using local default text embeddings."""

    def __init__(self, settings: Settings | None = None) -> None:
        active_settings = settings or get_settings()
        path = Path(active_settings.chroma_path)
        if not path.is_absolute():
            project_root = Path(__file__).resolve().parents[3]
            path = project_root / path
        path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(path))
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=DefaultEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"},
        )

    def index_chunks(self, chunked: ChunkedDocument | Sequence[DocumentChunk]) -> None:
        """Replace a document's existing passages and add its chunks in batches."""
        if isinstance(chunked, ChunkedDocument):
            document_id = chunked.document_id
            chunks = list(chunked.chunks)
        else:
            chunks = list(chunked)
            if not chunks:
                return
            document_id = chunks[0].document_id

        if any(chunk.document_id != document_id for chunk in chunks):
            raise ValueError("index_chunks accepts chunks for exactly one document_id")

        self.delete_document(document_id)
        for start in range(0, len(chunks), _BATCH_SIZE):
            batch = chunks[start : start + _BATCH_SIZE]
            self.collection.add(
                ids=[chunk.chunk_id for chunk in batch],
                documents=[chunk.text for chunk in batch],
                metadatas=[_chunk_metadata(chunk) for chunk in batch],
            )

    def delete_document(self, document_id: str) -> None:
        """Delete every passage belonging to a document ID."""
        self.collection.delete(where={"document_id": document_id})

    def count(self) -> int:
        """Return the total number of indexed passage chunks."""
        return self.collection.count()

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        """Return the nearest chunks, original metadata, and raw cosine distances."""
        if not query or not query.strip():
            raise ValueError("Search query must not be empty")
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        if self.count() == 0:
            return []

        result = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.count()),
            include=["documents", "metadatas", "distances"],
        )
        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]
        return [
            SearchResult(
                chunk_id=chunk_id,
                text=text,
                metadata=metadata,
                distance=float(distance),
            )
            for chunk_id, text, metadata, distance in zip(
                ids, documents, metadatas, distances, strict=True
            )
        ]


def _chunk_metadata(chunk: DocumentChunk) -> dict[str, str | int | float | bool]:
    return {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "original_filename": chunk.original_filename,
        "display_title": chunk.display_title,
        "page_number": chunk.page_number,
        "chunk_index": chunk.chunk_index,
        "language": chunk.language,
    }
