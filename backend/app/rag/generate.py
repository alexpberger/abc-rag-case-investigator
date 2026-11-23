"""Grounded generation. One schema retry, then the caller returns 502."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import get_settings
from app.rag.citations import filter_citation_ids
from app.rag.embeddings import get_openai_client
from app.rag.retrieve import ASK_K, RetrievedChunk, retrieve, retrieve_investigation
from app.schemas import (
    AskDraft,
    AskRequest,
    AskResponse,
    Citation,
    EvidenceDraft,
    EvidenceItem,
    InvestigationDraft,
    InvestigationReport,
)

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 6

SYSTEM_RULES = """You are an investigation assistant for one fictional personal-loan file at Example Bank.

You organise evidence for a human case worker. You are not a lender, and you are not an automated credit decision-maker.

Rules:
- Use only the case brief and the source chunks in the user message. Do not add outside knowledge about lending, credit scoring, or affordability formulas.
- citation ids must be copied from the chunks you were given, from the lines that start with [chunk_id: ...]. Never invent an id.
- Do not say the loan should be approved, declined, granted, or refused. Do not recommend a lending outcome.
- If the chunks conflict, or if they leave a material gap, leave that question unresolved.
- A human lender at Example Bank makes the lending decision. You only describe what the file does and does not establish.
- determination must be "insufficient_evidence" when the chunks do not establish that documented income, employment tenure, and obligations are present and consistent with the application. Use "not_determined" only when the chunks are not about that question.
- Write the summary from the chunks. Do not assume a verdict that those chunks do not support.
"""


class GenerationError(RuntimeError):
    """The chat deployment did not return schema-valid JSON after one retry."""


def load_case_brief() -> str:
    path: Path = get_settings().resolved_knowledge_dir() / "case-brief.md"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def format_chunks(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no chunks retrieved)"
    blocks: list[str] = []
    for chunk in chunks:
        blocks.append(
            "\n".join(
                [
                    f"[chunk_id: {chunk.id}]",
                    f"Document: {chunk.document_title} ({chunk.document_id})",
                    f"Section: {chunk.section_path}",
                    chunk.content,
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def format_history(history: list) -> str:
    if not history:
        return "(no earlier turns)"
    return "\n".join(f"{turn.role}: {turn.content}" for turn in history)


def _complete(messages: list[dict], response_model: type):
    client = get_openai_client()
    settings = get_settings()
    feedback: str | None = None
    last_error = "The model did not return a valid response."
    for _ in range(2):
        attempt = list(messages)
        if feedback:
            attempt.append({"role": "user", "content": feedback})
        try:
            completion = client.chat.completions.parse(
                model=settings.azure_openai_chat_deployment,
                messages=attempt,
                response_format=response_model,
                temperature=0.2,
            )
        except Exception as exc:
            last_error = str(exc)
            logger.warning("chat completion failed: %s", last_error)
            feedback = (
                "The previous call failed. Return only a JSON object that matches the schema. "
                f"Error: {last_error[:1500]}"
            )
            continue
        message = completion.choices[0].message
        if message.parsed is not None:
            return message.parsed
        last_error = message.refusal or message.content or "empty response"
        logger.warning("chat completion was not valid schema JSON")
        feedback = (
            "The previous response did not match the schema. Return only valid JSON. "
            f"Problem: {str(last_error)[:1500]}"
        )
    raise GenerationError(last_error)


def citation_from_chunk(chunk: RetrievedChunk) -> Citation:
    return Citation(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        document_title=chunk.document_title,
        section_path=chunk.section_path,
        content=chunk.content,
    )


def _ground_items(
    items: list[EvidenceDraft],
    allowed_ids: set[str],
    used: list[str],
) -> list[EvidenceItem]:
    grounded: list[EvidenceItem] = []
    for item in items:
        citation_ids = filter_citation_ids(item.citation_ids, allowed_ids)
        used.extend(citation_ids)
        grounded.append(EvidenceItem(statement=item.statement, citation_ids=citation_ids))
    return grounded


def _unique(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for citation_id in ids:
        if citation_id not in seen:
            seen.add(citation_id)
            ordered.append(citation_id)
    return ordered


def ground_investigation(
    draft: InvestigationDraft,
    chunks: list[RetrievedChunk],
) -> InvestigationReport:
    allowed_ids = {chunk.id for chunk in chunks}
    by_id = {chunk.id: chunk for chunk in chunks}
    used: list[str] = []
    supporting = _ground_items(draft.supporting_evidence, allowed_ids, used)
    contradicting = _ground_items(draft.contradicting_evidence, allowed_ids, used)
    policy = _ground_items(draft.policy_and_guidelines, allowed_ids, used)
    citations = [citation_from_chunk(by_id[citation_id]) for citation_id in _unique(used)]
    return InvestigationReport(
        summary=draft.summary,
        determination=draft.determination,
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        policy_and_guidelines=policy,
        missing_information=list(draft.missing_information),
        recommended_steps=list(draft.recommended_steps),
        citations=citations,
    )


def ground_answer(draft: AskDraft, chunks: list[RetrievedChunk]) -> AskResponse:
    allowed_ids = {chunk.id for chunk in chunks}
    by_id = {chunk.id: chunk for chunk in chunks}
    citation_ids = filter_citation_ids(draft.citation_ids, allowed_ids)
    return AskResponse(
        answer=draft.answer,
        citations=[citation_from_chunk(by_id[citation_id]) for citation_id in citation_ids],
    )


def run_investigation() -> InvestigationReport:
    brief = load_case_brief()
    chunks = retrieve_investigation()
    logger.info("investigation retrieved %s chunks", len(chunks))
    messages = [
        {"role": "system", "content": SYSTEM_RULES},
        {
            "role": "user",
            "content": (
                "Prepare a structured investigation report.\n\n"
                f"Case brief:\n{brief}\n\n"
                f"Source chunks:\n{format_chunks(chunks)}\n\n"
                "Fill supporting_evidence with observations that tend to support the application.\n"
                "Fill contradicting_evidence with concerns, risks, or inconsistencies in the file.\n"
                "Fill policy_and_guidelines with the credit policy terms and case-worker rules that govern this question.\n"
                "List missing_information and recommended_steps only when the chunks support them.\n"
                "Cite chunk ids on every evidence statement."
            ),
        },
    ]
    draft = _complete(messages, InvestigationDraft)
    return ground_investigation(draft, chunks)


def run_ask(request: AskRequest) -> AskResponse:
    brief = load_case_brief()
    history = request.history[-MAX_HISTORY_TURNS:]
    chunks = retrieve(request.question, k=ASK_K)
    logger.info("follow-up retrieved %s chunks", len(chunks))
    messages = [
        {"role": "system", "content": SYSTEM_RULES},
        {
            "role": "user",
            "content": (
                "Answer the case worker's question from the source chunks.\n\n"
                f"Case brief:\n{brief}\n\n"
                f"Earlier turns:\n{format_history(history)}\n\n"
                f"Question:\n{request.question}\n\n"
                f"Source chunks:\n{format_chunks(chunks)}\n\n"
                "Answer only what the chunks support. Cite the chunk ids you used. "
                "Do not decide the loan."
            ),
        },
    ]
    draft = _complete(messages, AskDraft)
    return ground_answer(draft, chunks)
