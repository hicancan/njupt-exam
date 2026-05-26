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
    ensure_absent(manifest, {"llm", "llm_provider", "llm_schema_version", "semantic_mode", "task_frames"})
    if manifest.get("strategy") != "pure-sitegraph-code-search-v1":
        fail(f"unexpected manifest strategy: {manifest.get('strategy')!r}")
    core_search = manifest.get("core_search") if isinstance(manifest.get("core_search"), dict) else {}
    if core_search.get("llm_in_core_path") is not False:
        fail("LLM must not be in the core search path")
    if core_search.get("source_channel_production_enabled") is not False:
        fail("Source-Channel production path must be disabled")
    if core_search.get("github_resource_production_enabled") is not False:
        fail("GitHub resource production path must be disabled")
    if core_search.get("full_text_loading") != "on_demand_by_shard":
        fail("full text must be loaded on demand by shard")

    required = (
        "doc_meta.json",
        "inverted_index.json",
        "section_index.json",
        "attachment_index.json",
        "external_index.json",
        "query_aliases.json",
        "sitegraph/jwc/outcomes.json",
    )
    for relative in required:
        if not (PUBLIC_INDEX_DIR / relative).exists():
            fail(f"missing pure sitegraph index artifact: {relative}")
    for stale in ("documents.json", "task_frames.json", "ontology.json"):
        if (PUBLIC_INDEX_DIR / stale).exists():
            fail(f"stale old search artifact still exists: {stale}")

    if DEFAULT_SITEGRAPH_INDEX.exists():
        validate_generated_index(validate_sitegraph_package(DEFAULT_SITEGRAPH_INDEX))
    print("[validate_search_index] ok")


if __name__ == "__main__":
    main()
