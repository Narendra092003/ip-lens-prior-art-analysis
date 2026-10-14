"""Bounded LangGraph workflow for claim-by-claim prior-art analysis."""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any, Literal, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from backend.app.config import Settings, get_settings
from backend.app.schemas import (
    AnalysisSettings,
    AnalysisReport,
    ClaimFinding,
    EvidenceCitation,
    ReviewedClaim,
    ScoreComponents,
)
from backend.app.services.claim_comparison import (
    compare_claim_result,
    no_evidence_finding as build_no_evidence_finding,
)
from backend.app.services.gemini import ClaimComparisonResult
from backend.app.services.gemini import GeminiServiceError
from backend.app.services.reports import calculate_risk_score
from backend.app.services.retrieval import ClaimRetrieval, retrieve_claims
from backend.app.services.vector_store import VectorStore


class AnalysisState(TypedDict):
    """Small per-run state; passages contain excerpts, never whole documents."""

    analysis_id: str
    disclosure_text: str
    invention_summary: str
    analysis_settings: AnalysisSettings
    reviewed_claims: list[ReviewedClaim]
    current_claim_index: int
    retrieval_results: dict[str, ClaimRetrieval]
    findings: list[ClaimFinding]
    pending_finding: ClaimFinding | None
    pending_comparison: ClaimComparisonResult | None
    discarded_citation_counts: dict[str, int]
    risk_score: int | None
    risk_band: str | None
    score_components: ScoreComponents | None
    report: AnalysisReport | None
    durations_ms: dict[str, float]
    route_trace: list[str]
    status: Literal["running", "completed", "error"]
    error: str | None


def run_analysis(
    disclosure_text: str,
    reviewed_claims: Sequence[ReviewedClaim],
    *,
    top_k: int | None = None,
    prompt_version: str = "v2",
    invention_summary: str = "Summary not provided.",
    settings: Settings | None = None,
    vector_store: Any | None = None,
    gemini_client: Any | None = None,
    analysis_id: str | None = None,
) -> AnalysisState:
    """Execute the graph and return its final state, including safe errors."""
    active_settings = settings or get_settings()
    active_store = vector_store if vector_store is not None else VectorStore(active_settings)
    active_top_k = top_k if top_k is not None else active_settings.default_top_k
    analysis_settings = AnalysisSettings(
        comparison_prompt_version=prompt_version,
        gemini_model=active_settings.gemini_model,
        min_similarity=active_settings.min_similarity,
        top_k=active_top_k,
        corpus_passage_count=active_store.count(),
    )
    initial: AnalysisState = {
        "analysis_id": analysis_id or str(uuid4()),
        "disclosure_text": disclosure_text,
        "invention_summary": invention_summary,
        "analysis_settings": analysis_settings,
        "reviewed_claims": list(reviewed_claims),
        "current_claim_index": 0,
        "retrieval_results": {},
        "findings": [],
        "pending_finding": None,
        "pending_comparison": None,
        "discarded_citation_counts": {},
        "risk_score": None,
        "risk_band": None,
        "score_components": None,
        "report": None,
        "durations_ms": {},
        "route_trace": [],
        "status": "running",
        "error": None,
    }
    graph = _build_graph(
        settings=active_settings,
        vector_store=active_store,
        gemini_client=gemini_client,
        top_k=top_k,
        prompt_version=prompt_version,
    )
    return graph.invoke(initial)


