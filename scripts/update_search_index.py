import argparse
import base64
import fnmatch
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.parse import quote, urljoin, urlparse, urlunparse

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from indexer_config import (
    BASE_DIR, PUBLIC_DIR, INDEX_DIR, DOCUMENTS_PATH, MANIFEST_PATH, GITHUB_SOURCE_CONFIG_PATH,
    BEIJING_TZ, HEADERS, MAX_DOCS_PER_SOURCE, DETAIL_FETCH_LIMIT_PER_SOURCE, REQUEST_TIMEOUT,
    MIN_STUDENT_SCORE, GITHUB_TOKEN_ENV, GITHUB_API_BASE, GITHUB_FILE_SIZE_LIMIT_BYTES,
    NEGATIVE_KEYWORDS, SourceConfig, GitHubSourceConfig, SOURCES,
    JOB_API_BASE, JOB_STATION_CODE, CATEGORY_KEYWORDS,
    NAV_TITLES, STATIC_EXTENSIONS, ATTACHMENT_EXTENSIONS, POSITIVE_KEYWORDS
)
from llm_scorer import LLM_MODEL_NAME, LLM_SCHEMA_VERSION, analyze_document_with_llm, llm_enabled

_DOC_CACHE: dict[str, dict[str, Any]] = {}
_RUN_CONFIG: dict[str, Any] = {
    "force_llm": False,
    "no_llm": False,
    "llm_schema_version": LLM_SCHEMA_VERSION,
    "source_filter": set(),
    "llm_limit": None,
    "dry_run": False,
    "no_github": False,
}
_RUN_STATS: dict[str, int] = {
    "cache_reused": 0,
    "llm_reused": 0,
    "llm_attempted": 0,
    "llm_reprocessed": 0,
    "llm_failed": 0,
    "llm_fallback": 0,
    "llm_skipped_by_limit": 0,
    "restricted": 0,
}
from heuristics import (
    RESTRICTED_TEXT_PATTERNS, ACTION_KEYWORDS, SENSITIVE_PATTERNS, SENSITIVE_MATERIAL_PATTERNS,
    clean_text, parse_date, is_expired, is_restricted_content, parse_deadline_candidate,
    infer_deadline, infer_action, infer_attachment_role, enrich_attachment_metadata,
    detect_sensitive_info, is_low_evidence_content, metadata_only_summary
)
from semantic_model import (
    derive_legacy_category, extract_evidence, infer_domain, infer_intent, infer_lifecycle,
    normalize_domain, normalize_intent, normalize_source_type
)

SOURCE_PRIORITY = {
    "本科生院 / 教务处": 1.0,
    "研究生院": 0.98,
    "学生工作处": 0.96,
    "研究生工作部": 0.94,
    "创新创业教育学院": 0.92,
    "团委 / 青春南邮": 0.88,
    "就业信息网": 0.86,
    "图书馆": 0.78,
    "保卫处": 0.72,
    "后勤管理处": 0.72,
}

def load_document_cache() -> None:
    global _DOC_CACHE
    if os.path.exists(DOCUMENTS_PATH):
        try:
            with open(DOCUMENTS_PATH, "r", encoding="utf-8") as f:
                docs = json.load(f)
                for doc in docs:
                    if "hash" in doc:
                        _DOC_CACHE[doc["hash"]] = doc
                    if "cache_key" in doc:
                        _DOC_CACHE[doc["cache_key"]] = doc
        except Exception:
            pass



def get_beijing_time() -> datetime:
    return datetime.now(timezone.utc).astimezone(BEIJING_TZ)





def clamp01(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def cache_is_current(cached: dict[str, Any] | None) -> bool:
    if not cached:
        return False
    if _RUN_CONFIG["force_llm"] and not _RUN_CONFIG["no_llm"]:
        return False
    if cached.get("llm_schema_version") != active_llm_schema_version():
        return False
    if cache_needs_reprocessing(cached):
        return False
    if cached.get("status") == "restricted":
        return True
    llm_meta = cached.get("llm") if isinstance(cached.get("llm"), dict) else {}
    if _RUN_CONFIG["no_llm"] and llm_meta.get("used"):
        return False
    if runtime_llm_enabled() and not llm_meta.get("used"):
        return False
    return True


def cache_needs_reprocessing(cached: dict[str, Any]) -> bool:
    sensitive_types = {str(item) for item in cached.get("sensitive_types", [])}
    if cached.get("sensitive") and sensitive_types and sensitive_types.issubset(set(SENSITIVE_MATERIAL_PATTERNS)):
        return True
    return False


def cached_with_freshness(cached: dict[str, Any], published_at: str | None, now: datetime) -> dict[str, Any]:
    _RUN_STATS["cache_reused"] += 1
    llm_meta = cached.get("llm") if isinstance(cached.get("llm"), dict) else {}
    if llm_meta.get("used"):
        _RUN_STATS["llm_reused"] += 1
    fresh_at = published_at or cached.get("published_at")
    return {**cached, "freshness_score": calculate_freshness(fresh_at, now)}


def cached_documents_for_source_id(id_prefix: str) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for document in _DOC_CACHE.values():
        doc_id = str(document.get("id", ""))
        if doc_id.startswith(id_prefix):
            unique[doc_id] = document
    return list(unique.values())


def active_llm_schema_version() -> str:
    return str(_RUN_CONFIG.get("llm_schema_version") or LLM_SCHEMA_VERSION)


def runtime_llm_enabled() -> bool:
    return bool(not _RUN_CONFIG["no_llm"] and llm_enabled())


def source_selected(source_id: str) -> bool:
    filters = _RUN_CONFIG.get("source_filter") or set()
    return not filters or source_id in filters


def llm_cache_key(source_id: str, url: str, content: str, attachments: list[dict[str, Any]]) -> str:
    attachment_digest = document_hash(attachments)
    return document_hash(source_id, normalize_url(url), content, attachment_digest, active_llm_schema_version())


def analyze_with_runtime_llm(title: str, content: str, source_domain: str) -> dict[str, Any] | None:
    if _RUN_CONFIG["no_llm"] or not llm_enabled():
        _RUN_STATS["llm_fallback"] += 1
        return None

    llm_limit = _RUN_CONFIG.get("llm_limit")
    if llm_limit is not None and _RUN_STATS["llm_attempted"] >= int(llm_limit):
        _RUN_STATS["llm_skipped_by_limit"] += 1
        _RUN_STATS["llm_fallback"] += 1
        return None

    _RUN_STATS["llm_attempted"] += 1
    result = analyze_document_with_llm(
        title,
        content,
        source_domain,
        enabled=True,
        schema_version=active_llm_schema_version(),
    )
    if result:
        _RUN_STATS["llm_reprocessed"] += 1
    else:
        _RUN_STATS["llm_failed"] += 1
        _RUN_STATS["llm_fallback"] += 1
    return result


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, "", parsed.query, ""))


