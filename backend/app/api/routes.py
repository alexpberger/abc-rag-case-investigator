"""HTTP routes. Generation stays behind require_retrieval_ready."""

from __future__ import annotations

import logging

import psycopg
from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.db import count_chunks, database_ok, fetch_chunks
from app.rag.chunk import DocumentFormatError, load_documents
from app.rag.embeddings import EmbeddingError
from app.rag.generate import GenerationError, load_case_brief, run_ask, run_investigation
from app.schemas import (
    AskRequest,
    AskResponse,
    CaseResponse,
    ChunkDetail,
    ChunkRef,
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
    InvestigationReport,
    SectionInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter()

INGEST_COMMAND = "python -m app.rag.ingest"


def missing_azure() -> list[str]:
    return get_settings().missing_azure_env()


def ingestion_status() -> str:
    """ready, empty, or unavailable."""
    try:
        count = count_chunks()
    except Exception:
        logger.warning("could not count chunks", exc_info=True)
        return "unavailable"
    return "ready" if count else "empty"


def require_retrieval_ready() -> None:
    missing = missing_azure()
    if missing:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "azure_not_configured",
                "missing": missing,
                "message": "Azure OpenAI is not configured. Set the listed variables in .env.",
            },
        )
    status = ingestion_status()
    if status == "unavailable":
        raise HTTPException(
            status_code=503,
            detail={
                "error": "database_unavailable",
                "message": "PostgreSQL is not reachable. Start it with docker compose up -d postgres.",
            },
        )
    if status == "empty":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "knowledge_base_not_ingested",
                "command": INGEST_COMMAND,
                "message": "The knowledge base has not been ingested.",
            },
        )


def _source_documents():
    knowledge = get_settings().resolved_knowledge_dir()
    try:
        return load_documents(knowledge / "documents", knowledge.parent)
    except DocumentFormatError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "knowledge_base_invalid", "message": str(exc)},
        ) from exc


def _sections(document) -> list[SectionInfo]:
    return [
        SectionInfo(ordinal=chunk.ordinal, heading=chunk.section_heading, section_path=chunk.section_path)
        for chunk in document.chunks
    ]


@router.get("/health")
def health() -> dict[str, str]:
    if not database_ok():
        raise HTTPException(
            status_code=503,
            detail={"status": "degraded", "database": "unavailable"},
        )
    return {"status": "ok", "database": "ok"}


@router.get("/case", response_model=CaseResponse)
def get_case() -> CaseResponse:
    try:
        markdown = load_case_brief()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "case_brief_missing", "message": "knowledge/case-brief.md is missing."},
        ) from exc
    return CaseResponse(markdown=markdown)


@router.get("/documents", response_model=DocumentListResponse)
def list_documents() -> DocumentListResponse:
    documents = _source_documents()
    stored = fetch_chunks()
    grouped: dict[str, list[ChunkRef]] = {}
    if stored is not None:
        for row in stored:
            grouped.setdefault(row["document_id"], []).append(
                ChunkRef(
                    id=row["id"],
                    section_heading=row["section_heading"],
                    section_path=row["section_path"],
                    ordinal=row["ordinal"],
                )
            )
    summaries = [
        DocumentSummary(
            id=document.id,
            title=document.title,
            source_path=document.source_path,
            sections=_sections(document),
            chunks=grouped.get(document.id, []),
        )
        for document in documents
    ]
    return DocumentListResponse(documents=summaries, database_available=stored is not None)


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str) -> DocumentDetail:
    documents = {document.id: document for document in _source_documents()}
    document = documents.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Document not found."})
    stored = fetch_chunks(document_id)
    chunks = []
    if stored is not None:
        chunks = [
            ChunkDetail(
                id=row["id"],
                section_heading=row["section_heading"],
                section_path=row["section_path"],
                ordinal=row["ordinal"],
                content=row["content"],
            )
            for row in stored
        ]
    return DocumentDetail(
        id=document.id,
        title=document.title,
        source_path=document.source_path,
        markdown=document.raw_text,
        sections=_sections(document),
        chunks=chunks,
        database_available=stored is not None,
    )


def _generation_error(exc: Exception) -> HTTPException:
    if isinstance(exc, psycopg.Error):
        return HTTPException(
            status_code=503,
            detail={
                "error": "database_unavailable",
                "message": "PostgreSQL is not reachable.",
            },
        )
    if isinstance(exc, EmbeddingError):
        logger.exception("embedding failed")
        return HTTPException(
            status_code=502,
            detail={
                "error": "generation_failed",
                "message": "Embeddings could not be created.",
            },
        )
    logger.exception("generation failed")
    message = (
        "The model response did not match the investigation schema."
        if isinstance(exc, GenerationError)
        else "The response could not be generated."
    )
    return HTTPException(
        status_code=502,
        detail={"error": "generation_failed", "message": message},
    )


@router.post("/investigate", response_model=InvestigationReport)
def investigate() -> InvestigationReport:
    require_retrieval_ready()
    try:
        return run_investigation()
    except Exception as exc:
        raise _generation_error(exc) from exc


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    require_retrieval_ready()
    try:
        return run_ask(request)
    except Exception as exc:
        raise _generation_error(exc) from exc
