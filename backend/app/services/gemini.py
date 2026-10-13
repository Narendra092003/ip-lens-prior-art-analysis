"""Gemini provider boundary for structured, project-model output."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any, Sequence, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from backend.app.config import Settings, get_settings
from backend.app.schemas import DisclosureExtractResponse

T = TypeVar("T", bound=BaseModel)

_REQUEST_TIMEOUT_MS = 30_000
_MAX_RETRIES = 2
_DISCLOSURE_PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "prompts" / "disclosure_extract_v1.md"
)
logger = logging.getLogger(__name__)


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


class _GeminiDisclosureExtractResponse(BaseModel):
    """Provider schema kept separate from the strict public API contract."""

    invention_summary: str
    claims: list[str]


def _generate_structured(
    prompt: str,
    response_model: type[T],
    *,
    settings: Settings | None = None,
    client: Any | None = None,
    response_schema: type[BaseModel] | None = None,
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
                    response_schema=response_schema or response_model,
                ),
            )
        except Exception as exc:
            category = _transient_category(exc)
            if category is None:
                _log_provider_failure(exc, prompt=prompt, api_key=api_key)
                raise GeminiProviderError("Gemini could not complete the request.") from exc
            if attempt < _MAX_RETRIES:
                time.sleep(0.25 * (2**attempt))
                continue
            _log_provider_failure(exc, prompt=prompt, api_key=api_key)
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
            if isinstance(parsed, BaseModel):
                parsed = parsed.model_dump()
            return response_model.model_validate(parsed)
        output_text = response.text
        if not output_text:
            raise ValueError("Structured response is empty")
        return response_model.model_validate_json(output_text)
    except (ValidationError, ValueError, TypeError, AttributeError) as exc:
        logger.warning(
            "Gemini structured response validation failed: error_class=%s",
            type(exc).__name__,
        )
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


def _log_provider_failure(error: Exception, *, prompt: str, api_key: str) -> None:
    """Log provider diagnostics while removing request data and credentials."""
    message = getattr(error, "message", None)
    if not isinstance(message, str) or not message:
        message = "(provider message unavailable)"
    if prompt:
        message = message.replace(prompt, "[redacted prompt]")
        disclosure_marker = "<disclosure_text>\n"
        if disclosure_marker in prompt:
            disclosure = prompt.split(disclosure_marker, 1)[1].split(
                "\n</disclosure_text>", 1
            )[0]
            if disclosure:
                message = message.replace(disclosure, "[redacted disclosure]")
    if api_key:
        message = message.replace(api_key, "[redacted key]")
    logger.warning(
        "Gemini provider request failed: error_class=%s status_code=%s message=%s",
        type(error).__name__,
        _status_code(error),
        message,
    )


def _load_disclosure_prompt_template() -> str:
    """Load the versioned disclosure extraction prompt from the application package."""
    return _DISCLOSURE_PROMPT_PATH.read_text(encoding="utf-8")


def structure_disclosure(
    text: str,
    *,
    settings: Settings | None = None,
    client: Any | None = None,
) -> DisclosureExtractResponse:
    """Summarize a disclosure and propose claims for analyst review."""
    template = _load_disclosure_prompt_template()
    prompt = (
        f"{template.rstrip()}\n\n"
        "<disclosure_text>\n"
        f"{text}\n"
        "</disclosure_text>"
    )
    result = _generate_structured(
        prompt,
        DisclosureExtractResponse,
        settings=settings,
        client=client,
        response_schema=_GeminiDisclosureExtractResponse,
    )
    return DisclosureExtractResponse(
        invention_summary=result.invention_summary,
        claims=[re.sub(r"^\s*\d+\.\s+", "", claim) for claim in result.claims],
    )


def compare_claim(
    claim: BaseModel,
    passages: Sequence[BaseModel],
    prompt_version: str = "v1",
) -> BaseModel:
    """Phase 12 stub: compare a reviewed claim against its retrieved passages."""
    raise NotImplementedError("compare_claim is implemented in Phase 12")
