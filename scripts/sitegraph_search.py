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
    "s": 60.0,
    "g": 45.0,
    "b": 12.0,
}


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
    return {
        "manifest": manifest,
        "doc_meta": read_json(PUBLIC_INDEX_DIR / "doc_meta.json"),
        "inverted": read_json(PUBLIC_INDEX_DIR / "inverted_index.json"),
        "aliases": read_json(PUBLIC_INDEX_DIR / "query_aliases.json"),
    }


def load_shards_for_indices(manifest: dict[str, Any], indices: set[int]) -> dict[int, dict[str, Any]]:
    shard_paths = [item["path"] for item in manifest["sitegraph"]["full_shards"]]
    docs_by_index: dict[int, dict[str, Any]] = {}
    wanted_shards = {index // 1000 for index in indices}
    for shard_index in wanted_shards:
        if shard_index < 0 or shard_index >= len(shard_paths):
            continue
        payload = read_json(BASE_DIR / "public" / shard_paths[shard_index])
        for doc in payload:
            docs_by_index[int(doc["doc_index"])] = doc
    return docs_by_index


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
    return max(0.0, 30.0 - min(days, 365.0) / 365.0 * 30.0)


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
    score += freshness_score(document)

    ranked = dict(document)
    ranked["score"] = round(score, 4)
    ranked["score_reason"] = "；".join(reasons or ["倒排候选"])
    return ranked


def recall_documents(query: str, *, limit: int = 20, candidate_limit: int = 120) -> list[dict[str, Any]]:
    index = load_index()
    manifest = index["manifest"]
    doc_meta = index["doc_meta"]
    inverted_tokens = index["inverted"]["tokens"]
    terms = tokens_for_query(query, index["aliases"])
    scores: dict[int, float] = {}
    for term in terms:
        postings = inverted_tokens.get(term)
        if not isinstance(postings, dict):
            continue
        for field, ids in postings.items():
            weight = FIELD_WEIGHTS.get(field, 8.0)
            for doc_index in ids:
                scores[int(doc_index)] = scores.get(int(doc_index), 0.0) + weight + min(len(term), 8)

    normalized_query = normalize_text(query)
    if len(scores) < 8:
        for meta in doc_meta:
            haystack = text_blob(meta, "title", "summary", "section", "nav_path_text", "tags")
            if normalized_query and normalized_query in haystack:
                index_id = int(meta["doc_index"])
                scores[index_id] = scores.get(index_id, 0.0) + 90.0

    if not scores:
        return []

    candidate_indices = {
        doc_index
        for doc_index, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:candidate_limit]
    }
    full_docs = load_shards_for_indices(manifest, candidate_indices)
    ranked = [
        rank_document(full_docs[doc_index], query, terms, scores.get(doc_index, 0.0))
        for doc_index in candidate_indices
        if doc_index in full_docs
    ]
    ranked.sort(key=lambda item: (-float(item.get("score") or 0), str(item.get("published_at") or ""), str(item.get("id") or "")))
    return ranked[:limit]
