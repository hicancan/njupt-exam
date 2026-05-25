import math
import os
import re
from datetime import datetime, timezone
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
    return _rank_documents_frontend_compatible(query, documents, hybrid_index, query_aliases, ranking_weights or {}, limit=limit)


def _rank_documents_frontend_compatible(
    query: str,
    documents: List[Dict[str, Any]],
    hybrid_index: Dict[str, Any],
    query_aliases: Dict[str, Any],
    ranking_weights: Dict[str, Any],
    *,
    limit: int | None = None,
) -> List[Dict[str, Any]]:
    routes = get_routes()
    route = route_query(query, routes)
    trimmed = str(query or "").strip()
    if len(trimmed) < 2:
        ranked = []
        for document in documents:
            score = (
                float(document.get("importance_score", 0) or 0)
                * intent_weight(str(document.get("intent", "")), ranking_weights)
                * lifecycle_weight(str(document.get("lifecycle", "")), ranking_weights)
                * source_type_weight(str(document.get("source_type", "")), ranking_weights)
                * deadline_urgency_weight(document.get("deadline"), ranking_weights)
            )
            ranked.append({**document, "score": round(score, 4), "score_reason": build_score_reason_ts(document)})
        ranked.sort(
            key=lambda item: (
                item["score"],
                date_sort_value(item.get("published_at")),
                float(item.get("importance_score", 0) or 0),
            ),
            reverse=True,
        )
        return ranked[: limit or 30]

    target_domains = set(route.get("target_domains", []) or [])
    target_intents = set(route.get("target_intents", []) or [])
    blocked_domains = set(route.get("blocked_domains_for_top5", []) or [])
    blocked_sources = set(route.get("blocked_sources_for_top5", []) or [])
    preferred_sources = set(route.get("preferred_sources", []) or [])
    allow_resource_top5 = route.get("allow_resource_top5", True)

    bad_result_terms = route.get("bad_result_terms", []) or []
    must_include_terms = route.get("must_include_terms_for_top_results", []) or []
    allow_blocked_fallback = bool(route.get("allow_blocked_fallback", True)) and not must_include_terms
    top1_exact = bool(route.get("top1_prefer_exact_title", False))
    hybrid_documents = (hybrid_index.get("documents") or {}) if hybrid_index else {}
    expanded_terms = alias_terms_for_query(trimmed, query_aliases)
    query_with_aliases = " ".join([trimmed, *expanded_terms])
    bm25_by_doc = bm25_scores(tokenize_text(query_with_aliases), hybrid_index or {}) if hybrid_index else {}

    candidates: List[Dict[str, Any]] = []
    for document in documents:
        doc_id = str(document.get("id", ""))
        text_score = score_text_match(document, trimmed, expanded_terms, ranking_weights)
        hybrid_payload = hybrid_documents.get(doc_id, {})
        terms = hybrid_payload.get("terms") or {}
        fields = hybrid_payload.get("fields") or {}
        bm25_proxy = min(1.0, float(bm25_by_doc.get(doc_id, 0.0)) / 8.0) if terms else text_score / 24
        field_score = score_hybrid_fields(fields, query_with_aliases, ranking_weights) if fields else min(1, text_score / 24)
        tag_score = overlap_score(query_with_aliases, " ".join(str(item) for item in document.get("tags", []) or []))
        task_text = " ".join(
            f"{frame.get('what', '')} {((frame.get('action') or {}).get('summary') or '')} "
            f"{' '.join(str(item.get('text', '')) for item in frame.get('evidence', []) or [])}"
            for frame in document.get("task_frames", []) or []
        )
        task_frame_score = overlap_score(query_with_aliases, task_text) if task_text else 0

        domain = normalize(str(document.get("domain", "")))
        intent = normalize(str(document.get("intent", "")))
        source = normalize(str(document.get("source", "")))
        source_id = normalize(str(document.get("source_id", "")))
        title = normalize(str(document.get("title", "")))
        content = normalize(str(document.get("content", "")))
        full_text = f"{title} {content}"

        is_exact_title = normalize(trimmed) in title
        if not is_exact_title and route.get("query_type") == "class_exam_lookup" and top1_exact:
            doc_class = str(document.get("class_name", "") or "").lower()
            if doc_class:
                for word in trimmed.lower().split():
                    if len(word) >= 7 and word in doc_class:
                        is_exact_title = True
                        break

        tier = "C"
        if top1_exact and is_exact_title:
            tier = "A"
        elif domain in target_domains and intent in target_intents:
            tier = "A"
        elif domain in target_domains or intent in target_intents or is_exact_title:
            tier = "B"
        elif not target_domains and not target_intents:
            tier = "A"

        is_blocked = False
        if (domain in blocked_domains or source in blocked_sources or source_id in blocked_sources) and not is_exact_title:
            is_blocked = True
        if not allow_resource_top5 and document.get("source_type") == "github_resource":
            is_blocked = True
        if any(normalize(str(term)) in full_text for term in bad_result_terms):
            is_blocked = True
        if must_include_terms and not any(normalize(str(term)) in full_text for term in must_include_terms):
            is_blocked = True

        if tier == "A":
            tier_multiplier = section_weight(ranking_weights, "tier_multipliers", "A", 2.0)
        elif tier == "B":
            tier_multiplier = section_weight(ranking_weights, "tier_multipliers", "B", 1.2)
        else:
            tier_multiplier = section_weight(ranking_weights, "tier_multipliers", "C", 0.1)

        source_boost = 1.0
        if source in preferred_sources or source_id in preferred_sources:
            source_boost = section_weight(ranking_weights, "source_boosts", "preferred", 1.25)
            if route.get("query_type") == "class_exam_lookup":
                source_boost = section_weight(ranking_weights, "source_boosts", "class_exam_lookup", 10.0)
                tier_multiplier = section_weight(ranking_weights, "tier_multipliers", "A", 2.0)
                tier = "A"

        raw_match_score = (
            section_weight(ranking_weights, "weights", "bm25", 0.26) * min(1, bm25_proxy)
            + section_weight(ranking_weights, "weights", "field", 0.22) * field_score
            + section_weight(ranking_weights, "weights", "tag", 0.15) * tag_score
            + section_weight(ranking_weights, "weights", "task_frame", 0.15) * max(task_frame_score, overlap_score(" ".join(expanded_terms), str(document.get("content", ""))))
        )
        has_match = text_score > 0 or raw_match_score > 0

        utility_score = (
            section_weight(ranking_weights, "utility_weights", "student_score", 0.42) * float(document.get("student_score", 0) or 0)
            + section_weight(ranking_weights, "utility_weights", "importance_score", 0.3) * float(document.get("importance_score", 0) or 0)
            + section_weight(ranking_weights, "utility_weights", "source_weight", 0.2) * float(document.get("source_weight", 0.8) or 0.8)
        )
        risk_penalty = (
            (section_weight(ranking_weights, "risk_penalties", "sensitive", 0.5) if document.get("sensitive") else 0)
            + (section_weight(ranking_weights, "risk_penalties", "review_required", 0.25) if document.get("review_required") else 0)
            + (section_weight(ranking_weights, "risk_penalties", "restricted", 0.5) if document.get("status") == "restricted" else 0)
        )
        utility_score = max(0, utility_score - risk_penalty)
        hybrid_score = (
            raw_match_score
            + section_weight(ranking_weights, "utility_weights", "utility_multiplier", 0.2) * min(1, utility_score)
            - section_weight(ranking_weights, "weights", "risk_penalty", 0.05) * min(1, risk_penalty)
            if has_match
            else 0
        )
        weighted_score = (
            (text_score + hybrid_score * 32)
            * source_boost
            * (0.55 + float(document.get("student_score", 0) or 0) * 0.45)
            * (0.72 + float(document.get("freshness_score", 0) or 0) * 0.28)
            * (0.7 + float(document.get("importance_score", 0) or 0) * 0.3)
            * intent_weight(str(document.get("intent", "")), ranking_weights)
            * lifecycle_weight(str(document.get("lifecycle", "")), ranking_weights)
            * source_type_weight(str(document.get("source_type", "")), ranking_weights)
            * deadline_urgency_weight(document.get("deadline"), ranking_weights)
            * tier_multiplier
            if has_match
            else 0
        )

        if top1_exact and is_exact_title:
            weighted_score += 10.0
            if route.get("query_type") == "class_exam_lookup" and document.get("source_id") == "exam_vertical":
                weighted_score += 20.0

        if weighted_score <= 0:
            continue

        components = {
            "bm25": min(1, bm25_proxy),
            "field": field_score,
            "tag": tag_score,
            "task_frame": task_frame_score,
            "utility": min(1, utility_score),
            "risk_penalty": min(1, risk_penalty),
            "tier": tier_multiplier,
        }
        result_entry = {
            **document,
            "score": round(weighted_score, 4),
            "score_reason": build_score_reason_ts(document, components) + f" [{tier}]",
            "is_blocked_for_top5": is_blocked,
            "tierCategory": tier,
            "score_components": {key: round(value, 4) for key, value in components.items()},
            "degraded_fallback": False,
        }
        candidates.append(result_entry)

    strong = []
    weak = []
    fallback = []
    blocked = []
    for doc in candidates:
        if doc["is_blocked_for_top5"]:
            blocked.append(doc)
        elif doc["tierCategory"] == "A":
            strong.append(doc)
        elif doc["tierCategory"] == "B":
            weak.append(doc)
        else:
            fallback.append(doc)

    sort_fn = lambda item: (item["score"], date_sort_value(item.get("published_at")))
    strong.sort(key=sort_fn, reverse=True)
    weak.sort(key=sort_fn, reverse=True)
    fallback.sort(key=sort_fn, reverse=True)
    blocked.sort(key=sort_fn, reverse=True)

    max_results = 30 if limit is None else limit
    valid = [*strong, *weak, *fallback][:max_results]
    if allow_blocked_fallback and len(valid) < max_results:
        for doc in blocked:
            if len(valid) >= max_results:
                break
            doc["degraded_fallback"] = True
            doc["score_reason"] += "，目标候选不足，作为降级补位"
            valid.append(doc)
    return valid


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").lower())


