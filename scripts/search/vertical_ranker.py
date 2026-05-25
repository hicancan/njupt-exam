import os
from typing import Any, Dict, List

from core.bm25_indexer import bm25_scores, tokenize_text
from core.query_expander import understand_query
from core.hybrid_ranker import token_overlap
from search.query_router import route_query, load_query_routes

DEFAULT_WEIGHTS = {
    "bm25": 0.26,
    "field": 0.22,
    "tag": 0.15,
    "entity": 0.10,
    "semantic_expansion": 0.12,
    "utility": 0.20,
    "risk_penalty": 0.05,
}

ROUTES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "query_routes.json")
_cached_routes = None

def get_routes():
    global _cached_routes
    if _cached_routes is None:
        _cached_routes = load_query_routes(ROUTES_PATH)
    return _cached_routes


def vertical_rank_documents(
    query: str,
    documents: List[Dict[str, Any]],
    hybrid_index: Dict[str, Any],
    query_aliases: Dict[str, Any],
    ranking_weights: Dict[str, Any] | None = None,
    *,
    limit: int | None = None,
) -> List[Dict[str, Any]]:
    routes = get_routes()
    route = route_query(query, routes)
    understood = understand_query(query, query_aliases)
    
    field_weights = (ranking_weights or {}).get("field_weights", {})
    base_weights = {**DEFAULT_WEIGHTS, **((ranking_weights or {}).get("weights", ranking_weights or {}))}
    
    query_type = route.get("query_type", "general_search")
    
    if query_type == "class_exam_lookup":
        base_weights["entity"] += 0.3
        base_weights["field"] += 0.2
    elif query_type == "exam_notice_search":
        base_weights["entity"] += 0.2
    elif query_type == "degree_defense_search":
        base_weights["entity"] += 0.2
    elif query_type == "resource_search":
        base_weights["tag"] += 0.2
        base_weights["semantic_expansion"] += 0.1
    elif query_type == "innovation_project_search":
        base_weights["entity"] += 0.15
        
    query_tokens = tokenize_text(" ".join([understood["normalized_query"], *understood.get("aliases", []), *understood.get("semantic_queries", [])]))
    bm25 = bm25_scores(query_tokens, hybrid_index)
    
    doc_lookup = {str(document.get("id")): document for document in documents}
    
    scored_results = []

    target_domains = set(route.get("target_domains", []))
    preferred_sources = set(route.get("preferred_sources", []))
    preferred_channels = set(route.get("preferred_channels", []))
    blocked_domains = set(route.get("blocked_domains_for_top5", []))
    blocked_sources = set(route.get("blocked_sources_for_top5", []))
    allow_resource = route.get("allow_resource_top5", True)

    bad_result_terms = route.get("bad_result_terms", [])
    must_include_terms = route.get("must_include_terms_for_top_results", [])
    top1_exact = route.get("top1_prefer_exact_title", False)

    # 4-bucket approach for degraded fallback
    strong: List[Dict[str, Any]] = []   # Tier A
    weak: List[Dict[str, Any]] = []     # Tier B
    fallback: List[Dict[str, Any]] = [] # Tier C
    blocked_candidates: List[Dict[str, Any]] = []  # blocked but kept for backfill

    for doc_id, document in doc_lookup.items():
        index_payload = (hybrid_index.get("documents") or {}).get(doc_id, {})
        components = score_components_vertical(document, index_payload, understood, route, bm25.get(doc_id, 0.0), field_weights)

        total = (
            base_weights["bm25"] * components["bm25"]
            + base_weights["field"] * components["field"]
            + base_weights["tag"] * components["tag"]
            + base_weights["entity"] * components["entity"]
            + base_weights["semantic_expansion"] * components["semantic_expansion"]
            + base_weights["utility"] * components["utility"]
            - base_weights["risk_penalty"] * components["risk_penalty"]
        )

        if total <= 0:
            continue

        doc_domain = str(document.get("domain", ""))
        doc_source = str(document.get("source", ""))
        doc_channel = str(document.get("channel", ""))
        doc_title = str(document.get("title", ""))
        doc_content = str(document.get("content", ""))
        doc_text = (doc_title + " " + doc_content).lower()

        tier = "C"
        is_exact_title = understood["normalized_query"].lower() in doc_title.lower()

        # class_exam_lookup: also match class_name field for "B250403 高数" style queries
        if not is_exact_title and route.get("query_type") == "class_exam_lookup" and top1_exact:
            doc_class = str(document.get("class_name", "")).lower()
            if doc_class:
                for word in understood["normalized_query"].lower().split():
                    if len(word) >= 7 and word in doc_class:
                        is_exact_title = True
                        break

        if top1_exact and is_exact_title:
            tier = "A"
            total += 10.0
            # class_exam_lookup: ensure exam_vertical docs rank top1
            if route.get("query_type") == "class_exam_lookup" and document.get("source_id") == "exam_vertical":
                total += 20.0
        elif doc_domain in target_domains or doc_source in preferred_sources or doc_channel in preferred_channels or is_exact_title:
            tier = "A"
        elif understood["target_domains"] and doc_domain in understood["target_domains"]:
            tier = "B"

        is_blocked_for_top5 = False
        if doc_domain in blocked_domains and not is_exact_title:
            is_blocked_for_top5 = True
        if doc_source in preferred_sources or document.get("source_id") in preferred_sources:
            components["source_boost"] = 1.25
            total *= 1.25
            if route.get("id") == "class_exam_lookup":
                components["source_boost"] = 10.0
                total *= 10.0
                tier = "A"
        if (doc_source in blocked_sources or document.get("source_id") in blocked_sources) and not is_exact_title:
            is_blocked_for_top5 = True
        if not allow_resource and document.get("source_type") == "github_resource":
            is_blocked_for_top5 = True

        if any(bt.lower() in doc_text for bt in bad_result_terms):
            is_blocked_for_top5 = True

        if must_include_terms:
            if not any(mt.lower() in doc_text for mt in must_include_terms):
                is_blocked_for_top5 = True

        if tier == "C":
            total *= 0.5

        result_entry = {
            **document,
            "score": round(total, 6),
            "tier": tier,
            "is_blocked_for_top5": is_blocked_for_top5,
            "score_components": components,
            "score_reason": build_chinese_reason(document, components, route, tier, is_blocked_for_top5),
            "degraded_fallback": False,
        }

        if is_blocked_for_top5:
            blocked_candidates.append(result_entry)
        elif tier == "A":
            strong.append(result_entry)
        elif tier == "B":
            weak.append(result_entry)
        else:
            fallback.append(result_entry)

    # Sort each bucket by score descending
    sort_key = lambda item: (item["score"], item.get("published_at") or "")
    strong.sort(key=sort_key, reverse=True)
    weak.sort(key=sort_key, reverse=True)
    fallback.sort(key=sort_key, reverse=True)
    blocked_candidates.sort(key=sort_key, reverse=True)

    # Assemble: strong -> weak -> fallback -> blocked (backfill only when needed)
    final_limit = limit if limit is not None else len(doc_lookup)

    scored_results = _take(strong, final_limit)
    if len(scored_results) < final_limit:
        scored_results += _take(weak, final_limit - len(scored_results))
    if len(scored_results) < final_limit:
        scored_results += _take(fallback, final_limit - len(scored_results))
    if len(scored_results) < final_limit:
        for doc in _take(blocked_candidates, final_limit - len(scored_results)):
            doc["degraded_fallback"] = True
            doc["score_reason"] += "，目标候选不足，作为降级补位"
            scored_results.append(doc)

    return scored_results


