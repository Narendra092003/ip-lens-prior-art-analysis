"""Pure presentation helpers shared by the Streamlit results view and its tests."""

from __future__ import annotations

from typing import Any


def claim_status_display(
    finding: dict[str, Any],
    similarity_threshold: int,
) -> tuple[str, str]:
    """Return a readable status label and explanation for one claim result."""
    status = finding.get("evidence_status", "unsupported")
    if status == "evidence":
        return "Evidence", "Useful retrieved passages were cited as supporting parts of this claim."
    if status == "no_evidence":
        return (
            "No evidence",
            f"No passage reached the similarity threshold ({similarity_threshold}).",
        )
    if status == "no_supporting_passage":
        return (
            "No supporting passage",
            f"{finding.get('useful_passage_count', 0)} related passages were retrieved "
            f"(best similarity {finding.get('best_retrieval_similarity')}), "
            "but none supported this claim.",
        )
    return (
        "Unsupported",
        "Gemini returned citations that could not be matched to retrieved passages.",
    )


def display_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge same-document/page citation excerpts only when text overlaps."""
    groups: list[dict[str, Any]] = []
    for citation in citations:
        excerpt = " ".join(str(citation.get("excerpt", "")).split())
        for group in groups:
            current = group["citation"]
            if (
                current.get("document_id") != citation.get("document_id")
                or current.get("page") != citation.get("page")
            ):
                continue
            merged = _combine_overlapping_text(group["excerpt"], excerpt)
            if merged is None:
                continue
            group["excerpt"] = merged
            group["combines_adjacent_passages"] = True
            if citation.get("retrieval_similarity", 0) > current.get("retrieval_similarity", 0):
                group["citation"] = citation
            break
        else:
            groups.append(
                {
                    "citation": citation,
                    "excerpt": excerpt,
                    "combines_adjacent_passages": False,
                }
            )
    return [
        {
            "filename": item["citation"].get("filename", "Unknown file"),
            "page": item["citation"].get("page", "?"),
            "retrieval_similarity": item["citation"].get("retrieval_similarity", "?"),
            "excerpt": item["excerpt"],
            "combines_adjacent_passages": item["combines_adjacent_passages"],
        }
        for item in groups
    ]


def _combine_overlapping_text(first: str, second: str) -> str | None:
    if first in second:
        return second
    if second in first:
        return first
    for overlap in range(min(len(first), len(second)), 31, -1):
        if first.endswith(second[:overlap]):
            return first + second[overlap:]
        if second.endswith(first[:overlap]):
            return second + first[overlap:]
    return None
