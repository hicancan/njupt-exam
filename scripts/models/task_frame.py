import hashlib
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TaskAudience(BaseModel):
    audience: list[str] = Field(default_factory=list)
    college: list[str] = Field(default_factory=list)
    grade: list[str] = Field(default_factory=list)
    major: list[str] = Field(default_factory=list)
    class_name: list[str] = Field(default_factory=list)

    @field_validator("audience", "college", "grade", "major", "class_name", mode="before")
    @classmethod
    def _coerce_list(cls, value: Any) -> list[str]:
        return coerce_str_list(value)


class TaskAction(BaseModel):
    required: bool = False
    verb: str | None = None
    object: str | None = None
    summary: str | None = None


class TaskTime(BaseModel):
    published_at: str | None = None
    deadline: str | None = None
    lifecycle: str = "unknown"
    urgency_days: int | None = None


class TaskMaterial(BaseModel):
    name: str
    role: str | None = None
    required: bool = False
    sensitive: bool = False


class TaskLocation(BaseModel):
    place: str | None = None
    online: str | None = None
    contact: str | None = None


class TaskSource(BaseModel):
    source_id: str
    channel_id: str
    authority: float = Field(default=0.7, ge=0, le=1)
    official: bool = True


class TaskEvidence(BaseModel):
    field: str
    text: str


class TaskRisk(BaseModel):
    sensitive: bool = False
    restricted: bool = False
    low_evidence: bool = False
    review_required: bool = False


class TaskFrame(BaseModel):
    task_id: str
    doc_id: str
    task_type: str = "read"
    who: TaskAudience = Field(default_factory=TaskAudience)
    what: str
    action: TaskAction = Field(default_factory=TaskAction)
    time: TaskTime = Field(default_factory=TaskTime)
    materials: list[TaskMaterial] = Field(default_factory=list)
    location: TaskLocation = Field(default_factory=TaskLocation)
    source: TaskSource
    evidence: list[TaskEvidence] = Field(default_factory=list)
    risk: TaskRisk = Field(default_factory=TaskRisk)
    confidence: float = Field(default=0.5, ge=0, le=1)

    @field_validator("materials", mode="before")
    @classmethod
    def _coerce_materials(cls, value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, str):
            return [{"name": value}]
        if isinstance(value, list):
            result: list[dict[str, Any]] = []
            for item in value:
                if isinstance(item, dict):
                    result.append(item)
                else:
                    text = str(item).strip()
                    if text:
                        result.append({"name": text})
            return result
        return []

    @field_validator("evidence", mode="before")
    @classmethod
    def _coerce_evidence(cls, value: Any) -> list[dict[str, str]]:
        if value is None:
            return []
        if isinstance(value, str):
            return [{"field": "general", "text": value}]
        if isinstance(value, list):
            result: list[dict[str, str]] = []
            for item in value:
                if isinstance(item, dict):
                    text = str(item.get("text") or "").strip()
                    if text:
                        result.append({"field": str(item.get("field") or "general"), "text": text[:180]})
                else:
                    text = str(item).strip()
                    if text:
                        result.append({"field": "general", "text": text[:180]})
            return result
        return []


def coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def normalize_task_frames(
    raw_frames: Any,
    *,
    doc_id: str,
    source_id: str,
    channel_id: str,
    authority: float,
    fallback_title: str,
    fallback_audience: list[str],
    fallback_domain: str,
    fallback_intent: str,
    published_at: str | None,
    deadline: str | None,
    lifecycle: str,
    evidence: list[str],
    attachments: list[dict[str, Any]],
    action_required: bool,
    action_type: str | None,
    action_summary: str | None,
    risk: dict[str, Any],
    confidence: float | None = None,
) -> list[dict[str, Any]]:
    frames: list[TaskFrame] = []
    for index, item in enumerate(raw_frames if isinstance(raw_frames, list) else []):
        if not isinstance(item, dict):
            continue
        try:
            frame = TaskFrame.model_validate(fill_task_frame_defaults(
                item,
                index=index,
                doc_id=doc_id,
                source_id=source_id,
                channel_id=channel_id,
                authority=authority,
                fallback_title=fallback_title,
                fallback_audience=fallback_audience,
                fallback_domain=fallback_domain,
                fallback_intent=fallback_intent,
                published_at=published_at,
                deadline=deadline,
                lifecycle=lifecycle,
                evidence=evidence,
                attachments=attachments,
                action_required=action_required,
                action_type=action_type,
                action_summary=action_summary,
                risk=risk,
                confidence=confidence,
            ))
            frames.append(frame)
        except Exception:
            continue

    if frames or risk.get("restricted") or risk.get("sensitive"):
        return [frame.model_dump() for frame in frames]

    if should_create_rule_frame(action_required, fallback_intent, deadline, attachments):
        frames.append(TaskFrame.model_validate(fill_task_frame_defaults(
            {},
            index=0,
            doc_id=doc_id,
            source_id=source_id,
            channel_id=channel_id,
            authority=authority,
            fallback_title=fallback_title,
            fallback_audience=fallback_audience,
            fallback_domain=fallback_domain,
            fallback_intent=fallback_intent,
            published_at=published_at,
            deadline=deadline,
            lifecycle=lifecycle,
            evidence=evidence,
            attachments=attachments,
            action_required=action_required,
            action_type=action_type,
            action_summary=action_summary,
            risk=risk,
            confidence=confidence,
        )))
    return [frame.model_dump() for frame in frames]