def _take(items: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    return items[:n]


def score_components_vertical(
    document: Dict[str, Any],
    index_payload: Dict[str, Any],
    understood: Dict[str, Any],
    route: Dict[str, Any],
    bm25_raw: float,
    field_weights: Dict[str, Any],
) -> Dict[str, float]:
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
            
    target_domains = set(route.get("target_domains", []) + understood.get("target_domains", []))
    preferred_sources = set(route.get("preferred_sources", []))
    target_intents = set(route.get("target_intents", []) + understood.get("target_intents", []))
    
    doc_domain = str(document.get("domain", ""))
    doc_source = str(document.get("source", ""))
    doc_intent = str(document.get("intent", ""))
    
    domain_score = 1.0 if doc_domain in target_domains else 0.0
    intent_score = 1.0 if doc_intent in target_intents else 0.0
    source_score = 1.0 if doc_source in preferred_sources else 0.0
    
    tag_score = token_overlap(query_text, " ".join(str(item) for item in document.get("tags", [])))
    semantic_score = token_overlap(query_text, " ".join(str(item) for item in document.get("evidence", [])))
    
    from core.hybrid_ranker import utility_score, risk_penalty_score
    utility = utility_score(document)
    risk_penalty = risk_penalty_score(document)
    
    return {
        "bm25": min(1.0, bm25_raw / 8),
        "field": min(1.0, field_score / max(max_field, 1.0)),
        "tag": tag_score,
        "entity": max(domain_score, intent_score, source_score, token_overlap(query_text, doc_source)),
        "semantic_expansion": semantic_score,
        "utility": utility,
        "risk_penalty": risk_penalty,
    }

def build_chinese_reason(document: Dict[str, Any], components: Dict[str, float], route: Dict[str, Any], tier: str, is_blocked: bool) -> str:
    source = document.get('source', '未知来源')
    domain = document.get('domain', '未知领域')
    route_name = route.get('query_type', '通用查询')
    
    reason = f"命中意图【{route_name}】；"
    reason += f"来源为 {source}，领域为 {domain}。"
    
    if is_blocked:
        reason += f" (由于来源或领域不符合意图预期，已被大幅降权)"
    elif tier == "C":
        reason += f" (仅由于关键词弱匹配成为候选，已降权)"
    elif tier == "A":
        reason += f" (强匹配候选)"
        
    if components.get("risk_penalty", 0) > 0.2:
        reason += " (包含风险降权)"
        
    return reason
