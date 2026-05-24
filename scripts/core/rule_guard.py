from datetime import datetime
from typing import Any

from core.heuristics import (
    detect_sensitive_info,
    is_low_evidence_content,
    is_restricted_content,
)


ADMIN_NOISE_TERMS = (
    "采购",
    "招标",
    "比选",
    "中标",
    "成交",
    "验收",
    "资产处置",
    "巡察",
    "审计",
    "干部任免",
    "党委理论学习",
    "离退休",
)

EVERGREEN_TERMS = ("下载", "指南", "流程", "制度", "办法", "手册", "表格", "模板", "常见问题")


def evaluate_rule_guard(
    *,
    title: str,
    content: str,
    attachments: list[dict[str, Any]],
    published_at: str | None,
    lifecycle: str | None = None,
    domain: str | None = None,
    intent: str | None = None,
    source_type: str | None = None,
    duplicate: bool = False,
) -> dict[str, Any]:
    text = f"{title} {content}"
    restricted = is_restricted_content(text)
    sensitive, sensitive_types = detect_sensitive_info(text, attachments)
    low_evidence = is_low_evidence_content(content, attachments)
    expired = lifecycle == "expired"
    evergreen = bool(
        domain in {"resource", "policy"}
        or intent == "download"
        or any(term in text for term in EVERGREEN_TERMS)
    )
    admin_noise = is_admin_noise(text)
    risk_flags: list[str] = []
    if restricted:
        risk_flags.append("restricted_content")
    if sensitive:
        risk_flags.append("sensitive_personal_info")
    if low_evidence:
        risk_flags.append("low_evidence_content")
    if duplicate:
        risk_flags.append("duplicate")
    if expired and not evergreen:
        risk_flags.append("expired")
    if evergreen:
        risk_flags.append("evergreen")
    if source_type == "github_resource":
        risk_flags.append("github_resource")
    if admin_noise:
        risk_flags.append("administrative_noise")

    allow_llm = not restricted and not sensitive and not low_evidence and not admin_noise
    allow_full_text_display = not restricted and not sensitive
    review_required = restricted or sensitive or low_evidence

    return {
        "restricted": restricted,
        "sensitive": sensitive,
        "sensitive_types": sensitive_types,
        "low_evidence": low_evidence,
        "duplicate": duplicate,
        "expired": expired,
        "evergreen": evergreen,
        "administrative_noise": admin_noise,
        "risk_flags": sorted(set(risk_flags)),
        "allow_llm": allow_llm,
        "allow_full_text_display": allow_full_text_display,
        "review_required": review_required,
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
    }


def is_admin_noise(text: str) -> bool:
    if not any(term in text for term in ADMIN_NOISE_TERMS):
        return False
    student_terms = (
        "学生",
        "本科生",
        "研究生",
        "考试",
        "选课",
        "奖学金",
        "助学金",
        "就业",
        "实习",
        "停水",
        "停电",
        "图书馆",
        "报名",
    )
    return not any(term in text for term in student_terms)


def restricted_summary() -> str:
    return "该页面访问受限，请点击原文在允许的网络环境下查看"
