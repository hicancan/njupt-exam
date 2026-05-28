from __future__ import annotations

import argparse
import json
from pathlib import Path

from .sitegraph_search import PUBLIC_INDEX_DIR
from .sitegraph_query_smoke_test import validate_quality
from .sitegraph_task_query_eval import validate_task_queries


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic njupt-search representative query evaluation.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    smoke_parser = subparsers.add_parser("run-smoke-queries", help="Run the representative query smoke suite.")
    smoke_parser.add_argument("--collection", type=Path, default=None, help="Generated collection directory. Reserved for the layout migration.")
    task_parser = subparsers.add_parser("run-task-queries", help="Run data-driven student task query expectations.")
    task_parser.add_argument("--collection", type=Path, default=None, help="Generated collection directory. Reserved for the layout migration.")
    task_parser.add_argument("--expectations", type=Path, default=None, help="Path to expected_results.json.")
    args = parser.parse_args()

    if args.collection is not None and args.collection.resolve() != PUBLIC_INDEX_DIR.resolve():
        raise SystemExit(f"Only the generated njupt-public collection is supported: {PUBLIC_INDEX_DIR}")
    if args.command == "run-smoke-queries":
        print(json.dumps(validate_quality(), ensure_ascii=False, indent=2))
    elif args.command == "run-task-queries":
        print(json.dumps(validate_task_queries(args.expectations) if args.expectations else validate_task_queries(), ensure_ascii=False, indent=2))