def tokenize(query: str) -> List[str]:
    normalized = str(query or "").strip()
    if not normalized:
        return []
    parts = [part.strip() for part in re.split(r"[\s,，、/|]+", normalized) if part.strip()]
    return parts if parts else [normalized]


def overlap_score(query: str, text: str) -> float:
    query_tokens = {normalize(token) for token in tokenize(query) if normalize(token)}
    if not query_tokens:
        return 0.0
    candidate = normalize(text)
    hits = sum(1 for token in query_tokens if token in candidate)
    return hits / len(query_tokens)


def section_weight(config: Dict[str, Any], section: str, key: str, fallback: float) -> float:
    payload = config.get(section) if isinstance(config, dict) else {}
    if not isinstance(payload, dict):
        return fallback
    try:
        value = float(payload.get(key, fallback))
    except (TypeError, ValueError):
        return fallback
    return value if math.isfinite(value) else fallback


def score_hybrid_fields(fields: Dict[str, Any], query: str, ranking_weights: Dict[str, Any]) -> float:
    weights = ranking_weights.get("field_weights", {}) if isinstance(ranking_weights, dict) else {}
    score = 0.0
    max_score = 0.0
    for field, value in fields.items():
        weight = float(weights.get(field, 1))
        max_score += weight
        score += weight * overlap_score(query, str(value))
    return min(1.0, score / max_score) if max_score > 0 else 0.0


