"""Seed an empty local corpus with the fictional demo prior-art documents."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import get_settings
from backend.app.services.ingestion import IngestionService
from backend.app.services.vector_store import VectorStore


def main() -> int:
    settings = get_settings()
    vector_store = VectorStore(settings)
    existing_count = vector_store.count()
    if existing_count:
        print(f"Demo seeding skipped: corpus already has {existing_count} passages.")
        return 0

    service = IngestionService(settings=settings, vector_store=vector_store)
    documents = sorted((PROJECT_ROOT / "examples").glob("synthetic_prior_art_*.txt"))
    if not documents:
        print("No synthetic demo documents were found.", file=sys.stderr)
        return 1

    failures: list[str] = []
    for path in documents:
        try:
            result = service.ingest(path.name, path.read_bytes())
            print(f"Indexed {path.name}: {result.passage_count} passages.")
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")

    if failures:
        for failure in failures:
            print(f"Failed to seed {failure}", file=sys.stderr)
        return 1

    print(f"Seeded {len(documents)} fictional documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
