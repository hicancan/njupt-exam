from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import unicodedata
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

QUERY_SYNONYMS: dict[str, list[str]] = {
    "校历": ["教学日历", "教学周历", "2025-2026学年校历"],
    "慕课考试": ["慕课", "MOOC", "SPOC", "在线开放课程", "线下考试"],
    "期末考试": ["期末", "考试安排", "考场安排", "考试周"],
    "转专业": ["专业变更", "转入转出", "转专业管理办法"],
    "规章制度": ["规章", "制度", "管理办法", "政策文件"],
    "办事流程": ["流程", "办理指南", "办事指南", "申请流程"],
    "学生相关文件及表格": ["学生表格", "常用下载", "表格下载", "学生相关文件"],
    "教务管理系统": ["正方教务", "教务系统", "jwxt"],
    "大创": ["大学生创新创业", "创新创业", "创新训练", "创业训练"],
    "推免": ["免试攻读研究生", "推荐免试", "推免生"],
    "成绩": ["成绩查询", "成绩单", "绩点", "成绩复核"],
    "附件1": ["附件 1", "附件一", "附件"],
    "xlsx": ["xls", "Excel", "表格"],
}

FIELD_CODES = {
    "title": "t",
    "section": "s",
    "attachment": "a",
    "external": "e",
    "body": "b",
    "tag": "g",
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


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"\s+", "", text)


