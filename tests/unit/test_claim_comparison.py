from types import SimpleNamespace

from backend.app.schemas import ReviewedClaim
from backend.app.services.claim_comparison import (
    compare_claim_result,
    no_evidence_finding,
)
from backend.app.services.gemini import ClaimComparisonResult
from backend.app.services.retrieval import ClaimRetrieval, RetrievedPassage


class FakeClient:
    def __init__(self, text):
        self.models = SimpleNamespace(calls=[], text=text)
        self.models.generate_content = self.generate_content

    def generate_content(self, **kwargs):
        self.models.calls.append(kwargs)
        return SimpleNamespace(parsed=None, text=self.models.text)


def _passage():
    return RetrievedPassage(
        chunk_id="chunk-a",
        document_id="doc-a",
        filename="patent.txt",
        title="Patent",
        page=2,
        excerpt="A tractor includes a sensor.",
        retrieval_similarity=80,
        distance=0.2,
    )


def test_no_evidence_finding_skips_gemini() -> None:
    claim = ReviewedClaim(claim_id="c1", text="A tractor with a sensor.")
    client = FakeClient('{"unused": true}')

    finding = no_evidence_finding(claim)

    assert finding.claim_id == "c1"
    assert finding.evidence_status == "no_evidence"
    assert finding.coverage_estimate is None
    assert finding.citations == []
    assert "No useful passage was retrieved" in finding.assessment
    assert client.models.calls == []


def test_comparison_calls_gemini_and_returns_raw_result_for_validation() -> None:
    claim = ReviewedClaim(claim_id="c1", text="A tractor with a sensor.")
    retrieval = ClaimRetrieval(claim_id="c1", passages=[_passage()], dropped_count=0)
    client = FakeClient(
        '{"shared_elements":["tractor with sensor"],"missing_elements":[],'
        '"coverage_estimate":85,"assessment":"The passage states these elements.",'
        '"uncertainty":"Other details are unclear.","cited_passage_labels":["P1"]}'
    )

    result = compare_claim_result(claim, retrieval, client=client)

    assert isinstance(result, ClaimComparisonResult)
    assert result.cited_chunk_ids == ["chunk-a"]
    assert result.discarded_citation_count == 0
    assert len(client.models.calls) == 1


def test_invented_passage_label_is_discarded() -> None:
    claim = ReviewedClaim(claim_id="c1", text="A tractor with a sensor.")
    retrieval = ClaimRetrieval(claim_id="c1", passages=[_passage()], dropped_count=0)
    client = FakeClient(
        '{"shared_elements":["tractor with sensor"],"missing_elements":[],'
        '"coverage_estimate":85,"assessment":"The passage states these elements.",'
        '"uncertainty":"Other details are unclear.","cited_passage_labels":["P1","P99"]}'
    )

    result = compare_claim_result(claim, retrieval, client=client)

    assert result.cited_chunk_ids == ["chunk-a"]
    assert result.discarded_citation_count == 1


def test_v2_converts_independent_elements_calculates_coverage_and_excludes_claim_reference():
    claim = ReviewedClaim(
        claim_id="c1",
        text="The system of claim 1, wherein a tractor includes a sensor and a display.",
    )
    retrieval = ClaimRetrieval(claim_id="c1", passages=[_passage()], dropped_count=0)
    client = FakeClient(
        '{"elements":['
        '{"element_text":"The system of claim 1","status":"explicit",'
        '"explanation":"","supporting_passage_labels":["P99"]},'
        '{"element_text":"a tractor includes a sensor","status":"explicit",'
        '"explanation":"","supporting_passage_labels":["P1"]},'
        '{"element_text":"a display","status":"missing",'
        '"explanation":"No passage describes a display.","supporting_passage_labels":[]},'
        '{"element_text":"an equivalent controller","status":"inferred",'
        '"explanation":"The passage describes the same control function.",'
        '"supporting_passage_labels":["P1"]},'
        '{"element_text":"a configured threshold","status":"partial",'
        '"explanation":"The threshold value is not stated.","supporting_passage_labels":["P1"]}'
        '],"assessment":"Some elements are supported.","uncertainty":"Scope is unclear."}'
    )

    result = compare_claim_result(claim, retrieval, prompt_version="v2", client=client)

    assert result.coverage_estimate == 56  # (1 + 0 + .75 + .5) / 4 * 100
    assert result.shared_elements == [
        "a tractor includes a sensor",
        "an equivalent controller (inferred: The passage describes the same control function.)",
        "a configured threshold (partially covered: The threshold value is not stated.)",
    ]
    assert result.missing_elements == ["a display"]
    assert result.cited_chunk_ids == ["chunk-a"]
    assert result.discarded_citation_count == 0
    assert "The system of claim 1" not in result.shared_elements


def test_v2_coverage_weights_each_status():
    claim = ReviewedClaim(claim_id="c1", text="A device with four features.")
    retrieval = ClaimRetrieval(claim_id="c1", passages=[_passage()], dropped_count=0)
    client = FakeClient(
        '{"elements":['
        '{"element_text":"one","status":"explicit","explanation":"",' 
        '"supporting_passage_labels":["P1"]},'
        '{"element_text":"two","status":"inferred","explanation":"Equivalent operation.",'
        '"supporting_passage_labels":["P1"]},'
        '{"element_text":"three","status":"partial","explanation":"One part missing.",'
        '"supporting_passage_labels":["P1"]},'
        '{"element_text":"four","status":"missing","explanation":"",'
        '"supporting_passage_labels":[]}],"assessment":"Assessment.","uncertainty":"Uncertain."}'
    )

    result = compare_claim_result(claim, retrieval, prompt_version="v2", client=client)

    assert result.coverage_estimate == 56
