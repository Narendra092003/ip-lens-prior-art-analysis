from __future__ import annotations

import pytest

from backend.app.services.documents import (
    EmptyDocumentError,
    NoPagesInSelectedLanguagesError,
    ScannedPdfError,
    UnreadableDocumentError,
    UnsupportedDocumentError,
    detect_language,
    extract_document,
)


def _make_pdf(page_texts: list[str]) -> bytes:
    """Build a minimal text PDF without requiring a separate PDF-generation package."""
    page_ids = [4 + index * 2 for index in range(len(page_texts))]
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_texts)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for index, text in enumerate(page_texts):
        page_id = page_ids[index]
        stream_id = page_id + 1
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 10 Tf 40 750 Td ({escaped}) Tj ET".encode("latin-1")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>".encode()
        )
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_id} 0 obj\n".encode() + body + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(pdf)


def test_extracts_txt_with_source_title_page_and_normalized_text() -> None:
    extracted = extract_document(
        "patent_notes.txt",
        b"  A system   comprising a sensor.\r\n\r\n  The sensor measures pressure.  ",
        index_languages={"en"},
    )

    assert extracted.source_filename == "patent_notes.txt"
    assert extracted.display_title == "patent notes"
    assert len(extracted.pages) == 1
    assert extracted.pages[0].page_number == 1
    assert extracted.pages[0].text == "A system comprising a sensor.\n\nThe sensor measures pressure."
    assert extracted.pages[0].included_in_index is True


def test_txt_form_feed_separates_pages_with_one_based_numbers() -> None:
    extracted = extract_document(
        "two_pages.txt",
        b"The first page describes a sensor.\fThe second page describes a controller.",
        index_languages={"en"},
    )

    assert [page.page_number for page in extracted.pages] == [1, 2]
    assert [page.text for page in extracted.pages] == [
        "The first page describes a sensor.",
        "The second page describes a controller.",
    ]


def test_extracts_text_searchable_pdf_page_number() -> None:
    text = "A patent describes a pressure sensor connected to a controller and a valve."
    extracted = extract_document("sample.pdf", _make_pdf([text]), index_languages={"en"})

    assert extracted.pages[0].page_number == 1
    assert "pressure sensor" in extracted.pages[0].text
    assert extracted.pages[0].language == "en"


def test_empty_text_input_has_clear_error() -> None:
    with pytest.raises(EmptyDocumentError, match="empty"):
        extract_document("empty.md", b" \r\n\t")


def test_pdf_skips_near_empty_drawing_page_and_reports_count() -> None:
    useful = "A system comprising a controller configured to measure pressure and operate a valve."
    extracted = extract_document("drawings.pdf", _make_pdf(["Fig. 1", useful]), index_languages={"en"})

    assert extracted.skipped_page_count == 1
    assert [page.page_number for page in extracted.pages] == [2]


def test_pdf_skips_us_drawing_sheet_with_sheet_marker_and_reference_numbers() -> None:
    drawing_sheet = "Sheet 3 of 24 FIG. 3 " + " ".join(str(number) for number in range(100, 131))
    assert len("".join(drawing_sheet.split())) >= 50
    useful_text = "A system comprising a battery sensor and a controller configured to measure voltage."

    extracted = extract_document(
        "drawing_sheet.pdf",
        _make_pdf([drawing_sheet, useful_text]),
        index_languages={"en"},
    )

    assert [page.page_number for page in extracted.pages] == [2]
    assert extracted.skipped_page_count == 1


def test_pdf_keeps_normal_paragraph_that_mentions_figure_label() -> None:
    paragraph = (
        "The illustrated apparatus includes a battery housing and a controller connected to "
        "multiple sensors. In this embodiment, FIG. 3 shows the assembly positioned inside a "
        "protective enclosure, while a power converter regulates voltage and a communication "
        "module sends operating data to a remote monitoring device. The system also includes "
        "a thermal interface that transfers excess heat toward an external cooling surface "
        "during normal operation."
    )

    extracted = extract_document("description.pdf", _make_pdf([paragraph]), index_languages={"en"})

    assert extracted.skipped_page_count == 0
    assert len(extracted.pages) == 1
    assert "FIG. 3" in extracted.pages[0].text


def test_page_language_is_tagged_and_non_selected_language_excluded() -> None:
    french = "Le dispositif est dans une chambre avec les capteurs et un contrôleur."
    english = "The sensor is connected to a controller and the system operates with a valve."
    extracted = extract_document(
        "brevet.txt",
        f"{french}\f{english}".encode(),
        index_languages={"en"},
    )

    assert extracted.pages[0].language == "fr"
    assert extracted.pages[0].included_in_index is False
    assert extracted.pages[1].language == "en"
    assert extracted.pages[1].included_in_index is True
    assert extracted.excluded_language_page_count == 1


def test_raises_when_all_pages_are_excluded_by_language() -> None:
    french = "Le dispositif est dans une chambre avec les capteurs et un contrôleur."

    with pytest.raises(NoPagesInSelectedLanguagesError, match="No pages in the selected index languages"):
        extract_document("brevet.txt", french.encode(), index_languages={"en"})


def test_unknown_language_when_text_has_no_stopword_signal() -> None:
    assert detect_language("ZXQTR blorf mivvek") == "unknown"


def test_unsupported_and_unreadable_documents_have_clear_errors() -> None:
    with pytest.raises(UnsupportedDocumentError, match="PDF, TXT, or Markdown"):
        extract_document("patent.docx", b"content")
    with pytest.raises(UnreadableDocumentError, match="UTF-8"):
        extract_document("patent.txt", b"\xff\xfe")


def test_scanned_only_pdf_is_rejected_as_unsupported_ocr() -> None:
    with pytest.raises(ScannedPdfError, match="OCR is not supported") as exc_info:
        extract_document("scanned.pdf", _make_pdf([""]))

    assert exc_info.value.skipped_page_count == 1
