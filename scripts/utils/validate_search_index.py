from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from models.search_contract import (  # noqa: E402
    SEARCH_CATEGORIES,
    SEARCH_DOCUMENT_KINDS,
    SEARCH_DOMAINS,
    SEARCH_INTENTS,
    SEARCH_LIFECYCLES,
    SEARCH_SEMANTIC_MODES,
    SEARCH_SOURCE_TYPES,
    TASK_FRAME_SOURCE_MODES,
    TASK_TYPES,
)
from validate_sitegraph_ingest import validate_generated_index  # noqa: E402


DOCUMENTS_PATH = BASE_DIR / "public" / "index" / "documents.json"
MANIFEST_PATH = BASE_DIR / "public" / "index" / "manifest.json"
TASK_FRAMES_PATH = BASE_DIR / "public" / "index" / "task_frames.json"

REQUIRED_DOCUMENT_FIELDS = {
    "id",
    "kind",
    "source_id",
    "channel_id",
    "channel",
    "title",
    "url",
    "source",
    "source_domain",
    "source_type",
    "category",
    "domain",
    "intent",
    "lifecycle",
    "audience",
    "published_at",
    "content",
    "attachments",
    "tags",
    "hash",
    "canonical",
    "rule_guard",
    "task_frames",
    "semantic_mode",
    "sitegraph_provenance",
}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fail(message: str) -> None:
    print(f"[validate_search_index] {message}", file=sys.stderr)
    raise SystemExit(1)


def contract_error(path: str, item_id: str, field: str, value: object, allowed: tuple[str, ...]) -> str:
    return (
        f"{path} item {item_id} invalid {field}={value!r}; "
        f"allowed values: {', '.join(allowed)}"
    )


def validate_contract_value(path: str, item_id: str, field: str, value: object, allowed: tuple[str, ...]) -> None:
    if str(value or "") not in allowed:
        fail(contract_error(path, item_id, field, value, allowed))


def validate_attachment(document_id: str, attachment: dict[str, Any]) -> None:
    for field in ("name", "url", "extension", "parent_url", "section_path"):
        if not attachment.get(field):
            fail(f"document {document_id} attachment missing {field}")
    if attachment.get("metadata_only") is not True:
        fail(f"document {document_id} attachment must be metadata_only")


def validate_task_frame(frame: dict[str, Any]) -> None:
    frame_id = str(frame.get("task_id") or frame.get("doc_id") or "<unknown>")
    for field in ("task_id", "doc_id", "source_mode", "task_type", "who", "what", "action", "time", "source", "evidence", "risk"):
        if field not in frame:
            fail(f"task frame {frame_id} missing {field}")
    validate_contract_value(str(TASK_FRAMES_PATH), frame_id, "source_mode", frame.get("source_mode"), TASK_FRAME_SOURCE_MODES)
    validate_contract_value(str(TASK_FRAMES_PATH), frame_id, "task_type", frame.get("task_type"), TASK_TYPES)
    time_payload = frame.get("time") if isinstance(frame.get("time"), dict) else {}
    validate_contract_value(str(TASK_FRAMES_PATH), frame_id, "time.lifecycle", time_payload.get("lifecycle"), SEARCH_LIFECYCLES)