DOMAIN_LABELS = {
    "academic": "学业事务",
    "exam": "考试",
    "course": "课程选课",
    "degree": "学位培养",
    "scholarship": "资助评优",
    "employment": "就业实习",
    "competition": "竞赛活动",
    "project": "项目机会",
    "innovation_project": "大创项目",
    "international": "国际交流",
    "life": "校园生活",
    "library": "图书馆",
    "security": "安全保卫",
    "logistics": "后勤服务",
    "campus_network": "校园网络",
    "subsidy": "资助补助",
    "medical_insurance": "医保体检",
    "archive": "档案服务",
    "lecture": "讲座活动",
    "research": "科研事务",
    "resource": "学习资料",
    "news": "校园新闻",
    "policy": "政策制度",
}

INTENT_LABELS = {
    "apply": "申请",
    "register": "报名",
    "submit": "提交",
    "attend": "参加",
    "check_result": "查结果",
    "publicity": "公示",
    "download": "下载",
    "read": "阅读",
    "schedule": "安排",
    "alert": "提醒",
    "pay": "缴费",
    "contact": "联系",
    "export": "导出",
}

SOURCE_TYPE_LABELS = {
    "central_admin": "校级部门",
    "central_notice": "校级通知",
    "central_news": "校园新闻",
    "college": "学院站",
    "service_unit": "服务单位",
    "job_platform": "就业平台",
    "github_resource": "资料仓库",
    "research_admin": "科研管理",
    "policy": "信息公开",
    "exam_vertical": "考试频道",
}


