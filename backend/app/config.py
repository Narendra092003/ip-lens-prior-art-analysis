"""Environment-backed application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables and an optional project .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    gemini_api_key: SecretStr | None = Field(default=None, repr=False)
    gemini_model: str = "gemini-2.5-flash"
    api_base_url: str = "http://127.0.0.1:8000"
    chroma_path: Path = Path("data/chroma")
    max_upload_mb: int = Field(default=25, ge=1, le=500)
    max_claims: int = Field(default=10, ge=1, le=100)
    chunk_size: int = Field(default=1200, ge=100, le=100_000)
    chunk_overlap: int = Field(default=180, ge=0, le=99_999)
    default_top_k: int = Field(default=4, ge=1, le=10)
    min_similarity: int = Field(default=35, ge=0, le=100)
    index_languages: set[str] = Field(default_factory=lambda: {"en"})

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def normalize_api_key_placeholder(cls, value: object) -> object:
        if isinstance(value, str) and value.strip().lower() in {
            "",
            "your-key-here",
            "your_api_key_here",
        }:
            return None
        return value

    @field_validator("gemini_model", mode="before")
    @classmethod
    def use_default_model_when_blank(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return "gemini-2.5-flash"
        return value

    @field_validator("api_base_url")
    @classmethod
    def normalize_api_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("index_languages")
    @classmethod
    def normalize_index_languages(cls, value: set[str]) -> set[str]:
        languages = {language.strip().lower() for language in value}
        supported = {"en", "de", "fr", "unknown"}
        unsupported = languages - supported
        if unsupported:
            raise ValueError(
                "INDEX_LANGUAGES values must be en, de, fr, or unknown; "
                f"unsupported: {', '.join(sorted(unsupported))}"
            )
        if not languages:
            raise ValueError("INDEX_LANGUAGES must contain at least one language")
        return languages

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.get_secret_value().strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for application-wide dependency injection."""
    return Settings()
