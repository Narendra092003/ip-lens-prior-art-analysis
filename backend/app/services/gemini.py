"""Gemini provider boundary for structured, project-model output."""

from __future__ import annotations

import time
from typing import Any, Sequence, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from backend.app.config import Settings, get_settings
from backend.app.schemas import DisclosureExtractResponse

T = TypeVar("T", bound=BaseModel)

_REQUEST_TIMEOUT_MS = 30_000
_MAX_RETRIES = 2


class GeminiServiceError(RuntimeError):
    """Base class for safe provider errors exposed to the application."""


class GeminiNotConfiguredError(GeminiServiceError):
    """Raised when no non-empty Gemini API key is configured."""


class GeminiRateLimitedError(GeminiServiceError):
    """Raised when Gemini continues to rate-limit after bounded retries."""


class GeminiTimeoutError(GeminiServiceError):
    """Raised when a Gemini request times out after bounded retries."""


class GeminiMalformedOutputError(GeminiServiceError):
    """Raised when structured output cannot be parsed into its requested model."""


class GeminiProviderError(GeminiServiceError):
    """Raised for non-transient or exhausted provider failures."""


def _generate_structured(
    prompt: str,
    response_model: type[T],
    *,
    settings: Settings | None = None,
    client: Any | None = None,
) -> T:
    """Generate JSON with Gemini's schema mode and validate it as a Pydantic model."""
    active_settings = settings or get_settings()
    if not active_settings.gemini_api_key:
        raise GeminiNotConfiguredError("GEMINI_API_KEY is not configured.")
    api_key = active_settings.gemini_api_key.get_secret_value().strip()
    if not api_key:
        raise GeminiNotConfiguredError("GEMINI_API_KEY is not configured.")

    active_client = client
    for attempt in range(_MAX_RETRIES + 1):
        try:
            if active_client is None:
                active_client = genai.Client(
                    api_key=api_key,
                    http_options=types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS),
                )
            response = active_client.models.generate_content(
                model=active_settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_model,
                ),
            )
        except Exception as exc:
            category = _transient_category(exc)
            if category is None:
                raise GeminiProviderError("Gemini could not complete the request.") from exc
            if attempt < _MAX_RETRIES:
                time.sleep(0.25 * (2**attempt))
                continue
            if category == "rate_limit":
                raise GeminiRateLimitedError("Gemini rate limit persisted after retries.") from exc
            if category == "timeout":
                raise GeminiTimeoutError("Gemini request timed out after retries.") from exc
            raise GeminiProviderError("Gemini server error persisted after retries.") from exc

        return _parse_response(response, response_model)

    raise GeminiProviderError("Gemini could not complete the request.")


def _parse_response(response: Any, response_model: type[T]) -> T:
    try:
        parsed = response.parsed
        if parsed is not None:
            if isinstance(parsed, response_model):
                return parsed
            return response_model.model_validate(parsed)
        output_text = response.text
        if not output_text:
            raise ValueError("Structured response is empty")
        return response_model.model_validate_json(output_text)
    except (ValidationError, ValueError, TypeError, AttributeError) as exc:
        raise GeminiMalformedOutputError(
            "Gemini returned malformed structured output."
        ) from exc


def _transient_category(error: Exception) -> str | None:
    error_name = type(error).__name__.lower()
    if isinstance(error, TimeoutError) or "timeout" in error_name:
        return "timeout"

    status_code = _status_code(error)
    if status_code == 429:
        return "rate_limit"
    if status_code is not None and 500 <= status_code <= 599:
        return "server"
    return None


def _status_code(error: Exception) -> int | None:
    for value in (
        getattr(error, "code", None),
        getattr(error, "status_code", None),
        getattr(getattr(error, "response", None), "status_code", None),
    ):
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            continue
    return None


def structure_disclosure(text: str) -> DisclosureExtractResponse:
    """Phase 10 stub: build and send the disclosure-structuring prompt."""
    raise NotImplementedError("structure_disclosure is implemented in Phase 10")


def compare_claim(
    claim: BaseModel,
    passages: Sequence[BaseModel],
    prompt_version: str = "v1",
) -> BaseModel:
    """Phase 12 stub: compare a reviewed claim against its retrieved passages."""
    raise NotImplementedError("compare_claim is implemented in Phase 12")
