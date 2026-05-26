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

from build_sitegraph_index import DEFAULT_SITEGRAPH_INDEX, validate_sitegraph_package  # noqa: E402
from validate_sitegraph_index import validate_generated_index  # noqa: E402


PUBLIC_INDEX_DIR = BASE_DIR / "public" / "index"


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fail(message: str) -> None:
    print(f"[validate_search_index] {message}", file=sys.stderr)
    raise SystemExit(1)


def validate_contract_value(path: str, item_id: str, field: str, value: object, allowed: tuple[str, ...]) -> None:
    if str(value or "") not in allowed:
        fail(f"{path} item {item_id} invalid {field}={value!r}; allowed values: {', '.join(allowed)}")


def ensure_absent(payload: Any, forbidden: set[str], path: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in forbidden:
                fail(f"{path}.{key} is forbidden in the pure sitegraph index")
            ensure_absent(value, forbidden, f"{path}.{key}")
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            ensure_absent(item, forbidden, f"{path}[{index}]")


def main() -> None:
    os.chdir(BASE_DIR)
    manifest_path = PUBLIC_INDEX_DIR / "manifest.json"
    if not manifest_path.exists():
        fail("public/index/manifest.json does not exist")
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        fail("manifest must be an object")
    ensure_absent(
        manifest,
        {
            "llm",
            "llm_provider",
            "llm_schema_version",
            "semantic_mode",
            "task_frames",
            "llm_in_core_path",
            "old_hytask_removed",
            "source_channel_production_enabled",
            "github_resource_production_enabled",
        },
    )
    if manifest.get("strategy") != "pure-sitegraph-code-search-v2":
        fail(f"unexpected manifest strategy: {manifest.get('strategy')!r}")
    manifest_text = json.dumps(manifest, ensure_ascii=False)
    if "D:\\" in manifest_text or "D:/" in manifest_text:
        fail("public manifest must not expose local D: paths")
    for field in ("producer_repo", "producer_ref", "site_id", "artifact_path", "upstream_generated_at", "truth_counts"):
        if not manifest.get(field):
            fail(f"manifest missing required v2 producer field: {field}")
    core_search = manifest.get("core_search") if isinstance(manifest.get("core_search"), dict) else {}
    if core_search.get("execution_model") != "pure_frontend_worker":
        fail("core search must execute in the pure frontend worker")
    if core_search.get("first_screen_artifacts") != ["doc_meta_light", "light_inverted_index", "query_aliases"]:
        fail("first screen must only load manifest, doc_meta_light, light_inverted_index, and query_aliases")
    if core_search.get("body_index_loading") != "on_deep_search":
        fail("body index must be loaded only on deep search")
    if core_search.get("full_text_loading") != "on_demand_by_candidate_shard":
        fail("full text must be loaded on demand by candidate shard")
    if core_search.get("search_worker") is not True:
        fail("search worker must be enabled")

    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    required = (
        "doc_meta_light",
        "light_inverted_index",
        "body_inverted_index",
        "section_index",
        "attachment_index",
        "external_index",
        "query_aliases",
        "outcomes",
        "size_report",
    )
    for name in required:
        entry = artifacts.get(name)
        if not isinstance(entry, dict) or not entry.get("path"):
            fail(f"manifest.artifacts.{name}.path is missing")
        relative = str(entry["path"])
        if "\\" in relative or ":" in relative:
            fail(f"artifact path must be public-relative: {relative}")
        if not (BASE_DIR / "public" / relative).exists():
            fail(f"missing pure sitegraph index artifact: {relative}")
        if not relative.endswith(".json") or len(relative.rsplit(".", 2)) < 3:
            fail(f"artifact must use content hash filename: {relative}")
    for stale in (
        "documents.json",
        "task_frames.json",
        "ontology.json",
        "doc_meta.json",
        "inverted_index.json",
        "section_index.json",
        "attachment_index.json",
        "external_index.json",
        "query_aliases.json",
    ):
        if (PUBLIC_INDEX_DIR / stale).exists():
            fail(f"stale old search artifact still exists: {stale}")

    if DEFAULT_SITEGRAPH_INDEX.exists():
        validate_generated_index(validate_sitegraph_package(DEFAULT_SITEGRAPH_INDEX))
    print("[validate_search_index] ok")


if __name__ == "__main__":
    main()
