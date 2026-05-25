from typing import Any

from core.bm25_indexer import bm25_scores, tokenize_text
from core.query_expander import understand_query


DEFAULT_WEIGHTS = {
    "bm25": 0.26,
    "field": 0.22,
    "tag": 0.15,
    "entity": 0.10,
    "semantic_expansion": 0.12,
    "utility": 0.20,
    "risk_penalty": 0.05,
}


def rank_documents(
    query: str,
    documents: list[dict[str, Any]],
    hybrid_index: dict[str, Any],
    query_aliases: dict[str, Any],
    ranking_weights: dict[str, Any] | None = None,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    from search.vertical_ranker import vertical_rank_documents
    return vertical_rank_documents(query, documents, hybrid_index, query_aliases, ranking_weights, limit=limit)


def token_overlap(query_text: str, candidate_text: str) -> float:
    query_tokens = set(tokenize_text(query_text))
    if not query_tokens:
        return 0.0
    candidate_tokens = set(tokenize_text(candidate_text))
    if not candidate_tokens:
        return 0.0
    return len(query_tokens & candidate_tokens) / len(query_tokens)


def utility_score(document: dict[str, Any]) -> float:
    student = float(document.get("student_score", 0) or 0)
    importance = float(document.get("importance_score", 0) or 0)
    source = float(document.get("source_weight", 0.7) or 0.7)
    task_bonus = 0.08 if document.get("task_frames") else 0.0
    lifecycle = str(document.get("lifecycle") or "")
    lifecycle_bonus = 0.08 if lifecycle in {"active", "upcoming"} else (-0.08 if lifecycle == "expired" else 0.0)
    base = 0.42 * student + 0.30 * importance + 0.20 * source + task_bonus + lifecycle_bonus
    if str(document.get("source_type")) == "github_resource":
        base = 0.82 * base
    return max(0.0, min(1.0, base))


def risk_penalty_score(document: dict[str, Any]) -> float:
    penalty = 0.0
    if document.get("sensitive"):
        penalty += 0.5
    if document.get("review_required"):
        penalty += 0.25
    if document.get("status") == "restricted":
        penalty += 0.5
    if document.get("lifecycle") == "expired":
        penalty += 0.2
    return min(1.0, penalty)
