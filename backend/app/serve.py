"""Container entrypoint. Local development starts uvicorn directly and does not use this module.

Wait until Postgres answers, ingest the knowledge base, then replace this process with uvicorn.
Unchanged documents are not re-embedded. A fresh replica pays for embeddings once.
"""

from __future__ import annotations

import logging
import os
import time

import psycopg

from app.config import get_settings
from app.rag.embeddings import EmbeddingError
from app.rag.ingest import IngestError, ingest

logger = logging.getLogger(__name__)

WAIT_SECONDS = 120


def wait_for_database() -> None:
    settings = get_settings()
    deadline = time.monotonic() + WAIT_SECONDS
    last_error = "the database did not answer"
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
                conn.execute("SELECT 1")
            return
        except Exception as exc:
            last_error = str(exc)
            logger.info("waiting for postgres")
            time.sleep(2)
    raise SystemExit(f"postgres did not become ready: {last_error}")


def ingest_knowledge() -> None:
    try:
        for line in ingest():
            print(line, flush=True)
    except IngestError as exc:
        message = str(exc)
        if message.startswith("Azure OpenAI is not configured"):
            print(message, flush=True)
            return
        raise SystemExit(f"ingest failed: {message}") from exc
    except EmbeddingError as exc:
        raise SystemExit(f"ingest failed: {exc}") from exc


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    wait_for_database()
    ingest_knowledge()
    os.execvp(
        "uvicorn",
        ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    )


if __name__ == "__main__":
    main()
