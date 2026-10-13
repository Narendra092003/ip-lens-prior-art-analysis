"""FastAPI routes and overridable application dependencies."""

from collections.abc import Iterator

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.app.config import Settings, get_settings
from backend.app.schemas import (
    CorpusResponse,
    DisclosureExtractRequest,
    DisclosureExtractResponse,
    DocumentFailure,
    DocumentUploadResponse,
    HealthResponse,
    IndexedDocument,
)
from backend.app.services.documents import DocumentExtractionError
from backend.app.services.ingestion import IngestionService, UploadTooLargeError
from backend.app.services.gemini import (
    GeminiMalformedOutputError,
    GeminiNotConfiguredError,
    GeminiProviderError,
    GeminiRateLimitedError,
    GeminiTimeoutError,
    structure_disclosure,
)
from backend.app.services.vector_store import VectorStore

router = APIRouter()


def get_settings_dependency() -> Settings:
    """Dependency wrapper so tests can override application configuration."""
    return get_settings()


def get_vector_store(
    settings: Settings = Depends(get_settings_dependency),
) -> Iterator[VectorStore]:
    """Provide the persistent vector store through FastAPI dependency injection."""
    yield VectorStore(settings)


def get_ingestion_service(
    settings: Settings = Depends(get_settings_dependency),
    vector_store: VectorStore = Depends(get_vector_store),
) -> IngestionService:
    """Build the shared ingestion service from overridable app dependencies."""
    return IngestionService(settings=settings, vector_store=vector_store)


@router.get("/health", response_model=HealthResponse)
def health(
    settings: Settings = Depends(get_settings_dependency),
) -> HealthResponse:
    """Report service health and whether Gemini is configured, without its key."""
    return HealthResponse(gemini_configured=settings.gemini_configured)


@router.get("/api/corpus", response_model=CorpusResponse)
def corpus(
    vector_store: VectorStore = Depends(get_vector_store),
) -> CorpusResponse:
    """Return the indexed passage count and local storage mode."""
    return CorpusResponse(passage_count=vector_store.count())


@router.post(
    "/api/disclosures/extract",
    response_model=DisclosureExtractResponse,
)
def extract_disclosure(
    request: DisclosureExtractRequest,
    settings: Settings = Depends(get_settings_dependency),
) -> DisclosureExtractResponse:
    """Structure disclosure text into a summary and candidate claims for review."""
    try:
        return structure_disclosure(request.disclosure_text, settings=settings)
    except GeminiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GeminiRateLimitedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except GeminiTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except (GeminiMalformedOutputError, GeminiProviderError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/api/documents", response_model=DocumentUploadResponse)
def upload_documents(
    files: list[UploadFile] = File(...),
    service: IngestionService = Depends(get_ingestion_service),
    settings: Settings = Depends(get_settings_dependency),
) -> DocumentUploadResponse:
    """Ingest multiple files independently, enforcing the per-file limit first."""
    indexed: list[IndexedDocument] = []
    failures: list[DocumentFailure] = []
    max_bytes = settings.max_upload_mb * 1024 * 1024

    for upload in files:
        filename = upload.filename or "(unnamed file)"
        try:
            if upload.size is not None and upload.size > max_bytes:
                raise UploadTooLargeError(settings.max_upload_mb)
            content = upload.file.read(max_bytes + 1)
            if len(content) > max_bytes:
                raise UploadTooLargeError(settings.max_upload_mb)

            result = service.ingest(filename, content)
            indexed.append(
                IndexedDocument(
                    document_id=result.document_id,
                    filename=result.filename,
                    title=result.title,
                    passage_count=result.passage_count,
                    skipped_page_count=result.skipped_page_count,
                    excluded_language_page_count=result.excluded_language_page_count,
                )
            )
        except (DocumentExtractionError, UploadTooLargeError) as exc:
            failures.append(DocumentFailure(filename=filename, error=str(exc)))
        except Exception:
            failures.append(
                DocumentFailure(
                    filename=filename,
                    error="The document could not be indexed because of a storage error.",
                )
            )
        finally:
            upload.file.close()

    return DocumentUploadResponse(indexed=indexed, failures=failures)
