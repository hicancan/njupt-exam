import re
from datetime import datetime
from indexer_config import CATEGORY_KEYWORDS, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS, MIN_STUDENT_SCORE, BEIJING_TZ

def calculate_freshness(published_at: str | None, now: datetime) -> float:
    if not published_at:
        return 0.45
    try:
        published = datetime.fromisoformat(published_at).replace(tzinfo=BEIJING_TZ)
    except ValueError:
        return 0.45

    days = (now - published).days
    if days < 0:
        return 0.92
    if days <= 3:
        return 1.0
    if days <= 7:
        return 0.92
    if days <= 30:
        return 0.78
    if days <= 180:
        return 0.58
    return 0.42

def infer_category(text: str) -> str:
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        scores[category] = sum(1 for keyword in keywords if keyword.lower() in text.lower())

    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        return "公告"
    return best_category

def infer_tags(text: str, category: str) -> list[str]:
    tags = [category]
    for keyword in POSITIVE_KEYWORDS:
        if keyword.lower() in text.lower() and keyword not in tags:
            tags.append(keyword)
    return tags[:8]

def calculate_student_score(text: str, source_weight: float) -> float:
    positive_hits = sum(1 for keyword in POSITIVE_KEYWORDS if keyword.lower() in text.lower())
    category_hits = sum(
        1
        for keywords in CATEGORY_KEYWORDS.values()
        for keyword in keywords
        if keyword.lower() in text.lower()
    )
    negative_hits = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword.lower() in text.lower())
    score = (
        0.32
        + positive_hits * 0.08
        + min(category_hits, 5) * 0.045
        + source_weight * 0.18
        - negative_hits * 0.16
    )
    return round(max(0.05, min(1.0, score)), 4)

def is_student_facing_document(document: dict) -> bool:
    text = f"{document['title']} {document.get('content', '')}"
    category = document.get("category", "公告")
    domain = str(document.get("domain", "news"))
    intent = str(document.get("intent", "read"))
    source_type = str(document.get("source_type", "central_admin"))
    lifecycle = str(document.get("lifecycle", "unknown"))
    negative_hits = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword.lower() in text.lower())
    threshold_by_category = {
        "公告": 0.68, "资料": 0.62, "学院": 0.58,
        "讲座": 0.56, "生活": 0.54, "项目": 0.56,
    }
    threshold_by_domain = {
        "exam": 0.5, "course": 0.52, "scholarship": 0.52, "employment": 0.5,
        "competition": 0.52, "project": 0.56, "international": 0.54,
        "library": 0.54, "security": 0.54, "logistics": 0.54,
        "lecture": 0.56, "academic": 0.58, "resource": 0.52,
        "news": 0.78, "policy": 0.74, "research": 0.68,
    }

    if negative_hits > 0 and document["student_score"] < 0.74:
        return False
    if source_type in {"central_news", "research_admin", "policy"} and intent == "read" and document["student_score"] < 0.82:
        return False
    if lifecycle == "expired" and domain not in {"resource", "policy"} and document["student_score"] < 0.86:
        return False

    threshold = max(
        threshold_by_category.get(str(category), MIN_STUDENT_SCORE),
        threshold_by_domain.get(domain, MIN_STUDENT_SCORE),
    )
    return document["student_score"] >= threshold

def calculate_importance_score(text: str, category: str, attachments_count: int, source_weight: float) -> float:
    category_bonus = {
        "考试": 0.18, "选课": 0.14, "竞赛": 0.13,
        "奖助": 0.13, "就业": 0.12, "生活": 0.1,
        "研究生": 0.1,
    }.get(category, 0.04)
    title_bonus = 0.1 if any(keyword in text for keyword in ("通知", "公示", "安排", "报名", "开放")) else 0
    attachment_bonus = min(0.08, attachments_count * 0.025)
    score = 0.48 + source_weight * 0.18 + category_bonus + title_bonus + attachment_bonus
    return round(max(0.05, min(1.0, score)), 4)
