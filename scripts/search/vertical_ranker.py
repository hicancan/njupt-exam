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
    
    # Adjust weights based on vertical
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
        
        # Candidate Gating Tier
        tier = "C"
        is_exact_title = understood["normalized_query"].lower() in doc_title.lower()
        
        if doc_domain in target_domains or doc_source in preferred_sources or doc_channel in preferred_channels or is_exact_title:
            tier = "A"
        elif understood["target_domains"] and doc_domain in understood["target_domains"]:
            tier = "B"
            
        # Hard blocks for top 5 (simulated by massive penalty if tier is C or blocked)
        is_blocked_for_top5 = False
        if doc_domain in blocked_domains and not is_exact_title:
            is_blocked_for_top5 = True
        if doc_source in blocked_sources and not is_exact_title:
            is_blocked_for_top5 = True
        if not allow_resource and document.get("source_type") == "github_resource":
            is_blocked_for_top5 = True
            
        # Apply tier and block penalties
        if is_blocked_for_top5:
            total *= 0.1 # Heavily penalize, effectively pushing it out of top 5 unless nothing else matches
            components["block_penalty"] = 0.9
            
        if tier == "C":
            total *= 0.5 # Tier C is fallback
            
        scored_results.append({
            **document,
            "score": round(total, 6),
            "tier": tier,
            "is_blocked_for_top5": is_blocked_for_top5,
            "score_components": components,
            "score_reason": build_chinese_reason(document, components, route, tier, is_blocked_for_top5),
        })
        
    scored_results.sort(key=lambda item: (
        0 if item["is_blocked_for_top5"] else 1,
        2 if item["tier"] == "A" else (1 if item["tier"] == "B" else 0),
        item["score"],
        item.get("published_at") or ""
    ), reverse=True)
    
    return scored_results[:limit] if limit else scored_results

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
