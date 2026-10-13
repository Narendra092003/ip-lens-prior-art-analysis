"""Ingest each supported file in a folder using the application's ingestion service."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import get_settings
from backend.app.services.documents import DocumentExtractionError
from backend.app.services.ingestion import IngestionService, UploadTooLargeError
from backend.app.services.vector_store import VectorStore

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "folder",
        nargs="?",
        type=Path,
        default=Path("examples/real"),
        help="Folder containing PDF, TXT, or Markdown documents (default: examples/real)",
    )
    args = parser.parse_args()
    if not args.folder.is_dir():
        parser.error(f"Folder does not exist: {args.folder}")

    settings = get_settings()
    service = IngestionService(settings=settings, vector_store=VectorStore(settings))
    files = sorted(
        path for path in args.folder.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    total = len(files)
    succeeded = 0
    failures = 0
    indexed_passages = 0
    skipped_pages = 0
    excluded_pages = 0

    for position, path in enumerate(files, start=1):
        print(f"[{position}/{total}] {path.name}", flush=True)
        try:
            max_bytes = settings.max_upload_mb * 1024 * 1024
            if path.stat().st_size > max_bytes:
                raise UploadTooLargeError(settings.max_upload_mb)
            result = service.ingest(path.name, path.read_bytes())
            succeeded += 1
            indexed_passages += result.passage_count
            skipped_pages += result.skipped_page_count
            excluded_pages += result.excluded_language_page_count
            print(
                f"  indexed {result.passage_count} chunks; "
                f"skipped drawings {result.skipped_page_count}; "
                f"excluded languages {result.excluded_language_page_count}"
            )
        except (DocumentExtractionError, UploadTooLargeError) as exc:
            failures += 1
            print(f"  failed: {exc}")
        except Exception:
            failures += 1
            print("  failed: the document could not be indexed because of a storage error")

    print(
        f"Summary: {succeeded} succeeded, {failures} failed, "
        f"{indexed_passages} chunks indexed, {skipped_pages} drawing pages skipped, "
        f"{excluded_pages} pages excluded by language."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