def fill_task_frame_defaults(item: dict[str, Any], **context: Any) -> dict[str, Any]:
    doc_id = str(context["doc_id"])
    task_type = str(item.get("task_type") or infer_task_type(context["fallback_domain"], context["fallback_intent"]))
    what = str(item.get("what") or context["fallback_title"]).strip()
    task_id = str(item.get("task_id") or stable_task_id(doc_id, task_type, what, context["index"]))
    risk = context["risk"]
    action = item.get("action") if isinstance(item.get("action"), dict) else {}
    time_payload = item.get("time") if isinstance(item.get("time"), dict) else {}
    who = item.get("who") if isinstance(item.get("who"), dict) else {}
    location = item.get("location") if isinstance(item.get("location"), dict) else {}
    evidence = item.get("evidence") if item.get("evidence") else [
        {"field": "general", "text": text} for text in context["evidence"][:4]
    ]
    materials = item.get("materials")
    if not materials:
        materials = [
            {
                "name": str(attachment.get("name") or "附件"),
                "role": attachment.get("role"),
                "required": bool(context["action_required"]),
                "sensitive": bool(attachment.get("sensitive", False)),
            }
            for attachment in context["attachments"][:5]
        ]
    return {
        "task_id": task_id,
        "doc_id": doc_id,
        "task_type": task_type,
        "who": {
            "audience": coerce_str_list(who.get("audience") or context["fallback_audience"]),
            "college": coerce_str_list(who.get("college")),
            "grade": coerce_str_list(who.get("grade")),
            "major": coerce_str_list(who.get("major")),
            "class_name": coerce_str_list(who.get("class_name")),
        },
        "what": what,
        "action": {
            "required": bool(action.get("required", context["action_required"])),
            "verb": action.get("verb") or context["action_type"],
            "object": action.get("object"),
            "summary": action.get("summary") or context["action_summary"],
        },
        "time": {
            "published_at": time_payload.get("published_at") or context["published_at"],
            "deadline": time_payload.get("deadline") or context["deadline"],
            "lifecycle": time_payload.get("lifecycle") or context["lifecycle"],
            "urgency_days": time_payload.get("urgency_days") or urgency_days(context["deadline"]),
        },
        "materials": materials,
        "location": {
            "place": location.get("place"),
            "online": location.get("online"),
            "contact": location.get("contact"),
        },
        "source": {
            "source_id": context["source_id"],
            "channel_id": context["channel_id"],
            "authority": context["authority"],
            "official": True,
        },
        "evidence": evidence,
        "risk": {
            "sensitive": bool(risk.get("sensitive")),
            "restricted": bool(risk.get("restricted")),
            "low_evidence": bool(risk.get("low_evidence")),
            "review_required": bool(risk.get("review_required")),
        },
        "confidence": float(item.get("confidence", context["confidence"] or 0.58)),
    }


def infer_task_type(domain: str, intent: str) -> str:
    if intent in {"apply", "register", "submit"}:
        return "application"
    if intent in {"schedule", "alert"}:
        return "schedule"
    if intent in {"check_result", "publicity"}:
        return "result_check"
    if intent == "download":
        return "download"
    if domain in {"competition", "project", "employment", "international"}:
        return "opportunity"
    return "read"


def should_create_rule_frame(action_required: bool, intent: str, deadline: str | None, attachments: list[dict[str, Any]]) -> bool:
    if action_required or deadline:
        return True
    if intent in {"apply", "register", "submit", "schedule", "alert", "download", "check_result"}:
        return True
    return bool(attachments and intent == "download")


def urgency_days(deadline: str | None) -> int | None:
    if not deadline:
        return None
    try:
        value = datetime.fromisoformat(deadline)
        now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
        return int((value - now).total_seconds() // 86400)
    except ValueError:
        return None


def stable_task_id(doc_id: str, task_type: str, what: str, index: int) -> str:
    normalized = re.sub(r"\s+", "", f"{doc_id}:{task_type}:{what}:{index}")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"task_{digest}"
