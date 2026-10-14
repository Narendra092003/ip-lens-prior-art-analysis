"""FastAPI routes and overridable application dependencies."""

from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.app.config import Settings, get_settings
from backend.app.schemas import (
    AnalysisExports,
    AnalysisReport,
    AnalysisRequest,
    AnalysisResponse,
    CorpusResponse,
    DisclosureExtractRequest,
    DisclosureExtractResponse,
    DocumentFailure,
    DocumentUploadResponse,
    HealthResponse,
    IndexedDocument,
    ReviewedClaim,
)
from backend.app.services.documents import DocumentExtractionError
from backend.app.services.ingestion import IngestionService, UploadTooLargeError
from backend.app.services.reports import export_report_json, export_report_markdown
from backend.app.services.gemini import (
    GeminiMalformedOutputError,
    GeminiNotConfiguredError,
    GeminiProviderError,
    GeminiRateLimitedError,
    GeminiTimeoutError,
    structure_disclosure,
)
from backend.app.services.vector_store import VectorStore
from backend.app.workflow import run_analysis

router = APIRouter()


def get_settings_dependency() -> Settings:
    """Dependency wrapper so tests can override application configuration."""
    return get_settings()


def get_gemini_client() -> Any | None:
    """Dependency hook for replacing the Gemini client in API tests."""
    return None


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


@router.post("/api/analyses", response_model=AnalysisResponse)
def analyze(
    request: AnalysisRequest,
    settings: Settings = Depends(get_settings_dependency),
    vector_store: VectorStore = Depends(get_vector_store),
    gemini_client: Any | None = Depends(get_gemini_client),
) -> AnalysisResponse:
    """Analyze user-reviewed claims and return one report with both export formats."""
    if len(request.reviewed_claims) > settings.max_claims:
        raise HTTPException(
            status_code=400,
            detail=f"At most {settings.max_claims} reviewed claims may be analyzed.",
        )
    if not settings.gemini_configured:
        raise HTTPException(status_code=503, detail="Gemini is not configured.")

    reviewed_claims = [
        ReviewedClaim(claim_id=f"claim-{index}", text=text)
        for index, text in enumerate(request.reviewed_claims, start=1)
    ]
    try:
        state = run_analysis(
            request.disclosure_text,
            reviewed_claims,
            top_k=request.top_k,
            prompt_version=request.prompt_version,
            invention_summary=request.invention_summary or "Summary not provided.",
            settings=settings,
            vector_store=vector_store,
            gemini_client=gemini_client,
        )
    except GeminiNotConfiguredError:
        raise HTTPException(status_code=503, detail="Gemini is not configured.") from None
    except (
        GeminiRateLimitedError,
        GeminiTimeoutError,
        GeminiMalformedOutputError,
        GeminiProviderError,
    ):
        raise HTTPException(
            status_code=502,
            detail="The analysis could not be completed because the model provider failed.",
        ) from None

    if state.get("status") != "completed" or state.get("report") is None:
        raise HTTPException(
            status_code=502,
            detail="The analysis could not be completed because the model provider failed.",
        )
    report: AnalysisReport = state["report"]
    return AnalysisResponse(
        report=report,
        exports=AnalysisExports(
            json_export=export_report_json(report),
            markdown_export=export_report_markdown(report),
        ),
    )


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
