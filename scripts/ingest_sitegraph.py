from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SITEGRAPH_INDEX = BASE_DIR.parent / "njupt-site-graph" / "data" / "sites" / "jwc" / "index"
PUBLIC_INDEX_DIR = BASE_DIR / "public" / "index"
PUBLIC_SITEGRAPH_DIR = PUBLIC_INDEX_DIR / "sitegraph" / "jwc"

REQUIRED_SITEGRAPH_FILES = {
    "manifest.json",
    "site.json",
    "sections.json",
    "list_pages.jsonl",
    "detail_pages.jsonl",
    "attachments.jsonl",
    "external_links.jsonl",
    "edges.jsonl",
}

COUNT_FIELDS = (
    "sections",
    "nav_nodes",
    "homepage_modules",
    "list_pages",
    "detail_pages",
    "low_content_detail_pages",
    "attachments",
    "external_links",
    "edges",
    "url_outcomes",
)

EXTRA_QUERY_ALIASES: dict[str, dict[str, Any]] = {
    "校历": {
        "aliases": ["校历查询", "教学日历", "教学周历"],
        "domains": ["academic", "exam"],
        "intents": ["schedule", "read"],
    },
    "慕课考试": {
        "aliases": ["慕课", "MOOC", "SPOC", "在线开放课程", "考试"],
        "domains": ["course", "exam"],
        "intents": ["schedule", "read"],
    },
    "期末考试": {
        "aliases": ["期末", "考试安排", "考场安排", "考试周"],
        "domains": ["exam"],
        "intents": ["schedule"],
    },
    "规章制度": {
        "aliases": ["规章", "制度", "管理办法", "政策文件"],
        "domains": ["policy"],
        "intents": ["read"],
    },
    "办事流程": {
        "aliases": ["流程", "学生事务", "办理指南", "办事指南"],
        "domains": ["academic"],
        "intents": ["read", "download"],
    },
    "学生相关文件及表格": {
        "aliases": ["学生表格", "常用下载", "表格下载"],
        "domains": ["resource"],
        "intents": ["download"],
    },
    "教务管理系统": {
        "aliases": ["正方教务", "教务系统", "jwxt"],
        "domains": ["academic", "course"],
        "intents": ["read"],
    },
    "成绩": {
        "aliases": ["成绩查询", "成绩单", "绩点"],
        "domains": ["academic"],
        "intents": ["check_result", "read"],
    },
    "附件1": {
        "aliases": ["附件 1", "附件一", "附件"],
        "domains": ["resource"],
        "intents": ["download"],
    },
    "xlsx": {
        "aliases": ["Excel", "xls"],
        "domains": ["resource"],
        "intents": ["download"],
    },
}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} line {line_number} is not valid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path} line {line_number} must be a JSON object")
            rows.append(row)
    return rows


def write_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        if compact:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")


