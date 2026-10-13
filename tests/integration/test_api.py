from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.api import get_settings_dependency, get_vector_store
from backend.app.config import Settings
from backend.app.main import app
from backend.app.services import gemini
from backend.app.services.vector_store import VectorStore


@pytest.fixture
def api_client(tmp_path):
    settings = Settings(
        _env_file=None,
        chroma_path=tmp_path / "chroma",
        max_upload_mb=1,
        gemini_api_key="test-secret-key-that-must-not-leak",
    )
    vector_store = VectorStore(settings)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_settings_dependency] = lambda: settings
    app.dependency_overrides[get_vector_store] = lambda: vector_store
    with TestClient(app) as client:
        yield client, vector_store
    app.dependency_overrides.clear()


def test_health_returns_boolean_configuration_without_secret(api_client) -> None:
    client, _ = api_client

    response = client.get("/health")

    assert response.status_code == 200
    assert isinstance(response.json()["gemini_configured"], bool)
    assert response.json()["gemini_configured"] is True
    assert "test-secret-key-that-must-not-leak" not in response.text


def test_corpus_returns_vector_store_passage_count(api_client) -> None:
    client, vector_store = api_client
    vector_store.collection.add(
        ids=["test-chunk-a", "test-chunk-b"],
        embeddings=[[0.1, 0.2, 0.3], [0.3, 0.2, 0.1]],
        documents=["First test passage.", "Second test passage."],
        metadatas=[
            {"document_id": "doc-a", "chunk_id": "test-chunk-a"},
            {"document_id": "doc-b", "chunk_id": "test-chunk-b"},
        ],
    )

    response = client.get("/api/corpus")

    assert response.status_code == 200
    assert response.json()["passage_count"] == 2


def test_document_upload_indexes_valid_text_file(api_client) -> None:
    client, _ = api_client
    content = (
        b"This invention describes a battery sensor and a controller that measure "
        b"state of charge in an electric vehicle."
    )

    response = client.post(
        "/api/documents",
        files=[("files", ("battery.txt", content, "text/plain"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["failures"] == []
    assert len(body["indexed"]) == 1
    assert body["indexed"][0]["filename"] == "battery.txt"
    assert body["indexed"][0]["title"] == "battery"
    assert body["indexed"][0]["passage_count"] >= 1


def test_document_upload_reports_unsupported_type(api_client) -> None:
    client, _ = api_client

    response = client.post(
        "/api/documents",
        files=[("files", ("patent.docx", b"not supported", "application/octet-stream"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["indexed"] == []
    assert body["failures"][0]["filename"] == "patent.docx"
    assert "Unsupported file type" in body["failures"][0]["error"]


def test_document_upload_reports_oversized_file(api_client) -> None:
    client, _ = api_client
    oversized = b"x" * (1024 * 1024 + 1)

    response = client.post(
        "/api/documents",
        files=[("files", ("large.txt", oversized, "text/plain"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["indexed"] == []
    assert "1 MB" in body["failures"][0]["error"]


def test_mixed_upload_keeps_success_when_another_file_fails(api_client) -> None:
    client, _ = api_client
    content = b"The controller measures a battery state of charge with a voltage sensor."

    response = client.post(
        "/api/documents",
        files=[
            ("files", ("unsupported.docx", b"docx", "application/octet-stream")),
            ("files", ("valid.txt", content, "text/plain")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["filename"] for item in body["indexed"]] == ["valid.txt"]
    assert [item["filename"] for item in body["failures"]] == ["unsupported.docx"]


def test_disclosure_extract_returns_structured_result_with_fake_gemini(
    api_client, monkeypatch
) -> None:
    class FakeModels:
        def generate_content(self, **kwargs):
            self.call = kwargs
            return SimpleNamespace(
                parsed=None,
                text='{"invention_summary":"A pressure sensor","claims":["1. A pressure sensor."]}',
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    client, _ = api_client
    monkeypatch.setattr(gemini.genai, "Client", FakeClient)

    response = client.post(
        "/api/disclosures/extract",
        json={"disclosure_text": "A sensor measures pressure in a chamber."},
    )

    assert response.status_code == 200
    assert response.json() == {
        "invention_summary": "A pressure sensor",
        "claims": ["A pressure sensor."],
    }


def test_disclosure_extract_returns_clear_error_when_gemini_not_configured(api_client) -> None:
    client, _ = api_client
    app.dependency_overrides[get_settings_dependency] = lambda: Settings(
        _env_file=None,
        gemini_api_key=None,
    )

    response = client.post(
        "/api/disclosures/extract",
        json={"disclosure_text": "A sensor measures pressure."},
    )

    assert response.status_code == 503
    assert "GEMINI_API_KEY is not configured" in response.json()["detail"]