def same_domain(url: str, source: SourceConfig) -> bool:
    host = urlparse(url).netloc.lower()
    source_host = urlparse(source.base_url).netloc.lower()
    return host == source_host or host.endswith("." + source_host)


def extension_from_url(url: str) -> str:
    return os.path.splitext(urlparse(url).path.lower())[1]


def document_hash(*parts: Any) -> str:
    serialized = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:20]


def contains_relevant_keyword(text: str) -> bool:
    lowered = text.lower()
    all_keywords = POSITIVE_KEYWORDS + [keyword for keywords in CATEGORY_KEYWORDS.values() for keyword in keywords]
    return any(keyword.lower() in lowered for keyword in all_keywords)


def looks_like_notice_link(title: str, parent_text: str, url: str, now: datetime) -> bool:
    stripped_title = title.strip()
    lowered_title = stripped_title.lower()
    path = urlparse(url).path.lower()

    if stripped_title in NAV_TITLES or lowered_title in NAV_TITLES:
        return False
    if path.endswith("/main.htm") or path.endswith("main.htm") or path.endswith("list.htm"):
        return False
    if len(stripped_title) < 6:
        return False

    combined = f"{stripped_title} {parent_text} {url}"
    has_date = parse_date(combined, now) is not None
    return any(keyword.lower() in lowered for keyword in all_keywords)


def looks_like_notice_link(title: str, parent_text: str, url: str, now: datetime) -> bool:
    stripped_title = title.strip()
    lowered_title = stripped_title.lower()
    path = urlparse(url).path.lower()

    if stripped_title in NAV_TITLES or lowered_title in NAV_TITLES:
        return False
    if path.endswith("/main.htm") or path.endswith("main.htm") or path.endswith("list.htm"):
        return False
    if len(stripped_title) < 6:
        return False

    combined = f"{stripped_title} {parent_text} {url}"
    has_date = parse_date(combined, now) is not None
    has_detail_shape = bool(re.search(r"/20\d{2}/\d{4}/", path)) or path.endswith("page.htm")
    has_relevant_keyword = contains_relevant_keyword(combined)

    return has_detail_shape or (has_date and has_relevant_keyword)


def matches_source_patterns(url: str, title: str, source: SourceConfig) -> bool:
    values = (url, urlparse(url).path, title, f"{url} {title}")
    if source.include_patterns:
        include_hit = any(fnmatch.fnmatch(value, pattern) for pattern in source.include_patterns for value in values)
        if not include_hit:
            return False
    if source.exclude_patterns:
        exclude_hit = any(fnmatch.fnmatch(value, pattern) for pattern in source.exclude_patterns for value in values)
        if exclude_hit:
            return False
    return True


