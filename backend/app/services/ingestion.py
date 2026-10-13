"""Connect document extraction, page-aware chunking, and persistent indexing."""

from dataclasses import dataclass

from backend.app.config import Settings, get_settings
from backend.app.services.chunking import chunk_document
from backend.app.services.documents import extract_document
from backend.app.services.vector_store import VectorStore


class UploadTooLargeError(ValueError):
    """Raised when an upload exceeds the configured per-file limit."""

    def __init__(self, max_upload_mb: int) -> None:
        super().__init__(f"File exceeds the per-file upload limit of {max_upload_mb} MB.")


class DocumentStorageError(ValueError):
    """Raised when extracted chunks cannot be written to the local vector store."""


@dataclass(frozen=True, slots=True)
class IngestionResult:
    document_id: str
    filename: str
    title: str
    passage_count: int
    skipped_page_count: int
    excluded_language_page_count: int


class IngestionService:
    """Ingest one upload with shared project settings and vector storage."""

    def __init__(self, settings: Settings | None = None, vector_store: VectorStore | None = None):
        self.settings = settings or get_settings()
        self.vector_store = vector_store or VectorStore(self.settings)

    def ingest(self, filename: str, content: bytes) -> IngestionResult:
        """Extract, chunk and index one file, returning safe source/count metadata."""
        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise UploadTooLargeError(self.settings.max_upload_mb)

        extracted = extract_document(
            filename,
            content,
            index_languages=self.settings.index_languages,
        )
        chunked = chunk_document(extracted, content, settings=self.settings)
        try:
            self.vector_store.index_chunks(chunked)
        except Exception as exc:
            raise DocumentStorageError("The document could not be written to local storage.") from exc

        return IngestionResult(
            document_id=chunked.document_id,
            filename=extracted.source_filename,
            title=extracted.display_title,
            passage_count=len(chunked.chunks),
            skipped_page_count=extracted.skipped_page_count,
            excluded_language_page_count=extracted.excluded_language_page_count,
        )
