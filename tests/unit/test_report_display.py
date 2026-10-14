from frontend.report_display import claim_status_display, display_citations


def test_status_messages_explain_no_evidence_and_no_supporting_passage():
    no_evidence = {
        "evidence_status": "no_evidence",
        "useful_passage_count": 0,
        "best_retrieval_similarity": None,
    }
    label, explanation = claim_status_display(no_evidence, 50)
    assert label == "No evidence"
    assert explanation == "No passage reached the similarity threshold (50)."

    no_support = {
        "evidence_status": "no_supporting_passage",
        "useful_passage_count": 4,
        "best_retrieval_similarity": 68,
    }
    label, explanation = claim_status_display(no_support, 50)
    assert label == "No supporting passage"
    assert explanation == (
        "4 related passages were retrieved (best similarity 68), "
        "but none supported this claim."
    )


def test_screen_citation_display_merges_only_overlapping_same_page_citations():
    overlap = "shared segment repeated for neighbouring passages " * 2
    citations = [
        {
            "document_id": "doc-a",
            "filename": "source.pdf",
            "page": 3,
            "retrieval_similarity": 70,
            "excerpt": f"first excerpt {overlap}",
        },
        {
            "document_id": "doc-a",
            "filename": "source.pdf",
            "page": 3,
            "retrieval_similarity": 75,
            "excerpt": f"{overlap}second excerpt",
        },
        {
            "document_id": "doc-a",
            "filename": "source.pdf",
            "page": 4,
            "retrieval_similarity": 60,
            "excerpt": f"{overlap}separate page",
        },
    ]

    shown = display_citations(citations)

    assert len(shown) == 2
    assert shown[0]["combines_adjacent_passages"] is True
    assert shown[0]["retrieval_similarity"] == 75
    assert "first excerpt" in shown[0]["excerpt"]
    assert "second excerpt" in shown[0]["excerpt"]
    assert shown[1]["combines_adjacent_passages"] is False
