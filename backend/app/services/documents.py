"""Extract normalized, page-aware text from supported patent document formats."""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Collection, Literal

from pypdf import PdfReader

from backend.app.config import get_settings

Language = Literal["en", "de", "fr", "unknown"]

_STOPWORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        "a an and are as at be by for from in into is of on or that the this to was with".split()
    ),
    "de": frozenset(
        "aber als am an auch auf aus bei das dem den der des die durch ein eine einer einem für im in ist mit nach nicht oder und von vom zu zum zur".split()
    ),
    "fr": frozenset(
        "a au aux avec ce ces dans de des du elle en et est il la le les leur mais ne ou par pas pour que qui sur un une".split()
    ),
}
_WORD_RE = re.compile(r"[a-zà-ÿ]+", re.IGNORECASE)
_ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf"}
_MIN_PDF_PAGE_CHARACTERS = 50


class DocumentExtractionError(ValueError):
    """Base class for readable, caller-safe document extraction failures."""

    def __init__(self, message: str, *, skipped_page_count: int = 0) -> None:
        super().__init__(message)
        self.skipped_page_count = skipped_page_count


class UnsupportedDocumentError(DocumentExtractionError):
    """Raised when the filename extension is not supported."""


class EmptyDocumentError(DocumentExtractionError):
    """Raised when the input or extracted text is empty."""


class UnreadableDocumentError(DocumentExtractionError):
    """Raised when a supported file cannot be decoded or parsed."""


class ScannedPdfError(DocumentExtractionError):
    """Raised when a PDF contains no usable text layer; OCR is not supported."""


class NoPagesInSelectedLanguagesError(DocumentExtractionError):
    """Raised when all extracted text pages are excluded by the language filter."""


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    page_number: int
    text: str
    language: Language
    included_in_index: bool


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    source_filename: str
    display_title: str
    pages: tuple[ExtractedPage, ...]
    skipped_page_count: int
    excluded_language_page_count: int


def detect_language(text: str) -> Language:
    """Guess English, German, or French from stopword counts; abstain on weak/tied input."""
    words = _WORD_RE.findall(text.lower())
    if not words:
        return "unknown"

    counts = {
        language: sum(word in stopwords for word in words)
        for language, stopwords in _STOPWORDS.items()
    }
    best_count = max(counts.values())
    winners = [language for language, count in counts.items() if count == best_count]
    if best_count < 2 or len(winners) != 1:
        return "unknown"
    return winners[0]  # type: ignore[return-value]


def extract_document(
    filename: str,
    content: bytes | bytearray | memoryview | BinaryIO,
    *,
    index_languages: Collection[str] | None = None,
) -> ExtractedDocument:
    """Extract pages from TXT, Markdown, or searchable PDF content.

    Pages retain their physical 1-based PDF page number. Text formats use page 1,
    incrementing only when an explicit form-feed page marker is present. PDF pages
    with fewer than 50 non-whitespace characters are skipped as drawing pages.
    """
    source_filename = Path(filename).name
    extension = Path(source_filename).suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise UnsupportedDocumentError(
            f"Unsupported file type '{extension or '(no extension)'}'. "
            "Upload a PDF, TXT, or Markdown file."
        )

    raw = _read_content(content)
    if not raw or not raw.strip():
        raise EmptyDocumentError("The uploaded file is empty.")

    active_languages = (
        {language.lower() for language in index_languages}
        if index_languages is not None
        else get_settings().index_languages
    )

    if extension == ".pdf":
        raw_pages, skipped_count = _extract_pdf_pages(raw)
    else:
        raw_pages, skipped_count = _extract_text_pages(raw)

    pages: list[ExtractedPage] = []
    excluded_count = 0
    for page_number, raw_text in raw_pages:
        text = _normalize_text(raw_text)
        if not text:
            continue
        language = detect_language(text)
        included = language in active_languages
        if not included:
            excluded_count += 1
        pages.append(
            ExtractedPage(
                page_number=page_number,
                text=text,
                language=language,
                included_in_index=included,
            )
        )

    if not pages:
        if extension == ".pdf":
            raise ScannedPdfError(
                "No searchable text was found in this PDF. It may be scanned or contain "
                "only drawing pages; OCR is not supported.",
                skipped_page_count=skipped_count,
            )
        raise EmptyDocumentError("No text was found in the uploaded file.")
    if excluded_count == len(pages):
        raise NoPagesInSelectedLanguagesError(
            "No pages in the selected index languages.",
            skipped_page_count=skipped_count,
        )

    return ExtractedDocument(
        source_filename=source_filename,
        display_title=_display_title(source_filename),
        pages=tuple(pages),
        skipped_page_count=skipped_count,
        excluded_language_page_count=excluded_count,
    )


def _read_content(content: bytes | bytearray | memoryview | BinaryIO) -> bytes:
    try:
        raw = content.read() if hasattr(content, "read") else content
    except Exception as exc:
        raise UnreadableDocumentError("The uploaded file could not be read.") from exc
    if isinstance(raw, str):
        try:
            return raw.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise UnreadableDocumentError("The uploaded text could not be encoded as UTF-8.") from exc
    if not isinstance(raw, (bytes, bytearray, memoryview)):
        raise UnreadableDocumentError("The uploaded file content is not readable bytes.")
    return bytes(raw)


def _extract_text_pages(raw: bytes) -> tuple[list[tuple[int, str]], int]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UnreadableDocumentError(
            "Text files must use UTF-8 encoding; this file could not be decoded."
        ) from exc
    pages = [(number, page) for number, page in enumerate(text.split("\f"), start=1)]
    return pages, 0


def _extract_pdf_pages(raw: bytes) -> tuple[list[tuple[int, str]], int]:
    try:
        reader = PdfReader(BytesIO(raw), strict=False)
        extracted: list[tuple[int, str]] = []
        skipped = 0
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if _is_drawing_page(text):
                skipped += 1
                continue
            extracted.append((page_number, text))
    except Exception as exc:
        raise UnreadableDocumentError(
            "The PDF could not be read. Confirm that it is a valid PDF file."
        ) from exc
    return extracted, skipped


def _is_drawing_page(text: str) -> bool:
    if len(re.sub(r"\s", "", text)) < _MIN_PDF_PAGE_CHARACTERS:
        return True
    has_sheet_marker = re.search(r"\bsheet\s+\d+\s+of\s+\d+\b", text, re.IGNORECASE)
    has_figure_label = re.search(r"\bfig(?:ure)?\.?\s*\d+\b", text, re.IGNORECASE)
    if not (has_sheet_marker or has_figure_label):
        return False
    real_word_count = len(re.findall(r"\b[^\W\d_]{3,}\b", text, re.UNICODE))
    return real_word_count < 40


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[\t\v ]+", " ", line).strip() for line in text.split("\n")]
    normalized = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", normalized).strip()


def _display_title(filename: str) -> str:
    stem = Path(filename).stem
    title = re.sub(r"[_\s]+", " ", stem).strip(" .-")
    return title or "Untitled document"
