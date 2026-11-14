"""Environment configuration. Secrets stay in the process environment or a gitignored .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> repository root when the checkout layout is intact.
REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = REPO_ROOT / ".env"

# schema.sql fixes the vector column at this width (text-embedding-3-small).
SCHEMA_EMBEDDING_DIMENSIONS = 1536


def default_knowledge_dir() -> Path:
    candidate = REPO_ROOT / "knowledge"
    if candidate.is_dir():
        return candidate
    return Path("/app/knowledge")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.is_file() else None,
        extra="ignore",
    )

    database_url: str = "postgresql://postgres:postgres@127.0.0.1:5432/cases"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = "gpt-4.1"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    embedding_dimensions: int = SCHEMA_EMBEDDING_DIMENSIONS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    knowledge_dir: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def missing_azure_env(self) -> list[str]:
        missing: list[str] = []
        if not self.azure_openai_endpoint.strip():
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not self.azure_openai_api_key.strip():
            missing.append("AZURE_OPENAI_API_KEY")
        return missing

    def resolved_knowledge_dir(self) -> Path:
        raw = self.knowledge_dir.strip()
        path = Path(raw) if raw else default_knowledge_dir()
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
