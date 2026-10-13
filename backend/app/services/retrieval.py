"""Claim-by-claim retrieval and similarity thresholding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from backend.app.config import Settings, get_settings
from backend.app.schemas import ReviewedClaim
from backend.app.services.vector_store import SearchResult, VectorStore


@dataclass(frozen=True, slots=True)
class RetrievedPassage:
    """A useful retrieved passage with source provenance and raw distance."""

    chunk_id: str
    document_id: str
    filename: str
    title: str
    page: int
    excerpt: str
    retrieval_similarity: int
    distance: float


@dataclass(frozen=True, slots=True)
class ClaimRetrieval:
    """Useful passages and threshold-drop count for one reviewed claim."""

    claim_id: str
    passages: list[RetrievedPassage]
    dropped_count: int


def cosine_distance_to_similarity(distance: float) -> int:
    """Convert cosine distance to clamped 0-100 retrieval similarity."""
    return max(0, min(100, round((1 - distance) * 100)))


def retrieve_claims(
    reviewed_claims: Sequence[ReviewedClaim],
    *,
    top_k: int | None = None,
    vector_store: VectorStore | None = None,
    settings: Settings | None = None,
) -> dict[str, ClaimRetrieval]:
    """Search separately for each claim and retain passages meeting MIN_SIMILARITY."""
    active_settings = settings or get_settings()
    active_top_k = active_settings.default_top_k if top_k is None else top_k
    if not 1 <= active_top_k <= 10:
        raise ValueError("top_k must be between 1 and 10")

    store = vector_store if vector_store is not None else VectorStore(active_settings)
    results: dict[str, ClaimRetrieval] = {}
    for claim in reviewed_claims:
        useful: list[RetrievedPassage] = []
        dropped_count = 0
        for result in store.search(claim.text, top_k=active_top_k):
            similarity = cosine_distance_to_similarity(result.distance)
            if similarity < active_settings.min_similarity:
                dropped_count += 1
                continue
            useful.append(_to_passage(result, similarity))
        results[claim.claim_id] = ClaimRetrieval(
            claim_id=claim.claim_id,
            passages=useful,
            dropped_count=dropped_count,
        )
    return results


def _to_passage(result: SearchResult, similarity: int) -> RetrievedPassage:
    metadata = result.metadata
    return RetrievedPassage(
        chunk_id=result.chunk_id,
        document_id=str(metadata["document_id"]),
        filename=str(metadata["original_filename"]),
        title=str(metadata["display_title"]),
        page=int(metadata["page_number"]),
        excerpt=result.text,
        retrieval_similarity=similarity,
        distance=result.distance,
    )