def score_text_match(
    document: Dict[str, Any],
    query: str,
    expanded_terms: List[str] | None = None,
    ranking_weights: Dict[str, Any] | None = None,
) -> float:
    ranking_weights = ranking_weights or {}
    tokens = tokenize(" ".join([query, *(expanded_terms or [])]))
    if not tokens:
        return 0.0

    title = normalize(str(document.get("title", "")))
    content = normalize(str(document.get("content", "")))
    channel = normalize(str(document.get("channel", "")))
    source = normalize(str(document.get("source", "")))
    domain = normalize(DOMAIN_LABELS.get(str(document.get("domain", "")), str(document.get("domain", ""))))
    intent = normalize(INTENT_LABELS.get(str(document.get("intent", "")), str(document.get("intent", ""))))
    source_type = normalize(SOURCE_TYPE_LABELS.get(str(document.get("source_type", "")), str(document.get("source_type", ""))))
    tags = normalize(" ".join(str(item) for item in document.get("tags", []) or []))
    evidence = normalize(" ".join(str(item) for item in document.get("evidence", []) or []))
    class_name = normalize(str(document.get("class_name", "") or ""))
    task_text = normalize(
        " ".join(
            " ".join(
                str(part)
                for part in [
                    frame.get("what", ""),
                    (frame.get("action") or {}).get("summary", ""),
                    (frame.get("action") or {}).get("verb", ""),
                    (frame.get("time") or {}).get("deadline", ""),
                    *[material.get("name", "") for material in frame.get("materials", []) or []],
                    *[item.get("text", "") for item in frame.get("evidence", []) or []],
                ]
                if part
            )
            for frame in document.get("task_frames", []) or []
        )
    )

    score = 0.0
    normalized_query = normalize(query)
    if title == normalized_query:
        score += section_weight(ranking_weights, "text_match_weights", "exact_title", 18)
    if normalized_query and normalized_query in title:
        score += section_weight(ranking_weights, "text_match_weights", "title_contains_query", 12)
    if class_name and class_name == normalized_query:
        score += section_weight(ranking_weights, "text_match_weights", "class_exact", 16)

    for token in tokens:
        normalized_token = normalize(token)
        if not normalized_token:
            continue
        if normalized_token in title:
            score += section_weight(ranking_weights, "text_match_weights", "title", 8)
        if normalized_token in tags:
            score += section_weight(ranking_weights, "text_match_weights", "tags", 4)
        if normalized_token in domain:
            score += section_weight(ranking_weights, "text_match_weights", "domain", 4)
        if normalized_token in intent:
            score += section_weight(ranking_weights, "text_match_weights", "intent", 3)
        if normalized_token in source_type:
            score += section_weight(ranking_weights, "text_match_weights", "source_type", 2)
        if normalized_token in channel:
            score += section_weight(ranking_weights, "text_match_weights", "channel", 3)
        if normalized_token in source:
            score += section_weight(ranking_weights, "text_match_weights", "source", 3)
        if normalized_token in evidence:
            score += section_weight(ranking_weights, "text_match_weights", "evidence", 2)
        if normalized_token in task_text:
            score += section_weight(ranking_weights, "text_match_weights", "task_text", 5)
        if normalized_token in content:
            score += section_weight(ranking_weights, "text_match_weights", "content", 1.5)
        if normalized_token in class_name:
            score += section_weight(ranking_weights, "text_match_weights", "class_name", 8)
    return score


