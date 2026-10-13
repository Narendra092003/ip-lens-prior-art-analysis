import pytest
from fastapi.testclient import TestClient

from backend.app.api import get_settings_dependency, get_vector_store
from backend.app.config import Settings
from backend.app.main import app
from backend.app.services.vector_store import VectorStore


@pytest.fixture
def api_client(tmp_path):
    settings = Settings(
        _env_file=None,
        chroma_path=tmp_path / "chroma",
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
