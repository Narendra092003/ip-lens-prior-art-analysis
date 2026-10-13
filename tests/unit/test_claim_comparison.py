from types import SimpleNamespace

from backend.app.schemas import ReviewedClaim
from backend.app.services.gemini import ClaimComparisonResult
from backend.app.services.claim_comparison import compare_claim_finding
from backend.app.services.retrieval import ClaimRetrieval, RetrievedPassage


class FakeClient:
    def __init__(self):
        self.models = SimpleNamespace(calls=[])


def test_no_evidence_finding_skips_gemini() -> None:
    claim = ReviewedClaim(claim_id="c1", text="A tractor with a sensor.")
    retrieval = ClaimRetrieval(claim_id="c1", passages=[], dropped_count=2)
    client = FakeClient()

    finding = compare_claim_finding(claim, retrieval, client=client)

    assert finding.claim_id == "c1"
    assert finding.evidence_status == "no_evidence"
    assert finding.coverage_estimate is None
    assert finding.citations == []
    assert "No useful passage was retrieved" in finding.assessment
    assert client.models.calls == []


def test_useful_passage_comparison_builds_claim_finding_with_citation(monkeypatch) -> None:
    claim = ReviewedClaim(claim_id="c1", text="A tractor with a sensor.")
    passage = RetrievedPassage(
        chunk_id="chunk-a",
        document_id="doc-a",
        filename="patent.txt",
        title="Patent",
        page=2,
        excerpt="A tractor includes a sensor.",
        retrieval_similarity=80,
        distance=0.2,
    )
    retrieval = ClaimRetrieval(claim_id="c1", passages=[passage], dropped_count=0)
    client = FakeClient()
    from backend.app.services import claim_comparison

    def fake_compare(received_claim, passages, **kwargs):
        client.models.calls.append((received_claim, passages, kwargs))
        return ClaimComparisonResult(
            shared_elements=["tractor with sensor"],
            missing_elements=[],
            coverage_estimate=85,
            assessment="The passage explicitly describes the shared elements.",
            uncertainty="Other implementation details are unspecified.",
            cited_chunk_ids=["chunk-a"],
        )

    monkeypatch.setattr(claim_comparison, "compare_claim", fake_compare)
    finding = compare_claim_finding(claim, retrieval, client=client)

    assert finding.evidence_status == "evidence"
    assert finding.coverage_estimate == 85
    assert [citation.chunk_id for citation in finding.citations] == ["chunk-a"]
    assert finding.citations[0].page == 2
    assert len(client.models.calls) == 1
