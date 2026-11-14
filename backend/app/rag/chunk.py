"""Deterministic Markdown chunker.

Front matter is two scalar keys, id and title. Headings at levels 1–3 open
sections. Deeper headings stay inside the current section. A section longer
than MAX_CHUNK_CHARS is split on blank lines, with no overlap.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

MAX_CHUNK_CHARS = 6000
_HEADING = re.compile(r"^(#{1,3}) +(.+?)\s*$")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class DocumentFormatError(ValueError):
    """A knowledge file does not match the chunk contract."""


@dataclass(frozen=True)
class ChunkDraft:
    id: str
    document_id: str
    section_heading: str
    section_path: str
    ordinal: int
    content: str
    content_hash: str


@dataclass(frozen=True)
class ParsedDocument:
    id: str
    title: str
    source_path: str
    raw_text: str
    content_hash: str
    chunks: list[ChunkDraft]


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse_front_matter(text: str) -> tuple[str, str, str]:
    if not text.startswith("---\n"):
        raise DocumentFormatError("Document must start with a YAML front matter block.")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise DocumentFormatError("Front matter is not closed with '---'.")
    block = text[4:end]
    body = text[end + 5 :]
    fields: dict[str, str] = {}
    for line_number, line in enumerate(block.splitlines(), start=2):
        if not line.strip():
            continue
        if ":" not in line:
            raise DocumentFormatError(f"Invalid front matter line {line_number}: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in fields:
            raise DocumentFormatError(f"Duplicate front matter key: {key}")
        fields[key] = value
    unexpected = sorted(set(fields) - {"id", "title"})
    if unexpected:
        raise DocumentFormatError(
            "Front matter may only contain id and title "
            f"(found {', '.join(unexpected)})."
        )
    document_id = fields.get("id", "")
    title = fields.get("title", "")
    if not document_id or not title:
        raise DocumentFormatError("Front matter requires id and title.")
    if not _SLUG.fullmatch(document_id):
        raise DocumentFormatError("id must be a lowercase slug (letters, numbers, hyphens).")
    return document_id, title, body


def split_long_section(text: str) -> list[str]:
    """Split on blank lines so each part is at most MAX_CHUNK_CHARS. No overlap."""
    stripped = text.strip()
    if len(stripped) <= MAX_CHUNK_CHARS:
        return [stripped]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", stripped) if part.strip()]
    parts: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            parts.append("\n\n".join(current))
            current.clear()

    for paragraph in paragraphs:
        pieces = (
            [
                paragraph[index : index + MAX_CHUNK_CHARS]
                for index in range(0, len(paragraph), MAX_CHUNK_CHARS)
            ]
            if len(paragraph) > MAX_CHUNK_CHARS
            else [paragraph]
        )
        for piece in pieces:
            candidate = "\n\n".join([*current, piece]) if current else piece
            if current and len(candidate) > MAX_CHUNK_CHARS:
                flush()
            current.append(piece)
    flush()
    return parts


def chunk_markdown(document_id: str, title: str, body: str) -> list[ChunkDraft]:
    sections: list[tuple[str, str, str]] = []
    stack: list[tuple[int, str]] = []
    heading = title
    path = title
    buffer: list[str] = []

    def flush() -> None:
        content = "\n".join(buffer).strip()
        buffer.clear()
        if content:
            sections.append((heading, path, content))

    for line in body.split("\n"):
        match = _HEADING.match(line)
        if match is None:
            buffer.append(line)
            continue
        flush()
        level = len(match.group(1))
        heading_text = match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, heading_text))
        heading = heading_text
        path = " / ".join(item for _, item in stack)

    flush()

    drafts: list[ChunkDraft] = []
    for section_heading, section_path, content in sections:
        for part in split_long_section(content):
            ordinal = len(drafts)
            drafts.append(
                ChunkDraft(
                    id=f"{document_id}/{ordinal}",
                    document_id=document_id,
                    section_heading=section_heading,
                    section_path=section_path,
                    ordinal=ordinal,
                    content=part,
                    content_hash=content_hash(part),
                )
            )
    return drafts


def parse_document(text: str, source_path: str) -> ParsedDocument:
    normalized = normalize_newlines(text)
    document_id, title, body = parse_front_matter(normalized)
    return ParsedDocument(
        id=document_id,
        title=title,
        source_path=source_path,
        raw_text=normalized,
        content_hash=content_hash(normalized),
        chunks=chunk_markdown(document_id, title, body),
    )


def load_documents(directory: Path, root: Path) -> list[ParsedDocument]:
    paths = sorted(path for path in directory.glob("*.md") if path.is_file())
    if not paths:
        raise DocumentFormatError(f"No Markdown documents in {directory}.")
    documents: list[ParsedDocument] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        documents.append(parse_document(text, source_path=relative))
    ids = [document.id for document in documents]
    duplicates = sorted({document_id for document_id in ids if ids.count(document_id) > 1})
    if duplicates:
        raise DocumentFormatError(f"Duplicate document id: {', '.join(duplicates)}.")
    return documents