def sha1_text(text: str, length: int = 20) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: list[Any], *, limit: int | None = None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = normalize_space(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if limit is not None and len(result) >= limit:
            break
    return result


def count_nav_nodes(nav_tree: dict[str, Any]) -> int:
    nodes = nav_tree.get("nodes")
    if isinstance(nodes, list):
        return len(nodes)
    return 0


def validate_sitegraph_package(index_dir: Path) -> dict[str, Any]:
    missing = sorted(name for name in REQUIRED_SITEGRAPH_FILES if not (index_dir / name).exists())
    if missing:
        raise ValueError(f"JWC sitegraph package missing required files: {', '.join(missing)}")

    manifest = read_json(index_dir / "manifest.json")
    if not isinstance(manifest, dict):
        raise ValueError("manifest.json must be a JSON object")
    quality = manifest.get("quality") if isinstance(manifest.get("quality"), dict) else {}
    if int(quality.get("errors", -1)) != 0:
        raise ValueError(f"JWC manifest quality.errors must be 0, got {quality.get('errors')}")
    if quality.get("all_discovered_urls_have_outcomes") is not True:
        raise ValueError("JWC manifest all_discovered_urls_have_outcomes must be true")
    if quality.get("attachment_policy") != "metadata_only":
        raise ValueError(f"JWC attachment_policy must be metadata_only, got {quality.get('attachment_policy')!r}")
    if quality.get("external_link_policy") != "record_only":
        raise ValueError(f"JWC external_link_policy must be record_only, got {quality.get('external_link_policy')!r}")

    sections = read_json(index_dir / "sections.json")
    homepage_modules_payload = read_json(index_dir / "homepage_modules.json") if (index_dir / "homepage_modules.json").exists() else []
    homepage_modules = (
        homepage_modules_payload.get("modules")
        if isinstance(homepage_modules_payload, dict)
        else homepage_modules_payload
    )
    nav_tree = read_json(index_dir / "nav_tree.json") if (index_dir / "nav_tree.json").exists() else {}
    list_pages = read_jsonl(index_dir / "list_pages.jsonl")
    detail_pages = read_jsonl(index_dir / "detail_pages.jsonl")
    attachments = read_jsonl(index_dir / "attachments.jsonl")
    external_links = read_jsonl(index_dir / "external_links.jsonl")
    edges = read_jsonl(index_dir / "edges.jsonl")

    if not isinstance(sections, list):
        raise ValueError("sections.json must be a list")
    if not isinstance(homepage_modules, list):
        raise ValueError("homepage_modules.json must be a list")

    actual_counts = {
        "sections": len(sections),
        "nav_nodes": count_nav_nodes(nav_tree if isinstance(nav_tree, dict) else {}),
        "homepage_modules": len(homepage_modules),
        "list_pages": len(list_pages),
        "detail_pages": len(detail_pages),
        "low_content_detail_pages": sum(1 for row in detail_pages if row.get("content_status") == "low_content"),
        "attachments": len(attachments),
        "external_links": len(external_links),
        "edges": len(edges),
        "url_outcomes": len(manifest.get("url_outcomes") if isinstance(manifest.get("url_outcomes"), dict) else {}),
    }
    manifest_totals = manifest.get("totals") if isinstance(manifest.get("totals"), dict) else {}
    mismatches = {
        field: {"manifest": int(manifest_totals.get(field, -1) or 0), "actual": actual_counts[field]}
        for field in COUNT_FIELDS
        if int(manifest_totals.get(field, -1) or 0) != actual_counts[field]
    }
    if mismatches:
        raise ValueError(f"JWC sitegraph package count mismatch: {json.dumps(mismatches, ensure_ascii=False)}")

    return {
        "manifest": manifest,
        "sections": sections,
        "homepage_modules": homepage_modules,
        "nav_tree": nav_tree,
        "list_pages": list_pages,
        "detail_pages": detail_pages,
        "attachments": attachments,
        "external_links": external_links,
        "edges": edges,
        "actual_counts": actual_counts,
    }


def section_label(section: dict[str, Any] | None) -> str:
    if not section:
        return "教务处"
    nav_path = section.get("nav_path") if isinstance(section.get("nav_path"), list) else []
    return " / ".join(str(item) for item in nav_path if str(item).strip()) or str(section.get("name") or "教务处")


def section_tags(section: dict[str, Any] | None) -> list[str]:
    if not section:
        return []
    tags = section.get("business_tags")
    return [str(item) for item in tags] if isinstance(tags, list) else []


def classify(text: str, section: dict[str, Any] | None, attachments: list[dict[str, Any]], *, is_resource: bool = False) -> dict[str, Any]:
    haystack = normalize_space(text)
    tags = set(section_tags(section))
    section_type = str((section or {}).get("section_type") or "")
    has_attachments = bool(attachments)

    category = "公告"
    domain = "academic"
    intent = "read"
    lifecycle = "unknown"
    action_required = False
    action_type = None

    if is_resource or has_attachments or "resource" in tags or "download" in tags or "下载" in haystack or "表格" in haystack:
        category = "资料"
        domain = "resource"
        intent = "download"
        lifecycle = "evergreen"
        action_required = False
        action_type = "下载"

    if any(term in haystack for term in ("规章", "制度", "办法", "条例", "政策", "章程", "细则")) or {"policy", "regulation"} & tags:
        category = "资料"
        domain = "policy"
        intent = "read"
        lifecycle = "evergreen"

    if any(term in haystack for term in ("考试", "考场", "补考", "缓考", "四六级", "CET", "期末", "监考", "普通话测试")):
        category = "考试"
        domain = "exam"
        intent = "schedule"
        lifecycle = "active"
        action_type = "查看安排"

    if any(term in haystack for term in ("慕课", "MOOC", "SPOC", "选课", "课程", "任选课", "重修", "开课")):
        category = "选课"
        domain = "course"
        intent = "register" if any(term in haystack for term in ("选课", "报名", "申报")) else "read"
        lifecycle = "active"

    if any(term in haystack for term in ("成绩", "绩点", "成绩单")):
        category = "公告"
        domain = "academic"
        intent = "check_result"

    if any(term in haystack for term in ("转专业", "学籍", "休学", "复学", "退学")):
        category = "公告"
        domain = "academic" if domain != "policy" else "policy"
        intent = "apply" if any(term in haystack for term in ("申请", "报名", "提交")) else intent
        lifecycle = "active" if intent == "apply" else lifecycle

    if any(term in haystack for term in ("推免", "保研", "推荐免试", "免试攻读研究生")):
        category = "研究生"
        domain = "degree"
        intent = "apply" if any(term in haystack for term in ("申请", "推荐", "报名")) else "read"
        lifecycle = "active"

    if any(term in haystack for term in ("大创", "大学生创新创业训练", "创新创业训练", "STITP")):
        category = "项目"
        domain = "innovation_project"
        intent = "submit" if any(term in haystack for term in ("提交", "申报", "结题", "中期")) else "apply"
        lifecycle = "active"

    if any(term in haystack for term in ("学科竞赛", "竞赛", "挑战杯", "蓝桥杯", "数学建模")):
        if domain != "innovation_project":
            category = "竞赛"
            domain = "competition"
            intent = "register" if any(term in haystack for term in ("报名", "参赛")) else "read"
            lifecycle = "active"

    if any(term in haystack for term in ("校历", "教学日历", "教学进程")):
        intent = "schedule"
        lifecycle = "evergreen"

    if any(term in haystack for term in ("公示", "名单")) and intent == "read":
        intent = "publicity"
    if any(term in haystack for term in ("申请", "申报", "报名", "提交", "填报")):
        action_required = True
        action_type = "申请/提交"
        if intent == "read":
            intent = "apply"
            lifecycle = "active"

    if "homepage_module" in tags or section_type == "homepage_module":
        lifecycle = "active" if lifecycle == "unknown" else lifecycle

    if lifecycle == "unknown":
        lifecycle = "evergreen" if domain in {"policy", "resource"} else "active"

    return {
        "category": category,
        "domain": domain,
        "intent": intent,
        "lifecycle": lifecycle,
        "action_required": action_required,
        "action_type": action_type,
    }


def action_summary(intent: str, title: str) -> str | None:
    if intent in {"apply", "register", "submit"}:
        return f"按官方通知要求处理：{title}"
    if intent == "download":
        return "查看附件元数据并从官方链接下载。"
    if intent == "schedule":
        return "查看官方安排和时间信息。"
    if intent == "check_result":
        return "查看官方查询或结果说明。"
    return None


def make_attachment_metadata(
    attachment: dict[str, Any],
    section: dict[str, Any] | None,
    parent_title: str | None = None,
) -> dict[str, Any]:
    extension = str(attachment.get("extension") or "").lower().strip(".")
    name = normalize_space(attachment.get("name") or attachment.get("url") or "附件")
    return {
        "name": name,
        "url": str(attachment.get("url") or ""),
        "type": extension or None,
        "extension": extension or None,
        "role": "附件",
        "description": parent_title,
        "sensitive": False,
        "parent_url": str(attachment.get("parent_url") or ""),
        "section_id": str((section or {}).get("section_id") or ""),
        "section_path": section_label(section),
        "position": attachment.get("position"),
        "attachment_id": str(attachment.get("attachment_id") or sha1_text(str(attachment.get("url") or name))),
        "metadata_only": True,
    }


def build_task_frame(document: dict[str, Any]) -> dict[str, Any] | None:
    intent = str(document.get("intent") or "")
    attachments = document.get("attachments") if isinstance(document.get("attachments"), list) else []
    if intent not in {"apply", "register", "submit", "download", "schedule", "check_result"} and not attachments:
        return None
    task_type = {
        "apply": "application",
        "register": "application",
        "submit": "application",
        "download": "download",
        "schedule": "schedule",
        "check_result": "result_check",
    }.get(intent, "read")
    materials = [
        {
            "name": normalize_space(item.get("name") or "附件"),
            "role": item.get("role") or "附件",
            "required": task_type in {"application", "download"},
            "sensitive": False,
        }
        for item in attachments[:8]
        if isinstance(item, dict)
    ]
    title = str(document.get("title") or "")
    summary = action_summary(intent, title)
    evidence = [
        {"field": "title", "text": title},
        {"field": "section", "text": str(document.get("channel") or "")},
    ]
    if document.get("summary"):
        evidence.append({"field": "summary", "text": str(document["summary"])[:240]})
    return {
        "task_id": f"task-{document['id']}",
        "doc_id": document["id"],
        "source_mode": "heuristic_rule_frame",
        "field_sources": {
            "task_type": "sitegraph_rule",
            "action": "sitegraph_rule",
            "time": "sitegraph_metadata",
            "materials": "sitegraph_attachment_metadata",
        },
        "task_type": task_type,
        "who": {"audience": ["本科生"], "college": [], "grade": [], "major": [], "class_name": []},
        "what": title[:120],
        "action": {
            "required": bool(document.get("action_required")),
            "verb": document.get("action_type") or ("下载" if task_type == "download" else "查看"),
            "object": title[:80],
            "summary": summary,
        },
        "time": {
            "published_at": document.get("published_at"),
            "deadline": document.get("deadline"),
            "lifecycle": document.get("lifecycle") or "unknown",
            "urgency_days": None,
        },
        "materials": materials,
        "location": {"place": None, "online": document.get("url"), "contact": None},
        "source": {
            "source_id": document.get("source_id") or "jwc",
            "channel_id": document.get("channel_id") or "jwc",
            "authority": 1.0,
            "official": True,
        },
        "evidence": evidence,
        "risk": {
            "sensitive": False,
            "restricted": False,
            "low_evidence": bool((document.get("rule_guard") or {}).get("low_evidence")),
            "review_required": False,
        },
        "confidence": 0.72,
    }


def make_common_document(
    *,
    doc_id: str,
    kind: str,
    title: str,
    url: str,
    section: dict[str, Any] | None,
    content: str,
    summary: str,
    published_at: str | None,
    publisher: str | None,
    attachments: list[dict[str, Any]],
    provenance: dict[str, Any],
    status: str = "ok",
    is_resource: bool = False,
) -> dict[str, Any]:
    text_for_classification = " ".join(
        [
            title,
            section_label(section),
            " ".join(section_tags(section)),
            content[:2000],
            " ".join(item.get("name", "") for item in attachments),
        ]
    )
    classification = classify(text_for_classification, section, attachments, is_resource=is_resource)
    hash_value = sha1_text("\n".join([title, url, content, json.dumps(attachments, ensure_ascii=False)]), 40)
    nav_path = section.get("nav_path") if isinstance((section or {}).get("nav_path"), list) else []
    section_path = section_label(section)
    tags = unique_strings(
        [
            title,
            section_path,
            *(nav_path or []),
            *((section or {}).get("business_tags") or []),
            classification["category"],
            classification["domain"],
            classification["intent"],
            publisher,
            *(item.get("name") for item in attachments),
            *(item.get("extension") for item in attachments),
        ],
        limit=48,
    )
    evidence = unique_strings([title, section_path, summary, content[:240], *(item.get("name") for item in attachments)], limit=12)
    channel_id = str((section or {}).get("section_id") or "jwc_unsectioned")
    document = {
        "id": doc_id,
        "kind": kind,
        "status": status,
        "source_id": "jwc",
        "channel_id": channel_id,
        "channel": section_path,
        "title": title,
        "url": url,
        "source": "本科生院 / 教务处",
        "source_domain": "jwc.njupt.edu.cn",
        "source_type": "central_admin",
        "category": classification["category"],
        "domain": classification["domain"],
        "intent": classification["intent"],
        "lifecycle": classification["lifecycle"],
        "evidence": evidence,
        "confidence": 0.72,
        "sub_category": str((section or {}).get("section_type") or "") or None,
        "deadline": None,
        "action_required": classification["action_required"],
        "action_type": classification["action_type"],
        "action_summary": action_summary(classification["intent"], title),
        "required_materials": [item["name"] for item in attachments[:8]],
        "sensitive": False,
        "sensitive_types": [],
        "review_required": False,
        "risk_flags": [],
        "audience": ["本科生"],
        "published_at": published_at,
        "publisher": publisher,
        "content": content or title,
        "summary": summary or title,
        "attachments": attachments,
        "tags": tags,
        "hash": hash_value,
        "cache_key": f"sitegraph:jwc:{hash_value}",
        "llm_schema_version": "sitegraph-rule-v1",
        "llm": {
            "used": False,
            "provider": None,
            "model": None,
            "prompt_version": "sitegraph-rule-v1",
            "confidence": None,
            "review_required": False,
        },
        "canonical": {
            "doc_id": doc_id,
            "canonical_url": url,
            "content_hash": hash_value,
            "dedupe_key": f"jwc:{url}",
        },
        "notice_card": {
            "title": title,
            "source": "本科生院 / 教务处",
            "channel": section_path,
            "url": url,
            "published_at": published_at,
            "publisher": publisher,
            "official": True,
            "provenance": "jwc-sitegraph",
        },
        "typed_search_terms": [
            {"type": "title", "value": title, "source": "sitegraph"},
            {"type": "section", "value": section_path, "source": "sitegraph"},
            {"type": "section_id", "value": channel_id, "source": "sitegraph"},
            *[
                {"type": "nav_path", "value": str(item), "source": "sitegraph"}
                for item in nav_path
            ],
            *[
                {"type": "attachment", "value": item.get("name"), "source": "sitegraph"}
                for item in attachments
                if item.get("name")
            ],
            *[
                {"type": "attachment_extension", "value": item.get("extension"), "source": "sitegraph"}
                for item in attachments
                if item.get("extension")
            ],
        ],
        "synonyms": unique_strings([*tags, title.replace(" ", ""), section_path.replace(" / ", "")], limit=32),
        "rule_guard": {
            "restricted": False,
            "sensitive": False,
            "low_evidence": provenance.get("content_status") == "low_content",
            "duplicate": False,
            "expired": False,
            "evergreen": classification["lifecycle"] == "evergreen",
            "risk_flags": [],
            "allow_llm": False,
            "allow_full_text_display": True,
            "review_required": False,
        },
        "semantic_mode": "sitegraph_rule",
        "semantic_pipeline_version": "sitegraph-ingest-v1",
        "field_sources": {
            "category": "sitegraph_rule",
            "domain": "sitegraph_rule",
            "intent": "sitegraph_rule",
            "lifecycle": "sitegraph_rule",
            "summary": "sitegraph_content",
            "attachments": "sitegraph_attachment_metadata",
        },
        "raw_field_presence": {
            "title": bool(title),
            "content": bool(content),
            "published_at": bool(published_at),
            "publisher": bool(publisher),
            "attachments": bool(attachments),
        },
        "sitegraph_provenance": provenance,
        "task_frames": [],
    }
    frame = build_task_frame(document)
    if frame:
        document["task_frames"] = [frame]
    return document


def summarize_content(content: str, fallback: str, length: int = 220) -> str:
    text = normalize_space(content)
    if not text:
        return fallback
    return text[:length]


def slim_document(document: dict[str, Any], max_content_chars: int = 160) -> dict[str, Any]:
    content = normalize_space(str(document.get("content") or ""))
    attachments = [
        {
            "name": str(item.get("name") or ""),
            "url": str(item.get("url") or ""),
            "type": item.get("type"),
            "extension": item.get("extension"),
            "role": item.get("role"),
            "description": item.get("description"),
            "sensitive": bool(item.get("sensitive", False)),
            "parent_url": str(item.get("parent_url") or ""),
            "section_path": str(item.get("section_path") or ""),
            "metadata_only": True,
        }
        for item in document.get("attachments", [])
        if isinstance(item, dict)
    ]
    attachment_terms = unique_strings(
        [
            *(item.get("name") for item in attachments),
            *(item.get("extension") for item in attachments),
            *(item.get("parent_url") for item in attachments),
            *(item.get("section_path") for item in attachments),
        ],
        limit=80,
    )
    provenance = document.get("sitegraph_provenance") if isinstance(document.get("sitegraph_provenance"), dict) else {}
    slim_provenance = {
        "site_id": provenance.get("site_id"),
        "section_id": provenance.get("section_id"),
        "section_name": provenance.get("section_name"),
        "section_type": provenance.get("section_type"),
        "nav_path": provenance.get("nav_path") or [],
        "url_outcome": provenance.get("url_outcome"),
        "content_status": provenance.get("content_status"),
        "official": provenance.get("official", True),
    }
    slim = {
        "id": document["id"],
        "kind": document["kind"],
        "source_id": document["source_id"],
        "channel_id": document["channel_id"],
        "channel": document["channel"],
        "title": document["title"],
        "url": document["url"],
        "source": document["source"],
        "source_domain": document["source_domain"],
        "source_type": document["source_type"],
        "category": document["category"],
        "domain": document["domain"],
        "intent": document["intent"],
        "lifecycle": document["lifecycle"],
        "audience": list(document.get("audience", ["本科生"])),
        "published_at": document.get("published_at"),
        "content": normalize_space(" ".join([content[:max_content_chars], document.get("channel") or "", *attachment_terms])),
        "summary": document.get("summary"),
        "tags": unique_strings([*(document.get("tags") or []), *attachment_terms], limit=12),
        "hash": document["hash"],
        "semantic_mode": "sitegraph_rule",
        "sitegraph_provenance": slim_provenance,
    }
    optional_fields = {
        "deadline": document.get("deadline"),
        "action_type": document.get("action_type"),
        "publisher": document.get("publisher"),
    }
    for key, value in optional_fields.items():
        if value not in (None, "", [], {}):
            slim[key] = value
    if document.get("status") and document.get("status") != "ok":
        slim["status"] = document.get("status")
    if document.get("action_required"):
        slim["action_required"] = True
        if document.get("action_summary"):
            slim["action_summary"] = document.get("action_summary")
    if document.get("sensitive"):
        slim["sensitive"] = True
    if document.get("review_required"):
        slim["review_required"] = True
    if document.get("sensitive_types"):
        slim["sensitive_types"] = list(document.get("sensitive_types", []))
    if document.get("risk_flags"):
        slim["risk_flags"] = list(document.get("risk_flags", []))
    return slim


def build_query_aliases() -> dict[str, Any]:
    config_path = BASE_DIR / "config" / "query_aliases.json"
    aliases = read_json(config_path) if config_path.exists() else {}
    if not isinstance(aliases, dict):
        aliases = {}
    merged = dict(aliases)
    for key, payload in EXTRA_QUERY_ALIASES.items():
        current = merged.get(key) if isinstance(merged.get(key), dict) else {}
        merged[key] = {
            **current,
            "aliases": unique_strings([*(current.get("aliases", []) if isinstance(current, dict) else []), *payload["aliases"]]),
            "domains": unique_strings([*(current.get("domains", []) if isinstance(current, dict) else []), *payload["domains"]]),
            "intents": unique_strings([*(current.get("intents", []) if isinstance(current, dict) else []), *payload["intents"]]),
        }
    return merged


def build_documents(package: dict[str, Any]) -> dict[str, Any]:
    manifest = package["manifest"]
    sections = package["sections"]
    list_pages = package["list_pages"]
    detail_pages = package["detail_pages"]
    attachments = package["attachments"]
    external_links = package["external_links"]
    edges = package["edges"]

    sections_by_id = {str(row.get("section_id")): row for row in sections if row.get("section_id")}
    sections_by_url = {str(row.get("url")): row for row in sections if row.get("url")}
    list_section_by_url = {
        str(row.get("url")): sections_by_id.get(str(row.get("section_id")))
        for row in list_pages
        if row.get("url")
    }
    detail_by_url = {str(row.get("url")): row for row in detail_pages if row.get("url")}
    detail_urls = set(detail_by_url)

    attachments_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    attachment_outcomes = manifest.get("url_outcomes") if isinstance(manifest.get("url_outcomes"), dict) else {}
    for attachment in attachments:
        parent_url = str(attachment.get("parent_url") or "")
        attachments_by_parent[parent_url].append(attachment)

    documents: list[dict[str, Any]] = []
    outcomes: dict[str, Any] = {
        "detail_page_records": [],
        "direct_attachment_records": [],
        "external_record_only": [],
        "external_system_records": [],
        "utility_link_records": [],
    }

    for page in detail_pages:
        url = str(page.get("url") or "")
        section = sections_by_id.get(str(page.get("section_id") or ""))
        parent_attachments = [
            make_attachment_metadata(item, section, normalize_space(page.get("title")))
            for item in attachments_by_parent.get(url, [])
        ]
        title = normalize_space(page.get("title") or url)
        content = normalize_space(page.get("content_text") or title)
        provenance = {
            "site_id": "jwc",
            "page_id": str(page.get("page_id") or sha1_text(url)),
            "page_type": page.get("page_type"),
            "url_outcome": (manifest.get("url_outcomes") or {}).get(url, {}).get("outcome") if isinstance(manifest.get("url_outcomes"), dict) else None,
            "official": True,
            "source_files": ["detail_pages.jsonl", "sections.json", "attachments.jsonl", "manifest.json"],
            "section_id": str(page.get("section_id") or ""),
            "section_name": str((section or {}).get("name") or ""),
            "section_type": str((section or {}).get("section_type") or ""),
            "nav_path": (section or {}).get("nav_path") or [],
            "business_tags": section_tags(section),
            "content_status": page.get("content_status"),
            "extraction_strategy": page.get("extraction_strategy"),
            "attachment_count": len(parent_attachments),
            "view_count": page.get("view_count"),
        }
        doc_id = f"sitegraph-jwc-detail-{str(page.get('page_id') or sha1_text(url))}"
        document = make_common_document(
            doc_id=doc_id,
            kind="notice",
            title=title,
            url=url,
            section=section,
            content=content,
            summary=summarize_content(content, title),
            published_at=str(page.get("published_at") or "") or None,
            publisher=str(page.get("publisher") or "") or None,
            attachments=parent_attachments,
            provenance=provenance,
        )
        documents.append(document)
        outcomes["detail_page_records"].append({"url": url, "document_id": doc_id, "outcome": "search_record"})

    for attachment in attachments:
        parent_url = str(attachment.get("parent_url") or "")
        if parent_url in detail_urls:
            continue
        section = list_section_by_url.get(parent_url) or sections_by_url.get(parent_url)
        outcome = attachment_outcomes.get(str(attachment.get("url") or ""), {}) if isinstance(attachment_outcomes, dict) else {}
        metadata = make_attachment_metadata(attachment, section)
        title = normalize_space(attachment.get("name") or attachment.get("url") or "附件")
        parent_label = section_label(section)
        doc_id = f"sitegraph-jwc-attachment-{str(attachment.get('attachment_id') or sha1_text(str(attachment.get('url') or title)))}"
        content = normalize_space(" ".join([title, metadata.get("extension") or "", parent_url, parent_label, "metadata only"]))
        provenance = {
            "site_id": "jwc",
            "page_id": str(attachment.get("attachment_id") or sha1_text(str(attachment.get("url") or title))),
            "page_type": "direct_attachment_metadata",
            "url_outcome": outcome.get("outcome") or "attachment_metadata_only",
            "official": True,
            "source_files": ["attachments.jsonl", "list_pages.jsonl", "sections.json", "manifest.json"],
            "section_id": metadata.get("section_id") or "",
            "section_name": str((section or {}).get("name") or ""),
            "section_type": str((section or {}).get("section_type") or ""),
            "nav_path": (section or {}).get("nav_path") or [],
            "business_tags": section_tags(section),
            "content_status": "metadata_only",
            "attachment_count": 1,
            "parent_url": parent_url,
        }
        document = make_common_document(
            doc_id=doc_id,
            kind="resource",
            title=title,
            url=str(attachment.get("url") or parent_url),
            section=section,
            content=content,
            summary=f"附件元数据：{title}",
            published_at=None,
            publisher="本科生院 / 教务处",
            attachments=[metadata],
            provenance=provenance,
            is_resource=True,
        )
        documents.append(document)
        outcomes["direct_attachment_records"].append(
            {"url": attachment.get("url"), "document_id": doc_id, "parent_url": parent_url, "outcome": "metadata_search_record"}
        )

    for link in external_links:
        category = str(link.get("category") or "")
        label = normalize_space(link.get("label") or link.get("url") or "外部链接")
        source_section = sections_by_id.get(str(link.get("source_section_id") or ""))
        record = {
            "url": link.get("url"),
            "label": label,
            "category": category,
            "source_url": link.get("source_url"),
            "source_section_id": link.get("source_section_id"),
            "outcome": "record_only",
        }
        if category == "external_system_link":
            doc_id = f"sitegraph-jwc-external-system-{str(link.get('external_id') or sha1_text(str(link.get('url') or label)))}"
            content = normalize_space(" ".join([label, str(link.get("url") or ""), "综合信息服务 外部系统 record only"]))
            provenance = {
                "site_id": "jwc",
                "page_id": str(link.get("external_id") or sha1_text(str(link.get("url") or label))),
                "page_type": "external_system_record",
                "url_outcome": "external_system_link_recorded",
                "official": True,
                "source_files": ["external_links.jsonl", "manifest.json"],
                "section_id": str(link.get("source_section_id") or "jwc_home_module_8c416cb0a096"),
                "section_name": str((source_section or {}).get("name") or "综合信息服务"),
                "section_type": str((source_section or {}).get("section_type") or "homepage_module"),
                "nav_path": (source_section or {}).get("nav_path") or ["首页", "综合信息服务"],
                "business_tags": section_tags(source_section),
                "content_status": "record_only",
                "external_category": category,
                "source_url": link.get("source_url"),
            }
            document = make_common_document(
                doc_id=doc_id,
                kind="resource",
                title=label,
                url=str(link.get("url") or ""),
                section=source_section or sections_by_id.get("jwc_home_module_8c416cb0a096"),
                content=content,
                summary=f"JWC 记录的外部系统链接：{label}",
                published_at=str(link.get("recorded_at") or "") or None,
                publisher="本科生院 / 教务处",
                attachments=[],
                provenance=provenance,
                is_resource=True,
            )
            document["domain"] = "academic"
            document["intent"] = "read"
            document["category"] = "资料"
            document["action_required"] = False
            document["action_type"] = None
            document["action_summary"] = None
            document["required_materials"] = []
            document["task_frames"] = []
            documents.append(document)
            record["document_id"] = doc_id
            outcomes["external_system_records"].append(record)
        else:
            outcomes["external_record_only"].append(record)

    utility_labels = {"考试信息查询"}
    for edge in edges:
        label = normalize_space(edge.get("anchor_text"))
        if label not in utility_labels:
            continue
        target_url = str(edge.get("to_url") or "")
        section = sections_by_url.get(target_url) or list_section_by_url.get(target_url)
        doc_id = f"sitegraph-jwc-utility-link-{str(edge.get('edge_id') or sha1_text(target_url + label))}"
        provenance = {
            "site_id": "jwc",
            "page_id": str(edge.get("edge_id") or sha1_text(target_url + label)),
            "page_type": "homepage_utility_link_record",
            "url_outcome": "crawled_list_ok",
            "official": True,
            "source_files": ["edges.jsonl", "sections.json", "manifest.json"],
            "section_id": str((section or {}).get("section_id") or ""),
            "section_name": str((section or {}).get("name") or label),
            "section_type": str((section or {}).get("section_type") or "section_list_page"),
            "nav_path": (section or {}).get("nav_path") or ["首页", label],
            "business_tags": section_tags(section),
            "content_status": "record_only",
            "source_url": edge.get("from_url"),
        }
        document = make_common_document(
            doc_id=doc_id,
            kind="resource",
            title=label,
            url=target_url,
            section=section,
            content=f"{label} {target_url} 首页 综合信息服务",
            summary=f"JWC 首页记录的入口：{label}",
            published_at=None,
            publisher="本科生院 / 教务处",
            attachments=[],
            provenance=provenance,
            is_resource=True,
        )
        document["domain"] = "exam"
        document["intent"] = "read"
        document["category"] = "考试"
        document["action_required"] = False
        document["action_type"] = None
        document["action_summary"] = None
        document["task_frames"] = []
        documents.append(document)
        outcomes["utility_link_records"].append({"url": target_url, "label": label, "document_id": doc_id, "outcome": "search_record"})

    ids = [str(item.get("id")) for item in documents]
    duplicates = [doc_id for doc_id, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate generated document ids: {duplicates[:10]}")

    return {"documents": documents, "outcomes": outcomes}


def write_public_index(package: dict[str, Any], documents: list[dict[str, Any]], outcomes: dict[str, Any], *, shard_size: int) -> dict[str, Any]:
    if PUBLIC_SITEGRAPH_DIR.exists():
        shutil.rmtree(PUBLIC_SITEGRAPH_DIR)
    PUBLIC_SITEGRAPH_DIR.mkdir(parents=True, exist_ok=True)

    full_shards: list[dict[str, Any]] = []
    for index in range(0, len(documents), shard_size):
        shard_number = index // shard_size
        shard_docs = documents[index : index + shard_size]
        shard_name = f"documents.{shard_number:03d}.json"
        shard_path = PUBLIC_SITEGRAPH_DIR / shard_name
        write_json(shard_path, shard_docs, compact=True)
        full_shards.append(
            {
                "path": f"index/sitegraph/jwc/{shard_name}",
                "count": len(shard_docs),
                "full_text": True,
            }
        )

    slim_docs = [slim_document(document) for document in documents]
    write_json(PUBLIC_INDEX_DIR / "documents.json", slim_docs, compact=True)
    write_json(PUBLIC_INDEX_DIR / "task_frames.json", [frame for doc in documents for frame in doc.get("task_frames", [])], compact=True)
    write_json(PUBLIC_INDEX_DIR / "query_aliases.json", build_query_aliases())
    ontology_config = BASE_DIR / "config" / "ontology.json"
    write_json(PUBLIC_INDEX_DIR / "ontology.json", read_json(ontology_config) if ontology_config.exists() else {})

    source_counts = Counter(str(document.get("source_id")) for document in documents)
    channel_counts = Counter(str(document.get("channel_id")) for document in documents)
    semantic_mode_counts = Counter(str(document.get("semantic_mode")) for document in documents)
    task_frames = [frame for doc in documents for frame in doc.get("task_frames", [])]
    detail_record_count = sum(1 for document in documents if document["id"].startswith("sitegraph-jwc-detail-"))
    direct_attachment_count = sum(1 for document in documents if document["id"].startswith("sitegraph-jwc-attachment-"))
    external_system_count = sum(1 for document in documents if document["id"].startswith("sitegraph-jwc-external-system-"))
    utility_link_count = sum(1 for document in documents if document["id"].startswith("sitegraph-jwc-utility-link-"))
    attachment_metadata_count = sum(len(document.get("attachments") or []) for document in documents)
    upstream_counts = dict(package["actual_counts"])
    manifest = {
        "generated_at": now_iso(),
        "total_documents": len(documents),
        "strategy": "sitegraph-backed-jwc-v1",
        "semantic_pipeline_version": "sitegraph-ingest-v1",
        "llm_schema_version": "sitegraph-rule-v1",
        "llm_enabled": False,
        "llm_provider": None,
        "llm_model": None,
        "source_count": 1,
        "channel_count": len(channel_counts),
        "audited_channel_count": upstream_counts["sections"],
        "production_channel_count": upstream_counts["sections"],
        "failed_channel_count": 0,
        "task_frame_count": len(task_frames),
        "documents_with_task_frame": sum(1 for document in documents if document.get("task_frames")),
        "semantic_mode_counts": dict(semantic_mode_counts),
        "field_source_counts": {"sitegraph_rule": len(documents)},
        "review_required_count": 0,
        "low_evidence_count": sum(1 for document in documents if (document.get("rule_guard") or {}).get("low_evidence")),
        "old_source_channel_production_enabled": False,
        "github_resource_production_enabled": False,
        "exam_vertical_preserved": True,
        "sitegraph": {
            "site_id": "jwc",
            "source": str(package.get("source_index_dir") or DEFAULT_SITEGRAPH_INDEX),
            "actual_source": str(package.get("source_index_dir") or ""),
            "truth_counts": upstream_counts,
            "quality": package["manifest"].get("quality"),
            "upstream_generated_at": package["manifest"].get("generated_at"),
            "detail_page_records": detail_record_count,
            "direct_attachment_records": direct_attachment_count,
            "attachment_metadata_records": attachment_metadata_count,
            "external_system_records": external_system_count,
            "utility_link_records": utility_link_count,
            "shards": full_shards,
            "default_index": "index/documents.json",
            "full_text_policy": "default index is slim; full JWC shards load in background",
            "attachment_policy": "metadata_only",
            "external_link_policy": "record_only",
        },
        "sources": [
            {
                "id": "jwc",
                "name": "本科生院 / 教务处",
                "domain": "jwc.njupt.edu.cn",
                "source_type": "central_admin",
                "status": "ok",
                "documents": source_counts["jwc"],
                "last_fetch_at": package["manifest"].get("generated_at"),
                "channels": [
                    {
                        "id": channel_id,
                        "name": channel_id,
                        "status": "ok",
                        "documents": count,
                    }
                    for channel_id, count in sorted(channel_counts.items())
                ],
            }
        ],
    }
    write_json(PUBLIC_INDEX_DIR / "manifest.json", manifest)
    write_json(PUBLIC_SITEGRAPH_DIR / "manifest.json", manifest)
    write_json(PUBLIC_SITEGRAPH_DIR / "outcomes.json", outcomes, compact=True)
    return manifest


def ingest_sitegraph(index_dir: Path, *, shard_size: int = 1000) -> dict[str, Any]:
    package = validate_sitegraph_package(index_dir)
    package["source_index_dir"] = str(index_dir)
    built = build_documents(package)
    documents = built["documents"]
    outcomes = built["outcomes"]
    manifest = write_public_index(package, documents, outcomes, shard_size=shard_size)
    return {
        "sitegraph_index": str(index_dir),
        "generated_documents": len(documents),
        "detail_page_records": manifest["sitegraph"]["detail_page_records"],
        "direct_attachment_records": manifest["sitegraph"]["direct_attachment_records"],
        "attachment_metadata_records": manifest["sitegraph"]["attachment_metadata_records"],
        "external_system_records": manifest["sitegraph"]["external_system_records"],
        "utility_link_records": manifest["sitegraph"]["utility_link_records"],
        "truth_counts": manifest["sitegraph"]["truth_counts"],
        "shards": manifest["sitegraph"]["shards"],
        "public_index": str(PUBLIC_INDEX_DIR),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build njupt-search public/index from the JWC sitegraph package.")
    parser.add_argument("--sitegraph-index", type=Path, default=DEFAULT_SITEGRAPH_INDEX, help="Path to njupt-site-graph/data/sites/jwc/index")
    parser.add_argument("--shard-size", type=int, default=1000, help="Number of full documents per sitegraph shard")
    args = parser.parse_args()
    summary = ingest_sitegraph(args.sitegraph_index.resolve(), shard_size=args.shard_size)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
