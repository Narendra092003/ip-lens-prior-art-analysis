from backend.app.config import Settings
from backend.app.services.chunking import ChunkedDocument, DocumentChunk
from backend.app.services.vector_store import VectorStore


def _store(path) -> VectorStore:
    return VectorStore(Settings(_env_file=None, chroma_path=path))


def _chunk(
    document_id: str,
    chunk_id: str,
    text: str,
    *,
    page_number: int = 1,
    chunk_index: int = 0,
) -> DocumentChunk:
    return DocumentChunk(
        document_id=document_id,
        chunk_id=chunk_id,
        original_filename=f"{document_id}.pdf",
        display_title=f"Patent {document_id}",
        page_number=page_number,
        chunk_index=chunk_index,
        language="en",
        text=text,
    )


def test_indexing_and_count(tmp_path) -> None:
    store = _store(tmp_path / "chroma")
    chunks = (
        _chunk("doc-one", "chunk-one-a", "A sensor measures pressure in a hydraulic system."),
        _chunk("doc-one", "chunk-one-b", "The controller adjusts the pump output.", chunk_index=1),
    )

    store.index_chunks(ChunkedDocument(document_id="doc-one", chunks=chunks))

    assert store.count() == 2


def test_reindex_replaces_existing_chunks_without_duplicates(tmp_path) -> None:
    store = _store(tmp_path / "chroma")
    store.index_chunks(
        ChunkedDocument(
            document_id="doc-one",
            chunks=(
                _chunk("doc-one", "old-a", "Old first chunk."),
                _chunk("doc-one", "old-b", "Old second chunk.", chunk_index=1),
            ),
        )
    )

    store.index_chunks(
        ChunkedDocument(
            document_id="doc-one",
            chunks=(_chunk("doc-one", "new-a", "Replacement content."),),
        )
    )

    assert store.count() == 1
    assert store.collection.get(include=["documents"])["ids"] == ["new-a"]


def test_data_persists_when_a_new_client_is_created(tmp_path) -> None:
    path = tmp_path / "persistent-chroma"
    first_client = _store(path)
    first_client.index_chunks(
        ChunkedDocument(
            document_id="doc-persist",
            chunks=(_chunk("doc-persist", "persisted-chunk", "A persisted patent passage."),),
        )
    )

    second_client = _store(path)

    assert second_client.count() == 1
    assert second_client.collection.get(include=["documents"])["ids"] == ["persisted-chunk"]


def test_search_returns_expected_chunk_first_with_metadata_and_raw_distance(tmp_path) -> None:
    store = _store(tmp_path / "chroma")
    store.index_chunks(
        ChunkedDocument(
            document_id="doc-search",
            chunks=(
                _chunk(
                    "doc-search",
                    "battery-chunk",
                    "A battery temperature sensor monitors lithium cell overheating and cooling.",
                ),
                _chunk(
                    "doc-search",
                    "pasta-chunk",
                    "Boil pasta in salted water and add tomato sauce before serving.",
                    page_number=2,
                    chunk_index=1,
                ),
            ),
        )
    )

    results = store.search("lithium battery temperature monitoring sensor", top_k=2)

    assert results[0].chunk_id == "battery-chunk"
    assert "battery temperature" in results[0].text
    assert results[0].metadata["document_id"] == "doc-search"
    assert results[0].metadata["page_number"] == 1
    assert isinstance(results[0].distance, float)
    assert results[0].distance >= 0
