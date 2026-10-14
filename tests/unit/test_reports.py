from backend.app.schemas import (
    AnalysisReport,
    ClaimFinding,
    EvidenceCitation,
    ReviewedClaim,
)
from backend.app.services.reports import calculate_risk_score


def _finding(
    claim_id: str,
    status: str,
    *,
    coverage: int | None = None,
    similarity: int | None = None,
    discarded: int = 0,
) -> ClaimFinding:
    citations = []
    if status == "evidence":
        citations = [
            EvidenceCitation(
                chunk_id=f"chunk-{claim_id}",
                document_id="doc-1",
                title="Example source",
                filename="example.txt",
                page=1,
                excerpt="Example retrieved passage.",
                retrieval_similarity=similarity or 0,
            )
        ]
    useful_count = 1 if status in {"evidence", "no_supporting_passage", "unsupported"} else 0
    return ClaimFinding(
        claim_id=claim_id,
        claim_text="A test claim.",
        evidence_status=status,
        coverage_estimate=coverage,
        useful_passage_count=useful_count,
        best_retrieval_similarity=similarity if useful_count else None,
        discarded_citation_count=discarded,
        shared_elements=[],
        missing_elements=[],
        assessment="Test assessment.",
        uncertainty="Test uncertainty.",
        citations=citations,
    )


def test_score_uses_documented_formula_and_populates_components():
    finding = _finding("c1", "evidence", coverage=80, similarity=60)

    score, band, components = calculate_risk_score([finding])

    assert score == round(0.65 * 80 + 0.35 * 60) == 73
    assert band == "High"
    assert components.max_claim_coverage == 80
    assert components.best_cited_retrieval_similarity == 60
    assert components.formula == (
        "round(0.65 * max_claim_coverage + 0.35 * best_cited_retrieval_similarity)"
    )


def test_score_band_boundaries_34_35_and_69_70():
    cases = [
        (0, 97, 34, "Low"),
        (0, 100, 35, "Moderate"),
        (100, 11, 69, "Moderate"),
        (100, 15, 70, "High"),
    ]
    for index, (coverage, similarity, expected_score, expected_band) in enumerate(cases):
        score, band, _ = calculate_risk_score(
            [_finding(f"c{index}", "evidence", coverage=coverage, similarity=similarity)]
        )
        assert (score, band) == (expected_score, expected_band)


def test_all_non_evidence_findings_return_not_scored():
    findings = [
        _finding("none", "no_evidence"),
        _finding("no-support", "no_supporting_passage", similarity=100),
        _finding("unsupported", "unsupported", similarity=100, discarded=1),
    ]

    score, band, components = calculate_risk_score(findings)

    assert score is None
    assert band == "Not scored"
    assert components.max_claim_coverage is None
    assert components.best_cited_retrieval_similarity is None


def test_non_evidence_findings_do_not_contribute_even_with_higher_retrieval_similarity():
    evidence = _finding("evidence", "evidence", coverage=20, similarity=60)
    no_support = _finding("no-support", "no_supporting_passage", similarity=100)
    unsupported = _finding("unsupported", "unsupported", similarity=100, discarded=1)

    score, band, components = calculate_risk_score([evidence, no_support, unsupported])

    assert score == 34
    assert band == "Low"
    assert components.max_claim_coverage == 20
    assert components.best_cited_retrieval_similarity == 60


def test_analysis_report_accepts_calculated_score_and_components():
    finding = _finding("c1", "evidence", coverage=80, similarity=60)
    score, band, components = calculate_risk_score([finding])
    reviewed_claim = ReviewedClaim(claim_id="c1", text="A test claim.")

    report = AnalysisReport.model_validate(
        {
            "analysis_id": "analysis-1",
            "invention_summary": "Test invention summary.",
            "reviewed_claims": [reviewed_claim.model_dump()],
            "risk_score": score,
            "risk_band": band,
            "score_components": components.model_dump(),
            "claims": [finding.model_dump()],
            "limitations": (
                "The score is an unvalidated triage heuristic over the uploaded corpus only, "
                "not a probability or a legal conclusion; coverage comes from model judgements "
                "that can vary between runs."
            ),
        }
    )

    assert report.risk_score == 73
    assert report.score_components == components
