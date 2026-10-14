"""Deterministic score calculation for assembled analysis reports."""

from collections.abc import Sequence
import html
import re

from backend.app.schemas import AnalysisReport, ClaimFinding, ScoreComponents


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


def export_report_json(report: AnalysisReport) -> str:
    """Serialize the validated report without rebuilding or changing its data."""
    return report.model_dump_json(indent=2)


def export_report_markdown(report: AnalysisReport) -> str:
    """Render a human-readable export from the same validated report object."""
    lines = [
        "# IP Lens Analysis",
        "",
        "## Summary",
        "",
        _markdown_text(report.invention_summary),
        "",
        "## Score",
        "",
        f"- Risk score: {_score_text(report.risk_score)}",
        f"- Risk band: {_markdown_text(report.risk_band)}",
        f"- Maximum claim coverage: {_score_text(report.score_components.max_claim_coverage)}",
        "- Best cited retrieval similarity: "
        f"{_score_text(report.score_components.best_cited_retrieval_similarity)}",
        f"- Formula: `{report.score_components.formula}`",
        "",
        "## Claim findings",
        "",
    ]
    for finding in report.claims:
        lines.extend(
            [
                f"### {_markdown_text(finding.claim_id)}",
                "",
                f"**Claim:** {_markdown_text(finding.claim_text)}",
                f"**Status:** {_markdown_text(finding.evidence_status)}",
                f"**Coverage:** {_score_text(finding.coverage_estimate)}",
                "",
                "#### Shared elements",
                "",
                *_markdown_list(finding.shared_elements),
                "",
                "#### Missing elements",
                "",
                *_markdown_list(finding.missing_elements),
                "",
                f"**Assessment:** {_markdown_text(finding.assessment)}",
                "",
                f"**Uncertainty:** {_markdown_text(finding.uncertainty)}",
                "",
                "#### Citations",
                "",
            ]
        )
        if not finding.citations:
            lines.append("No citations.")
        for citation in finding.citations:
            lines.extend(
                [
                    f"- **{_markdown_text(citation.filename)}**, page {citation.page}; "
                    f"similarity {citation.retrieval_similarity}",
                    f"  > {_markdown_text(citation.excerpt)}",
                ]
            )
        lines.append("")
    lines.extend(
        [
            "## Limitations",
            "",
            _markdown_text(report.limitations),
            "",
            "This is a human-review aid, not legal advice.",
            "",
        ]
    )
    return "\n".join(lines)


def _markdown_list(values: list[str]) -> list[str]:
    return [f"- {_markdown_text(value)}" for value in values] or ["- None reported."]


def _score_text(value: int | None) -> str:
    return "Not scored" if value is None else str(value)


def _markdown_text(value: str) -> str:
    escaped = html.escape(value, quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+!|>])", r"\\\1", escaped)
