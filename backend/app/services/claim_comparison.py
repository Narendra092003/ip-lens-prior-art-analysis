"""Claim-by-claim comparison of useful retrieved passages."""

from __future__ import annotations

from typing import Any

from backend.app.config import Settings
from backend.app.schemas import ClaimFinding, EvidenceCitation, ReviewedClaim
from backend.app.services.gemini import ClaimComparisonResult, compare_claim
from backend.app.services.retrieval import ClaimRetrieval, RetrievedPassage


def compare_claim_finding(
    claim: ReviewedClaim,
    retrieval: ClaimRetrieval,
    *,
    prompt_version: str = "v1",
    settings: Settings | None = None,
    client: Any | None = None,
) -> ClaimFinding:
    """Return a finding for one reviewed claim, skipping Gemini without evidence."""
    if not retrieval.passages:
        return ClaimFinding(
            claim_id=claim.claim_id,
            claim_text=claim.text,
            evidence_status="no_evidence",
            coverage_estimate=None,
            shared_elements=[],
            missing_elements=[],
            assessment="No useful passage was retrieved for this claim.",
            uncertainty="The indexed corpus may not contain relevant material; this is not evidence of novelty.",
            citations=[],
        )

    comparison = compare_claim(
        claim,
        retrieval.passages,
        prompt_version=prompt_version,
        settings=settings,
        client=client,
    )
    passages_by_id = {passage.chunk_id: passage for passage in retrieval.passages}
    citations = [
        _citation(passages_by_id[chunk_id])
        for chunk_id in comparison.cited_chunk_ids
        if chunk_id in passages_by_id
    ]
    return ClaimFinding(
        claim_id=claim.claim_id,
        claim_text=claim.text,
        evidence_status="evidence",
        coverage_estimate=comparison.coverage_estimate,
        shared_elements=comparison.shared_elements,
        missing_elements=comparison.missing_elements,
        assessment=comparison.assessment,
        uncertainty=comparison.uncertainty,
        citations=citations,
    )


def _citation(passage: RetrievedPassage) -> EvidenceCitation:
    return EvidenceCitation(
        chunk_id=passage.chunk_id,
        document_id=passage.document_id,
        title=passage.title,
        filename=passage.filename,
        page=passage.page,
        excerpt=passage.excerpt,
        retrieval_similarity=passage.retrieval_similarity,
    )
