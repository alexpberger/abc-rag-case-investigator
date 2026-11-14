from app.rag.citations import filter_citation_ids
from app.rag.generate import ground_answer, ground_investigation
from app.rag.retrieve import RetrievedChunk
from app.schemas import AskDraft, EvidenceDraft, InvestigationDraft


def _chunk(chunk_id: str, distance: float = 0.1) -> RetrievedChunk:
    document_id, _ordinal = chunk_id.split("/")
    return RetrievedChunk(
        id=chunk_id,
        document_id=document_id,
        document_title=document_id,
        section_heading="Section",
        section_path="Section",
        content=f"content of {chunk_id}",
        distance=distance,
    )


def test_filter_drops_unknown_ids_and_keeps_known_ones_in_order():
    allowed = {"policy/0", "policy/1"}
    assert filter_citation_ids(
        ["missing/0", "policy/1", "policy/1", "policy/0", "also-missing"],
        allowed,
    ) == ["policy/1", "policy/0"]


def test_filter_keeps_statement_when_every_id_is_unknown():
    draft = InvestigationDraft(
        summary="The file does not settle the cause.",
        determination="insufficient_evidence",
        supporting_evidence=[
            EvidenceDraft(statement="The customer described a sudden leak.", citation_ids=["nope/0"])
        ],
        contradicting_evidence=[],
        policy_and_guidelines=[
            EvidenceDraft(
                statement="Sudden discharge is covered.",
                citation_ids=["policy/0", "invented/9"],
            )
        ],
        missing_information=["Maintenance history"],
        recommended_steps=["Ask for the pipe age"],
    )
    report = ground_investigation(draft, [_chunk("policy/0")])
    assert report.supporting_evidence[0].statement == "The customer described a sudden leak."
    assert report.supporting_evidence[0].citation_ids == []
    assert report.policy_and_guidelines[0].citation_ids == ["policy/0"]
    assert [citation.chunk_id for citation in report.citations] == ["policy/0"]
    assert report.summary == draft.summary
    assert report.determination == "insufficient_evidence"


def test_citations_are_deduped_in_first_seen_order():
    draft = InvestigationDraft(
        summary="Summary from the model.",
        determination="not_determined",
        supporting_evidence=[
            EvidenceDraft(statement="First.", citation_ids=["policy/1", "policy/0"])
        ],
        contradicting_evidence=[
            EvidenceDraft(statement="Second.", citation_ids=["policy/0", "plumber/0"])
        ],
        policy_and_guidelines=[],
        missing_information=[],
        recommended_steps=[],
    )
    chunks = [_chunk("policy/0"), _chunk("policy/1"), _chunk("plumber/0")]
    report = ground_investigation(draft, chunks)
    assert [citation.chunk_id for citation in report.citations] == [
        "policy/1",
        "policy/0",
        "plumber/0",
    ]


def test_answer_citations_drop_ids_that_were_not_retrieved():
    response = ground_answer(
        AskDraft(answer="The adjuster decides.", citation_ids=["policy/2", "missing/1"]),
        [_chunk("policy/2")],
    )
    assert response.answer == "The adjuster decides."
    assert [citation.chunk_id for citation in response.citations] == ["policy/2"]
    assert response.citations[0].content == "content of policy/2"
