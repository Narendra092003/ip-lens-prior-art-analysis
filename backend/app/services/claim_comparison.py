"""Claim-by-claim comparison of useful retrieved passages."""

from __future__ import annotations

import re
from typing import Any

from backend.app.config import Settings
from backend.app.schemas import ClaimFinding, ReviewedClaim
from backend.app.services.gemini import (
    ClaimComparisonResult,
    ClaimComparisonV2Result,
    compare_claim,
)
from backend.app.services.retrieval import ClaimRetrieval


def compare_claim_result(
    claim: ReviewedClaim,
    retrieval: ClaimRetrieval,
    *,
    prompt_version: str = "v1",
    settings: Settings | None = None,
    client: Any | None = None,
) -> ClaimComparisonResult:
    """Compare one claim with its useful passages and retain proposed IDs for validation."""
    if not retrieval.passages:
        raise ValueError("compare_claim_result requires at least one useful passage")
    result = compare_claim(
        claim,
        retrieval.passages,
        prompt_version=prompt_version,
        settings=settings,
        client=client,
    )
    if prompt_version == "v1":
        return result
    if not isinstance(result, ClaimComparisonV2Result):
        raise TypeError("Prompt v2 must return element-level comparison results")
    return _convert_v2_result(result, retrieval)


_COVERAGE_POINTS = {"explicit": 1.0, "inferred": 0.75, "partial": 0.5, "missing": 0.0}
_CLAIM_REFERENCE_ONLY = re.compile(
    r"^\s*(?:the\s+)?(?:system|apparatus|method|device|invention)\s+of\s+claim\s+\d+\s*[,;:.]?\s*$",
    re.IGNORECASE,
)


def _convert_v2_result(
    result: ClaimComparisonV2Result,
    retrieval: ClaimRetrieval,
) -> ClaimComparisonResult:
    """Convert element-level judgments into the existing finding contract."""
    elements = [
        element
        for element in result.elements
        if not _CLAIM_REFERENCE_ONLY.fullmatch(element.element_text)
    ]
    if not elements:
        raise ValueError("Prompt v2 returned no technical claim elements")

    shared_elements: list[str] = []
    missing_elements: list[str] = []
    labels: list[str] = []
    for element in elements:
        if element.status == "explicit":
            shared_elements.append(element.element_text)
        elif element.status == "inferred":
            detail = f": {element.explanation}" if element.explanation else ""
            shared_elements.append(f"{element.element_text} (inferred{detail})")
        elif element.status == "partial":
            detail = f": {element.explanation}" if element.explanation else ""
            shared_elements.append(f"{element.element_text} (partially covered{detail})")
        else:
            missing_elements.append(element.element_text)
        labels.extend(element.supporting_passage_labels)

    coverage = round(
        sum(_COVERAGE_POINTS[element.status] for element in elements) / len(elements) * 100
    )
    label_to_chunk_id = {
        f"P{index}": passage.chunk_id
        for index, passage in enumerate(retrieval.passages, start=1)
    }
    cited_chunk_ids: list[str] = []
    discarded_count = 0
    for label in dict.fromkeys(labels):
        chunk_id = label_to_chunk_id.get(label)
        if chunk_id is None:
            discarded_count += 1
            continue
        cited_chunk_ids.append(chunk_id)
    return ClaimComparisonResult(
        shared_elements=shared_elements,
        missing_elements=missing_elements,
        coverage_estimate=coverage,
        assessment=result.assessment,
        uncertainty=result.uncertainty,
        cited_chunk_ids=cited_chunk_ids,
        discarded_citation_count=discarded_count,
    )


def no_evidence_finding(claim: ReviewedClaim) -> ClaimFinding:
    """Build a no-evidence finding in Python without calling Gemini."""
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
