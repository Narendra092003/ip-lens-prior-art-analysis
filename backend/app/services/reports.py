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
    settings = report.analysis_settings
    duration_seconds = sum(report.durations_ms.values()) / 1000
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
        "## Settings",
        "",
        f"- Comparison prompt version: `{settings.comparison_prompt_version}`",
        f"- Gemini model: `{_markdown_text(settings.gemini_model)}`",
        f"- MIN_SIMILARITY: {settings.min_similarity}",
        f"- top_k: {settings.top_k}",
        f"- Corpus passages at analysis time: {settings.corpus_passage_count}",
        f"- Total analysis duration: {duration_seconds:.1f} seconds",
        "",
        "## Claim findings",
        "",
    ]
    status_labels = {
        "evidence": "Evidence",
        "no_evidence": "No evidence",
        "no_supporting_passage": "No supporting passage",
        "unsupported": "Unsupported",
    }
    for finding in report.claims:
        status_label = status_labels[finding.evidence_status]
        if finding.evidence_status == "no_supporting_passage":
            status_explanation = (
                f"{finding.useful_passage_count} related passages were retrieved "
                f"(best similarity {finding.best_retrieval_similarity}), but none supported this claim."
            )
        elif finding.evidence_status == "no_evidence":
            status_explanation = (
                "No passage reached the similarity threshold "
                f"({settings.min_similarity})."
            )
        else:
            status_explanation = ""
        lines.extend(
            [
                f"### {_markdown_text(finding.claim_id)}",
                "",
                f"**Claim:** {_markdown_text(finding.claim_text)}",
                f"**Status:** {status_label}",
                f"**Coverage:** {_coverage_text(finding.coverage_estimate)}",
                "",
                *([_markdown_text(status_explanation), ""] if status_explanation else []),
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
        citation_views = _merged_citation_views(finding.citations)
        if not citation_views:
            lines.append("No citations.")
        for citation, excerpt, combined in citation_views:
            combined_note = " *(Combines adjacent passages.)*" if combined else ""
            lines.extend(
                [
                    f"- **{_markdown_text(citation.filename)}**, page {citation.page}; "
                    f"similarity {citation.retrieval_similarity}{combined_note}",
                    f"  > {_markdown_text(_shorten_excerpt(excerpt))}",
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


def _coverage_text(value: int | None) -> str:
    return "Not assessed" if value is None else f"{value}/100"


def _shorten_excerpt(excerpt: str, limit: int = 400) -> str:
    if len(excerpt) <= limit:
        return excerpt
    prefix = excerpt[: limit - 1]
    boundary = prefix.rfind(" ")
    if boundary >= limit * 0.7:
        prefix = prefix[:boundary]
    return f"{prefix.rstrip()}…"


def _merged_citation_views(citations):
    """Merge display excerpts only when same-page chunks share substantial text."""
    groups = []
    for citation in citations:
        excerpt = " ".join(citation.excerpt.split())
        merged = False
        for group in groups:
            existing = group["citation"]
            if (
                existing.document_id != citation.document_id
                or existing.page != citation.page
            ):
                continue
            combination = _combine_overlapping_text(group["excerpt"], excerpt)
            if combination is None:
                continue
            group["excerpt"] = combination
            group["combined"] = True
            if citation.retrieval_similarity > existing.retrieval_similarity:
                group["citation"] = citation
            merged = True
            break
        if not merged:
            groups.append({"citation": citation, "excerpt": excerpt, "combined": False})
    return [
        (group["citation"], group["excerpt"], group["combined"])
        for group in groups
    ]


def _combine_overlapping_text(first: str, second: str) -> str | None:
    if first in second:
        return second
    if second in first:
        return first
    max_overlap = min(len(first), len(second))
    for overlap in range(max_overlap, 31, -1):
        if first.endswith(second[:overlap]):
            return first + second[overlap:]
        if second.endswith(first[:overlap]):
            return second + first[overlap:]
    return None


def _markdown_text(value: str) -> str:
    escaped = html.escape(value, quote=False)
    return re.sub(r"([\\`*_{}\[\]#+!|>])", r"\\\1", escaped)
