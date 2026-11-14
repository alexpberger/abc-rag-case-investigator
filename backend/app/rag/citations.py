"""Drop citation ids the model was not given. Statements stay even if nothing remains."""

from __future__ import annotations


def filter_citation_ids(citation_ids: list[str], allowed_ids: set[str]) -> list[str]:
    kept: list[str] = []
    seen: set[str] = set()
    for citation_id in citation_ids:
        if citation_id in allowed_ids and citation_id not in seen:
            kept.append(citation_id)
            seen.add(citation_id)
    return kept
