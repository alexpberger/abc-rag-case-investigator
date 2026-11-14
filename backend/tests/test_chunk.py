from pathlib import Path

import pytest

from app.rag.chunk import (
    MAX_CHUNK_CHARS,
    DocumentFormatError,
    load_documents,
    parse_document,
)

SAMPLE = """---
id: sample-doc
title: Sample Policy
---
This preamble explains the excerpt.

# Coverage
Covered events are listed here.

## Sudden water
Water from a sudden discharge is described here.

# Exclusions
## Gradual leakage
Gradual leakage is described here.

### Detail
#### Not a new section
Still inside the detail section.
"""


def test_front_matter_preamble_nesting_and_order():
    document = parse_document(SAMPLE, "knowledge/documents/sample.md")
    assert document.id == "sample-doc"
    assert document.title == "Sample Policy"
    assert document.source_path == "knowledge/documents/sample.md"
    paths = [chunk.section_path for chunk in document.chunks]
    assert paths == [
        "Sample Policy",
        "Coverage",
        "Coverage / Sudden water",
        "Exclusions / Gradual leakage",
        "Exclusions / Gradual leakage / Detail",
    ]
    assert document.chunks[0].section_heading == "Sample Policy"
    assert document.chunks[0].content == "This preamble explains the excerpt."
    assert "#### Not a new section" in document.chunks[-1].content
    assert "Still inside the detail section." in document.chunks[-1].content
    assert [chunk.ordinal for chunk in document.chunks] == list(range(len(document.chunks)))
    assert [chunk.id for chunk in document.chunks] == [
        f"sample-doc/{ordinal}" for ordinal in range(len(document.chunks))
    ]


def test_chunk_ids_are_stable():
    first = parse_document(SAMPLE, "sample.md")
    second = parse_document(SAMPLE, "sample.md")
    assert first.chunks == second.chunks
    assert first.content_hash == second.content_hash


def test_newlines_do_not_change_the_hash():
    unix = parse_document(SAMPLE, "sample.md")
    windows = parse_document(SAMPLE.replace("\n", "\r\n"), "sample.md")
    assert unix.content_hash == windows.content_hash
    assert [chunk.content for chunk in unix.chunks] == [chunk.content for chunk in windows.chunks]


def test_empty_parent_heading_is_omitted_but_kept_in_the_path():
    document = parse_document(SAMPLE, "sample.md")
    assert all(chunk.section_path != "Exclusions" for chunk in document.chunks)
    assert any(chunk.section_path.startswith("Exclusions / ") for chunk in document.chunks)


def test_long_section_splits_on_blank_lines_without_overlap():
    paragraph_a = "A" * 3500
    paragraph_b = "B" * 3500
    text = f"---\nid: big-doc\ntitle: Big\n---\n# Big\n\n{paragraph_a}\n\n{paragraph_b}\n"
    document = parse_document(text, "big.md")
    assert len(document.chunks) == 2
    assert all(len(chunk.content) <= MAX_CHUNK_CHARS for chunk in document.chunks)
    assert document.chunks[0].content == paragraph_a
    assert document.chunks[1].content == paragraph_b
    assert document.chunks[0].section_path == document.chunks[1].section_path == "Big"
    assert document.chunks[0].id == "big-doc/0"
    assert document.chunks[1].id == "big-doc/1"


def test_oversized_paragraph_splits_on_a_character_boundary():
    blob = "X" * (MAX_CHUNK_CHARS + 1)
    text = f"---\nid: wide-doc\ntitle: Wide\n---\n# Wide\n\n{blob}\n"
    document = parse_document(text, "wide.md")
    assert len(document.chunks) == 2
    assert "".join(chunk.content for chunk in document.chunks) == blob
    assert all(len(chunk.content) <= MAX_CHUNK_CHARS for chunk in document.chunks)


def test_section_under_the_limit_stays_one_chunk():
    body = "Y" * MAX_CHUNK_CHARS
    text = f"---\nid: exact-doc\ntitle: Exact\n---\n# Exact\n\n{body}\n"
    document = parse_document(text, "exact.md")
    assert len(document.chunks) == 1
    assert document.chunks[0].content == body


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("No front matter\n", "front matter"),
        ("---\nid: only-id\n---\n\nBody\n", "id and title"),
        ("---\nid: sample-doc\ntitle: Sample\nowner: someone\n---\n\nBody\n", "only contain"),
        ("---\nid: Not A Slug\ntitle: Sample\n---\n\nBody\n", "lowercase slug"),
        ("---\nid: sample-doc\ntitle: Sample\n\nBody without a closer\n", "not closed"),
    ],
)
def test_front_matter_errors(text: str, message: str):
    with pytest.raises(DocumentFormatError, match=message):
        parse_document(text, "bad.md")


def test_duplicate_document_ids_are_rejected(tmp_path: Path):
    root = tmp_path
    directory = root / "knowledge" / "documents"
    directory.mkdir(parents=True)
    body = "---\nid: same-id\ntitle: One\n---\n\nHello\n"
    (directory / "a.md").write_text(body, encoding="utf-8")
    (directory / "b.md").write_text(body, encoding="utf-8")
    with pytest.raises(DocumentFormatError, match="Duplicate document id"):
        load_documents(directory, root)


def test_missing_directory_files_are_rejected(tmp_path: Path):
    directory = tmp_path / "empty"
    directory.mkdir()
    with pytest.raises(DocumentFormatError, match="No Markdown documents"):
        load_documents(directory, tmp_path)
