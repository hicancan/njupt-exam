from typing import Any

from models.task_frame import normalize_task_frames


def extract_task_frames(
    document: dict[str, Any],
    *,
    llm_result: dict[str, Any] | None,
    rule_guard: dict[str, Any],
) -> list[dict[str, Any]]:
    if rule_guard.get("restricted") or rule_guard.get("sensitive"):
        return []

    risk = {
        "sensitive": bool(document.get("sensitive") or rule_guard.get("sensitive")),
        "restricted": bool(document.get("status") == "restricted" or rule_guard.get("restricted")),
        "low_evidence": bool(rule_guard.get("low_evidence")),
        "review_required": bool(document.get("review_required") or rule_guard.get("review_required")),
    }
    raw_frames = llm_result.get("task_frames") if isinstance(llm_result, dict) else []
    frames = normalize_task_frames(
        raw_frames,
        doc_id=str(document.get("id")),
        source_id=str(document.get("source_id") or ""),
        channel_id=str(document.get("channel_id") or ""),
        authority=float(document.get("source_weight", 0.7) or 0.7),
        fallback_title=str(document.get("title") or ""),
        fallback_audience=list(document.get("audience") or []),
        fallback_domain=str(document.get("domain") or "news"),
        fallback_intent=str(document.get("intent") or "read"),
        published_at=document.get("published_at"),
        deadline=document.get("deadline"),
        lifecycle=str(document.get("lifecycle") or "unknown"),
        evidence=list(document.get("evidence") or []),
        attachments=list(document.get("attachments") or []),
        action_required=bool(document.get("action_required")),
        action_type=document.get("action_type"),
        action_summary=document.get("action_summary"),
        risk=risk,
        confidence=document.get("confidence"),
    )
    return frames
