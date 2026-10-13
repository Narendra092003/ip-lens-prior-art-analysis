from pathlib import Path
import hashlib
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import get_settings
from backend.app.schemas import ReviewedClaim
from backend.app.services.retrieval import ClaimRetrieval, RetrievedPassage, retrieve_claims
from backend.app.services.vector_store import VectorStore

LABELS_PATH = PROJECT_ROOT / "examples" / "eval" / "retrieval_labels.json"
TOP_K = 10
NO_ANSWER_IDS = {"q14", "q15"}


def _is_relevant(passage: RetrievedPassage, relevant_labels: list[dict[str, str]]) -> bool:
    filename = Path(passage.filename).name.casefold()
    excerpt = passage.excerpt.casefold()
    return any(
        filename == Path(label["filename"]).name.casefold()
        and label["phrase"].casefold() in excerpt
        for label in relevant_labels
    )


def _passage_rows(
    retrieval: ClaimRetrieval,
    relevant_labels: list[dict[str, str]],
) -> list[tuple[int, RetrievedPassage, bool]]:
    return [
        (rank, passage, _is_relevant(passage, relevant_labels))
        for rank, passage in enumerate(retrieval.passages, start=1)
    ]


def _best_relevant(rows: list[tuple[int, RetrievedPassage, bool]]) -> tuple[int, int] | None:
    for rank, passage, relevant in rows:
        if relevant:
            return rank, passage.retrieval_similarity
    return None


def _highest_non_relevant(
    rows: list[tuple[int, RetrievedPassage, bool]],
) -> tuple[int, RetrievedPassage] | None:
    candidates = [(rank, passage) for rank, passage, relevant in rows if not relevant]
    return max(candidates, key=lambda item: item[1].retrieval_similarity, default=None)


def _source_category(
    passage: RetrievedPassage,
    labelled_filenames: set[str],
    real_patent_filenames: set[str],
) -> str:
    filename = Path(passage.filename).name.casefold()
    if filename in labelled_filenames:
        return "same labelled file"
    if filename in real_patent_filenames:
        return "real patent"
    return "another synthetic file"


def main() -> int:
    label_bytes = LABELS_PATH.read_bytes()
    labels = json.loads(label_bytes)
    settings = get_settings()
    # Use a settings copy so this evaluation retrieves top_k=10 without filtering.
    unthresholded_settings = settings.model_copy(
        update={"default_top_k": TOP_K, "min_similarity": 0}
    )
    store = VectorStore(unthresholded_settings)
    claims = [
        ReviewedClaim(claim_id=item["query_id"], text=item["claim"])
        for item in labels
    ]
    retrieved = retrieve_claims(
        claims,
        top_k=TOP_K,
        vector_store=store,
        settings=unthresholded_settings,
    )
    labels_by_id = {item["query_id"]: item for item in labels}
    real_patent_filenames = {
        path.name.casefold()
        for path in (PROJECT_ROOT / "examples" / "real").glob("*")
        if path.is_file()
    }
    rows_by_id = {
        query_id: _passage_rows(retrieved[query_id], labels_by_id[query_id]["relevant"])
        for query_id in labels_by_id
    }

    print("Retrieval evaluation")
    print(
        "Dataset version: retrieval_labels.json SHA-256 "
        f"{hashlib.sha256(label_bytes).hexdigest()}"
    )
    print(f"Current corpus passages: {store.count()}")
    print(
        f"Chunk size: {settings.chunk_size}; overlap: {settings.chunk_overlap}; "
        f"top_k: {TOP_K}; retrieval threshold: none"
    )
    print()

    print("Per-claim results (ranks and similarities are within the top 10)")
    print(
        f"{'Claim ID':<10} {'Best relevant chunk rank / sim':<34} "
        "Highest non-relevant chunk (sim / source)"
    )
    print("-" * 100)
    for item in labels:
        query_id = item["query_id"]
        rows = rows_by_id[query_id]
        best = _best_relevant(rows)
        best_display = f"rank {best[0]} / {best[1]}" if best else "not found"
        highest = _highest_non_relevant(rows)
        labelled_filenames = {
            Path(label["filename"]).name.casefold()
            for label in item["relevant"]
        }
        if highest is None:
            highest_non_relevant = "—"
        else:
            _, passage = highest
            category = _source_category(
                passage,
                labelled_filenames,
                real_patent_filenames,
            )
            highest_non_relevant = f"{passage.retrieval_similarity} / {category}"
        print(f"{query_id:<10} {best_display:<34} {highest_non_relevant}")

    answerable = [item for item in labels if item["relevant"]]
    answerable_count = len(answerable)
    same_labelled_file_count = sum(
        1
        for item in answerable
        if (highest := _highest_non_relevant(rows_by_id[item["query_id"]])) is not None
        and Path(highest[1].filename).name.casefold()
        in {
            Path(label["filename"]).name.casefold()
            for label in item["relevant"]
        }
    )
    print(
        "Highest non-relevant chunk from the same labelled file: "
        f"{same_labelled_file_count}/{answerable_count}"
    )
    for cutoff in (1, 4):
        chunk_hits = sum(
            1
            for item in answerable
            if (best := _best_relevant(rows_by_id[item["query_id"]])) is not None
            and best[0] <= cutoff
        )
        document_hits = sum(
            any(
                rank <= cutoff
                and Path(passage.filename).name.casefold()
                in {
                    Path(label["filename"]).name.casefold()
                    for label in item["relevant"]
                }
                for rank, passage, _ in rows_by_id[item["query_id"]]
            )
            for item in answerable
        )
        chunk_recall = chunk_hits / answerable_count if answerable_count else 0.0
        document_recall = document_hits / answerable_count if answerable_count else 0.0
        print(
            f"Recall@{cutoff} chunk-level: {chunk_hits}/{answerable_count} "
            f"({chunk_recall:.1%})"
        )
        print(
            f"Recall@{cutoff} document-level: {document_hits}/{answerable_count} "
            f"({document_recall:.1%})"
        )

    print()
    print(
        "Threshold sweep (relevant top-10 chunks; non-relevant top-4 chunks; "
        "no-answer claims with any kept top-4 passage)"
    )
    print(
        f"{'Threshold':<12} {'Relevant kept (top 10)':<25} "
        f"{'Non-relevant kept (top 4)':<28} {'No-answer claims kept':<22}"
    )
    print("-" * 91)
    for threshold in range(30, 71, 5):
        relevant_kept = sum(
            1
            for query_id, rows in rows_by_id.items()
            for _, passage, relevant in rows
            if relevant and passage.retrieval_similarity >= threshold
        )
        non_relevant_top4_kept = sum(
            1
            for rows in rows_by_id.values()
            for rank, passage, relevant in rows
            if rank <= 4 and not relevant and passage.retrieval_similarity >= threshold
        )
        no_answer_with_any = sum(
            any(
                rank <= 4 and passage.retrieval_similarity >= threshold
                for rank, passage, _ in rows_by_id[query_id]
            )
            for query_id in NO_ANSWER_IDS
            if query_id in rows_by_id
        )
        print(
            f"{threshold:<12} {relevant_kept:<25} {non_relevant_top4_kept:<28} "
            f"{no_answer_with_any}/2"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
