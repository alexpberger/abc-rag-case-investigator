"""Idempotent ingest. Unchanged documents are not re-embedded unless --force is set."""

from __future__ import annotations

import argparse
import logging

import psycopg
from psycopg.rows import dict_row

from app.config import SCHEMA_EMBEDDING_DIMENSIONS, get_settings
from app.db import init_pool, pool
from app.rag.chunk import ChunkDraft, ParsedDocument, load_documents
from app.rag.embeddings import EmbeddingError, embed_texts

logger = logging.getLogger(__name__)


class IngestError(RuntimeError):
    """Ingest cannot run with the current configuration or knowledge files."""


def embedding_input(chunk: ChunkDraft) -> str:
    """Include the section path so the vector carries the heading, not only the body."""
    return f"{chunk.section_path}\n\n{chunk.content}"


def _knowledge_root():
    knowledge = get_settings().resolved_knowledge_dir()
    return knowledge, knowledge.parent


def ingest(force: bool = False) -> list[str]:
    settings = get_settings()
    missing = settings.missing_azure_env()
    if missing:
        raise IngestError("Azure OpenAI is not configured. Set: " + ", ".join(missing))
    if settings.embedding_dimensions != SCHEMA_EMBEDDING_DIMENSIONS:
        raise IngestError(
            f"EMBEDDING_DIMENSIONS is {settings.embedding_dimensions}; "
            f"schema.sql expects vector({SCHEMA_EMBEDDING_DIMENSIONS})."
        )

    knowledge, root = _knowledge_root()
    documents = load_documents(knowledge / "documents", root)
    try:
        init_pool()
    except psycopg.OperationalError as exc:
        raise IngestError(
            "Could not connect to Postgres. Start it with: docker compose up -d postgres"
        ) from exc

    with pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id, content_hash FROM documents")
            existing = {row["id"]: row["content_hash"] for row in cur.fetchall()}

    planned: list[tuple[ParsedDocument, list[list[float]] | None]] = []
    lines: list[str] = []
    for document in documents:
        unchanged = existing.get(document.id) == document.content_hash
        if unchanged and not force:
            lines.append(f"{document.id}: unchanged, skipped")
            planned.append((document, None))
            continue
        vectors = embed_texts([embedding_input(chunk) for chunk in document.chunks])
        lines.append(f"{document.id}: embedded {len(document.chunks)} chunks")
        planned.append((document, vectors))

    current_ids = [document.id for document in documents]
    with pool().connection() as conn:
        for document, vectors in planned:
            if vectors is None:
                continue
            _write_document(conn, document, vectors)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM documents WHERE NOT (id = ANY(%s))",
                (current_ids,),
            )
            removed = cur.rowcount
        conn.commit()
    if removed:
        lines.append(f"removed {removed} document(s) no longer in the knowledge directory")
    return lines


def _write_document(conn, document: ParsedDocument, vectors: list[list[float]]) -> None:
    if len(vectors) != len(document.chunks):
        raise IngestError(
            f"{document.id}: expected {len(document.chunks)} embeddings, got {len(vectors)}."
        )
    conn.execute(
        """
        INSERT INTO documents (id, title, source_path, content_hash, updated_at)
        VALUES (%s, %s, %s, %s, now())
        ON CONFLICT (id) DO UPDATE
        SET title = EXCLUDED.title,
            source_path = EXCLUDED.source_path,
            content_hash = EXCLUDED.content_hash,
            updated_at = now()
        """,
        (document.id, document.title, document.source_path, document.content_hash),
    )
    conn.execute("DELETE FROM chunks WHERE document_id = %s", (document.id,))
    rows = [
        (
            chunk.id,
            chunk.document_id,
            chunk.section_heading,
            chunk.section_path,
            chunk.ordinal,
            chunk.content,
            chunk.content_hash,
            vector,
        )
        for chunk, vector in zip(document.chunks, vectors, strict=True)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO chunks (
                id, document_id, section_heading, section_path, ordinal,
                content, content_hash, embedding
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Embed the Markdown knowledge base into Postgres.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed every document, including unchanged ones.",
    )
    args = parser.parse_args()
    try:
        for line in ingest(force=args.force):
            print(line)
    except (IngestError, EmbeddingError) as exc:
        raise SystemExit(f"ingest failed: {exc}") from exc


if __name__ == "__main__":
    main()
