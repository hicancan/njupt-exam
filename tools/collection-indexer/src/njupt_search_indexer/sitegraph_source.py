from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[4]
COLLECTION_ID = "njupt-public"
DEFAULT_COLLECTION_CONFIG = BASE_DIR / "config" / "collections" / "njupt-public.sitegraph.json"
DEFAULT_SITEGRAPH_REPO = BASE_DIR.parent / "njupt-site-graph"
DEFAULT_SOURCE_PACKAGE_PATHS = ("data/sites/jwc/index", "data/sites/xsc/index", "data/sites/cxcy/index")
DEFAULT_SITEGRAPH_INDEXES = tuple((DEFAULT_SITEGRAPH_REPO / source_path).resolve() for source_path in DEFAULT_SOURCE_PACKAGE_PATHS)
DEFAULT_SITEGRAPH_INDEX = DEFAULT_SITEGRAPH_INDEXES[0]
UNKNOWN_ALLOWLIST_FILE = "unknown_url_allowlist.json"

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


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


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


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def load_collection_source_packages(config_path: Path | None = None) -> list[Path]:
    path = config_path or DEFAULT_COLLECTION_CONFIG
    if not path.exists():
        return list(DEFAULT_SITEGRAPH_INDEXES)

    config = read_json(path)
    if not isinstance(config, dict):
        raise ValueError(f"{path} must be a JSON object")
    if config.get("collection_id") != COLLECTION_ID:
        raise ValueError(f"{path} collection_id must be {COLLECTION_ID!r}")

    env_name = str(config.get("sitegraph_repo_env") or "NJUPT_SITEGRAPH_REPO")
    sitegraph_repo_value = os.environ.get(env_name) or str(config.get("sitegraph_repo") or "../njupt-site-graph")
    sitegraph_repo = _resolve_path(sitegraph_repo_value, BASE_DIR)
    source_packages = config.get("source_packages")
    if not isinstance(source_packages, list) or not source_packages:
        raise ValueError(f"{path} source_packages must be a non-empty list")

    resolved: list[Path] = []
    for source_package in source_packages:
        if not isinstance(source_package, str) or not source_package:
            raise ValueError(f"{path} source_packages entries must be non-empty strings")
        resolved.append(_resolve_path(source_package, sitegraph_repo))
    return resolved


def count_nav_nodes(nav_tree: dict[str, Any]) -> int:
    nodes = nav_tree.get("nodes")
    return len(nodes) if isinstance(nodes, list) else 0


def unknown_url_outcomes(manifest: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    outcomes = manifest.get("url_outcomes")
    if not isinstance(outcomes, dict):
        return []
    return [
        (str(url), record)
        for url, record in outcomes.items()
        if isinstance(record, dict)
        and ("unknown" in str(record.get("target_type") or "") or "unknown" in str(record.get("outcome") or ""))
    ]


def assert_unknown_url_outcomes_allowlisted(index_dir: Path, source_id: str, manifest: dict[str, Any]) -> None:
    unknown = unknown_url_outcomes(manifest)
    if not unknown:
        return

    allowlist_path = index_dir / UNKNOWN_ALLOWLIST_FILE
    if not allowlist_path.exists():
        raise ValueError(f"{source_id} manifest contains unknown URL outcomes but no {UNKNOWN_ALLOWLIST_FILE}")

    allowlist = read_json(allowlist_path)
    if not isinstance(allowlist, dict):
        raise ValueError(f"{source_id} {UNKNOWN_ALLOWLIST_FILE} must be a JSON object")
    if clean_text(allowlist.get("site_id")) != source_id:
        raise ValueError(f"{source_id} {UNKNOWN_ALLOWLIST_FILE} site_id must match the package site_id")
    rules = allowlist.get("allowed_unknowns")
    if not isinstance(rules, list) or not rules:
        raise ValueError(f"{source_id} {UNKNOWN_ALLOWLIST_FILE} allowed_unknowns must be a non-empty list")

    compiled_rules: list[tuple[dict[str, Any], re.Pattern[str]]] = []
    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            raise ValueError(f"{source_id} {UNKNOWN_ALLOWLIST_FILE} rule {index} must be an object")
        if not clean_text(rule.get("reason")):
            raise ValueError(f"{source_id} {UNKNOWN_ALLOWLIST_FILE} rule {index} must include a reason")
        pattern = clean_text(rule.get("url_pattern"))
        if not pattern:
            raise ValueError(f"{source_id} {UNKNOWN_ALLOWLIST_FILE} rule {index} must include url_pattern")
        try:
            compiled_rules.append((rule, re.compile(pattern)))
        except re.error as exc:
            raise ValueError(f"{source_id} {UNKNOWN_ALLOWLIST_FILE} rule {index} has invalid url_pattern: {exc}") from exc

    unexpected: list[dict[str, Any]] = []
    matched_rules: set[int] = set()
    for url, record in unknown:
        matched = False
        for index, (rule, pattern) in enumerate(compiled_rules):
            if not pattern.search(url):
                continue
            if rule.get("target_type") and rule["target_type"] != record.get("target_type"):
                continue
            if rule.get("outcome") and rule["outcome"] != record.get("outcome"):
                continue
            matched = True
            matched_rules.add(index)
            break
        if not matched:
            unexpected.append({"url": url, "target_type": record.get("target_type"), "outcome": record.get("outcome")})

    if unexpected:
        raise ValueError(f"{source_id} manifest has unallowlisted unknown URL outcomes: {json.dumps(unexpected[:10], ensure_ascii=False)}")

    stale_rules = [
        str(rule.get("url_pattern"))
        for index, (rule, _pattern) in enumerate(compiled_rules)
        if index not in matched_rules
    ]
    if stale_rules:
        raise ValueError(f"{source_id} {UNKNOWN_ALLOWLIST_FILE} contains stale rules: {json.dumps(stale_rules, ensure_ascii=False)}")


def validate_sitegraph_package(index_dir: Path) -> dict[str, Any]:
    missing = sorted(name for name in REQUIRED_SITEGRAPH_FILES if not (index_dir / name).exists())
    if missing:
        raise ValueError(f"sitegraph package missing required files: {', '.join(missing)}")

    manifest = read_json(index_dir / "manifest.json")
    if not isinstance(manifest, dict):
        raise ValueError("manifest.json must be a JSON object")
    source_id = clean_text(manifest.get("site_id")) or index_dir.parent.name or "sitegraph"
    quality = manifest.get("quality") if isinstance(manifest.get("quality"), dict) else {}
    if int(quality.get("errors", -1)) != 0:
        raise ValueError(f"{source_id} manifest quality.errors must be 0, got {quality.get('errors')}")
    if quality.get("all_discovered_urls_have_outcomes") is not True:
        raise ValueError(f"{source_id} manifest all_discovered_urls_have_outcomes must be true")
    if quality.get("attachment_policy") != "metadata_only":
        raise ValueError(f"{source_id} attachment_policy must be metadata_only, got {quality.get('attachment_policy')!r}")
    if quality.get("external_link_policy") != "record_only":
        raise ValueError(f"{source_id} external_link_policy must be record_only, got {quality.get('external_link_policy')!r}")
    assert_unknown_url_outcomes_allowlisted(index_dir, source_id, manifest)

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
        raise ValueError(f"{source_id} sitegraph package count mismatch: {json.dumps(mismatches, ensure_ascii=False)}")

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


def package_source_id(package: dict[str, Any]) -> str:
    return clean_text(package.get("site", {}).get("site_id")) or clean_text(package.get("manifest", {}).get("site_id")) or "sitegraph"
