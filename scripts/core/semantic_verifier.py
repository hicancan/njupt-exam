import re
from collections import Counter
from typing import Any

from models.semantic_result import SemanticResult


DATE_OR_DEADLINE_RE = re.compile(
    r"(截止|截止时间|报名截止|申报截止|提交截止|于[^。；;]{0,40}前|"
    r"20\d{2}\s*[-/.年]\s*\d{1,2}\s*[-/.月]\s*\d{1,2}|"
    r"\d{1,2}\s*月\s*\d{1,2}\s*日|"
    r"\d{1,2}\s*[:：点]\s*\d{0,2})"
)
STUDENT_ACTION_RE = re.compile(
    r"(学生|本科生|研究生|同学|毕业生|参赛队|申请人|报名者|考生|各班|各学院学生|"
    r"报名|申请|申报|提交|报送|填写|上传|缴费|确认|参加|签到|下载|预约|办理|查询)"
)
ADMIN_ONLY_RE = re.compile(r"(各学院|各单位|各部门|各系|教师|辅导员|班主任|管理员).{0,30}(报送|提交|汇总|审核|组织)")
CONTACT_RE = re.compile(r"(\d{3,4}[- ]?\d{7,8}|1[3-9]\d{9}|[\w.+-]+@[\w.-]+\.\w+|联系人|联系电话|咨询)")
LOCATION_RE = re.compile(r"(校区|教学楼|教\d|图书馆|大学生活动中心|会议室|报告厅|办公室|线上|网址|https?://)")
SENSITIVE_MATERIAL_RE = re.compile(r"(身份证|学号|手机号|成绩|困难认定|处分|名单)")


def verify_semantic_result(
    semantic: SemanticResult,
    *,
    title: str,
    source_text: str,
    attachments: list[dict[str, Any]],
    guard: dict[str, Any],
) -> SemanticResult:
    corpus = evidence_corpus(title, source_text, semantic.evidence, attachments)
    removals: Counter[str] = Counter()

    guarded = (
        guard.get("restricted")
        or guard.get("sensitive")
        or guard.get("low_evidence")
        or guard.get("allow_llm") is False
    )
    if guarded:
        if semantic.deadline:
            removals["deadline"] += 1
        if semantic.action_required or semantic.action_type or semantic.action_summary:
            removals["action"] += 1
        if semantic.required_materials:
            removals["materials"] += len(semantic.required_materials)
        semantic.deadline = None
        semantic.action_required = False
        semantic.action_type = None
        semantic.action_summary = None
        semantic.required_materials = []
        semantic.review_required = True
        semantic.field_sources["task_frames"] = "guarded_metadata_empty"

    if semantic.deadline and not deadline_is_grounded(corpus):
        semantic.deadline = None
        semantic.review_required = True
        semantic.field_sources["deadline"] = "verifier_removed"
        semantic.risk_flags = add_flag(semantic.risk_flags, "ungrounded_deadline_removed")
        removals["deadline"] += 1

    if semantic.action_required and not action_is_grounded(corpus, semantic.action_summary):
        semantic.action_required = False
        semantic.action_type = None
        semantic.action_summary = None
        semantic.review_required = True
        semantic.field_sources["action_required"] = "verifier_removed"
        semantic.field_sources["action_summary"] = "verifier_removed"
        semantic.risk_flags = add_flag(semantic.risk_flags, "non_student_action_removed")
        removals["action"] += 1

    grounded_materials: list[str] = []
    for material in semantic.required_materials:
        name = str(material or "").strip()
        if not name:
            continue
        if text_mentions(corpus, name):
            grounded_materials.append(name)
        else:
            removals["materials"] += 1
    if len(grounded_materials) != len(semantic.required_materials):
        semantic.required_materials = grounded_materials
        semantic.review_required = True
        semantic.field_sources["required_materials"] = "verifier_removed"
        semantic.risk_flags = add_flag(semantic.risk_flags, "ungrounded_materials_removed")

    if any(SENSITIVE_MATERIAL_RE.search(item) for item in semantic.required_materials):
        semantic.risk_flags = add_flag(semantic.risk_flags, "sensitive_material_required")
        semantic.review_required = True

    if removals:
        semantic.llm = {
            **(semantic.llm or {}),
            "verifier_removals": dict(removals),
        }
    return semantic


