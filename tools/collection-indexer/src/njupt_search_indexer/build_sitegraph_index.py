from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from . import sitegraph_public_index as public_index
from .sitegraph_documents import build_documents
from .sitegraph_source import (
    load_collection_source_packages,
    package_source_id,
    validate_sitegraph_package,
)


_PUBLIC_INDEX_EXPORTS = {
    "BASE_DIR",
    "PUBLIC_ROOT",
    "COLLECTION_ID",
    "PUBLIC_INDEX_DIR",
    "PUBLIC_SITEGRAPH_DIR",
    "PUBLIC_ARTIFACT_DIR",
    "PUBLIC_SHARD_DIR",
    "OBSOLETE_INDEX_DIR",
}

aggregate_counts = public_index.aggregate_counts
configure_collection_output = public_index.configure_collection_output
write_public_index = public_index.write_public_index


def __getattr__(name: str) -> Any:
    if name in _PUBLIC_INDEX_EXPORTS:
        return getattr(public_index, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def merge_built_packages(built_packages: list[dict[str, Any]]) -> dict[str, Any]:
    documents: list[dict[str, Any]] = []
    attachment_index: list[dict[str, Any]] = []
    external_index: list[dict[str, Any]] = []
    outcomes: dict[str, list[dict[str, Any]]] = {
        "detail_page_records": [],
        "attachment_metadata_records": [],
        "direct_attachment_records": [],
        "external_link_records": [],
        "utility_link_records": [],
    }
    for built in built_packages:
        for document in built["documents"]:
            document["doc_index"] = len(documents)
            documents.append(document)
        attachment_index.extend(built["attachment_index"])
        external_index.extend(built["external_index"])
        for key in outcomes:
            outcomes[key].extend(built["outcomes"].get(key) or [])
    return {
        "documents": documents,
        "attachment_index": attachment_index,
        "external_index": external_index,
        "outcomes": outcomes,
    }


def build_sitegraph_indexes(index_dirs: list[Path] | tuple[Path, ...], *, shard_size: int = 1000) -> dict[str, Any]:
    packages = [validate_sitegraph_package(index_dir) for index_dir in index_dirs]
    built = merge_built_packages([build_documents(package) for package in packages])
    manifest = public_index.write_public_index(packages, built, shard_size=shard_size)
    return {
        "sitegraph_indexes": [str(index_dir) for index_dir in index_dirs],
        "source_ids": [package_source_id(package) for package in packages],
        "generated_documents": manifest["total_documents"],
        "detail_page_records": manifest["sitegraph"]["detail_page_records"],
        "attachment_metadata_records": manifest["sitegraph"]["attachment_metadata_records"],
        "direct_attachment_records": manifest["sitegraph"]["direct_attachment_records"],
        "external_link_records": manifest["sitegraph"]["external_link_records"],
        "utility_link_records": manifest["sitegraph"]["utility_link_records"],
        "truth_counts": manifest["sitegraph"]["truth_counts"],
        "source_manifests": manifest["sitegraph"]["source_manifests"],
        "total_shards": manifest["progressive_search"]["total_shards"],
        "public_index": str(public_index.PUBLIC_INDEX_DIR),
    }


def build_sitegraph_index(index_dir: Path, *, shard_size: int = 1000) -> dict[str, Any]:
    return build_sitegraph_indexes([index_dir], shard_size=shard_size)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build generated collection search artifacts for njupt-search.")
    parser.add_argument(
        "--source-package",
        dest="source_packages",
        action="append",
        type=Path,
        default=None,
        help="Path to an audited njupt-site-graph source package index. Repeat for multiple source packages.",
    )
    parser.add_argument("--collection-id", default=public_index.COLLECTION_ID)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--shard-size", type=int, default=1000, help="Number of full documents per shard")
    args = parser.parse_args()
    public_index.configure_collection_output(args.collection_id, args.out)
    source_packages = args.source_packages or load_collection_source_packages()
    summary = build_sitegraph_indexes([path.resolve() for path in source_packages], shard_size=args.shard_size)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
