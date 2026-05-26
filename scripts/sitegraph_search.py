from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
PUBLIC_INDEX_DIR = BASE_DIR / "public" / "index"

FIELD_WEIGHTS = {
    "t": 120.0,
    "a": 95.0,
    "e": 95.0,
    "y": 95.0,
    "s": 60.0,
    "n": 55.0,
    "g": 45.0,
    "m": 16.0,
    "c": 10.0,
}

DEFAULT_MAX_SHARD_LOADS = 32


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"\s+", "", text)


def tokens_for_query(query: str, aliases: dict[str, Any]) -> list[str]:
    candidates = [query]
    normalized_query = normalize_text(query)
    for key, payload in aliases.items():
        terms = [key]
        if isinstance(payload, dict) and isinstance(payload.get("aliases"), list):
            terms.extend(str(item) for item in payload["aliases"])
        if any(normalize_text(term) and normalize_text(term) in normalized_query for term in terms):
            candidates.extend(terms)
    tokens: set[str] = set()
    for candidate in candidates:
        text = normalize_text(candidate)
        if len(text) >= 2:
            tokens.add(text)
        for match in re.finditer(r"[\u4e00-\u9fff]{2,}|[a-z0-9][a-z0-9._-]{1,}", text):
            part = match.group(0)
            if re.fullmatch(r"[\u4e00-\u9fff]+", part):
                for size in range(2, min(5, len(part)) + 1):
                    for index in range(0, len(part) - size + 1):
                        tokens.add(part[index : index + size])
            else:
                tokens.add(part)
    return sorted(tokens, key=len, reverse=True)


def load_index() -> dict[str, Any]:
    manifest = read_json(PUBLIC_INDEX_DIR / "manifest.json")
    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}

    def artifact(name: str) -> Any:
        entry = artifacts.get(name)
        if not isinstance(entry, dict) or not entry.get("path"):
            raise FileNotFoundError(f"manifest.artifacts.{name}.path is missing")
        return read_json(BASE_DIR / "public" / str(entry["path"]))

    return {
        "manifest": manifest,
        "doc_meta": artifact("doc_meta_light"),
        "light_inverted": artifact("light_inverted_index"),
        "body_inverted": None,
        "aliases": artifact("query_aliases"),
    }


def load_body_index(index: dict[str, Any]) -> dict[str, Any]:
    if index.get("body_inverted") is not None:
        return index["body_inverted"]
    manifest = index["manifest"]
    entry = manifest["artifacts"]["body_inverted_index"]
    index["body_inverted"] = read_json(BASE_DIR / "public" / str(entry["path"]))
    return index["body_inverted"]


def shard_path_for_meta(manifest: dict[str, Any], meta: dict[str, Any]) -> str:
    shard = meta.get("shard") if isinstance(meta.get("shard"), dict) else {}
    path = str(shard.get("path") or "")
    if path:
        return path
    shard_id = str(shard.get("shard_id") or "")
    for item in ((manifest.get("sitegraph") or {}).get("full_shards") or []):
        if isinstance(item, dict) and item.get("shard_id") == shard_id:
            return str(item.get("path") or "")
    return ""


def load_shards_for_indices(
    manifest: dict[str, Any],
    doc_meta: list[dict[str, Any]],
    indices: set[int],
) -> tuple[dict[int, dict[str, Any]], set[str]]:
    docs_by_index: dict[int, dict[str, Any]] = {}
    wanted_paths: set[str] = set()
    for index in indices:
        if index < 0 or index >= len(doc_meta):
            continue
        path = shard_path_for_meta(manifest, doc_meta[index])
        if path:
            wanted_paths.add(path)
    for path in wanted_paths:
        payload = read_json(BASE_DIR / "public" / path)
        for doc in payload:
            docs_by_index[int(doc["doc_index"])] = doc
    return docs_by_index, wanted_paths


def text_blob(document: dict[str, Any], *fields: str) -> str:
    values: list[str] = []
    for field in fields:
        value = document.get(field)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        elif value is not None:
            values.append(str(value))
    return normalize_text(" ".join(values))


def freshness_score(document: dict[str, Any]) -> float:
    if document.get("facet") not in {"notice_article", "exam", "news"}:
        return 0.0
    raw = document.get("published_at")
    if not raw:
        return 0.0
    try:
        published = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    days = max(0.0, (datetime.now(timezone.utc) - published).total_seconds() / 86400)
    return max(0.0, 600.0 - min(days, 3650.0) / 3650.0 * 600.0)


