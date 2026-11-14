"""Opt-in retrieval eval. Generation is not scored."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from app.config import get_settings
from app.db import count_chunks, database_ok
from app.rag.retrieve import retrieve

CASES_PATH = Path(__file__).with_name("cases.yaml")
EVAL_K = 8


def _ready_reason() -> str | None:
    if get_settings().missing_azure_env():
        return "Azure OpenAI is not configured."
    try:
        if not database_ok():
            return "Postgres is not reachable."
        if count_chunks() == 0:
            return "The knowledge base has not been ingested. Run python -m app.rag.ingest."
    except Exception as exc:
        return f"Postgres is not reachable ({exc})."
    return None


@pytest.mark.eval
def test_retrieval_cases():
    if os.environ.get("RUN_RETRIEVAL_EVAL") != "1":
        pytest.skip(
            "Retrieval eval is opt-in. Set RUN_RETRIEVAL_EVAL=1 when Azure OpenAI and Postgres are configured."
        )
    reason = _ready_reason()
    if reason:
        pytest.skip(reason)

    cases = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))
    lines: list[str] = []
    failures: list[str] = []
    for case in cases:
        chunks = retrieve(case["query"], k=EVAL_K)
        found_docs = sorted({chunk.document_id for chunk in chunks})
        missing_docs = [
            document_id
            for document_id in case["expected_document_ids"]
            if document_id not in found_docs
        ]
        section_misses = [
            needle
            for needle in case.get("expected_section_contains") or []
            if not any(needle.lower() in chunk.section_path.lower() for chunk in chunks)
        ]
        status = "HIT" if not missing_docs and not section_misses else "MISS"
        section_paths = [chunk.section_path for chunk in chunks]
        lines.append(f"{status} {case['id']}: docs={found_docs} sections={section_paths}")
        if missing_docs or section_misses:
            failures.append(
                f"{case['id']}: missing_docs={missing_docs} missing_sections={section_misses}"
            )
    report = "\n".join(lines)
    print(report)
    assert not failures, "Retrieval eval misses:\n" + report
