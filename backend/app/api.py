"""FastAPI routes and overridable application dependencies."""

from collections.abc import Iterator

from fastapi import APIRouter, Depends

from backend.app.config import Settings, get_settings
from backend.app.schemas import CorpusResponse, HealthResponse
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