def alias_terms_for_query(query: str, query_aliases: Dict[str, Any]) -> List[str]:
    normalized_query = normalize(query)
    terms: List[str] = []
    for key, payload in (query_aliases or {}).items():
        aliases = [str(item) for item in payload.get("aliases", [])] if isinstance(payload, dict) else []
        candidates = [key, *aliases]
        if any(normalize(candidate) and normalize(candidate) in normalized_query for candidate in candidates):
            terms.extend(aliases)
    return list(dict.fromkeys(term for term in terms if term))


def intent_weight(intent: str, ranking_weights: Dict[str, Any] | None = None) -> float:
    return section_weight(ranking_weights or {}, "intent_weights", intent, 1.0)


def lifecycle_weight(lifecycle: str, ranking_weights: Dict[str, Any] | None = None) -> float:
    return section_weight(ranking_weights or {}, "lifecycle_weights", lifecycle, 1.0)


def source_type_weight(source_type: str, ranking_weights: Dict[str, Any] | None = None) -> float:
    return section_weight(ranking_weights or {}, "source_type_weights", source_type, 1.0)


def deadline_urgency_weight(deadline: Any, ranking_weights: Dict[str, Any] | None = None) -> float:
    ranking_weights = ranking_weights or {}
    if not deadline:
        return section_weight(ranking_weights, "deadline_urgency_weights", "none", 1.0)
    dt = parse_date(deadline)
    if not dt:
        return section_weight(ranking_weights, "deadline_urgency_weights", "none", 1.0)
    days = (dt - datetime.now(timezone.utc)).total_seconds() / 86400
    if days < 0:
        return section_weight(ranking_weights, "deadline_urgency_weights", "expired", 0.82)
    if days <= 1:
        return section_weight(ranking_weights, "deadline_urgency_weights", "within_1_day", 1.18)
    if days <= 3:
        return section_weight(ranking_weights, "deadline_urgency_weights", "within_3_days", 1.14)
    if days <= 7:
        return section_weight(ranking_weights, "deadline_urgency_weights", "within_7_days", 1.08)
    return section_weight(ranking_weights, "deadline_urgency_weights", "future", 1.02)


def parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value)
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def date_sort_value(value: Any) -> float:
    dt = parse_date(value)
    return dt.timestamp() * 1000 if dt else 0.0


def build_score_reason_ts(document: Dict[str, Any], components: Dict[str, float] | None = None) -> str:
    parts = [
        DOMAIN_LABELS.get(str(document.get("domain", "")), str(document.get("domain", ""))),
        INTENT_LABELS.get(str(document.get("intent", "")), str(document.get("intent", ""))),
        str(document.get("channel", "")),
    ]
    if document.get("attachments"):
        parts.append(f"{len(document.get('attachments') or [])}附件")
    lead = "·".join(parts)
    if not components:
        return lead
    ranked = sorted(
        ((name, value) for name, value in components.items() if value > 0.01),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    detail = " / ".join(f"{name}:{value:.2f}" for name, value in ranked)
    return f"{lead} · {detail}" if detail else lead


def _take(items: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    return items[:n]

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
