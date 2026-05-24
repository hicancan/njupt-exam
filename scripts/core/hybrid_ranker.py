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
    field_weights = (ranking_weights or {}).get("field_weights", {})
    understood = understand_query(query, query_aliases)
    query_type = understood.get("query_type", "general")
    
    base_weights = {**DEFAULT_WEIGHTS, **((ranking_weights or {}).get("weights", ranking_weights or {}))}
    if query_type == "task":
        base_weights["entity"] += 0.05
        base_weights["semantic_expansion"] += 0.05
    elif query_type == "exam":
        base_weights["entity"] += 0.1
        base_weights["field"] += 0.1
    elif query_type == "resource":
        base_weights["tag"] += 0.1
        base_weights["semantic_expansion"] += 0.05
        
    weights = base_weights
    
    query_tokens = tokenize_text(" ".join([understood["normalized_query"], *understood.get("aliases", []), *understood.get("semantic_queries", [])]))
    bm25 = bm25_scores(query_tokens, hybrid_index)
    doc_lookup = {str(document.get("id")): document for document in documents}
    results: list[dict[str, Any]] = []
    for doc_id, document in doc_lookup.items():
        index_payload = (hybrid_index.get("documents") or {}).get(doc_id, {})
        components = score_components(document, index_payload, understood, bm25.get(doc_id, 0.0), field_weights)
        total = (
            weights["bm25"] * components["bm25"]
            + weights["field"] * components["field"]
            + weights["tag"] * components["tag"]
            + weights["entity"] * components["entity"]
            + weights["semantic_expansion"] * components["semantic_expansion"]
            + weights["utility"] * components["utility"]
            - weights["risk_penalty"] * components["risk_penalty"]
        )
        if total <= 0:
            continue
        results.append({
            **document,
            "score": round(total, 6),
            "score_components": components,
            "score_reason": build_reason(document, components),
        })
    results.sort(key=lambda item: (item["score"], item.get("published_at") or ""), reverse=True)
    return results[:limit] if limit else results


def score_components(
    document: dict[str, Any],
    index_payload: dict[str, Any],
    understood: dict[str, Any],
    bm25_raw: float,
    field_weights: dict[str, Any],
) -> dict[str, float]:
    query_text = " ".join([
        understood["normalized_query"],
        *understood.get("aliases", []),
        *understood.get("semantic_queries", []),
    ]).lower()
    fields = index_payload.get("fields", {})
    field_score = 0.0
    max_field = 0.0
    for field, value in fields.items():
        weight = float(field_weights.get(field, 1.0) or 1.0)
        max_field += weight
        text = str(value).lower()
        if understood["normalized_query"].lower() and understood["normalized_query"].lower() in text:
            field_score += weight
        else:
            field_score += weight * token_overlap(query_text, text)
    target_domains = set(understood.get("target_domains", []))
    target_intents = set(understood.get("target_intents", []))
    domain_score = 1.0 if str(document.get("domain")) in target_domains else 0.0
    intent_score = 1.0 if str(document.get("intent")) in target_intents else 0.0
    tag_score = token_overlap(query_text, " ".join(str(item) for item in document.get("tags", [])))
    semantic_score = token_overlap(query_text, " ".join(str(item) for item in document.get("evidence", [])))
    utility = utility_score(document)
    risk_penalty = risk_penalty_score(document)
    return {
        "bm25": min(1.0, bm25_raw / 8),
        "field": min(1.0, field_score / max(max_field, 1.0)),
        "tag": tag_score,
        "entity": max(domain_score, intent_score, token_overlap(query_text, str(document.get("source") or ""))),
        "semantic_expansion": semantic_score,
        "utility": utility,
        "risk_penalty": risk_penalty,
    }


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


def build_reason(document: dict[str, Any], components: dict[str, float]) -> str:
    lead = f"{document.get('source', '')} · {document.get('channel', '')}".strip(" ·")
    ranked = sorted(components.items(), key=lambda item: item[1], reverse=True)[:3]
    detail_parts = []
    for name, value in ranked:
        if value > 0.01:
            detail_parts.append(f"{name}:{value:.2f}")
    detail = " / ".join(detail_parts)
    return f"{lead} · {detail}" if detail else lead