def discover_next_list_urls(soup: BeautifulSoup, list_url: str, source: SourceConfig) -> list[str]:
    urls: list[str] = []
    for anchor in soup.find_all("a"):
        text = clean_text(anchor.get_text(" ", strip=True))
        if "下一页" not in text:
            continue
        href = anchor.get("href")
        if not href:
            continue
        absolute_url = normalize_url(urljoin(list_url, href))
        if same_domain(absolute_url, source):
            urls.append(absolute_url)
    return urls


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, verify=False, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def post_json(url: str, body: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(url, json=body, headers=HEADERS, verify=False, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def normalize_title_for_dedupe(title: str) -> str:
    normalized = re.sub(r"^【[^】]+】", "", title)
    normalized = re.sub(r"^(关于|南京邮电大学)", "", normalized)
    normalized = re.sub(r"[，,。；;：:\s\"“”'‘’（）()《》<>·\-—_]+", "", normalized)
    return normalized.lower()


def llm_metadata(used: bool, confidence: float | None = None, review_required: bool = False) -> dict[str, Any]:
    return {
        "used": used,
        "model": LLM_MODEL_NAME if used else None,
        "prompt_version": active_llm_schema_version(),
        "confidence": confidence,
        "review_required": review_required,
    }


def derive_semantic_fields(
    title: str,
    content: str,
    default_category: str,
    source_weight: float,
    source_type: str,
    attachments: list[dict[str, Any]],
    published_at: str | None,
    now: datetime,
    llm_result: dict[str, Any] | None,
) -> dict[str, Any]:
    scoring_text = f"{title} {content}"
    rule_category = default_category if default_category in CATEGORY_KEYWORDS else infer_category(scoring_text)
    rule_student_score = calculate_student_score(scoring_text, source_weight)
    rule_importance_score = calculate_importance_score(scoring_text, rule_category, len(attachments), source_weight)
    fallback_action_required, fallback_action_type, fallback_action_summary = infer_action(scoring_text)
    fallback_deadline = infer_deadline(scoring_text, published_at, now)
    fallback_domain = infer_domain(scoring_text, rule_category, source_type)
    fallback_intent = infer_intent(scoring_text, fallback_action_required, len(attachments))
    fallback_evidence = extract_evidence(
        scoring_text,
        [fallback_action_type or "", fallback_deadline or "", rule_category, title],
    )

    if llm_result:
        domain = normalize_domain(llm_result.get("domain"), fallback_domain)
        intent = normalize_intent(llm_result.get("intent"), fallback_intent)
        category = derive_legacy_category(domain, intent, str(llm_result.get("category") or rule_category))
        llm_relevance = float(llm_result.get("student_relevance", 0.5))
        if llm_result.get("is_student_facing", True):
            student_score = clamp01(0.65 * llm_relevance + 0.35 * rule_student_score)
        else:
            student_score = clamp01(min(0.34, 0.65 * llm_relevance + 0.35 * rule_student_score))
        importance_score = clamp01(0.75 * float(llm_result.get("importance_score", 0.5)) + 0.25 * rule_importance_score)
        tags = [clean_text(str(tag)) for tag in llm_result.get("tags", []) if clean_text(str(tag))]
        summary = clean_text(str(llm_result.get("student_summary") or content[:180]))
        sub_category = llm_result.get("sub_category")
        deadline = llm_result.get("deadline") or fallback_deadline
        action_required = bool(llm_result.get("action_required", False)) or fallback_action_required
        action_type = llm_result.get("action_type") or fallback_action_type
        action_summary = llm_result.get("action_summary") or fallback_action_summary
        required_materials = [clean_text(str(item)) for item in llm_result.get("required_materials", []) if clean_text(str(item))]
        attachment_roles = llm_result.get("attachment_roles", [])
        sensitive = bool(llm_result.get("sensitive", False))
        sensitive_types = [clean_text(str(item)) for item in llm_result.get("sensitive_types", []) if clean_text(str(item))]
        risk_flags = [clean_text(str(item)) for item in llm_result.get("risk_flags", []) if clean_text(str(item))]
        evidence = [clean_text(str(item))[:180] for item in llm_result.get("evidence", []) if clean_text(str(item))] or fallback_evidence
        review_required = bool(llm_result.get("review_required", False))
        confidence = float(llm_result.get("confidence", 0.5))
        metadata = llm_metadata(True, confidence, review_required)
    else:
        domain = fallback_domain
        intent = fallback_intent
        category = rule_category
        student_score = rule_student_score
        importance_score = rule_importance_score
        tags = infer_tags(scoring_text, category)
        summary = content[:180]
        sub_category = None
        deadline = fallback_deadline
        action_required = fallback_action_required
        action_type = fallback_action_type
        action_summary = fallback_action_summary
        required_materials = []
        attachment_roles = []
        sensitive = False
        sensitive_types = []
        risk_flags = []
        evidence = fallback_evidence
        review_required = False
        metadata = llm_metadata(False)

    category = derive_legacy_category(domain, intent, category)
    attachments = enrich_attachment_metadata(attachments, attachment_roles)
    regex_sensitive, regex_sensitive_types = detect_sensitive_info(scoring_text, attachments)
    sensitive = sensitive or regex_sensitive
    sensitive_types = sorted(set(sensitive_types).union(regex_sensitive_types))
    actual_sensitive_types = set(regex_sensitive_types).union(
        item for item in sensitive_types if item not in SENSITIVE_MATERIAL_PATTERNS
    )
    material_only_types = set(sensitive_types).intersection(SENSITIVE_MATERIAL_PATTERNS)
    if sensitive and material_only_types and not actual_sensitive_types:
        sensitive = False
        risk_flags = sorted(set(risk_flags).union({"requires_sensitive_material"}))
    if is_low_evidence_content(content, attachments):
        review_required = True
        risk_flags = sorted(set(risk_flags).union({"low_evidence_content"}))
        if not fallback_deadline:
            action_required = False
            action_type = None
            action_summary = None
        summary = "该页面正文主要是附件列表，已保留标题和附件角色，请点击原文或附件确认具体流程。"
    if sensitive:
        risk_flags = sorted(set(risk_flags).union({"sensitive_personal_info"}))
        summary = metadata_only_summary()
        content = " ".join([title, *[str(item.get("name", "")) for item in attachments]])

    if category not in CATEGORY_KEYWORDS and category != "公告":
        category = "公告"
    if category not in tags:
        tags = [category, *tags]
    metadata["review_required"] = review_required

    return {
        "category": category,
        "domain": domain,
        "intent": intent,
        "lifecycle": infer_lifecycle(published_at, deadline, now),
        "evidence": evidence[:4],
        "confidence": metadata.get("confidence"),
        "sub_category": sub_category,
        "deadline": deadline,
        "action_required": action_required,
        "action_type": action_type,
        "action_summary": action_summary,
        "required_materials": required_materials,
        "sensitive": sensitive,
        "sensitive_types": sensitive_types,
        "review_required": review_required,
        "risk_flags": risk_flags,
        "content": content,
        "summary": summary,
        "attachments": attachments,
        "student_score": student_score,
        "importance_score": importance_score,
        "tags": tags[:10],
        "llm": metadata,
    }


def build_restricted_document(
    source: SourceConfig,
    title: str,
    url: str,
    published_at: str | None,
    content: str,
    now: datetime,
) -> dict[str, Any]:
    _RUN_STATS["restricted"] += 1
    digest = document_hash("restricted", title, url, content)
    scoring_text = f"{title} {content}"
    category = infer_category(scoring_text)
    domain = infer_domain(scoring_text, category, source.source_type)
    intent = infer_intent(scoring_text, False, 0)
    student_score = max(0.58, calculate_student_score(title, source.source_weight))
    return {
        "id": f"{source.id}-{digest}",
        "kind": "notice",
        "status": "restricted",
        "title": title,
        "url": url,
        "source": source.name,
        "source_domain": urlparse(source.base_url).netloc,
        "source_type": normalize_source_type(source.source_type),
        "category": category,
        "domain": domain,
        "intent": intent,
        "lifecycle": infer_lifecycle(published_at, None, now),
        "evidence": extract_evidence(scoring_text, ["校内", "登录", title]),
        "confidence": 0.35,
        "sub_category": None,
        "deadline": None,
        "action_required": False,
        "action_type": None,
        "action_summary": None,
        "required_materials": [],
        "sensitive": False,
        "sensitive_types": [],
        "review_required": True,
        "risk_flags": ["restricted_content"],
        "audience": list(source.audience),
        "published_at": published_at,
        "content": title,
        "summary": "该页面正文仅校内 IP 或登录后可访问，当前索引只保留标题和来源，请点击原文查看。",
        "attachments": [],
        "student_score": student_score,
        "freshness_score": calculate_freshness(published_at, now),
        "importance_score": calculate_importance_score(title, category, 0, source.source_weight),
        "source_weight": source.source_weight,
        "tags": infer_tags(scoring_text, category),
        "hash": digest,
        "cache_key": llm_cache_key(source.id, url, content, []),
        "llm_schema_version": active_llm_schema_version(),
        "llm": llm_metadata(False, review_required=True),
    }


from indexer_scoring import (
    calculate_freshness, infer_category, infer_tags, calculate_student_score,
    is_student_facing_document, calculate_importance_score
)


def extract_attachments(soup: BeautifulSoup, page_url: str) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if not href:
            continue
        absolute_url = normalize_url(urljoin(page_url, href))
        extension = extension_from_url(absolute_url)
        if extension not in ATTACHMENT_EXTENSIONS:
            continue
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        name = clean_text(anchor.get_text(" ", strip=True)) or os.path.basename(urlparse(absolute_url).path)
        attachments.append({"name": name, "url": absolute_url, "type": extension.lstrip(".")})
    return attachments[:8]


def extract_article_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    selectors = [
        ".wp_articlecontent",
        ".article",
        ".article_content",
        ".news_content",
        ".v_news_content",
        "#wp_content_w6_0",
        ".content",
        "main",
        "body",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = clean_text(node.get_text(" ", strip=True))
            if len(text) >= 20:
                return text[:2400]
    return clean_text(soup.get_text(" ", strip=True))[:2400]


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    return clean_text(BeautifulSoup(value, "html.parser").get_text(" ", strip=True))


def collect_candidates(source: SourceConfig, now: datetime) -> tuple[list[dict[str, str | None]], list[str]]:
    candidates: list[dict[str, str | None]] = []
    seen: set[str] = set()
    list_errors: list[str] = []
    pending = list(source.list_urls)
    visited_list_urls: set[str] = set()
    max_list_pages = max(1, len(source.list_urls) * source.max_pages)

    while pending and len(visited_list_urls) < max_list_pages:
        list_url = pending.pop(0)
        if list_url in visited_list_urls:
            continue
        visited_list_urls.add(list_url)
        try:
            html = fetch_html(list_url)
        except Exception as exc:
            list_errors.append(f"{list_url}: {exc}")
            continue
        soup = BeautifulSoup(html, "html.parser")

        for anchor in soup.find_all("a"):
            href = anchor.get("href")
            if not href:
                continue

            title = clean_text(anchor.get("title") or anchor.get_text(" ", strip=True))
            if len(title) < 4 or title in NAV_TITLES or title.lower() in NAV_TITLES:
                continue

            absolute_url = normalize_url(urljoin(list_url, href))
            parsed = urlparse(absolute_url)
            if parsed.scheme not in {"http", "https"} or not same_domain(absolute_url, source):
                continue

            extension = extension_from_url(absolute_url)
            if extension in STATIC_EXTENSIONS or extension in ATTACHMENT_EXTENSIONS:
                continue

            if absolute_url in seen:
                continue
            if not matches_source_patterns(absolute_url, title, source):
                continue

            parent_text = clean_text(anchor.parent.get_text(" ", strip=True)) if anchor.parent else title
            if not looks_like_notice_link(title, parent_text, absolute_url, now):
                continue

            seen.add(absolute_url)
            date_text = " ".join([title, parent_text, absolute_url])
            published_at = parse_date(date_text, now)
            
            if is_expired(published_at, now):
                continue

            candidates.append({
                "title": title,
                "url": absolute_url,
                "published_at": published_at,
            })

        if source.max_pages > 1:
            for next_url in discover_next_list_urls(soup, list_url, source):
                if next_url not in visited_list_urls and next_url not in pending:
                    pending.append(next_url)

    return candidates[:MAX_DOCS_PER_SOURCE * 2], list_errors[:8]


def enrich_candidate(source: SourceConfig, candidate: dict[str, str | None], now: datetime) -> dict[str, Any] | None:
    title = candidate["title"] or ""
    url = candidate["url"] or source.base_url
    published_at = candidate.get("published_at")
    content = title
    attachments: list[dict[str, str]] = []

    try:
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        title_node = (
            soup.select_one(".arti_title")
            or soup.select_one(".articleTitle")
            or soup.select_one(".news_title")
            or soup.find("h1")
        )
        page_title = clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
        if page_title and len(page_title) >= 4 and page_title not in NAV_TITLES:
            title = page_title
        content = extract_article_text(soup) or title
        attachments = extract_attachments(soup, url)
        published_at = published_at or parse_date(content, now)
    except Exception:
        content = title

    if is_expired(published_at, now):
        return None

    if is_restricted_content(content):
        return build_restricted_document(source, title, url, published_at, content, now)

    digest = document_hash(title, url, content, attachments)
    cache_key = llm_cache_key(source.id, url, content, attachments)
    cached = _DOC_CACHE.get(cache_key) or _DOC_CACHE.get(digest)
    if cache_is_current(cached):
        return cached_with_freshness(cached, published_at, now)

    llm_result = analyze_with_runtime_llm(title, content, urlparse(source.base_url).netloc)
    semantic = derive_semantic_fields(
        title, content, infer_category(f"{title} {content}"), source.source_weight, source.source_type,
        attachments, published_at, now, llm_result
    )

    freshness_score = calculate_freshness(published_at, now)

    return {
        "id": f"{source.id}-{digest}",
        "kind": "notice",
        "title": title,
        "url": url,
        "source": source.name,
        "source_domain": urlparse(source.base_url).netloc,
        "source_type": normalize_source_type(source.source_type),
        "category": semantic["category"],
        "domain": semantic["domain"],
        "intent": semantic["intent"],
        "lifecycle": semantic["lifecycle"],
        "evidence": semantic["evidence"],
        "confidence": semantic["confidence"],
        "sub_category": semantic["sub_category"],
        "deadline": semantic["deadline"],
        "action_required": semantic["action_required"],
        "action_type": semantic["action_type"],
        "action_summary": semantic["action_summary"],
        "required_materials": semantic["required_materials"],
        "sensitive": semantic["sensitive"],
        "sensitive_types": semantic["sensitive_types"],
        "review_required": semantic["review_required"],
        "risk_flags": semantic["risk_flags"],
        "audience": list(source.audience),
        "published_at": published_at,
        "content": semantic["content"],
        "summary": semantic["summary"],
        "attachments": semantic["attachments"],
        "student_score": semantic["student_score"],
        "freshness_score": freshness_score,
        "importance_score": semantic["importance_score"],
        "source_weight": source.source_weight,
        "tags": semantic["tags"],
        "hash": digest,
        "cache_key": cache_key,
        "llm_schema_version": active_llm_schema_version(),
        "llm": semantic["llm"],
    }


def build_job_document(
    source: SourceConfig,
    external_id: str,
    title: str,
    url: str,
    published_at: str | None,
    content: str,
    category: str,
    now: datetime,
) -> dict[str, Any] | None:
    if is_expired(published_at, now):
        return None
    digest = document_hash("job", external_id, title, url, content)

    cache_key = llm_cache_key(source.id, url, content, [])
    cached = _DOC_CACHE.get(cache_key) or _DOC_CACHE.get(digest)
    if cache_is_current(cached):
        return cached_with_freshness(cached, published_at, now)

    llm_result = analyze_with_runtime_llm(title, content, urlparse(source.base_url).netloc)
    semantic = derive_semantic_fields(
        title, content or title, category, source.source_weight, source.source_type,
        [], published_at, now, llm_result
    )
    semantic["student_score"] = max(0.68, semantic["student_score"])

    freshness_score = calculate_freshness(published_at, now)

    return {
        "id": f"{source.id}-{digest}",
        "kind": "notice",
        "title": title,
        "url": url,
        "source": source.name,
        "source_domain": urlparse(source.base_url).netloc,
        "source_type": normalize_source_type(source.source_type),
        "category": semantic["category"],
        "domain": semantic["domain"],
        "intent": semantic["intent"],
        "lifecycle": semantic["lifecycle"],
        "evidence": semantic["evidence"],
        "confidence": semantic["confidence"],
        "sub_category": semantic["sub_category"],
        "deadline": semantic["deadline"],
        "action_required": semantic["action_required"],
        "action_type": semantic["action_type"],
        "action_summary": semantic["action_summary"],
        "required_materials": semantic["required_materials"],
        "sensitive": semantic["sensitive"],
        "sensitive_types": semantic["sensitive_types"],
        "review_required": semantic["review_required"],
        "risk_flags": semantic["risk_flags"],
        "audience": list(source.audience),
        "published_at": published_at,
        "content": semantic["content"],
        "summary": semantic["summary"],
        "attachments": semantic["attachments"],
        "student_score": semantic["student_score"],
        "freshness_score": freshness_score,
        "importance_score": semantic["importance_score"],
        "source_weight": source.source_weight,
        "tags": semantic["tags"],
        "hash": digest,
        "cache_key": cache_key,
        "llm_schema_version": active_llm_schema_version(),
        "llm": semantic["llm"],
    }


def crawl_job_source(source: SourceConfig, now: datetime) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    meeting_body = {
        "current": 1,
        "xxxs": "",
        "fbsj": "",
        "ssxx": "",
        "keyword": "",
        "size": 10,
        "xxdm": JOB_STATION_CODE,
    }
    meeting_payload = post_json(f"{JOB_API_BASE}/getZphPageList", meeting_body)
    for item in meeting_payload.get("result", {}).get("records", [])[:10]:
        title = clean_text(str(item.get("zphmc", "")))
        if not title:
            continue
        start_time = clean_text(str(item.get("jbkssj", "")))
        end_time = clean_text(str(item.get("jbjssj", "")))
        location = clean_text(str(item.get("jbcd", "")))
        content = clean_text(" ".join([
            title,
            f"时间：{start_time} 至 {end_time}",
            f"地点：{location}",
            f"联系人：{item.get('lxr', '')}",
            f"电话：{item.get('lxdh', '')}",
        ]))
        external_id = str(item.get("zphid", ""))
        url = f"https://njupt.91job.org.cn/sub-station/recruitmentDetail?zphid={external_id}&xxdm={JOB_STATION_CODE}"
        doc = build_job_document(source, external_id, title, url, start_time[:10] or None, content, "就业", now)
        if doc:
            documents.append(doc)

    lecture_body = {
        "current": 1,
        "xxxs": "",
        "fbsj": "",
        "ssxx": "",
        "keyword": "",
        "size": 10,
        "xxdm": JOB_STATION_CODE,
    }
    lecture_payload = post_json(f"{JOB_API_BASE}/getXjhPageList", lecture_body)
    for item in lecture_payload.get("result", {}).get("records", [])[:8]:
        title = clean_text(str(item.get("xjhmc", "")))
        if not title:
            continue
        date = clean_text(str(item.get("jbrq", "")))
        time = clean_text(str(item.get("kssjd", "")) or str(item.get("jssjd", "")))
        location = clean_text(str(item.get("jbdd", "")))
        content = clean_text(" ".join([
            title,
            f"宣讲时间：{time}",
            f"地点：{location}",
            f"举办学校：{item.get('jbxx', '')}",
            f"联系人：{item.get('zplxr', '')}",
            f"电话：{item.get('lxdh', '')}",
            strip_html(str(item.get("xjhjs", ""))),
        ]))
        external_id = str(item.get("xjhid", ""))
        url = f"https://njupt.91job.org.cn/sub-station/lectureDetail?xjhid={external_id}&xxdm={JOB_STATION_CODE}"
        doc = build_job_document(source, external_id, title, url, date or None, content, "就业", now)
        if doc:
            documents.append(doc)

    return documents[:MAX_DOCS_PER_SOURCE]


def read_github_source_configs() -> tuple[GitHubSourceConfig, ...]:
    if not os.path.exists(GITHUB_SOURCE_CONFIG_PATH):
        return ()

    with open(GITHUB_SOURCE_CONFIG_PATH, "r", encoding="utf-8") as config_file:
        payload = json.load(config_file)

    raw_sources = payload.get("sources", []) if isinstance(payload, dict) else []
    sources: list[GitHubSourceConfig] = []
    for item in raw_sources:
        if not isinstance(item, dict):
            continue
        repo = clean_text(str(item.get("repo", "")))
        if "/" not in repo:
            continue
        include = item.get("include") if isinstance(item.get("include"), list) else ["README.md", "*.md", "docs/**/*.md"]
        exclude = item.get("exclude") if isinstance(item.get("exclude"), list) else []
        audience = item.get("audience") if isinstance(item.get("audience"), list) else ["本科生", "研究生"]
        sources.append(
            GitHubSourceConfig(
                repo=repo,
                label=clean_text(str(item.get("label") or repo)),
                category=clean_text(str(item.get("category") or "资料")),
                audience=tuple(str(value) for value in audience),
                include=tuple(str(value) for value in include),
                exclude=tuple(str(value) for value in exclude),
                max_files=max(1, min(int(item.get("max_files", 20)), 50)),
                source_weight=float(item.get("source_weight", 0.72)),
                enabled=bool(item.get("enabled", True)),
            )
        )
    return tuple(sources)


def github_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "njupt-search-indexer",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_api_get(endpoint: str, token: str | None) -> Any:
    response = requests.get(
        f"{GITHUB_API_BASE}{endpoint}",
        headers=github_headers(token),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def matches_path(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        normalized_pattern = pattern.replace("\\", "/")
        if "/" not in normalized_pattern and "/" in normalized:
            continue
        if fnmatch.fnmatch(normalized, normalized_pattern):
            return True
    return False


def select_github_files(source: GitHubSourceConfig, branch: str, token: str | None) -> list[dict[str, Any]]:
    tree_payload = github_api_get(
        f"/repos/{source.repo}/git/trees/{quote(branch, safe='')}?recursive=1",
        token,
    )
    files: list[dict[str, Any]] = []
    for item in tree_payload.get("tree", []):
        if item.get("type") != "blob":
            continue
        path = str(item.get("path", ""))
        size = int(item.get("size") or 0)
        if not path or size <= 0 or size > GITHUB_FILE_SIZE_LIMIT_BYTES:
            continue
        if source.exclude and matches_path(path, source.exclude):
            continue
        if not matches_path(path, source.include):
            continue
        files.append({"path": path, "size": size})

    files.sort(key=lambda file: (0 if file["path"].lower().endswith("readme.md") else 1, file["path"]))
    return files[: source.max_files]


def fetch_github_file_text(repo: str, branch: str, path: str, token: str | None) -> str:
    quoted_path = quote(path, safe="/")
    quoted_branch = quote(branch, safe="")
    payload = github_api_get(f"/repos/{repo}/contents/{quoted_path}?ref={quoted_branch}", token)
    content = payload.get("content", "")
    if payload.get("encoding") != "base64" or not isinstance(content, str):
        return ""
    return base64.b64decode(content).decode("utf-8", errors="replace")


def extract_markdown_title(path: str, text: str) -> str:
    for line in text.splitlines()[:50]:
        stripped = line.strip()
        if stripped.startswith("#"):
            title = clean_text(stripped.lstrip("#").strip())
            if title:
                return title
    return os.path.basename(path)


def normalize_markdown_text(text: str) -> str:
    without_fences = re.sub(r"```.*?```", " ", text, flags=re.S)
    without_markup = re.sub(r"[#>*_`|[\]()]+", " ", without_fences)
    return clean_text(without_markup)[:4000]


def build_github_document(
    source: GitHubSourceConfig,
    branch: str,
    path: str,
    text: str,
    repo_updated_at: str | None,
) -> dict[str, Any] | None:
    title = f"{source.label} · {extract_markdown_title(path, text)}"
    content = normalize_markdown_text(text) or title
    digest = document_hash("github", source.repo, branch, path, content)
    published_at = repo_updated_at[:10] if repo_updated_at else None
    now = get_beijing_time()

    cache_key = llm_cache_key(f"github:{source.repo}", f"https://github.com/{source.repo}/{path}", content, [])
    cached = _DOC_CACHE.get(cache_key) or _DOC_CACHE.get(digest)
    if cache_is_current(cached):
        return cached_with_freshness(cached, published_at, now)

    llm_result = analyze_with_runtime_llm(title, content, "github.com")
    semantic = derive_semantic_fields(
        title, content, source.category, source.source_weight, "github_resource",
        [], published_at, now, llm_result
    )
    semantic["student_score"] = max(0.55, semantic["student_score"])
    if "GitHub资料" not in semantic["tags"]:
        semantic["tags"].append("GitHub资料")

    return {
        "id": f"github-{source.repo.replace('/', '-')}-{digest}",
        "kind": "resource",
        "title": title,
        "url": f"https://github.com/{source.repo}/blob/{quote(branch, safe='')}/{quote(path, safe='/')}",
        "source": source.label,
        "source_domain": "github.com",
        "source_type": "github_resource",
        "category": semantic["category"],
        "domain": semantic["domain"],
        "intent": semantic["intent"],
        "lifecycle": infer_lifecycle(published_at, semantic["deadline"], now, "resource"),
        "evidence": semantic["evidence"],
        "confidence": semantic["confidence"],
        "sub_category": semantic["sub_category"],
        "deadline": semantic["deadline"],
        "action_required": semantic["action_required"],
        "action_type": semantic["action_type"],
        "action_summary": semantic["action_summary"],
        "required_materials": semantic["required_materials"],
        "sensitive": semantic["sensitive"],
        "sensitive_types": semantic["sensitive_types"],
        "review_required": semantic["review_required"],
        "risk_flags": semantic["risk_flags"],
        "audience": list(source.audience),
        "published_at": published_at,
        "content": semantic["content"],
        "summary": semantic["summary"],
        "attachments": semantic["attachments"],
        "student_score": semantic["student_score"],
        "freshness_score": calculate_freshness(published_at, now),
        "importance_score": semantic["importance_score"],
        "source_weight": source.source_weight,
        "tags": semantic["tags"],
        "hash": digest,
        "cache_key": cache_key,
        "llm_schema_version": active_llm_schema_version(),
        "llm": semantic["llm"],
    }


def crawl_github_resource_source(source: GitHubSourceConfig, now: datetime) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    print(f"Fetching GitHub resources {source.repo}")
    manifest_entry: dict[str, Any] = {
        "id": f"github:{source.repo}",
        "name": source.label,
        "domain": "github.com",
        "source_type": "github_resource",
        "status": "ok",
        "documents": 0,
        "last_fetch_at": now.isoformat(),
    }

    if not source.enabled:
        return [], manifest_entry

    token = os.environ.get(GITHUB_TOKEN_ENV) or os.environ.get("GITHUB_TOKEN")
    try:
        repo_payload = github_api_get(f"/repos/{source.repo}", token)
        branch = repo_payload.get("default_branch") or "main"
        updated_at = repo_payload.get("pushed_at") or repo_payload.get("updated_at")
        selected_files = select_github_files(source, branch, token)

        documents: list[dict[str, Any]] = []
        for file_entry in selected_files:
            path = str(file_entry["path"])
            text = fetch_github_file_text(source.repo, branch, path, token)
            if clean_text(text):
                doc = build_github_document(source, branch, path, text, updated_at)
                if doc:
                    documents.append(doc)

        manifest_entry["candidates"] = len(selected_files)
        manifest_entry["documents"] = len(documents)
        return documents, manifest_entry
    except Exception as exc:
        stale_documents = cached_documents_for_source_id(f"github-{source.repo.replace('/', '-')}")
        if stale_documents:
            manifest_entry["status"] = "ok"
            manifest_entry["warning"] = f"GitHub fetch failed; reused stale cached documents: {exc}"
            manifest_entry["documents"] = len(stale_documents)
            return stale_documents, manifest_entry
        manifest_entry["status"] = "error"
        manifest_entry["error"] = str(exc)
        return [], manifest_entry


def crawl_source(source: SourceConfig, now: datetime) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    print(f"Fetching {source.name} ({urlparse(source.base_url).netloc})")
    manifest_entry: dict[str, Any] = {
        "id": source.id,
        "name": source.name,
        "domain": urlparse(source.base_url).netloc,
        "source_type": normalize_source_type(source.source_type),
        "adapter_kind": source.adapter_kind,
        "priority": source.source_weight,
        "requires_devtools_audit": source.requires_devtools_audit,
        "status": "ok",
        "documents": 0,
        "last_fetch_at": now.isoformat(),
    }

    try:
        if source.adapter_kind == "job_api" or source.id == "job":
            documents = crawl_job_source(source, now)
            manifest_entry["documents"] = len(documents)
            return documents, manifest_entry

        candidates, list_errors = collect_candidates(source, now)
        if list_errors:
            manifest_entry["list_errors"] = list_errors
        enriched: list[dict[str, Any]] = []
        for candidate in candidates[:DETAIL_FETCH_LIMIT_PER_SOURCE]:
            doc = enrich_candidate(source, candidate, now)
            if doc:
                enriched.append(doc)

        filtered = [document for document in enriched if is_student_facing_document(document)]
        enriched.sort(
            key=lambda item: (
                item["student_score"],
                item["freshness_score"],
                item["importance_score"],
                item["published_at"] or "",
            ),
            reverse=True,
        )
        filtered.sort(
            key=lambda item: (
                item["student_score"],
                item["freshness_score"],
                item["importance_score"],
                item["published_at"] or "",
            ),
            reverse=True,
        )
        documents = filtered[:MAX_DOCS_PER_SOURCE]
        manifest_entry["candidates"] = len(enriched)
        manifest_entry["filtered_out"] = len(enriched) - len(filtered)
        manifest_entry["documents"] = len(documents)
        return documents, manifest_entry
    except Exception as exc:
        manifest_entry["status"] = "error"
        manifest_entry["error"] = str(exc)
        return [], manifest_entry


def deduplicate_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_key: dict[str, dict[str, Any]] = {}
    url_keys: set[str] = set()

    def rank(document: dict[str, Any]) -> tuple[float, float, float, float, int]:
        return (
            SOURCE_PRIORITY.get(str(document.get("source")), float(document.get("source_weight", 0.5))),
            float(document.get("student_score", 0)),
            float(document.get("importance_score", 0)),
            float(document.get("freshness_score", 0)),
            len(str(document.get("content", ""))),
        )

    for document in documents:
        title_key = normalize_title_for_dedupe(str(document.get("title", "")))
        if len(title_key) < 10:
            title_key = str(document.get("url", ""))
        key = title_key or str(document.get("url", ""))
        current = best_by_key.get(key)
        if current is None or rank(document) > rank(current):
            best_by_key[key] = document

    deduped = sorted(best_by_key.values(), key=rank, reverse=True)
    result: list[dict[str, Any]] = []
    for document in deduped:
        url = str(document.get("url", ""))
        if url in url_keys:
            continue
        url_keys.add(url)
        result.append(document)

    return result


def write_json_if_changed(path: str, payload: Any) -> bool:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as existing:
            if existing.read() == serialized:
                return False
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        output.write(serialized)
        output.write("\n")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the njupt-search campus search index.")
    parser.add_argument("--force-llm", action="store_true", help="Ignore cached LLM enrichments and reprocess documents.")
    parser.add_argument("--llm-schema-version", default=LLM_SCHEMA_VERSION, help="Override the LLM schema/cache version.")
    parser.add_argument("--source", action="append", default=[], help="Only crawl the given source id. Can be repeated.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of LLM calls in this run.")
    parser.add_argument("--dry-run", action="store_true", help="Run crawling/enrichment without writing index files.")
    parser.add_argument("--no-github", action="store_true", help="Skip GitHub resource sources.")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM enrichment and use rule fallbacks only.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _RUN_CONFIG.update({
        "force_llm": bool(args.force_llm),
        "no_llm": bool(args.no_llm),
        "llm_schema_version": str(args.llm_schema_version or LLM_SCHEMA_VERSION),
        "source_filter": set(args.source or []),
        "llm_limit": args.limit,
        "dry_run": bool(args.dry_run),
        "no_github": bool(args.no_github),
    })
    load_document_cache()
    os.makedirs(INDEX_DIR, exist_ok=True)
    now = get_beijing_time()
    all_documents: list[dict[str, Any]] = []
    source_entries: list[dict[str, Any]] = []

    for source in SOURCES:
        if not source_selected(source.id):
            continue
        documents, manifest_entry = crawl_source(source, now)
        all_documents.extend(documents)
        source_entries.append(manifest_entry)

    if not _RUN_CONFIG["no_github"]:
        for source in read_github_source_configs():
            github_id = f"github:{source.repo}"
            if not source_selected(github_id):
                continue
            documents, manifest_entry = crawl_github_resource_source(source, now)
            all_documents.extend(documents)
            source_entries.append(manifest_entry)

    all_documents = deduplicate_documents(all_documents)
    all_documents.sort(
        key=lambda item: (
            item["student_score"],
            item["freshness_score"],
            item["importance_score"],
            item["published_at"] or "",
        ),
        reverse=True,
    )

    manifest = {
        "generated_at": now.isoformat(),
        "total_documents": len(all_documents),
        "strategy": "phase3-source-registry-multiaxis-student-radar",
        "llm_schema_version": active_llm_schema_version(),
        "llm_enabled": runtime_llm_enabled(),
        "llm_stats": dict(_RUN_STATS),
        "source_count": len(source_entries),
        "sources": source_entries,
    }

    if _RUN_CONFIG["dry_run"]:
        print(json.dumps({
            "generated_documents": len(all_documents),
            "source_count": len(source_entries),
            "llm_stats": _RUN_STATS,
            "sources": source_entries,
        }, ensure_ascii=False, indent=2))
        return

    docs_changed = write_json_if_changed(DOCUMENTS_PATH, all_documents)
    manifest_changed = write_json_if_changed(MANIFEST_PATH, manifest)
    print(f"Generated {len(all_documents)} search documents")
    print(f"documents.json changed: {docs_changed}; manifest.json changed: {manifest_changed}")


if __name__ == "__main__":
    main()
