import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.schemas import ClaimFinding, EvidenceCitation, ReviewedClaim
from backend.app.services.chunking import ChunkedDocument, DocumentChunk
from backend.app.services.gemini import GeminiRateLimitedError
from backend.app.services.vector_store import VectorStore
from backend.app import workflow
from backend.app.workflow import run_analysis


def _finding_data(**updates):
    data = {
        "claim_id": "claim-1",
        "claim_text": "A tractor controller.",
        "evidence_status": "no_evidence",
        "coverage_estimate": None,
        "shared_elements": [],
        "missing_elements": [],
        "assessment": "No useful passage was retrieved.",
        "uncertainty": "The corpus may not include related material.",
        "citations": [],
    }
    data.update(updates)
    return data


def test_claim_finding_rejects_impossible_evidence_status_combinations():
    with pytest.raises(ValidationError, match="no_evidence findings must not have a coverage"):
        ClaimFinding.model_validate(_finding_data(coverage_estimate=0))

    with pytest.raises(ValidationError, match="evidence findings must have at least one citation"):
        ClaimFinding.model_validate(
        _finding_data(evidence_status="evidence", coverage_estimate=0)
        )

    unsupported = ClaimFinding.model_validate(
        _finding_data(
            evidence_status="unsupported",
            coverage_estimate=None,
            useful_passage_count=1,
            best_retrieval_similarity=90,
            discarded_citation_count=1,
        )
    )
    assert unsupported.citations == []


class FakeModels:
    def __init__(self, outcome):
        self.outcomes = outcome if isinstance(outcome, list) else [outcome]
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcome):
        self.models = FakeModels(outcome)


def _settings(path, *, max_claims=10):
    return Settings(
        _env_file=None,
        gemini_api_key="fake-key",
        gemini_model="test-model",
        chroma_path=path,
        max_claims=max_claims,
        min_similarity=85,
    )


def _store_with_useful_passage(settings, *, include_rover=False):
    store = VectorStore(settings)
    chunk = DocumentChunk(
        document_id="doc-tractor",
        chunk_id="chunk-tractor",
        original_filename="fictional-tractor.txt",
        display_title="Fictional tractor passage",
        page_number=1,
        chunk_index=0,
        language="en",
        text="A tractor controller receives an engine load estimate and adjusts the transmission ratio.",
    )
    store.index_chunks(ChunkedDocument(document_id=chunk.document_id, chunks=(chunk,)))
    if include_rover:
        rover_chunk = DocumentChunk(
            document_id="doc-rover",
            chunk_id="chunk-rover",
            original_filename="fictional-rover.txt",
            display_title="Fictional rover passage",
            page_number=1,
            chunk_index=0,
            language="en",
            text="A polar rover calibrates a planetary dust spectrometer by measuring ultraviolet reflectance.",
        )
        store.index_chunks(
            ChunkedDocument(document_id=rover_chunk.document_id, chunks=(rover_chunk,))
        )
    return store


def _claims():
    return [
        ReviewedClaim(
            claim_id="claim-1",
            text="A tractor controller receives an engine load estimate and adjusts the transmission ratio.",
        ),
        ReviewedClaim(
            claim_id="claim-2",
            text="A polar rover calibrates a planetary dust spectrometer by measuring ultraviolet reflectance.",
        ),
    ]


def _comparison_response(*, labels=None, missing=None, assessment=None, uncertainty=None):
    return SimpleNamespace(
        parsed=None,
        text=json.dumps(
            {
                "shared_elements": ["engine load estimate", "transmission ratio adjustment"],
                "missing_elements": missing if missing is not None else ["other claim details"],
                "coverage_estimate": 75,
                "assessment": assessment or "The passage explicitly states these operations.",
                "uncertainty": uncertainty or "The control criteria beyond these operations are unspecified.",
                "cited_passage_labels": labels if labels is not None else ["P1"],
            }
        ),
    )


def test_workflow_routes_claims_records_durations_and_calls_gemini_once(tmp_path):
    settings = _settings(tmp_path / "chroma")
    store = _store_with_useful_passage(settings)
    client = FakeClient(_comparison_response())

    result = run_analysis(
        "Fictional disclosure text.",
        _claims(),
        settings=settings,
        vector_store=store,
        gemini_client=client,
        analysis_id="analysis-test",
    )

    assert result["status"] == "completed"
    assert result["error"] is None
    assert [finding.evidence_status for finding in result["findings"]] == [
        "evidence",
        "no_evidence",
    ]
    assert result["analysis_id"] == "analysis-test"
    assert result["report"] is not None
    assert result["report"].risk_score == result["risk_score"]
    assert result["report"].score_components == result["score_components"]
    assert "unvalidated triage heuristic" in result["report"].limitations
    assert result["report"].durations_ms == result["durations_ms"]
    assert len(client.models.calls) == 1
    below_threshold = result["retrieval_results"]["claim-2"]
    assert below_threshold.passages == []
    assert below_threshold.dropped_count > 0
    assert result["route_trace"] == [
        "validate_input",
        "retrieve_current_claim",
        "compare_claim",
        "validate_citations",
        "advance_claim",
        "retrieve_current_claim",
        "no_evidence_finding",
        "advance_claim",
        "compute_score_and_assemble_report",
    ]
    assert set(result["durations_ms"]) == {
        "validate_input",
        "retrieve_current_claim",
        "compare_claim",
        "validate_citations",
        "advance_claim",
        "no_evidence_finding",
        "compute_score_and_assemble_report",
    }
    assert all(duration >= 0 for duration in result["durations_ms"].values())


