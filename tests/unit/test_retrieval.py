from backend.app.config import Settings
from backend.app.schemas import ReviewedClaim
from backend.app.services.retrieval import (
    cosine_distance_to_similarity,
    retrieve_claims,
)
from backend.app.services.vector_store import SearchResult


class FakeVectorStore:
    def __init__(self, results_by_query):
        self.results_by_query = results_by_query
        self.calls = []

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        self.calls.append((query, top_k))
        return self.results_by_query.get(query, [])[:top_k]


def _settings(*, default_top_k: int = 4, min_similarity: int = 50) -> Settings:
    return Settings(
        _env_file=None,
        default_top_k=default_top_k,
        min_similarity=min_similarity,
    )


def _result(chunk_id: str, distance: float, *, query: str = "") -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        text=f"Passage for {query or chunk_id}.",
        metadata={
            "document_id": f"doc-{chunk_id}",
            "original_filename": f"{chunk_id}.pdf",
            "display_title": f"Patent {chunk_id}",
            "page_number": 2,
            "chunk_index": 0,
            "language": "en",
        },
        distance=distance,
    )


def test_cosine_distance_conversion_and_clamping() -> None:
    assert cosine_distance_to_similarity(0.42) == 58
    assert cosine_distance_to_similarity(-0.2) == 100
    assert cosine_distance_to_similarity(1.5) == 0


def test_threshold_drops_just_below_and_keeps_exact_threshold() -> None:
    store = FakeVectorStore(
        {
            "pressure sensor claim": [
                _result("below", 0.51),  # similarity 49
                _result("at-threshold", 0.50),  # similarity 50
            ]
        }
    )
    claim = ReviewedClaim(claim_id="claim-1", text="pressure sensor claim")

    results = retrieve_claims([claim], vector_store=store, settings=_settings())

    assert [item.chunk_id for item in results["claim-1"].passages] == ["at-threshold"]
    assert results["claim-1"].passages[0].retrieval_similarity == 50
    assert results["claim-1"].passages[0].distance == 0.50
    assert results["claim-1"].dropped_count == 1


def test_each_claim_gets_a_separate_search_and_result_list() -> None:
    claims = [
        ReviewedClaim(claim_id="claim-a", text="battery sensor"),
        ReviewedClaim(claim_id="claim-b", text="optical row detector"),
    ]
    store = FakeVectorStore(
        {
            "battery sensor": [_result("battery-chunk", 0.2)],
            "optical row detector": [_result("optical-chunk", 0.3)],
        }
    )

    results = retrieve_claims(
        claims,
        vector_store=store,
        settings=_settings(default_top_k=6),
    )

    assert store.calls == [("battery sensor", 6), ("optical row detector", 6)]
    assert [item.chunk_id for item in results["claim-a"].passages] == ["battery-chunk"]
    assert [item.chunk_id for item in results["claim-b"].passages] == ["optical-chunk"]
    assert results["claim-a"].passages is not results["claim-b"].passages


def test_empty_corpus_returns_empty_passages_for_each_claim() -> None:
    claims = [
        ReviewedClaim(claim_id="claim-a", text="first claim"),
        ReviewedClaim(claim_id="claim-b", text="second claim"),
    ]
    store = FakeVectorStore({})

    results = retrieve_claims(claims, vector_store=store, settings=_settings())

    assert store.calls == [("first claim", 4), ("second claim", 4)]
    assert set(results) == {"claim-a", "claim-b"}
    assert all(result.passages == [] and result.dropped_count == 0 for result in results.values())
