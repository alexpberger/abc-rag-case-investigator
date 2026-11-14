"""Cosine similarity retrieval. Distance is pgvector `<=>` (lower is closer)."""

from __future__ import annotations

from dataclasses import dataclass

from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from app.db import pool
from app.rag.embeddings import embed_texts

# Fixed fan-out for the primary investigation. These are not chosen by the model.
INVESTIGATE_QUERIES: tuple[str, ...] = (
    "What sudden and accidental water damage the policy covers",
    "What gradual deterioration, seepage, or leakage over time the policy excludes",
    "What the customer says happened and when",
    "What the plumber observed about the pipe, corrosion, and duration",
    "What information the investigation guidelines say is still required before a coverage decision",
)
INVESTIGATE_K = 4
INVESTIGATE_CAP = 12
ASK_K = 6


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    document_id: str
    document_title: str
    section_heading: str
    section_path: str
    content: str
    distance: float


def merge_retrieved(groups: list[list[RetrievedChunk]], cap: int) -> list[RetrievedChunk]:
    """Keep the closest distance when a chunk is hit by more than one query."""
    merged: dict[str, RetrievedChunk] = {}
    for group in groups:
        for chunk in group:
            current = merged.get(chunk.id)
            if current is None or chunk.distance < current.distance:
                merged[chunk.id] = chunk
    ranked = sorted(merged.values(), key=lambda chunk: (chunk.distance, chunk.id))
    return ranked[:cap]


def _search(conn, vector: list[float], k: int) -> list[RetrievedChunk]:
    register_vector(conn)
    with conn.cursor(row_factory=dict_row) as cur:
        # `<=>` is cosine distance. Exact order, no ANN index, on a small table.
        cur.execute(
            """
            SELECT
                c.id,
                c.document_id,
                d.title AS document_title,
                c.section_heading,
                c.section_path,
                c.content,
                (c.embedding <=> %s) AS distance
            FROM chunks AS c
            JOIN documents AS d ON d.id = c.document_id
            ORDER BY c.embedding <=> %s
            LIMIT %s
            """,
            (vector, vector, k),
        )
        rows = cur.fetchall()
    return [
        RetrievedChunk(
            id=row["id"],
            document_id=row["document_id"],
            document_title=row["document_title"],
            section_heading=row["section_heading"],
            section_path=row["section_path"],
            content=row["content"],
            distance=float(row["distance"]),
        )
        for row in rows
    ]


def retrieve_vectors(vectors: list[list[float]], k: int) -> list[list[RetrievedChunk]]:
    with pool().connection() as conn:
        return [_search(conn, vector, k) for vector in vectors]


def retrieve(query: str, k: int = ASK_K) -> list[RetrievedChunk]:
    vectors = embed_texts([query])
    groups = retrieve_vectors(vectors, k)
    return groups[0] if groups else []


def retrieve_investigation() -> list[RetrievedChunk]:
    vectors = embed_texts(list(INVESTIGATE_QUERIES))
    groups = retrieve_vectors(vectors, INVESTIGATE_K)
    return merge_retrieved(groups, INVESTIGATE_CAP)