def test_too_many_claims_stop_before_retrieval_or_model_call(tmp_path):
    settings = _settings(tmp_path / "chroma", max_claims=1)
    store = VectorStore(settings)
    client = FakeClient(_comparison_response())

    result = run_analysis(
        "Fictional disclosure text.",
        _claims(),
        settings=settings,
        vector_store=store,
        gemini_client=client,
    )

    assert result["status"] == "error"
    assert result["error"] == "At most 1 reviewed claims may be analyzed."
    assert result["route_trace"] == ["validate_input"]
    assert client.models.calls == []


def test_gemini_error_stops_without_appending_a_fabricated_finding(tmp_path, monkeypatch):
    settings = _settings(tmp_path / "chroma")
    store = _store_with_useful_passage(settings)
    client = FakeClient(GeminiRateLimitedError("Gemini rate limit persisted after retries."))

    def fail_comparison(*args, **kwargs):
        raise GeminiRateLimitedError("Gemini rate limit persisted after retries.")

    monkeypatch.setattr(workflow, "compare_claim_result", fail_comparison)

    result = run_analysis(
        "Fictional disclosure text.",
        _claims()[:1],
        settings=settings,
        vector_store=store,
        gemini_client=client,
    )

    assert result["status"] == "error"
    assert result["error"] == "Gemini rate limit persisted after retries."
    assert result["findings"] == []
    assert result["route_trace"] == [
        "validate_input",
        "retrieve_current_claim",
        "compare_claim",
    ]


def test_invalid_citations_create_unsupported_and_continue_to_next_claim(tmp_path):
    settings = _settings(tmp_path / "chroma")
    store = _store_with_useful_passage(settings, include_rover=True)
    valid_response = json.loads(_comparison_response().text)
    valid_response["coverage_estimate"] = 25
    invalid_response = json.loads(_comparison_response().text)
    invalid_response["coverage_estimate"] = 99
    invalid_response["cited_passage_labels"] = ["P99"]
    client = FakeClient(
        [
            SimpleNamespace(parsed=None, text=json.dumps(valid_response)),
            SimpleNamespace(parsed=None, text=json.dumps(invalid_response)),
        ]
    )
    third_claim = ReviewedClaim(
        claim_id="claim-3",
        text="A system applies ultraviolet calibration to a deep ocean sonar buoy.",
    )

    result = run_analysis(
        "Fictional disclosure text.",
        [*_claims(), third_claim],
        settings=settings,
        vector_store=store,
        gemini_client=client,
    )

    findings = {finding.claim_id: finding for finding in result["findings"]}
    unsupported = findings["claim-2"]
    assert result["status"] == "completed"
    assert [findings[claim_id].evidence_status for claim_id in ("claim-1", "claim-2", "claim-3")] == [
        "evidence",
        "unsupported",
        "no_evidence",
    ]
    assert unsupported.coverage_estimate is None
    assert unsupported.citations == []
    assert unsupported.discarded_citation_count == 1
    assert "could not be linked to retrieved passages" in unsupported.assessment
    assert result["discarded_citation_counts"] == {
        "claim-1": 0,
        "claim-2": 1,
        "claim-3": 0,
    }
    assert len(client.models.calls) == 2
    assert result["current_claim_index"] == 3
    assert result["score_components"].max_claim_coverage == 25
    assert result["risk_score"] == round(0.65 * 25 + 0.35 * 100)
    assert "no_evidence_finding" in result["durations_ms"]


def test_zero_citations_preserve_comparison_and_record_retrieval_stats(tmp_path):
    settings = _settings(tmp_path / "chroma")
    store = _store_with_useful_passage(settings)
    response = _comparison_response(
        labels=[],
        missing=["an optical row-end sensor"],
        assessment="The passage does not describe optical row termination.",
        uncertainty="The sensor arrangement remains unclear.",
    )
    client = FakeClient(response)

    result = run_analysis(
        "Fictional disclosure text.",
        _claims()[:1],
        settings=settings,
        vector_store=store,
        gemini_client=client,
    )

    finding = result["findings"][0]
    retrieval = result["retrieval_results"]["claim-1"]
    assert finding.evidence_status == "no_supporting_passage"
    assert finding.coverage_estimate is None
    assert finding.citations == []
    assert finding.missing_elements == ["an optical row-end sensor"]
    assert finding.assessment == "The passage does not describe optical row termination."
    assert finding.uncertainty == "The sensor arrangement remains unclear."
    assert finding.useful_passage_count == len(retrieval.passages) > 0
    assert finding.best_retrieval_similarity == max(
        passage.retrieval_similarity for passage in retrieval.passages
    )
    assert result["risk_score"] is None
