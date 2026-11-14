"""Azure OpenAI embedding calls. The vector width is checked against schema.sql."""

from __future__ import annotations

from openai import AzureOpenAI

from app.config import SCHEMA_EMBEDDING_DIMENSIONS, get_settings

_client: AzureOpenAI | None = None


class EmbeddingError(RuntimeError):
    """The embedding deployment could not be used, or returned an unexpected width."""


def get_openai_client() -> AzureOpenAI:
    global _client
    settings = get_settings()
    missing = settings.missing_azure_env()
    if missing:
        raise EmbeddingError(
            "Azure OpenAI is not configured. Set: " + ", ".join(missing)
        )
    if _client is None:
        _client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
            timeout=60.0,
            max_retries=1,
        )
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    settings = get_settings()
    if settings.embedding_dimensions != SCHEMA_EMBEDDING_DIMENSIONS:
        raise EmbeddingError(
            f"EMBEDDING_DIMENSIONS is {settings.embedding_dimensions}; "
            f"schema.sql expects vector({SCHEMA_EMBEDDING_DIMENSIONS})."
        )
    try:
        response = get_openai_client().embeddings.create(
            model=settings.azure_openai_embedding_deployment,
            input=texts,
        )
    except EmbeddingError:
        raise
    except Exception as exc:
        raise EmbeddingError(f"Embedding request failed: {exc}") from exc
    ordered = sorted(response.data, key=lambda item: item.index)
    vectors = [list(item.embedding) for item in ordered]
    if len(vectors) != len(texts):
        raise EmbeddingError(
            f"Embedding request returned {len(vectors)} vectors for {len(texts)} inputs."
        )
    for vector in vectors:
        if len(vector) != SCHEMA_EMBEDDING_DIMENSIONS:
            raise EmbeddingError(
                f"Embedding model returned {len(vector)} dimensions; "
                f"schema.sql expects {SCHEMA_EMBEDDING_DIMENSIONS}."
            )
    return vectors
