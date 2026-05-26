from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ingest_sitegraph import (  # noqa: E402
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
    print(f"[validate_sitegraph_ingest] {message}", file=sys.stderr)
    raise SystemExit(1)


def load_full_documents(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    shards = (((manifest.get("sitegraph") or {}).get("shards")) or [])
    if not isinstance(shards, list) or not shards:
        fail("manifest.sitegraph.shards must be a non-empty list")
    documents: list[dict[str, Any]] = []
    for shard in shards:
        if not isinstance(shard, dict):
            fail("manifest.sitegraph.shards contains a non-object shard")
        shard_path = BASE_DIR / "public" / str(shard.get("path") or "")
        if not shard_path.exists():
            fail(f"full-text shard missing: {shard_path}")
        payload = read_json(shard_path)
        if not isinstance(payload, list):
            fail(f"full-text shard must be a list: {shard_path}")
        if int(shard.get("count", -1)) != len(payload):
            fail(f"full-text shard count mismatch for {shard_path}: manifest={shard.get('count')} actual={len(payload)}")
        documents.extend(payload)
    return documents


def validate_generated_index(package: dict[str, Any]) -> dict[str, Any]:
    manifest_path = PUBLIC_INDEX_DIR / "manifest.json"
    documents_path = PUBLIC_INDEX_DIR / "documents.json"
    outcomes_path = PUBLIC_SITEGRAPH_DIR / "outcomes.json"
    for path in (manifest_path, documents_path, outcomes_path):
        if not path.exists():
            fail(f"required generated artifact missing: {path}")

    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        fail("public/index/manifest.json must be an object")
    if manifest.get("strategy") != "sitegraph-backed-jwc-v1":
        fail(f"manifest.strategy must be sitegraph-backed-jwc-v1, got {manifest.get('strategy')!r}")
    if manifest.get("llm_enabled") is not False:
        fail("sitegraph-backed public index must not enable LLM")
    if manifest.get("old_source_channel_production_enabled") is not False:
        fail("old Source-Channel production path must be disabled")
    if manifest.get("github_resource_production_enabled") is not False:
        fail("GitHub resource production path must be disabled")
    if manifest.get("exam_vertical_preserved") is not True:
        fail("exam_vertical_preserved must be true")

    sitegraph = manifest.get("sitegraph") if isinstance(manifest.get("sitegraph"), dict) else {}
    truth_counts = sitegraph.get("truth_counts") if isinstance(sitegraph.get("truth_counts"), dict) else {}
    for field, actual in package["actual_counts"].items():
        if int(truth_counts.get(field, -1) or 0) != int(actual):
            fail(f"manifest.sitegraph.truth_counts.{field} mismatch: manifest={truth_counts.get(field)} actual={actual}")

    slim_documents = read_json(documents_path)
    if not isinstance(slim_documents, list):
        fail("public/index/documents.json must be a list")
    full_documents = load_full_documents(manifest)
    if len(slim_documents) != len(full_documents):
        fail(f"slim/full document count mismatch: slim={len(slim_documents)} full={len(full_documents)}")
    if int(manifest.get("total_documents", -1)) != len(full_documents):
        fail(f"manifest total_documents mismatch: manifest={manifest.get('total_documents')} full={len(full_documents)}")

    ids = [str(item.get("id") or "") for item in full_documents if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        fail("full documents contain duplicate ids")
    if len(ids) != len(full_documents):
        fail("full documents contain non-object or missing-id entries")

    detail_docs = {str(item.get("url")): item for item in full_documents if str(item.get("id", "")).startswith("sitegraph-jwc-detail-")}
    detail_urls = {str(item.get("url")) for item in package["detail_pages"]}
    missing_detail_urls = sorted(detail_urls.difference(detail_docs))
    if missing_detail_urls:
        fail(f"detail pages missing search records: {missing_detail_urls[:10]}")
    if len(detail_docs) != package["actual_counts"]["detail_pages"]:
        fail(f"detail document count mismatch: {len(detail_docs)} != {package['actual_counts']['detail_pages']}")

    attachment_metadata_count = 0
    for document in full_documents:
        if not isinstance(document, dict):
            fail("full documents contain non-object item")
        doc_id = str(document.get("id") or "")
        if document.get("source_id") != "jwc":
            fail(f"document {doc_id} has non-JWC source_id: {document.get('source_id')}")
        if document.get("semantic_mode") != "sitegraph_rule":
            fail(f"document {doc_id} has non-sitegraph semantic_mode: {document.get('semantic_mode')}")
        provenance = document.get("sitegraph_provenance")
        if not isinstance(provenance, dict) or provenance.get("site_id") != "jwc":
            fail(f"document {doc_id} missing JWC sitegraph_provenance")
        if document.get("llm", {}).get("used") is not False:
            fail(f"document {doc_id} unexpectedly used LLM")
        attachments = document.get("attachments") if isinstance(document.get("attachments"), list) else []
        attachment_metadata_count += len(attachments)
        for attachment in attachments:
            if not isinstance(attachment, dict):
                fail(f"document {doc_id} contains non-object attachment")
            for field in ("name", "url", "extension", "parent_url", "section_path"):
                if not attachment.get(field):
                    fail(f"document {doc_id} attachment missing searchable metadata field {field}")
            if attachment.get("metadata_only") is not True:
                fail(f"document {doc_id} attachment must be metadata_only")

    if attachment_metadata_count != package["actual_counts"]["attachments"]:
        fail(f"attachment metadata count mismatch: {attachment_metadata_count} != {package['actual_counts']['attachments']}")
    manifest_attachment_count = (manifest.get("sitegraph") or {}).get("attachment_metadata_records")
    if manifest_attachment_count != attachment_metadata_count:
        fail(
            "manifest.sitegraph.attachment_metadata_records mismatch: "
            f"{manifest_attachment_count} != {attachment_metadata_count}"
        )

    outcomes = read_json(outcomes_path)
    if not isinstance(outcomes, dict):
        fail("sitegraph outcomes must be an object")
    detail_records = outcomes.get("detail_page_records")
    if not isinstance(detail_records, list) or len(detail_records) != package["actual_counts"]["detail_pages"]:
        fail("outcomes.detail_page_records must cover every detail page")
    direct_attachment_records = outcomes.get("direct_attachment_records")
    if not isinstance(direct_attachment_records, list):
        fail("outcomes.direct_attachment_records must be a list")
    external_records = outcomes.get("external_record_only")
    if not isinstance(external_records, list):
        fail("outcomes.external_record_only must be a list")

    full_text = json.dumps(full_documents, ensure_ascii=False)
    for required in ("教务管理系统", "自主学分系统", "创新管理系统", "毕业设计系统", "考试信息查询"):
        if required not in full_text:
            fail(f"required system or utility record is not searchable: {required}")

    query_aliases_path = PUBLIC_INDEX_DIR / "query_aliases.json"
    if not query_aliases_path.exists():
        fail("public/index/query_aliases.json missing")
    aliases = read_json(query_aliases_path)
    for query in REQUIRED_QUERIES:
        if query not in full_text and query not in aliases:
            fail(f"representative query lacks searchable text or alias: {query}")

    return {
        "passed": True,
        "total_documents": len(full_documents),
        "detail_page_records": len(detail_docs),
        "direct_attachment_records": len(direct_attachment_records),
        "attachment_metadata_records": attachment_metadata_count,
        "external_record_only": len(external_records),
        "truth_counts": package["actual_counts"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the JWC sitegraph package and generated njupt-search index.")
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
