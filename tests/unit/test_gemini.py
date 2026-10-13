from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ConfigDict

from backend.app.config import Settings
from backend.app.services import gemini
from backend.app.services.gemini import (
    GeminiMalformedOutputError,
    GeminiNotConfiguredError,
    _generate_structured,
)


class StructuredResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    claims: list[str]


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)


def _settings(*, api_key="fake-key") -> Settings:
    return Settings(_env_file=None, gemini_api_key=api_key, gemini_model="test-model")


def _response(text: str):
    return SimpleNamespace(text=text, parsed=None)


def test_structured_output_parses_to_requested_pydantic_model() -> None:
    client = FakeClient([_response('{"summary":"A sensor","claims":["Claim one"]}')])

    result = _generate_structured(
        "safe test prompt",
        StructuredResult,
        settings=_settings(),
        client=client,
    )

    assert result == StructuredResult(summary="A sensor", claims=["Claim one"])
    assert client.models.calls[0]["model"] == "test-model"
    assert client.models.calls[0]["config"].response_schema is StructuredResult
    assert client.models.calls[0]["config"].response_mime_type == "application/json"


def test_malformed_structured_output_raises_project_error() -> None:
    client = FakeClient([_response('{"summary": 12, "unknown": true}')])

    with pytest.raises(GeminiMalformedOutputError):
        _generate_structured("test prompt", StructuredResult, settings=_settings(), client=client)


def test_missing_key_raises_without_calling_provider() -> None:
    client = FakeClient([_response('{"summary":"A sensor","claims":[]}')])

    with pytest.raises(GeminiNotConfiguredError, match="GEMINI_API_KEY"):
        _generate_structured("test prompt", StructuredResult, settings=_settings(api_key=None), client=client)

    assert client.models.calls == []


def test_transient_server_error_retries_then_succeeds(monkeypatch) -> None:
    class TemporaryServerError(Exception):
        code = 503

    sleeps = []
    monkeypatch.setattr(gemini.time, "sleep", sleeps.append)
    client = FakeClient(
        [TemporaryServerError("temporary"), _response('{"summary":"A sensor","claims":[]}')]
    )

    result = _generate_structured("test prompt", StructuredResult, settings=_settings(), client=client)

    assert result.summary == "A sensor"
    assert len(client.models.calls) == 2
    assert sleeps == [0.25]