def validate_documents(documents: list[dict[str, Any]], source: str) -> None:
    seen: set[str] = set()
    for document in documents:
        if not isinstance(document, dict):
            fail(f"{source} contains a non-object item")
        doc_id = str(document.get("id") or "")
        if not doc_id:
            fail(f"{source} contains document missing id")
        if doc_id in seen:
            fail(f"{source} contains duplicate document id: {doc_id}")
        seen.add(doc_id)
        missing = REQUIRED_DOCUMENT_FIELDS.difference(document)
        if missing:
            fail(f"document {doc_id} missing fields: {sorted(missing)}")
        validate_contract_value(source, doc_id, "kind", document.get("kind"), SEARCH_DOCUMENT_KINDS)
        validate_contract_value(source, doc_id, "category", document.get("category"), SEARCH_CATEGORIES)
        validate_contract_value(source, doc_id, "domain", document.get("domain"), SEARCH_DOMAINS)
        validate_contract_value(source, doc_id, "intent", document.get("intent"), SEARCH_INTENTS)
        validate_contract_value(source, doc_id, "source_type", document.get("source_type"), SEARCH_SOURCE_TYPES)
        validate_contract_value(source, doc_id, "lifecycle", document.get("lifecycle"), SEARCH_LIFECYCLES)
        validate_contract_value(source, doc_id, "semantic_mode", document.get("semantic_mode"), SEARCH_SEMANTIC_MODES)
        if document.get("source_id") != "jwc":
            fail(f"non-exam public search document must come from JWC sitegraph: {doc_id}")
        if document.get("semantic_mode") != "sitegraph_rule":
            fail(f"document {doc_id} must have semantic_mode=sitegraph_rule")
        if not isinstance(document.get("sitegraph_provenance"), dict):
            fail(f"document {doc_id} missing sitegraph_provenance")
        if document.get("llm", {}).get("used") is not False:
            fail(f"document {doc_id} must not use LLM")
        if not isinstance(document.get("canonical"), dict):
            fail(f"document {doc_id} has invalid canonical object")
        if not isinstance(document.get("rule_guard"), dict):
            fail(f"document {doc_id} has invalid rule_guard object")
        attachments = document.get("attachments")
        if not isinstance(attachments, list):
            fail(f"document {doc_id} has invalid attachments")
        for attachment in attachments:
            if not isinstance(attachment, dict):
                fail(f"document {doc_id} contains non-object attachment")
            validate_attachment(doc_id, attachment)
        frames = document.get("task_frames")
        if not isinstance(frames, list):
            fail(f"document {doc_id} has invalid task_frames")
        for frame in frames:
            if not isinstance(frame, dict):
                fail(f"document {doc_id} contains non-object task frame")
            validate_task_frame(frame)


def load_full_documents(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    shards = (((manifest.get("sitegraph") or {}).get("shards")) or [])
    if not isinstance(shards, list) or not shards:
        fail("manifest.sitegraph.shards missing")
    documents: list[dict[str, Any]] = []
    for shard in shards:
        shard_path = BASE_DIR / "public" / str(shard.get("path") or "")
        payload = read_json(shard_path)
        if not isinstance(payload, list):
            fail(f"full-text shard must be a list: {shard_path}")
        documents.extend(payload)
    return documents


def validate_manifest(manifest: dict[str, Any], full_documents: list[dict[str, Any]]) -> None:
    if manifest.get("strategy") != "sitegraph-backed-jwc-v1":
        fail(f"manifest strategy is not sitegraph-backed-jwc-v1: {manifest.get('strategy')}")
    if manifest.get("llm_enabled") is not False:
        fail("manifest must have llm_enabled=false")
    if manifest.get("old_source_channel_production_enabled") is not False:
        fail("old source-channel production path must be disabled")
    if manifest.get("github_resource_production_enabled") is not False:
        fail("GitHub production path must be disabled")
    if manifest.get("exam_vertical_preserved") is not True:
        fail("exam vertical preservation flag missing")
    if int(manifest.get("total_documents", -1)) != len(full_documents):
        fail("manifest total_documents does not match full document count")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or len(sources) != 1 or sources[0].get("id") != "jwc":
        fail("manifest sources must contain exactly the JWC sitegraph source")


def main() -> None:
    os.chdir(BASE_DIR)
    if not DOCUMENTS_PATH.exists():
        fail("public/index/documents.json does not exist")
    if not MANIFEST_PATH.exists():
        fail("public/index/manifest.json does not exist")
    manifest = read_json(MANIFEST_PATH)
    if not isinstance(manifest, dict):
        fail("manifest must be an object")
    slim_documents = read_json(DOCUMENTS_PATH)
    if not isinstance(slim_documents, list):
        fail("documents.json must be a list")
    full_documents = load_full_documents(manifest)
    if len(slim_documents) != len(full_documents):
        fail(f"slim/full document count mismatch: {len(slim_documents)} != {len(full_documents)}")
    validate_documents(full_documents, str(DOCUMENTS_PATH))
    validate_manifest(manifest, full_documents)

    task_frames = read_json(TASK_FRAMES_PATH)
    if not isinstance(task_frames, list):
        fail("task_frames.json must be a list")
    for frame in task_frames:
        if not isinstance(frame, dict):
            fail("task_frames.json contains non-object frame")
        validate_task_frame(frame)

    # If the sibling sitegraph checkout exists, run the stronger upstream/downstream proof.
    from ingest_sitegraph import DEFAULT_SITEGRAPH_INDEX, validate_sitegraph_package  # noqa: WPS433

    if DEFAULT_SITEGRAPH_INDEX.exists():
        validate_generated_index(validate_sitegraph_package(DEFAULT_SITEGRAPH_INDEX))
    print("[validate_search_index] ok")


if __name__ == "__main__":
    main()