def verify_search_document(document: dict[str, Any]) -> dict[str, Any]:
    guard = document.get("rule_guard") if isinstance(document.get("rule_guard"), dict) else {}
    corpus = evidence_corpus(
        str(document.get("title") or ""),
        str(document.get("content") or ""),
        [str(item) for item in document.get("evidence", []) or []],
        list(document.get("attachments") or []),
    )
    removals: Counter[str] = Counter()

    guarded = (
        guard.get("restricted")
        or guard.get("sensitive")
        or guard.get("low_evidence")
        or guard.get("allow_llm") is False
    )
    if guarded and document.get("task_frames"):
        removals["task_frames"] += len(document.get("task_frames") or [])
        document["task_frames"] = []

    if document.get("deadline") and not deadline_is_grounded(corpus):
        document["deadline"] = None
        document["review_required"] = True
        document["risk_flags"] = add_flag(list(document.get("risk_flags") or []), "ungrounded_deadline_removed")
        removals["deadline"] += 1

    frames: list[dict[str, Any]] = []
    for raw_frame in document.get("task_frames") or []:
        if not isinstance(raw_frame, dict):
            continue
        frame = verify_task_frame(raw_frame, corpus)
        frame_removals = frame.pop("_verifier_removals", {})
        for key, value in frame_removals.items():
            removals[f"task_frame_{key}"] += int(value)
        frames.append(frame)
    document["task_frames"] = frames

    if removals:
        document["review_required"] = bool(document.get("review_required") or any(key != "task_frames" for key in removals))
        document["risk_flags"] = add_flag(list(document.get("risk_flags") or []), "semantic_verifier_modified")
        document["semantic_verifier"] = {"removals": dict(removals)}
    return document


def verify_task_frame(frame: dict[str, Any], corpus: str) -> dict[str, Any]:
    removals: Counter[str] = Counter()
    time_payload = frame.get("time") if isinstance(frame.get("time"), dict) else {}
    if time_payload.get("deadline") and not deadline_is_grounded(corpus):
        time_payload["deadline"] = None
        time_payload["urgency_days"] = None
        frame["time"] = time_payload
        removals["deadline"] += 1

    action = frame.get("action") if isinstance(frame.get("action"), dict) else {}
    if action.get("required") and not action_is_grounded(corpus, action.get("summary") or action.get("verb")):
        action["required"] = False
        action["verb"] = None
        action["object"] = None
        action["summary"] = None
        frame["action"] = action
        removals["action"] += 1

    materials = []
    for material in frame.get("materials") or []:
        if not isinstance(material, dict):
            continue
        name = str(material.get("name") or "").strip()
        if name and text_mentions(corpus, name):
            materials.append(material)
        else:
            removals["materials"] += 1
    frame["materials"] = materials

    location = frame.get("location") if isinstance(frame.get("location"), dict) else {}
    for field, pattern in (("place", LOCATION_RE), ("online", LOCATION_RE), ("contact", CONTACT_RE)):
        value = str(location.get(field) or "").strip()
        if value and not (text_mentions(corpus, value) or pattern.search(corpus)):
            location[field] = None
            removals["location"] += 1
    frame["location"] = location

    if removals:
        risk = frame.get("risk") if isinstance(frame.get("risk"), dict) else {}
        risk["review_required"] = True
        frame["risk"] = risk
        frame["_verifier_removals"] = dict(removals)
    return frame


def evidence_corpus(
    title: str,
    source_text: str,
    evidence: list[str],
    attachments: list[dict[str, Any]],
) -> str:
    attachment_text = " ".join(
        " ".join(
            str(item.get(field) or "")
            for field in ("name", "role", "description", "url")
        )
        for item in attachments
        if isinstance(item, dict)
    )
    return re.sub(r"\s+", " ", " ".join([title, source_text, *evidence, attachment_text])).strip()


def deadline_is_grounded(corpus: str) -> bool:
    return bool(DATE_OR_DEADLINE_RE.search(corpus))


def action_is_grounded(corpus: str, summary: Any) -> bool:
    text = " ".join([corpus, str(summary or "")])
    if ADMIN_ONLY_RE.search(text) and not re.search(r"(学生|本科生|研究生|同学|考生|申请人)", text):
        return False
    return bool(STUDENT_ACTION_RE.search(text))


def text_mentions(corpus: str, value: str) -> bool:
    needle = re.sub(r"\s+", "", str(value or "")).lower()
    haystack = re.sub(r"\s+", "", corpus).lower()
    return bool(needle and (needle in haystack or haystack in needle))


def add_flag(flags: list[str], flag: str) -> list[str]:
    return sorted(set([*flags, flag]))
