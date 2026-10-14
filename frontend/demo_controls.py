"""Small, deterministic safeguards for the optional public demo UI."""

from __future__ import annotations

import hmac
from collections.abc import Iterable

DEMO_MAX_CLAIMS = 4
DEMO_MAX_UPLOAD_BYTES = 2 * 1024 * 1024


def access_code_is_valid(submitted: str | None, configured: str | None) -> bool:
    """Allow access when no code is configured; otherwise compare in constant time."""
    if not configured:
        return True
    return submitted is not None and hmac.compare_digest(
        submitted.encode("utf-8"), configured.encode("utf-8")
    )


def claim_count_is_allowed(claim_count: int, demo_mode: bool) -> bool:
    """Apply the four-claim cap only in public demo mode."""
    return not demo_mode or claim_count <= DEMO_MAX_CLAIMS


def uploads_are_enabled(demo_mode: bool, allow_demo_uploads: bool) -> bool:
    """Uploads remain available locally and require explicit opt-in in demo mode."""
    return not demo_mode or allow_demo_uploads


def upload_sizes_are_allowed(sizes: Iterable[int], demo_mode: bool) -> bool:
    """Apply the 2 MB per-file cap only in demo mode."""
    return not demo_mode or all(size <= DEMO_MAX_UPLOAD_BYTES for size in sizes)
