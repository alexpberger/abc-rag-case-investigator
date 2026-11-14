from app.rag.retrieve import RetrievedChunk, merge_retrieved


def _chunk(chunk_id: str, distance: float) -> RetrievedChunk:
    return RetrievedChunk(
        id=chunk_id,
        document_id=chunk_id.split("/")[0],
        document_title="Doc",
        section_heading="Section",
        section_path="Section",
        content="body",
        distance=distance,
    )


def test_merge_keeps_the_closer_hit_and_caps_the_list():
    groups = [
        [_chunk("a/0", 0.4), _chunk("a/1", 0.2)],
        [_chunk("a/0", 0.1), _chunk("b/0", 0.3)],
    ]
    merged = merge_retrieved(groups, cap=2)
    assert [(chunk.id, chunk.distance) for chunk in merged] == [("a/0", 0.1), ("a/1", 0.2)]


def test_merge_breaks_distance_ties_by_id():
    groups = [[_chunk("b/0", 0.2), _chunk("a/0", 0.2)]]
    merged = merge_retrieved(groups, cap=5)
    assert [chunk.id for chunk in merged] == ["a/0", "b/0"]
