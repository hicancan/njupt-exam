from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_sitegraph_index import (  # noqa: E402
    BASE_DIR,
    DEFAULT_SITEGRAPH_INDEX,
    PUBLIC_INDEX_DIR,
    PUBLIC_SITEGRAPH_DIR,
    validate_sitegraph_package,
)


REQUIRED_QUERIES = (
    "校历",
    "慕课考试",
    "期末考试",
    "转专业",
    "规章制度",
    "办事流程",
    "学生相关文件及表格",
    "教务管理系统",
    "大创",
    "推免",
    "成绩",
    "附件1",
    "xlsx",
)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fail(message: str) -> None:
    print(f"[validate_sitegraph_index] {message}", file=sys.stderr)
    raise SystemExit(1)


def load_full_documents(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    shards = (((manifest.get("sitegraph") or {}).get("full_shards")) or [])
    if not isinstance(shards, list) or not shards:
        fail("manifest.sitegraph.full_shards must be a non-empty list")
    documents: list[dict[str, Any]] = []
    for shard in shards:
        if not isinstance(shard, dict):
            fail("manifest.sitegraph.full_shards contains a non-object shard")
        shard_path = BASE_DIR / "public" / str(shard.get("path") or "")
        if not shard_path.exists():
            fail(f"full shard missing: {shard_path}")
        payload = read_json(shard_path)
        if not isinstance(payload, list):
            fail(f"full shard must be a list: {shard_path}")
        if int(shard.get("count", -1)) != len(payload):
            fail(f"full shard count mismatch for {shard_path}: manifest={shard.get('count')} actual={len(payload)}")
        documents.extend(payload)
    return documents


def ensure_no_llm_null(payload: Any, path: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "llm_provider" and value is None:
                fail(f"{path}.llm_provider must not be null")
            if key in {"llm", "semantic_mode", "task_frames", "llm_schema_version"}:
                fail(f"{path}.{key} is an old LLM/HyTask field and must not be in the sitegraph core index")
            ensure_no_llm_null(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            ensure_no_llm_null(item, f"{path}[{index}]")


def validate_generated_index(package: dict[str, Any]) -> dict[str, Any]:
    required_paths = {
        "manifest": PUBLIC_INDEX_DIR / "manifest.json",
        "doc_meta": PUBLIC_INDEX_DIR / "doc_meta.json",
        "inverted_index": PUBLIC_INDEX_DIR / "inverted_index.json",
        "section_index": PUBLIC_INDEX_DIR / "section_index.json",
        "attachment_index": PUBLIC_INDEX_DIR / "attachment_index.json",
        "external_index": PUBLIC_INDEX_DIR / "external_index.json",
        "query_aliases": PUBLIC_INDEX_DIR / "query_aliases.json",
        "outcomes": PUBLIC_SITEGRAPH_DIR / "outcomes.json",
    }
    for name, path in required_paths.items():
        if not path.exists():
            fail(f"required generated artifact missing: {name}: {path}")
    for stale in ("documents.json", "task_frames.json", "ontology.json"):
        if (PUBLIC_INDEX_DIR / stale).exists():
            fail(f"public/index/{stale} must not exist in the pure sitegraph contract")

    manifest = read_json(required_paths["manifest"])
    if not isinstance(manifest, dict):
        fail("public/index/manifest.json must be an object")
    ensure_no_llm_null(manifest)
    if manifest.get("strategy") != "pure-sitegraph-code-search-v1":
        fail(f"manifest.strategy must be pure-sitegraph-code-search-v1, got {manifest.get('strategy')!r}")
    core_search = manifest.get("core_search") if isinstance(manifest.get("core_search"), dict) else {}
    if core_search.get("llm_in_core_path") is not False:
        fail("core_search.llm_in_core_path must be false")
    if core_search.get("source_channel_production_enabled") is not False:
        fail("old source-channel production path must be disabled")
    if core_search.get("github_resource_production_enabled") is not False:
        fail("GitHub resource production path must be disabled")
    if core_search.get("light_first_screen") is not True:
        fail("core_search.light_first_screen must be true")
    if core_search.get("full_text_loading") != "on_demand_by_shard":
        fail("full text must be loaded on demand by shard")
    if manifest.get("exam_vertical_preserved") is not True:
        fail("exam_vertical_preserved must be true")

    sitegraph = manifest.get("sitegraph") if isinstance(manifest.get("sitegraph"), dict) else {}
    truth_counts = sitegraph.get("truth_counts") if isinstance(sitegraph.get("truth_counts"), dict) else {}
    for field, actual in package["actual_counts"].items():
        if int(truth_counts.get(field, -1) or 0) != int(actual):
            fail(f"manifest.sitegraph.truth_counts.{field} mismatch: manifest={truth_counts.get(field)} actual={actual}")

    doc_meta = read_json(required_paths["doc_meta"])
    if not isinstance(doc_meta, list):
        fail("doc_meta.json must be a list")
    full_documents = load_full_documents(manifest)
    if len(doc_meta) != len(full_documents):
        fail(f"doc_meta/full document count mismatch: meta={len(doc_meta)} full={len(full_documents)}")
    if int(manifest.get("total_documents", -1)) != len(full_documents):
        fail(f"manifest total_documents mismatch: manifest={manifest.get('total_documents')} full={len(full_documents)}")
    ensure_no_llm_null(full_documents)

    ids = [str(item.get("id") or "") for item in full_documents if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        fail("full documents contain duplicate ids")
    if len(ids) != len(full_documents):
        fail("full documents contain non-object or missing-id entries")

    detail_docs = {str(item.get("url")): item for item in full_documents if item.get("record_type") == "detail"}
    detail_urls = {str(item.get("url")) for item in package["detail_pages"]}
    missing_detail_urls = sorted(detail_urls.difference(detail_docs))
    if missing_detail_urls:
        fail(f"detail pages missing search records: {missing_detail_urls[:10]}")
    if len(detail_docs) != package["actual_counts"]["detail_pages"]:
        fail(f"detail document count mismatch: {len(detail_docs)} != {package['actual_counts']['detail_pages']}")

    attachment_index = read_json(required_paths["attachment_index"])
    if not isinstance(attachment_index, list):
        fail("attachment_index.json must be a list")
    if len(attachment_index) != package["actual_counts"]["attachments"]:
        fail(f"attachment index count mismatch: {len(attachment_index)} != {package['actual_counts']['attachments']}")
    for item in attachment_index:
        if item.get("metadata_only") is not True:
            fail("attachment_index contains non metadata_only record")
        for field in ("name", "url", "extension", "parent_url", "section", "nav_path"):
            if not item.get(field):
                fail(f"attachment_index record missing {field}")

    external_index = read_json(required_paths["external_index"])
    if not isinstance(external_index, list):
        fail("external_index.json must be a list")
    if len(external_index) != package["actual_counts"]["external_links"]:
        fail(f"external index count mismatch: {len(external_index)} != {package['actual_counts']['external_links']}")

    outcomes = read_json(required_paths["outcomes"])
    if not isinstance(outcomes, dict):
        fail("outcomes must be an object")
    if len(outcomes.get("detail_page_records") or []) != package["actual_counts"]["detail_pages"]:
        fail("outcomes.detail_page_records must cover every detail page")
    if len(outcomes.get("attachment_metadata_records") or []) != package["actual_counts"]["attachments"]:
        fail("outcomes.attachment_metadata_records must cover every attachment")
    if len(outcomes.get("external_link_records") or []) != package["actual_counts"]["external_links"]:
        fail("outcomes.external_link_records must cover every external link")

    inverted = read_json(required_paths["inverted_index"])
    if not isinstance(inverted, dict) or not isinstance(inverted.get("tokens"), dict) or not inverted["tokens"]:
        fail("inverted_index.json must contain tokens")

    full_text = json.dumps([doc_meta, attachment_index, external_index], ensure_ascii=False)
    for required in ("教务管理系统", "自主学分系统", "创新管理系统", "毕业设计系统", "考试信息查询"):
        if required not in full_text:
            fail(f"required system or utility entry is not searchable: {required}")
    aliases = read_json(required_paths["query_aliases"])
    for query in REQUIRED_QUERIES:
        if query not in full_text and query not in aliases:
            fail(f"representative query lacks searchable text or alias: {query}")

    return {
        "passed": True,
        "total_documents": len(full_documents),
        "detail_page_records": len(detail_docs),
        "attachment_metadata_records": len(attachment_index),
        "external_link_records": len(external_index),
        "truth_counts": package["actual_counts"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the JWC package and pure sitegraph search index.")
    parser.add_argument("--sitegraph-index", type=Path, default=DEFAULT_SITEGRAPH_INDEX, help="Path to njupt-site-graph/data/sites/jwc/index")
    parser.add_argument("--skip-output", action="store_true", help="Only validate the upstream JWC sitegraph package")
    args = parser.parse_args()

    package = validate_sitegraph_package(args.sitegraph_index.resolve())
    summary: dict[str, Any] = {
        "sitegraph_index": str(args.sitegraph_index.resolve()),
        "package_valid": True,
        "truth_counts": package["actual_counts"],
        "quality": package["manifest"].get("quality"),
    }
    if not args.skip_output:
        summary["generated_index"] = validate_generated_index(package)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
