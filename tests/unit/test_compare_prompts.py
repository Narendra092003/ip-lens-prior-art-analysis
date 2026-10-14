from scripts.compare_prompts import AttemptResult, calculate_metrics


def test_prompt_metrics_from_fixed_attempt_results():
    attempts = {
        "case-a": [
            AttemptResult(True, "evidence", 60, 1, 1),
            AttemptResult(True, "evidence", 75, 0, 0),
            AttemptResult(True, "evidence", 50, 2, 2),
        ],
        "case-b": [
            AttemptResult(True, "no_supporting_passage", None, 1, 0),
            AttemptResult(True, "no_supporting_passage", 40, 0, 0),
            AttemptResult(False, None, None, 0, 0),
        ],
    }

    metrics = calculate_metrics(attempts)

    assert metrics == {
        "schema_valid": 5,
        "attempts": 6,
        "schema_valid_rate": 5 / 6,
        "discarded_citations": 4,
        "status_agreement_cases": 1,
        "case_count": 2,
        "mean_coverage_spread": 12.5,
        "max_coverage_spread": 25,
        "cases_with_coverage": 2,
        "claim_reference_elements": 3,
    }
