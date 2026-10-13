from backend.app.config import Settings
from backend.app.services.chunking import chunk_document
from backend.app.services.documents import ExtractedDocument, ExtractedPage


def _settings(*, chunk_size: int = 100, chunk_overlap: int = 20) -> Settings:
    return Settings(_env_file=None, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def _document(*pages: ExtractedPage) -> ExtractedDocument:
    return ExtractedDocument(
        source_filename="sample_patent.txt",
        display_title="sample patent",
        pages=pages,
        skipped_page_count=0,
        excluded_language_page_count=0,
    )


def _page(number: int, text: str, *, included: bool = True) -> ExtractedPage:
    return ExtractedPage(
        page_number=number,
        text=text,
        language="en",
        included_in_index=included,
    )


def test_short_page_produces_one_chunk_with_source_metadata() -> None:
    document = _document(_page(1, "The sensor measures pressure."))

    result = chunk_document(document, b"original bytes", settings=_settings())

    assert len(result.chunks) == 1
    chunk = result.chunks[0]
    assert chunk.text == "The sensor measures pressure."
    assert chunk.original_filename == "sample_patent.txt"
    assert chunk.display_title == "sample patent"
    assert chunk.page_number == 1
    assert chunk.chunk_index == 0
    assert chunk.language == "en"
    assert chunk.document_id == result.document_id


def test_long_page_produces_overlapping_chunks() -> None:
    text = " ".join(f"word{index}" for index in range(80))
    result = chunk_document(_document(_page(1, text)), b"long page", settings=_settings())

    assert len(result.chunks) > 1
    assert all(len(chunk.text) <= 100 for chunk in result.chunks)
    assert set(result.chunks[0].text.split()) & set(result.chunks[1].text.split())


def test_chunks_never_cross_page_boundaries() -> None:
    first_page = "FIRSTPAGE " * 35
    second_page = "SECONDPAGE " * 35
    result = chunk_document(
        _document(_page(1, first_page), _page(2, second_page)),
        b"two pages",
        settings=_settings(),
    )

    assert {chunk.page_number for chunk in result.chunks} == {1, 2}
    assert all("SECONDPAGE" not in chunk.text for chunk in result.chunks if chunk.page_number == 1)
    assert all("FIRSTPAGE" not in chunk.text for chunk in result.chunks if chunk.page_number == 2)


def test_identical_input_produces_identical_document_and_chunk_ids() -> None:
    document = _document(_page(1, "A stable page with a sensor and controller."))

    first = chunk_document(document, b"same original content", settings=_settings())
    second = chunk_document(document, b"same original content", settings=_settings())

    assert first.document_id == second.document_id
    assert [chunk.chunk_id for chunk in first.chunks] == [chunk.chunk_id for chunk in second.chunks]


def test_excluded_pages_produce_no_chunks() -> None:
    document = _document(
        _page(1, "French page outside the selected language set.", included=False),
        _page(2, "Included English page."),
    )

    result = chunk_document(document, b"mixed language file", settings=_settings())

    assert result.chunks
    assert all(chunk.page_number == 2 for chunk in result.chunks)

