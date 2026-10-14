from backend.app.schemas import (
    AnalysisSettings,
    AnalysisReport,
    ClaimFinding,
    EvidenceCitation,
    ReviewedClaim,
)
from backend.app.services.reports import (
    calculate_risk_score,
    export_report_json,
    export_report_markdown,
)


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
            "analysis_settings": AnalysisSettings(
                comparison_prompt_version="v1",
                gemini_model="test-model",
                min_similarity=50,
                top_k=4,
                corpus_passage_count=1,
            ).model_dump(),
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


def _report_with_findings(findings, *, durations=None):
    return AnalysisReport(
        analysis_id="analysis-md",
        invention_summary="A fictional system.",
        reviewed_claims=[ReviewedClaim(claim_id=item.claim_id, text=item.claim_text) for item in findings],
        risk_score=None,
        risk_band="Not scored",
        score_components=calculate_risk_score(findings)[2],
        analysis_settings=AnalysisSettings(
            comparison_prompt_version="v2",
            gemini_model="test-model",
            min_similarity=50,
            top_k=4,
            corpus_passage_count=27,
        ),
        claims=findings,
        durations_ms=durations or {},
        limitations="Unvalidated triage heuristic over the uploaded corpus only.",
    )


def test_markdown_exports_settings_human_status_and_status_explanations():
    no_evidence = _finding("c1", "no_evidence")
    no_support = _finding("c2", "no_supporting_passage", similarity=68)
    no_support = no_support.model_copy(update={"useful_passage_count": 4})
    report = _report_with_findings([no_evidence, no_support])

    markdown = export_report_markdown(report)

    assert "## Settings" in markdown
    assert "Comparison prompt version: `v2`" in markdown
    assert "Gemini model: `test-model`" in markdown
    assert "MIN_SIMILARITY: 50" in markdown
    assert "top_k: 4" in markdown
    assert "Corpus passages at analysis time: 27" in markdown
    assert "**Status:** No evidence" in markdown
    assert "No passage reached the similarity threshold (50)." in markdown
    assert "**Status:** No supporting passage" in markdown
    assert "4 related passages were retrieved (best similarity 68), but none supported this claim." in markdown
    assert "**Coverage:** Not assessed" in markdown


def test_markdown_truncates_excerpts_and_reports_duration_while_json_keeps_full_text():
    excerpt = "word " * 120
    citation_finding = ClaimFinding(
        claim_id="c1",
        claim_text="A test claim.",
        evidence_status="evidence",
        coverage_estimate=80,
        useful_passage_count=1,
        best_retrieval_similarity=80,
        shared_elements=["a feature"],
        missing_elements=[],
        assessment="Supported.",
        uncertainty="Limited corpus.",
        citations=[
            EvidenceCitation(
                chunk_id="chunk-c1",
                document_id="doc-c1",
                title="Source",
                filename="source.txt",
                page=2,
                excerpt=excerpt,
                retrieval_similarity=80,
            )
        ],
    )
    report = _report_with_findings([citation_finding], durations={"retrieve": 1500, "compare": 875})

    markdown = export_report_markdown(report)
    json_export = export_report_json(report)
    excerpt_line = next(line for line in markdown.splitlines() if line.startswith("  > "))

    assert len(excerpt_line.removeprefix("  > ")) <= 400
    assert excerpt_line.endswith("…")
    assert "Total analysis duration: 2.4 seconds" in markdown
    assert excerpt.rstrip() in json_export


def test_overlapping_citations_are_combined_in_markdown_but_retained_in_json():
    overlap = "shared passage segment " * 3
    citations = [
        EvidenceCitation(
            chunk_id="chunk-a",
            document_id="doc-a",
            title="Source",
            filename="source.txt",
            page=1,
            excerpt=f"Opening text. {overlap}",
            retrieval_similarity=70,
        ),
        EvidenceCitation(
            chunk_id="chunk-b",
            document_id="doc-a",
            title="Source",
            filename="source.txt",
            page=1,
            excerpt=f"{overlap}Closing text.",
            retrieval_similarity=75,
        ),
    ]
    finding = _finding("c1", "evidence", coverage=80, similarity=70).model_copy(
        update={"citations": citations}
    )
    report = _report_with_findings([finding])

    markdown = export_report_markdown(report)
    json_export = export_report_json(report)

    assert markdown.count("Combines adjacent passages") == 1
    assert markdown.count("**source.txt**") == 1
    assert len(__import__("json").loads(json_export)["claims"][0]["citations"]) == 2
