from pathlib import Path

import yaml

from app.rag.chunk import load_documents

ROOT = Path(__file__).resolve().parents[2]
CASES = Path(__file__).resolve().parent / "eval" / "cases.yaml"
EXPECTED_IDS = [
    "insurance-policy",
    "claims-guidelines",
    "customer-claim",
    "plumber-report",
    "claims-correspondence",
]


def _documents():
    return load_documents(ROOT / "knowledge" / "documents", ROOT)


def test_corpus_shape_matches_the_chunk_contract():
    documents = _documents()
    assert [document.id for document in documents] == EXPECTED_IDS
    total = sum(len(document.chunks) for document in documents)
    assert 25 <= total <= 40
    for document in documents:
        words = len(document.raw_text.split())
        assert 400 <= words <= 800, f"{document.id} has {words} words"
        assert document.chunks
        assert [chunk.ordinal for chunk in document.chunks] == list(range(len(document.chunks)))
        assert all(len(chunk.content) <= 6000 for chunk in document.chunks)


def test_eval_cases_point_at_real_sections():
    cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))
    documents = {document.id: document for document in _documents()}
    assert len(cases) >= 6
    for case in cases:
        for document_id in case["expected_document_ids"]:
            assert document_id in documents
        for needle in case.get("expected_section_contains") or []:
            paths = [
                chunk.section_path
                for document_id in case["expected_document_ids"]
                for chunk in documents[document_id].chunks
            ]
            assert any(needle.lower() in path.lower() for path in paths), (
                f"{case['id']} needle {needle!r} not in {paths}"
            )
