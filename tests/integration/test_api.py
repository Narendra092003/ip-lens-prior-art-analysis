import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.api import get_gemini_client, get_settings_dependency, get_vector_store
from backend.app.config import Settings
from backend.app.main import app
from backend.app.services import gemini
from backend.app.services.chunking import ChunkedDocument, DocumentChunk
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


def test_public_settings_returns_non_secret_analysis_settings(api_client) -> None:
    client, _ = api_client

    response = client.get("/api/settings")

    assert response.status_code == 200
    assert response.json() == {
        "min_similarity": 50,
        "default_top_k": 4,
        "default_prompt_version": "v2",
        "max_claims": 10,
        "index_languages": ["en"],
        "chunk_size": 1200,
        "chunk_overlap": 180,
        "gemini_model": "gemini-2.5-flash",
    }
    assert "test-secret-key-that-must-not-leak" not in response.text
    assert "gemini_api_key" not in response.json()


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


def test_analysis_returns_validated_report_and_both_exports(api_client) -> None:
    class FakeModels:
        def generate_content(self, **kwargs):
            self.call = kwargs
            return SimpleNamespace(
                parsed=None,
                text=(
                    '{"elements":[{"element_text":"battery sensor measures the battery state",'
                    '"status":"explicit","explanation":"",'
                    '"supporting_passage_labels":["P1"]}],'
                    '"assessment":"The passage describes a battery sensor.",'
                    '"uncertainty":"Other control details are unclear."}'
                ),
            )

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

    client, vector_store = api_client
    chunk = DocumentChunk(
        document_id="analysis-doc",
        chunk_id="analysis-chunk",
        original_filename="battery.txt",
        display_title="Battery",
        page_number=1,
        chunk_index=0,
        language="en",
        text="A battery sensor measures the battery state and reports it to a controller.",
    )
    vector_store.index_chunks(
        ChunkedDocument(document_id=chunk.document_id, chunks=(chunk,))
    )
    app.dependency_overrides[get_gemini_client] = FakeClient

    response = client.post(
        "/api/analyses",
        json={
            "disclosure_text": "A battery system with a sensor.",
            "reviewed_claims": [
                {
                    "claim_id": "fictional-demo-claim-01",
                    "text": "A battery sensor measures the battery state.",
                }
            ],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["report"]["claims"][0]["evidence_status"] == "evidence"
    assert body["report"]["reviewed_claims"][0]["claim_id"] == "fictional-demo-claim-01"
    assert body["report"]["claims"][0]["claim_id"] == "fictional-demo-claim-01"
    assert body["report"]["analysis_settings"] == {
        "comparison_prompt_version": "v2",
        "gemini_model": "gemini-2.5-flash",
        "min_similarity": 50,
        "top_k": 4,
        "corpus_passage_count": 1,
    }
    assert body["report"]["risk_score"] is not None
    assert json.loads(body["exports"]["json_export"]) == body["report"]
    markdown = body["exports"]["markdown_export"]
    assert "**Status:** Evidence" in markdown
    assert "This is a human-review aid, not legal advice." in markdown
    assert body["report"]["limitations"] in markdown


def test_analysis_rejects_too_many_claims(api_client) -> None:
    client, _ = api_client
    current = Settings(_env_file=None, gemini_api_key="test-key", max_claims=1)
    app.dependency_overrides[get_settings_dependency] = lambda: current

    response = client.post(
        "/api/analyses",
        json={
            "disclosure_text": "Disclosure.",
            "reviewed_claims": ["Claim one.", "Claim two."],
        },
    )

    assert response.status_code == 400
    assert "At most 1 reviewed claims" in response.json()["detail"]


def test_analysis_reports_gemini_not_configured(api_client) -> None:
    client, _ = api_client
    app.dependency_overrides[get_settings_dependency] = lambda: Settings(
        _env_file=None,
        gemini_api_key=None,
    )

    response = client.post(
        "/api/analyses",
        json={"disclosure_text": "Disclosure.", "reviewed_claims": ["A claim."]},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Gemini is not configured."


def test_analysis_invalid_request_returns_400(api_client) -> None:
    client, _ = api_client

    response = client.post(
        "/api/analyses",
        json={
            "disclosure_text": "Disclosure.",
            "reviewed_claims": ["A claim."],
            "prompt_version": "v3",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid analysis request."


def test_analysis_rejects_duplicate_supplied_claim_ids(api_client) -> None:
    client, _ = api_client

    response = client.post(
        "/api/analyses",
        json={
            "disclosure_text": "Disclosure.",
            "reviewed_claims": [
                {"claim_id": "duplicate", "text": "Claim one."},
                {"claim_id": "duplicate", "text": "Claim two."},
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid analysis request."