def unique_strings(values: list[Any], *, limit: int | None = None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if limit is not None and len(result) >= limit:
            break
    return result


def count_nav_nodes(nav_tree: dict[str, Any]) -> int:
    nodes = nav_tree.get("nodes")
    return len(nodes) if isinstance(nodes, list) else 0


def sitegraph_tokens(value: Any, *, cjk_max_n: int = 3, cap: int | None = None) -> set[str]:
    text = normalize_text(value)
    tokens: set[str] = set()
    if not text:
        return tokens
    for match in re.finditer(r"[\u4e00-\u9fff]{2,}|[a-z0-9][a-z0-9._-]{1,}", text):
        part = match.group(0)
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            if len(part) <= 16:
                tokens.add(part)
            for size in range(2, cjk_max_n + 1):
                if len(part) < size:
                    continue
                for index in range(0, len(part) - size + 1):
                    tokens.add(part[index : index + size])
                    if cap is not None and len(tokens) >= cap:
                        return tokens
        else:
            tokens.add(part)
        if cap is not None and len(tokens) >= cap:
            return tokens
    return tokens


def query_alias_payload() -> dict[str, dict[str, list[str]]]:
    return {
        key: {"aliases": aliases}
        for key, aliases in sorted(QUERY_SYNONYMS.items())
    }


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

    site = read_json(index_dir / "site.json")
    sections = read_json(index_dir / "sections.json")
    homepage_modules_payload = read_json(index_dir / "homepage_modules.json") if (index_dir / "homepage_modules.json").exists() else []
    homepage_modules = homepage_modules_payload.get("modules") if isinstance(homepage_modules_payload, dict) else homepage_modules_payload
    nav_tree = read_json(index_dir / "nav_tree.json") if (index_dir / "nav_tree.json").exists() else {}
    list_pages = read_jsonl(index_dir / "list_pages.jsonl")
    detail_pages = read_jsonl(index_dir / "detail_pages.jsonl")
    attachments = read_jsonl(index_dir / "attachments.jsonl")
    external_links = read_jsonl(index_dir / "external_links.jsonl")
    edges = read_jsonl(index_dir / "edges.jsonl")

    if not isinstance(site, dict):
        raise ValueError("site.json must be an object")
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
        "source_index_dir": index_dir,
        "manifest": manifest,
        "site": site,
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


def section_label(section: dict[str, Any] | None) -> tuple[str, list[str], list[str]]:
    if not section:
        return "首页", ["首页"], []
    nav_path = [clean_text(item) for item in section.get("nav_path") or [] if clean_text(item)]
    if not nav_path:
        nav_path = [clean_text(section.get("name")) or clean_text(section.get("section_id"))]
    tags = [clean_text(item) for item in section.get("business_tags") or [] if clean_text(item)]
    return clean_text(section.get("name")) or nav_path[-1], nav_path, tags


def infer_facet(*, record_type: str, section: dict[str, Any] | None, title: str, content: str, external_category: str = "") -> str:
    section_name, nav_path, tags = section_label(section)
    text = normalize_text(" ".join([section_name, " ".join(nav_path), " ".join(tags), title, content, external_category]))
    if record_type == "external":
        return "system" if "external_system" in external_category else "external"
    if record_type == "attachment":
        return "download"
    if any(term in text for term in ("考试", "补考", "重修", "四六级", "慕课", "mooc", "考场")):
        return "exam"
    if any(term in text for term in ("规章", "制度", "管理办法", "policy", "regulation")):
        return "policy"
    if any(term in text for term in ("办事流程", "办理", "流程", "申请", "指南")):
        return "workflow"
    if any(term in text for term in ("下载", "表格", "附件", "resource", "download", "forms")):
        return "download"
    if any(term in text for term in ("新闻", "快讯", "动态", "news")):
        return "news"
    return "notice_article"


def summarize(content: str, title: str, limit: int = 180) -> str:
    text = clean_text(content)
    title_text = clean_text(title)
    if text.startswith(title_text):
        text = text[len(title_text):].strip()
    return text[:limit] if text else title_text


def attachment_metadata(item: dict[str, Any], *, parent_doc_id: str | None, section: dict[str, Any] | None) -> dict[str, Any]:
    section_name, nav_path, _ = section_label(section)
    return {
        "attachment_id": clean_text(item.get("attachment_id")) or sha1_text(str(item.get("url") or item.get("name"))),
        "name": clean_text(item.get("name")) or "未命名附件",
        "url": clean_text(item.get("url")),
        "extension": clean_text(item.get("extension")).lower() or None,
        "parent_url": clean_text(item.get("parent_url")),
        "parent_doc_id": parent_doc_id,
        "section_id": clean_text(section.get("section_id")) if section else None,
        "section": section_name,
        "nav_path": nav_path,
        "metadata_only": True,
        "position": item.get("position"),
    }


def doc_host(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc


def make_doc_meta(
    *,
    doc_index: int,
    doc_id: str,
    record_type: str,
    title: str,
    url: str,
    site: dict[str, Any],
    section: dict[str, Any] | None,
    page_type: str,
    published_at: str | None,
    publisher: str | None,
    summary: str,
    content_hash: str,
    attachment_count: int,
    facet: str,
    outcome: str,
    source_url: str | None = None,
    external_category: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    section_name, nav_path, section_tags = section_label(section)
    source_domain = clean_text(site.get("domain")) or doc_host(clean_text(site.get("base_url")))
    return {
        "doc_index": doc_index,
        "id": doc_id,
        "record_type": record_type,
        "page_type": page_type,
        "facet": facet,
        "title": clean_text(title) or clean_text(url),
        "url": clean_text(url),
        "source": clean_text(site.get("name")) or "本科生院 / 教务处",
        "source_domain": source_domain,
        "section_id": clean_text(section.get("section_id")) if section else None,
        "section": section_name,
        "nav_path": nav_path,
        "nav_path_text": " / ".join(nav_path),
        "published_at": clean_text(published_at) or None,
        "publisher": clean_text(publisher) or None,
        "summary": clean_text(summary),
        "attachment_count": int(attachment_count or 0),
        "hash": content_hash,
        "tags": unique_strings([*(tags or []), *section_tags, facet, record_type], limit=16),
        "provenance": {
            "site_id": clean_text(site.get("site_id")) or "jwc",
            "section_id": clean_text(section.get("section_id")) if section else None,
            "nav_path": nav_path,
            "source_url": source_url,
            "outcome": outcome,
            "external_category": external_category,
        },
    }


def build_documents(package: dict[str, Any]) -> dict[str, Any]:
    site = package["site"]
    sections_by_id = {clean_text(item.get("section_id")): item for item in package["sections"]}
    list_pages_by_url = {clean_text(item.get("url")): item for item in package["list_pages"]}
    detail_urls = {clean_text(item.get("url")) for item in package["detail_pages"]}
    detail_id_by_url: dict[str, str] = {}
    attachments_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for attachment in package["attachments"]:
        attachments_by_parent[clean_text(attachment.get("parent_url"))].append(attachment)

    docs: list[dict[str, Any]] = []
    attachment_index: list[dict[str, Any]] = []
    external_index: list[dict[str, Any]] = []
    outcomes = {
        "detail_page_records": [],
        "attachment_metadata_records": [],
        "direct_attachment_records": [],
        "external_link_records": [],
        "utility_link_records": [],
    }

    for page in package["detail_pages"]:
        url = clean_text(page.get("url"))
        section = sections_by_id.get(clean_text(page.get("section_id")))
        title = clean_text(page.get("title")) or url
        content = clean_text(page.get("content_text"))
        doc_id = f"jwc-detail-{clean_text(page.get('page_id')) or sha1_text(url)}"
        detail_id_by_url[url] = doc_id
        attachments = [
            attachment_metadata(item, parent_doc_id=doc_id, section=section)
            for item in attachments_by_parent.get(url, [])
        ]
        facet = infer_facet(record_type="detail", section=section, title=title, content=content)
        meta = make_doc_meta(
            doc_index=len(docs),
            doc_id=doc_id,
            record_type="detail",
            title=title,
            url=url,
            site=site,
            section=section,
            page_type=clean_text(page.get("page_type")) or "detail_article_page",
            published_at=clean_text(page.get("published_at")) or None,
            publisher=clean_text(page.get("publisher")) or None,
            summary=summarize(content, title),
            content_hash=clean_text(page.get("content_hash")) or sha1_text(content or title),
            attachment_count=len(attachments),
            facet=facet,
            outcome="search_record",
            source_url=url,
            tags=[clean_text(item) for item in page.get("headings") or []],
        )
        docs.append({**meta, "content": content or title, "attachments": attachments})
        outcomes["detail_page_records"].append({"url": url, "document_id": doc_id, "outcome": "search_record"})

    for attachment in package["attachments"]:
        parent_url = clean_text(attachment.get("parent_url"))
        parent_doc_id = detail_id_by_url.get(parent_url)
        section = None
        if parent_doc_id:
            parent_page = next((item for item in package["detail_pages"] if clean_text(item.get("url")) == parent_url), None)
            section = sections_by_id.get(clean_text(parent_page.get("section_id"))) if parent_page else None
        else:
            list_page = list_pages_by_url.get(parent_url)
            section = sections_by_id.get(clean_text(list_page.get("section_id"))) if list_page else None
        metadata = attachment_metadata(attachment, parent_doc_id=parent_doc_id, section=section)
        attachment_index.append(metadata)
        outcomes["attachment_metadata_records"].append(
            {
                "url": metadata["url"],
                "name": metadata["name"],
                "parent_url": metadata["parent_url"],
                "parent_doc_id": parent_doc_id,
                "outcome": "attachment_metadata_only",
            }
        )
        if parent_doc_id is None:
            doc_id = f"jwc-attachment-{metadata['attachment_id']}"
            metadata["parent_doc_id"] = doc_id
            title = metadata["name"]
            facet = "download"
            meta = make_doc_meta(
                doc_index=len(docs),
                doc_id=doc_id,
                record_type="attachment",
                title=title,
                url=metadata["url"],
                site=site,
                section=section,
                page_type="attachment_metadata",
                published_at=None,
                publisher=None,
                summary=f"附件元数据：{title}。来源栏目：{metadata['section']}。",
                content_hash=sha1_text(metadata["url"] or title),
                attachment_count=1,
                facet=facet,
                outcome="attachment_metadata_only",
                source_url=metadata["parent_url"],
                tags=[metadata.get("extension") or "", "附件", "下载"],
            )
            docs.append({**meta, "content": meta["summary"], "attachments": [metadata]})
            outcomes["direct_attachment_records"].append(
                {"url": metadata["url"], "name": title, "document_id": doc_id, "outcome": "search_record"}
            )

    for link in package["external_links"]:
        label = clean_text(link.get("label")) or clean_text(link.get("url"))
        url = clean_text(link.get("url"))
        section = sections_by_id.get(clean_text(link.get("source_section_id")))
        category = clean_text(link.get("category")) or "external_link"
        doc_id = f"jwc-external-{clean_text(link.get('external_id')) or sha1_text(url + label)}"
        facet = infer_facet(record_type="external", section=section, title=label, content=url, external_category=category)
        meta = make_doc_meta(
            doc_index=len(docs),
            doc_id=doc_id,
            record_type="external",
            title=label,
            url=url,
            site=site,
            section=section,
            page_type="external_link_record",
            published_at=clean_text(link.get("recorded_at")) or None,
            publisher=None,
            summary=f"JWC 记录的外链：{label}。该链接只记录入口，不递归抓取内容。",
            content_hash=sha1_text(url + label),
            attachment_count=0,
            facet=facet,
            outcome="external_record_only",
            source_url=clean_text(link.get("source_url")),
            external_category=category,
            tags=[category, doc_host(url), label],
        )
        docs.append({**meta, "content": meta["summary"], "attachments": []})
        external_index.append(
            {
                "external_id": clean_text(link.get("external_id")) or sha1_text(url + label),
                "label": label,
                "url": url,
                "category": category,
                "source_url": clean_text(link.get("source_url")),
                "source_section_id": clean_text(link.get("source_section_id")) or None,
                "document_id": doc_id,
                "outcome": "external_record_only",
            }
        )
        outcomes["external_link_records"].append({"url": url, "label": label, "document_id": doc_id, "outcome": "external_record_only"})

    for edge in package["edges"]:
        label = clean_text(edge.get("anchor_text"))
        if label != "考试信息查询":
            continue
        target_url = clean_text(edge.get("to_url"))
        section = None
        target_list = list_pages_by_url.get(target_url)
        if target_list:
            section = sections_by_id.get(clean_text(target_list.get("section_id")))
        doc_id = f"jwc-utility-{clean_text(edge.get('edge_id')) or sha1_text(target_url + label)}"
        meta = make_doc_meta(
            doc_index=len(docs),
            doc_id=doc_id,
            record_type="utility",
            title=label,
            url=target_url,
            site=site,
            section=section,
            page_type="utility_link_record",
            published_at=None,
            publisher=None,
            summary="JWC 首页记录的考试信息查询入口。",
            content_hash=sha1_text(target_url + label),
            attachment_count=0,
            facet="exam",
            outcome="search_record",
            source_url=clean_text(edge.get("from_url")),
            tags=["考试", "查询", "入口"],
        )
        docs.append({**meta, "content": meta["summary"], "attachments": []})
        outcomes["utility_link_records"].append({"url": target_url, "label": label, "document_id": doc_id, "outcome": "search_record"})

    return {
        "documents": docs,
        "attachment_index": attachment_index,
        "external_index": external_index,
        "outcomes": outcomes,
    }


def add_postings(index: dict[str, dict[str, set[int]]], doc_index: int, field_code: str, tokens: set[str]) -> None:
    for token in tokens:
        if not token:
            continue
        index[token][field_code].add(doc_index)


def build_inverted_index(documents: list[dict[str, Any]]) -> dict[str, Any]:
    raw_index: dict[str, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    for document in documents:
        doc_index = int(document["doc_index"])
        add_postings(raw_index, doc_index, FIELD_CODES["title"], sitegraph_tokens(document.get("title"), cjk_max_n=5))
        add_postings(raw_index, doc_index, FIELD_CODES["section"], sitegraph_tokens([document.get("section"), document.get("nav_path_text")], cjk_max_n=5))
        add_postings(raw_index, doc_index, FIELD_CODES["tag"], sitegraph_tokens(" ".join(document.get("tags") or []), cjk_max_n=4))
        add_postings(raw_index, doc_index, FIELD_CODES["body"], sitegraph_tokens(document.get("summary"), cjk_max_n=4, cap=60))
        add_postings(raw_index, doc_index, FIELD_CODES["body"], sitegraph_tokens(document.get("content"), cjk_max_n=3, cap=120))
        attachment_text = " ".join(
            " ".join(clean_text(attachment.get(field)) for field in ("name", "extension", "section", "parent_url"))
            for attachment in document.get("attachments") or []
        )
        add_postings(raw_index, doc_index, FIELD_CODES["attachment"], sitegraph_tokens(attachment_text, cjk_max_n=5))
        if document.get("record_type") == "external":
            add_postings(raw_index, doc_index, FIELD_CODES["external"], sitegraph_tokens([document.get("title"), document.get("url"), document.get("summary")], cjk_max_n=5))

    tokens: dict[str, dict[str, list[int]]] = {}
    for token, fields in raw_index.items():
        compact_fields: dict[str, list[int]] = {}
        for field, ids in fields.items():
            compact_fields[field] = sorted(ids)
        tokens[token] = compact_fields

    return {
        "version": "sitegraph-inverted-v1",
        "tokenizer": "nfkc-lower-cjk-ngram-code",
        "field_codes": FIELD_CODES,
        "tokens": tokens,
    }


def write_public_index(package: dict[str, Any], built: dict[str, Any], *, shard_size: int) -> dict[str, Any]:
    PUBLIC_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    if PUBLIC_SITEGRAPH_DIR.exists():
        shutil.rmtree(PUBLIC_SITEGRAPH_DIR)
    PUBLIC_SITEGRAPH_DIR.mkdir(parents=True, exist_ok=True)
    for stale in ("documents.json", "task_frames.json", "ontology.json"):
        stale_path = PUBLIC_INDEX_DIR / stale
        if stale_path.exists():
            stale_path.unlink()

    documents = built["documents"]
    full_shards: list[dict[str, Any]] = []
    for start in range(0, len(documents), shard_size):
        shard_number = start // shard_size
        shard_docs = documents[start : start + shard_size]
        shard_name = f"documents.{shard_number:03d}.json"
        shard_path = PUBLIC_SITEGRAPH_DIR / shard_name
        for item in shard_docs:
            item["shard"] = {
                "path": f"index/sitegraph/jwc/{shard_name}",
                "index": shard_number,
            }
        write_json(shard_path, shard_docs, compact=True)
        full_shards.append({"path": f"index/sitegraph/jwc/{shard_name}", "count": len(shard_docs), "contains": "full_documents"})

    doc_meta = [{key: value for key, value in document.items() if key not in {"content", "attachments"}} for document in documents]
    write_json(PUBLIC_INDEX_DIR / "doc_meta.json", doc_meta, compact=True)
    write_json(PUBLIC_INDEX_DIR / "inverted_index.json", build_inverted_index(documents), compact=True)
    write_json(PUBLIC_INDEX_DIR / "attachment_index.json", built["attachment_index"], compact=True)
    write_json(PUBLIC_INDEX_DIR / "external_index.json", built["external_index"], compact=True)
    write_json(PUBLIC_INDEX_DIR / "query_aliases.json", query_alias_payload())
    write_json(PUBLIC_SITEGRAPH_DIR / "outcomes.json", built["outcomes"], compact=True)

    section_counts = Counter(clean_text(document.get("section_id")) or "unknown" for document in documents)
    section_index = []
    for section in package["sections"]:
        section_id = clean_text(section.get("section_id"))
        section_name, nav_path, tags = section_label(section)
        section_index.append(
            {
                "section_id": section_id,
                "name": section_name,
                "url": clean_text(section.get("url")),
                "section_type": clean_text(section.get("section_type")),
                "nav_path": nav_path,
                "business_tags": tags,
                "document_count": section_counts.get(section_id, 0),
            }
        )
    write_json(PUBLIC_INDEX_DIR / "section_index.json", section_index)

    upstream_counts = dict(package["actual_counts"])
    record_counts = Counter(document["record_type"] for document in documents)
    facet_counts = Counter(document["facet"] for document in documents)
    generated_at = now_iso()
    manifest = {
        "generated_at": generated_at,
        "strategy": "pure-sitegraph-code-search-v1",
        "site_id": "jwc",
        "source": str(package.get("source_index_dir") or DEFAULT_SITEGRAPH_INDEX),
        "total_documents": len(documents),
        "record_counts": dict(record_counts),
        "facet_counts": dict(facet_counts),
        "exam_vertical_preserved": True,
        "core_search": {
            "algorithm": "static inverted index plus on-demand full shard ranking",
            "llm_in_core_path": False,
            "old_hytask_removed": True,
            "source_channel_production_enabled": False,
            "github_resource_production_enabled": False,
            "light_first_screen": True,
            "full_text_loading": "on_demand_by_shard",
        },
        "sitegraph": {
            "truth_counts": upstream_counts,
            "quality": package["manifest"].get("quality"),
            "upstream_generated_at": package["manifest"].get("generated_at"),
            "detail_page_records": record_counts.get("detail", 0),
            "attachment_metadata_records": len(built["attachment_index"]),
            "direct_attachment_records": record_counts.get("attachment", 0),
            "external_link_records": len(built["external_index"]),
            "external_document_records": record_counts.get("external", 0),
            "utility_link_records": record_counts.get("utility", 0),
            "attachment_policy": "metadata_only",
            "external_link_policy": "record_only",
            "full_shards": full_shards,
            "indexes": {
                "doc_meta": "index/doc_meta.json",
                "inverted_index": "index/inverted_index.json",
                "section_index": "index/section_index.json",
                "attachment_index": "index/attachment_index.json",
                "external_index": "index/external_index.json",
                "query_aliases": "index/query_aliases.json",
                "outcomes": "index/sitegraph/jwc/outcomes.json",
            },
        },
    }
    write_json(PUBLIC_INDEX_DIR / "manifest.json", manifest)
    write_json(PUBLIC_SITEGRAPH_DIR / "manifest.json", {"generated_at": generated_at, "full_shards": full_shards, "record_counts": dict(record_counts)})
    return manifest


def build_sitegraph_index(index_dir: Path, *, shard_size: int = 1000) -> dict[str, Any]:
    package = validate_sitegraph_package(index_dir)
    built = build_documents(package)
    manifest = write_public_index(package, built, shard_size=shard_size)
    return {
        "sitegraph_index": str(index_dir),
        "generated_documents": manifest["total_documents"],
        "detail_page_records": manifest["sitegraph"]["detail_page_records"],
        "attachment_metadata_records": manifest["sitegraph"]["attachment_metadata_records"],
        "direct_attachment_records": manifest["sitegraph"]["direct_attachment_records"],
        "external_link_records": manifest["sitegraph"]["external_link_records"],
        "utility_link_records": manifest["sitegraph"]["utility_link_records"],
        "truth_counts": manifest["sitegraph"]["truth_counts"],
        "full_shards": manifest["sitegraph"]["full_shards"],
        "public_index": str(PUBLIC_INDEX_DIR),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a pure code JWC sitegraph search index for njupt-search.")
    parser.add_argument("--sitegraph-index", type=Path, default=DEFAULT_SITEGRAPH_INDEX, help="Path to njupt-site-graph/data/sites/jwc/index")
    parser.add_argument("--shard-size", type=int, default=1000, help="Number of full documents per shard")
    args = parser.parse_args()
    summary = build_sitegraph_index(args.sitegraph_index.resolve(), shard_size=args.shard_size)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
