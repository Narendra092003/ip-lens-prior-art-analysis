import pytest

from backend.app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def isolate_gemini_settings_from_environment(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
