"""Postgres access. Schema setup and chunk reads live here in plain SQL."""

from __future__ import annotations

import logging
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

_pool: ConnectionPool | None = None


def apply_schema(conn: psycopg.Connection) -> None:
    raw = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [part.strip() for part in raw.split(";") if part.strip()]
    for statement in statements:
        conn.execute(statement)
    conn.commit()


def _configure(conn: psycopg.Connection) -> None:
    register_vector(conn)


def init_pool() -> ConnectionPool:
    """Apply schema.sql, then open a pool. The vector type has to exist before registration."""
    global _pool
    if _pool is not None:
        return _pool
    settings = get_settings()
    with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
        apply_schema(conn)
    _pool = ConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=4,
        timeout=5,
        kwargs={"connect_timeout": 3},
        configure=_configure,
        open=True,
    )
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def pool() -> ConnectionPool:
    if _pool is None:
        return init_pool()
    return _pool


def database_ok() -> bool:
    try:
        with pool().connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        logger.warning("database health check failed", exc_info=True)
        return False


def count_chunks() -> int:
    with pool().connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
    if row is None:
        return 0
    return int(row[0])


def fetch_chunks(document_id: str | None = None) -> list[dict] | None:
    """Return stored chunks, or None when Postgres cannot be queried."""
    sql = """
        SELECT id, document_id, section_heading, section_path, ordinal, content
        FROM chunks
    """
    params: tuple = ()
    if document_id is not None:
        sql += " WHERE document_id = %s"
        params = (document_id,)
    sql += " ORDER BY document_id, ordinal"
    try:
        with pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())
    except Exception:
        logger.warning("chunk query failed", exc_info=True)
        return None