def rank_document(document: dict[str, Any], query: str, terms: list[str], light_score: float) -> dict[str, Any]:
    normalized_query = normalize_text(query)
    title = text_blob(document, "title")
    section = text_blob(document, "section", "nav_path_text")
    summary = text_blob(document, "summary")
    content = text_blob(document, "content")
    tags = text_blob(document, "tags")
    external = title + text_blob(document, "url") if document.get("record_type") == "external" else ""
    attachment = normalize_text(" ".join(
        " ".join(str(attachment.get(field) or "") for field in ("name", "extension", "section", "parent_url"))
        for attachment in document.get("attachments") or []
    ))

    score = light_score
    reasons: list[str] = []
    if normalized_query and title == normalized_query:
        score += 5000
        reasons.append("标题精确")
    elif normalized_query and normalized_query in title:
        score += 520
        reasons.append("标题包含")
    if normalized_query and normalized_query in attachment:
        score += 360
        reasons.append("附件名命中")
    if normalized_query and normalized_query in external:
        score += 360
        reasons.append("外部系统/外链命中")
    if normalized_query and normalized_query in section:
        score += 180
        reasons.append("栏目路径命中")
    if normalized_query and normalized_query in content:
        score += 120
        reasons.append("正文命中")
    if normalized_query and normalized_query in tags:
        score += 80
        reasons.append("标签命中")

    matched_terms = []
    for term in terms[:12]:
        if term in title:
            score += 80
            matched_terms.append(term)
        elif term in attachment:
            score += 70
            matched_terms.append(term)
        elif term in external:
            score += 65
            matched_terms.append(term)
        elif term in section:
            score += 45
            matched_terms.append(term)
        elif term in summary or term in content:
            score += 12
            matched_terms.append(term)
    if matched_terms:
        reasons.append("词项: " + "、".join(sorted(set(matched_terms), key=len, reverse=True)[:6]))

    if document.get("facet") == "system" and any(term in normalized_query for term in ("系统", "jwxt", "教务")):
        score += 1500
        reasons.append("系统入口")
    if document.get("facet") == "download" and any(term in normalized_query for term in ("附件", "下载", "xlsx", "xls", "表格")):
        score += 120
        reasons.append("下载资源")
    if document.get("facet") == "policy" and any(term in normalized_query for term in ("规章", "制度", "管理办法", "政策")):
        score += 900
        reasons.append("政策制度")
    if document.get("facet") == "workflow" and any(term in normalized_query for term in ("办事流程", "办理", "申请流程", "流程")):
        score += 900
        reasons.append("办事流程")
    if document.get("facet") == "exam" and any(term in normalized_query for term in ("考试", "期末", "慕课", "mooc")):
        score += 650
        reasons.append("考试相关")
    score += freshness_score(document)

    ranked = dict(document)
    ranked["score"] = round(score, 4)
    ranked["score_reason"] = "；".join(reasons or ["倒排候选"])
    return ranked


def apply_postings(scores: dict[int, float], inverted_tokens: dict[str, Any], terms: list[str]) -> None:
    for term in terms:
        postings = inverted_tokens.get(term)
        if not isinstance(postings, dict):
            continue
        for field, ids in postings.items():
            weight = FIELD_WEIGHTS.get(field, 8.0)
            for doc_index in ids:
                scores[int(doc_index)] = scores.get(int(doc_index), 0.0) + weight + min(len(term), 8)


def recall_documents_with_stats(
    query: str,
    *,
    limit: int = 20,
    candidate_limit: int = 120,
    max_shard_loads: int = DEFAULT_MAX_SHARD_LOADS,
) -> dict[str, Any]:
    index = load_index()
    doc_meta = index["doc_meta"]
    terms = tokens_for_query(query, index["aliases"])
    scores: dict[int, float] = {}
    apply_postings(scores, index["light_inverted"]["tokens"], terms)

    normalized_query = normalize_text(query)
    used_body_index = False
    if len(scores) < 24:
        body_index = load_body_index(index)
        apply_postings(scores, body_index["tokens"], terms)
        used_body_index = True

    if len(scores) < 8:
        for meta in doc_meta:
            haystack = text_blob(meta, "title", "section", "nav_path_text")
            if normalized_query and normalized_query in haystack:
                index_id = int(meta["doc_index"])
                scores[index_id] = scores.get(index_id, 0.0) + 90.0

    if not scores:
        return {"results": [], "stats": {"used_body_index": used_body_index, "loaded_shard_count": 0, "loaded_shard_paths": []}}

    selected_candidate_indices: list[int] = []
    seen_shard_paths: set[str] = set()
    for doc_index, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:candidate_limit]:
        if doc_index < 0 or doc_index >= len(doc_meta):
            continue
        path = shard_path_for_meta(index["manifest"], doc_meta[doc_index])
        is_new_shard = bool(path) and path not in seen_shard_paths
        if is_new_shard and len(seen_shard_paths) >= max_shard_loads and len(selected_candidate_indices) >= limit:
            continue
        selected_candidate_indices.append(doc_index)
        if is_new_shard:
            seen_shard_paths.add(path)
    full_docs, loaded_paths = load_shards_for_indices(index["manifest"], doc_meta, set(selected_candidate_indices))
    ranked = [
        rank_document(full_docs[doc_index], query, terms, scores.get(doc_index, 0.0))
        for doc_index in selected_candidate_indices
        if doc_index in full_docs
    ]
    ranked.sort(key=lambda item: (-float(item.get("score") or 0), str(item.get("published_at") or ""), str(item.get("id") or "")))
    return {
        "results": ranked[:limit],
        "stats": {
            "used_body_index": used_body_index,
            "loaded_shard_count": len(loaded_paths),
            "loaded_shard_paths": sorted(loaded_paths),
            "candidate_count": len(selected_candidate_indices),
        },
    }


def recall_documents(
    query: str,
    *,
    limit: int = 20,
    candidate_limit: int = 120,
    max_shard_loads: int = DEFAULT_MAX_SHARD_LOADS,
) -> list[dict[str, Any]]:
    return recall_documents_with_stats(
        query,
        limit=limit,
        candidate_limit=candidate_limit,
        max_shard_loads=max_shard_loads,
    )["results"]
