from frontend.demo_controls import (
    DEMO_MAX_UPLOAD_BYTES,
    access_code_is_valid,
    claim_count_is_allowed,
    upload_sizes_are_allowed,
    uploads_are_enabled,
)


def test_access_code_is_optional_and_checked_when_configured() -> None:
    assert access_code_is_valid(None, None)
    assert access_code_is_valid("anything", "")
    assert access_code_is_valid("correct", "correct")
    assert not access_code_is_valid("wrong", "correct")
    assert not access_code_is_valid(None, "correct")


def test_demo_claim_limit_is_four_and_local_mode_is_unlimited() -> None:
    assert claim_count_is_allowed(4, demo_mode=True)
    assert not claim_count_is_allowed(5, demo_mode=True)
    assert claim_count_is_allowed(10, demo_mode=False)


def test_demo_uploads_need_opt_in_and_have_two_mb_per_file_limit() -> None:
    assert not uploads_are_enabled(demo_mode=True, allow_demo_uploads=False)
    assert uploads_are_enabled(demo_mode=True, allow_demo_uploads=True)
    assert uploads_are_enabled(demo_mode=False, allow_demo_uploads=False)
    assert upload_sizes_are_allowed([DEMO_MAX_UPLOAD_BYTES], demo_mode=True)
    assert not upload_sizes_are_allowed([DEMO_MAX_UPLOAD_BYTES + 1], demo_mode=True)
    assert upload_sizes_are_allowed([DEMO_MAX_UPLOAD_BYTES * 5], demo_mode=False)
