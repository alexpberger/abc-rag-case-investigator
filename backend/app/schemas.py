"""API models and the JSON shapes requested from the chat deployment."""

from typing import Literal

from pydantic import BaseModel, Field


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[HistoryTurn] = Field(default_factory=list, max_length=20)


class EvidenceDraft(BaseModel):
    statement: str
    citation_ids: list[str]


class InvestigationDraft(BaseModel):
    """Model output. The enum cannot express a pay or deny decision."""

    summary: str
    determination: Literal["insufficient_evidence", "not_determined"]
    supporting_evidence: list[EvidenceDraft]
    contradicting_evidence: list[EvidenceDraft]
    policy_and_guidelines: list[EvidenceDraft]
    missing_information: list[str]
    recommended_steps: list[str]


class AskDraft(BaseModel):
    answer: str
    citation_ids: list[str]


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    section_path: str
    content: str


class EvidenceItem(BaseModel):
    statement: str
    citation_ids: list[str]


class InvestigationReport(BaseModel):
    summary: str
    determination: Literal["insufficient_evidence", "not_determined"]
    supporting_evidence: list[EvidenceItem]
    contradicting_evidence: list[EvidenceItem]
    policy_and_guidelines: list[EvidenceItem]
    missing_information: list[str]
    recommended_steps: list[str]
    citations: list[Citation]


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]


class SectionInfo(BaseModel):
    ordinal: int
    heading: str
    section_path: str


class ChunkRef(BaseModel):
    id: str
    section_heading: str
    section_path: str
    ordinal: int


class ChunkDetail(ChunkRef):
    content: str


class DocumentSummary(BaseModel):
    id: str
    title: str
    source_path: str
    sections: list[SectionInfo]
    chunks: list[ChunkRef]


class DocumentDetail(BaseModel):
    id: str
    title: str
    source_path: str
    markdown: str
    sections: list[SectionInfo]
    chunks: list[ChunkDetail]
    database_available: bool


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]
    database_available: bool


class CaseResponse(BaseModel):
    markdown: str
