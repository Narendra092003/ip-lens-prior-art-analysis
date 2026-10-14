"""Deterministic score calculation for assembled analysis reports."""

from collections.abc import Sequence

from backend.app.schemas import ClaimFinding, ScoreComponents


def calculate_risk_score(
    findings: Sequence[ClaimFinding],
) -> tuple[int | None, str, ScoreComponents]:
    """Score evidence-backed findings from their coverage and valid citations only."""
    evidence_findings = [
        finding
        for finding in findings
        if finding.evidence_status == "evidence" and finding.citations
    ]
    if not evidence_findings:
        return None, "Not scored", ScoreComponents()

    max_coverage = max(
        finding.coverage_estimate
        for finding in evidence_findings
        if finding.coverage_estimate is not None
    )
    best_similarity = max(
        citation.retrieval_similarity
        for finding in evidence_findings
        for citation in finding.citations
    )
    risk_score = round(0.65 * max_coverage + 0.35 * best_similarity)
    risk_band = "Low" if risk_score <= 34 else "Moderate" if risk_score <= 69 else "High"
    components = ScoreComponents(
        max_claim_coverage=max_coverage,
        best_cited_retrieval_similarity=best_similarity,
    )
    return risk_score, risk_band, components