def _build_graph(
    *,
    settings: Settings,
    vector_store: Any | None,
    gemini_client: Any | None,
    top_k: int | None,
    prompt_version: str,
):
    store = vector_store

    def timed(name: str, operation):
        def invoke(state: AnalysisState) -> dict[str, Any]:
            started = time.perf_counter()
            update = operation(state)
            elapsed_ms = (time.perf_counter() - started) * 1000
            durations = dict(state["durations_ms"])
            durations[name] = durations.get(name, 0.0) + elapsed_ms
            trace = [*state["route_trace"], name]
            result = {**update, "durations_ms": durations, "route_trace": trace}
            report = result.get("report")
            if report is not None:
                result["report"] = report.model_copy(update={"durations_ms": durations})
            return result

        return invoke

    def validate_input(state: AnalysisState) -> dict[str, Any]:
        count = len(state["reviewed_claims"])
        if count == 0:
            return {"status": "error", "error": "At least one reviewed claim is required."}
        if count > settings.max_claims:
            return {
                "status": "error",
                "error": f"At most {settings.max_claims} reviewed claims may be analyzed.",
            }
        if len({claim.claim_id for claim in state["reviewed_claims"]}) != count:
            return {"status": "error", "error": "Reviewed claim IDs must be unique."}
        return {}

    def route_after_validation(state: AnalysisState) -> str:
        return "stop" if state["status"] == "error" else "retrieve"

    def retrieve_current_claim(state: AnalysisState) -> dict[str, Any]:
        nonlocal store
        claim = state["reviewed_claims"][state["current_claim_index"]]
        if store is None:
            store = VectorStore(settings)
        result = retrieve_claims(
            [claim],
            top_k=top_k,
            vector_store=store,
            settings=settings,
        )[claim.claim_id]
        retrieval_results = dict(state["retrieval_results"])
        retrieval_results[claim.claim_id] = result
        return {"retrieval_results": retrieval_results}

    def route_after_retrieval(state: AnalysisState) -> str:
        claim = state["reviewed_claims"][state["current_claim_index"]]
        retrieval = state["retrieval_results"][claim.claim_id]
        useful_passage_count = len(retrieval.passages)
        return "compare" if useful_passage_count > 0 else "no_evidence"

    def compare_current_claim(state: AnalysisState) -> dict[str, Any]:
        claim = state["reviewed_claims"][state["current_claim_index"]]
        retrieval = state["retrieval_results"][claim.claim_id]
        try:
            comparison = compare_claim_result(
                claim,
                retrieval,
                prompt_version=prompt_version,
                settings=settings,
                client=gemini_client,
            )
        except GeminiServiceError as exc:
            return {
                "status": "error",
                "error": str(exc),
                "pending_finding": None,
                "pending_comparison": None,
            }
        except ValidationError:
            return {
                "status": "error",
                "error": "Gemini comparison did not produce a valid evidence finding.",
                "pending_finding": None,
                "pending_comparison": None,
            }
        return {"pending_comparison": comparison}

    def route_after_comparison(state: AnalysisState) -> str:
        return "stop" if state["status"] == "error" else "validate_citations"

    def no_evidence_finding(state: AnalysisState) -> dict[str, Any]:
        claim = state["reviewed_claims"][state["current_claim_index"]]
        finding = build_no_evidence_finding(claim)
        discarded_counts = dict(state["discarded_citation_counts"])
        discarded_counts[claim.claim_id] = 0
        return {
            "pending_finding": finding,
            "discarded_citation_counts": discarded_counts,
        }

    def validate_citations(state: AnalysisState) -> dict[str, Any]:
        claim = state["reviewed_claims"][state["current_claim_index"]]
        retrieval = state["retrieval_results"][claim.claim_id]
        comparison = state["pending_comparison"]
        if comparison is None:
            return {}

        passages_by_id = {passage.chunk_id: passage for passage in retrieval.passages}
        citations: list[EvidenceCitation] = []
        discarded_count = comparison.discarded_citation_count
        for chunk_id in comparison.cited_chunk_ids:
            passage = passages_by_id.get(chunk_id)
            if passage is None:
                discarded_count += 1
                continue
            citations.append(
                EvidenceCitation(
                    chunk_id=passage.chunk_id,
                    document_id=passage.document_id,
                    filename=passage.filename,
                    title=passage.title,
                    page=passage.page,
                    excerpt=passage.excerpt,
                    retrieval_similarity=passage.retrieval_similarity,
                )
            )

        discarded_counts = dict(state["discarded_citation_counts"])
        discarded_counts[claim.claim_id] = discarded_count
        best_retrieval_similarity = max(
            (passage.retrieval_similarity for passage in retrieval.passages),
            default=None,
        )
        retrieval_metadata = {
            "useful_passage_count": len(retrieval.passages),
            "best_retrieval_similarity": best_retrieval_similarity,
            "discarded_citation_count": discarded_count,
        }
        if citations:
            finding = ClaimFinding(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                evidence_status="evidence",
                coverage_estimate=comparison.coverage_estimate,
                shared_elements=comparison.shared_elements,
                missing_elements=comparison.missing_elements,
                assessment=comparison.assessment,
                uncertainty=comparison.uncertainty,
                citations=citations,
                **retrieval_metadata,
            )
        elif discarded_count:
            finding = ClaimFinding(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                evidence_status="unsupported",
                coverage_estimate=None,
                shared_elements=comparison.shared_elements,
                missing_elements=comparison.missing_elements,
                assessment="The model's comparison could not be linked to retrieved passages.",
                uncertainty=(
                    "The model returned citation labels that did not resolve to passages "
                    "retrieved for this claim."
                ),
                citations=[],
                **retrieval_metadata,
            )
        else:
            finding = ClaimFinding(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                evidence_status="no_supporting_passage",
                coverage_estimate=None,
                shared_elements=comparison.shared_elements,
                missing_elements=comparison.missing_elements,
                assessment=comparison.assessment,
                uncertainty=comparison.uncertainty,
                citations=[],
                **retrieval_metadata,
            )
        return {
            "pending_finding": finding,
            "pending_comparison": None,
            "discarded_citation_counts": discarded_counts,
        }

    def advance_claim(state: AnalysisState) -> dict[str, Any]:
        findings = list(state["findings"])
        if state["pending_finding"] is not None:
            findings.append(state["pending_finding"])
        return {
            "findings": findings,
            "pending_finding": None,
            "pending_comparison": None,
            "current_claim_index": state["current_claim_index"] + 1,
        }

    def route_after_advance(state: AnalysisState) -> str:
        return (
            "retrieve"
            if state["current_claim_index"] < len(state["reviewed_claims"])
            else "assemble"
        )

    def compute_score_and_assemble_report(state: AnalysisState) -> dict[str, Any]:
        risk_score, risk_band, components = calculate_risk_score(state["findings"])
        limitations = (
            "The score is an unvalidated triage heuristic over the uploaded corpus only, "
            "not a probability or a legal conclusion; coverage comes from model judgements "
            "that can vary between runs."
        )
        report = AnalysisReport(
            analysis_id=state["analysis_id"],
            invention_summary=state["invention_summary"],
            reviewed_claims=state["reviewed_claims"],
            risk_score=risk_score,
            risk_band=risk_band,
            score_components=components,
            analysis_settings=state["analysis_settings"],
            claims=state["findings"],
            durations_ms=state["durations_ms"],
            limitations=limitations,
        )
        return {
            "risk_score": risk_score,
            "risk_band": risk_band,
            "score_components": components,
            "report": report,
            "status": "completed",
        }

    builder = StateGraph(AnalysisState)
    builder.add_node("validate_input", timed("validate_input", validate_input))
    builder.add_node("retrieve_current_claim", timed("retrieve_current_claim", retrieve_current_claim))
    builder.add_node("compare_claim", timed("compare_claim", compare_current_claim))
    builder.add_node("no_evidence_finding", timed("no_evidence_finding", no_evidence_finding))
    builder.add_node("validate_citations", timed("validate_citations", validate_citations))
    builder.add_node("advance_claim", timed("advance_claim", advance_claim))
    builder.add_node(
        "compute_score_and_assemble_report",
        timed("compute_score_and_assemble_report", compute_score_and_assemble_report),
    )
    builder.add_edge(START, "validate_input")
    builder.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {"stop": END, "retrieve": "retrieve_current_claim"},
    )
    builder.add_conditional_edges(
        "retrieve_current_claim",
        route_after_retrieval,
        {"compare": "compare_claim", "no_evidence": "no_evidence_finding"},
    )
    builder.add_conditional_edges(
        "compare_claim",
        route_after_comparison,
        {"stop": END, "validate_citations": "validate_citations"},
    )
    builder.add_edge("validate_citations", "advance_claim")
    builder.add_edge("no_evidence_finding", "advance_claim")
    builder.add_conditional_edges(
        "advance_claim",
        route_after_advance,
        {"retrieve": "retrieve_current_claim", "assemble": "compute_score_and_assemble_report"},
    )
    builder.add_edge("compute_score_and_assemble_report", END)
    return builder.compile()
