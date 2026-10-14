"""Compare claim-comparison prompts v1 and v2 on a fixed case set."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import get_settings
from backend.app.schemas import ReviewedClaim
from backend.app.services import gemini
from backend.app.services.gemini import (
    ClaimComparisonResult,
    ClaimComparisonV2Result,
    GeminiServiceError,
)
from backend.app.services.retrieval import ClaimRetrieval, retrieve_claims
from backend.app.services.vector_store import VectorStore

CASES_PATH = PROJECT_ROOT / "examples" / "eval" / "compare_cases.json"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "prompt_comparison.md"
PROMPT_VERSIONS = ("v1", "v2")
RUNS_PER_VERSION = 3
PAUSE_SECONDS = 4
_COVERAGE_POINTS = {"explicit": 1.0, "inferred": 0.75, "partial": 0.5, "missing": 0.0}
_CLAIM_REFERENCE = re.compile(
    r"\b(?:the\s+system\s+of\s+claim\s+1|dependent\s+on\s+claim\s+1)\b",
    re.IGNORECASE,
)
_CLAIM_REFERENCE_ONLY = re.compile(
    r"^\s*(?:the\s+)?(?:system|apparatus|method|device|invention)\s+of\s+claim\s+\d+\s*[,;:.]?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AttemptResult:
    """Metrics captured from one structured comparison attempt."""

    schema_valid: bool
    status: str | None
    coverage: int | None
    discarded_citations: int
    claim_reference_elements: int


def calculate_metrics(
    attempts_by_case: dict[str, list[AttemptResult]],
    *,
    runs_per_case: int = RUNS_PER_VERSION,
) -> dict[str, int | float]:
    """Calculate prompt comparison metrics from fixed or live attempt results."""
    case_count = len(attempts_by_case)
    attempt_count = case_count * runs_per_case
    valid_count = sum(
        attempt.schema_valid
        for attempts in attempts_by_case.values()
        for attempt in attempts
    )
    agreement_count = sum(
        len(attempts) == runs_per_case
        and all(attempt.schema_valid and attempt.status is not None for attempt in attempts)
        and len({attempt.status for attempt in attempts}) == 1
        for attempts in attempts_by_case.values()
    )
    spreads = []
    for attempts in attempts_by_case.values():
        coverage_values = [
            attempt.coverage
            for attempt in attempts
            if attempt.schema_valid and attempt.coverage is not None
        ]
        if coverage_values:
            spreads.append(max(coverage_values) - min(coverage_values))
    return {
        "schema_valid": valid_count,
        "attempts": attempt_count,
        "schema_valid_rate": valid_count / attempt_count if attempt_count else 0.0,
        "discarded_citations": sum(
            attempt.discarded_citations
            for attempts in attempts_by_case.values()
            for attempt in attempts
        ),
        "status_agreement_cases": agreement_count,
        "case_count": case_count,
        "mean_coverage_spread": sum(spreads) / len(spreads) if spreads else 0.0,
        "max_coverage_spread": max(spreads, default=0),
        "cases_with_coverage": len(spreads),
        "claim_reference_elements": sum(
            attempt.claim_reference_elements
            for attempts in attempts_by_case.values()
            for attempt in attempts
        ),
    }


def _attempt_result(result: Any, retrieval: ClaimRetrieval, version: str) -> AttemptResult:
    reference_candidates: list[str]
    if version == "v1":
        if not isinstance(result, ClaimComparisonResult):
            raise TypeError("Prompt v1 returned an unexpected result model")
        cited_ids = result.cited_chunk_ids
        discarded = result.discarded_citation_count
        coverage = result.coverage_estimate
        elements = [*result.shared_elements, *result.missing_elements]
        reference_candidates = elements
    else:
        if not isinstance(result, ClaimComparisonV2Result):
            raise TypeError("Prompt v2 returned an unexpected result model")
        reference_candidates = [element.element_text for element in result.elements]
        elements = [
            element.element_text
            for element in result.elements
            if not _CLAIM_REFERENCE_ONLY.fullmatch(element.element_text)
        ]
        element_results = [
            element
            for element in result.elements
            if not _CLAIM_REFERENCE_ONLY.fullmatch(element.element_text)
        ]
        coverage = (
            round(
                sum(_COVERAGE_POINTS[element.status] for element in element_results)
                / len(element_results)
                * 100
            )
            if element_results
            else None
        )
        labels = list(
            dict.fromkeys(
                label
                for element in element_results
                for label in element.supporting_passage_labels
            )
        )
        label_to_chunk = {
            f"P{index}": passage.chunk_id
            for index, passage in enumerate(retrieval.passages, start=1)
        }
        cited_ids = [label_to_chunk[label] for label in labels if label in label_to_chunk]
        discarded = sum(label not in label_to_chunk for label in labels)

    if not retrieval.passages:
        status = "no_evidence"
        coverage = None
    elif cited_ids:
        status = "evidence"
    elif discarded:
        status = "unsupported"
        coverage = None
    else:
        status = "no_supporting_passage"
        coverage = None
    reference_count = sum(
        bool(_CLAIM_REFERENCE.search(element)) for element in reference_candidates
    )
    return AttemptResult(
        schema_valid=True,
        status=status,
        coverage=coverage,
        discarded_citations=discarded,
        claim_reference_elements=reference_count,
    )


def _invalid_attempt() -> AttemptResult:
    return AttemptResult(False, None, None, 0, 0)


def _coverage_display(attempt: AttemptResult) -> str:
    return f"{attempt.coverage}" if attempt.coverage is not None else "—"


def _render_metrics(version: str, metrics: dict[str, int | float]) -> list[str]:
    return [
        f"### {version}",
        "",
        f"- Schema-valid rate: {metrics['schema_valid']}/{metrics['attempts']} "
        f"({metrics['schema_valid_rate']:.1%})",
        f"- Total discarded citations: {metrics['discarded_citations']}",
        f"- Status agreement (all 3 runs agree): {metrics['status_agreement_cases']}/"
        f"{metrics['case_count']} cases",
        f"- Coverage spread (cases with coverage: {metrics['cases_with_coverage']}): "
        f"mean {metrics['mean_coverage_spread']:.1f}, maximum {metrics['max_coverage_spread']}",
        f"- Claim-reference elements: {metrics['claim_reference_elements']} across all runs",
        "",
    ]


def _render_case_table(
    cases: list[dict[str, str]],
    attempts_by_version: dict[str, dict[str, list[AttemptResult]]],
    source: str,
) -> list[str]:
    lines = [
        f"#### {source.replace('_', ' ').title()} cases",
        "",
        "| Case ID | Source | v1 run 1 | v1 run 2 | v1 run 3 | v2 run 1 | v2 run 2 | v2 run 3 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for case in (item for item in cases if item["source"] == source):
        cells = [f"{case['case_id']} | {case['source']}"]
        for version in PROMPT_VERSIONS:
            for attempt in attempts_by_version[version][case["case_id"]]:
                if not attempt.schema_valid:
                    cells.append("invalid / —")
                else:
                    cells.append(f"{attempt.status} / {_coverage_display(attempt)}")
        lines.append(f"| {' | '.join(cells)} |")
    lines.append("")
    return lines


def _write_report(
    cases: list[dict[str, str]],
    attempts_by_version: dict[str, dict[str, list[AttemptResult]]],
    *,
    model: str,
    settings: Any,
    corpus_count: int,
) -> str:
    lines = [
        "# Prompt comparison: v1 and v2",
        "",
        f"- Date: {date.today().isoformat()}",
        f"- Gemini model: `{model}`",
        f"- Corpus passages at run time: {corpus_count}",
        f"- MIN_SIMILARITY: {settings.min_similarity}",
        f"- top_k: {settings.default_top_k}",
        f"- Chunk size / overlap: {settings.chunk_size} / {settings.chunk_overlap}",
        f"- Attempts: {RUNS_PER_VERSION} per case and prompt version",
        f"- Pause between Gemini calls: {PAUSE_SECONDS} seconds",
        "- Retrieval is performed once per case; both prompts and all runs use the same useful passages.",
        "- Coverage is shown only for evidence findings; other statuses are shown as not assessed.",
        "",
    ]
    for version in PROMPT_VERSIONS:
        metrics = calculate_metrics(attempts_by_version[version])
        lines.extend(_render_metrics(version, metrics))
    for source in ("demo", "held_out"):
        lines.extend(_render_case_table(cases, attempts_by_version, source))
    report = "\n".join(lines)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Override GEMINI_MODEL for this run")
    args = parser.parse_args(argv)

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    settings = get_settings()
    if args.model:
        settings = settings.model_copy(update={"gemini_model": args.model.strip()})
    store = VectorStore(settings)
    corpus_count = store.count()
    attempts_by_version: dict[str, dict[str, list[AttemptResult]]] = {
        version: {} for version in PROMPT_VERSIONS
    }
    total_calls = len(cases) * len(PROMPT_VERSIONS) * RUNS_PER_VERSION
    call_number = 0

    for case_index, case in enumerate(cases, start=1):
        claim = ReviewedClaim(claim_id=case["case_id"], text=case["claim"])
        print(f"[{case_index}/{len(cases)}] {case['case_id']}: retrieving once", flush=True)
        retrieval = retrieve_claims(
            [claim],
            top_k=settings.default_top_k,
            vector_store=store,
            settings=settings,
        )[claim.claim_id]
        print(f"    {len(retrieval.passages)} useful passage(s) retrieved", flush=True)

        for version in PROMPT_VERSIONS:
            attempts: list[AttemptResult] = []
            for run_index in range(1, RUNS_PER_VERSION + 1):
                call_number += 1
                print(
                    f"    Gemini call {call_number}/{total_calls}: {version}, run {run_index}",
                    flush=True,
                )
                try:
                    result = gemini.compare_claim(
                        claim,
                        retrieval.passages,
                        prompt_version=version,
                        settings=settings,
                    )
                    attempts.append(_attempt_result(result, retrieval, version))
                except Exception as exc:
                    if not isinstance(exc, GeminiServiceError):
                        print(f"      comparison failed ({type(exc).__name__})", flush=True)
                    else:
                        print(f"      comparison failed ({type(exc).__name__})", flush=True)
                    attempts.append(_invalid_attempt())
                if call_number < total_calls:
                    time.sleep(PAUSE_SECONDS)
            attempts_by_version[version][case["case_id"]] = attempts

    report = _write_report(
        cases,
        attempts_by_version,
        model=settings.gemini_model,
        settings=settings,
        corpus_count=corpus_count,
    )
    print(report)
    print(f"\nWrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
