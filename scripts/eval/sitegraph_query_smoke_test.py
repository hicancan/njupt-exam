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

from search.vertical_ranker import recall_documents  # noqa: E402


REPRESENTATIVE_QUERIES = (
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


def load_full_documents() -> list[dict[str, Any]]:
    manifest = read_json(BASE_DIR / "public" / "index" / "manifest.json")
    sitegraph = manifest.get("sitegraph") if isinstance(manifest, dict) else {}
    shards = sitegraph.get("shards") if isinstance(sitegraph, dict) else []
    documents: list[dict[str, Any]] = []
    for shard in shards or []:
        shard_path = BASE_DIR / "public" / str(shard.get("path") or "")
        payload = read_json(shard_path)
        if not isinstance(payload, list):
            raise ValueError(f"full-text shard must contain a list: {shard_path}")
        documents.extend(payload)
    if not documents:
        raise ValueError("no sitegraph full-text documents found")
    return documents


def main() -> None:
    os.chdir(BASE_DIR)
    documents = load_full_documents()
    query_aliases = read_json(BASE_DIR / "public" / "index" / "query_aliases.json")
    failures: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for query in REPRESENTATIVE_QUERIES:
        results = recall_documents(query, documents, query_aliases=query_aliases, limit=5)
        top = results[:5]
        if not top:
            failures.append({"query": query, "reason": "empty_top5"})
            rows.append({"query": query, "status": "fail", "top": []})
            continue
        if any(item.get("source_id") != "jwc" for item in top):
            failures.append({"query": query, "reason": "non_jwc_source_in_top5"})
        if query == "教务管理系统" and not any("教务管理系统" in str(item.get("title") or "") for item in top):
            failures.append({"query": query, "reason": "external_system_not_visible"})
        rows.append(
            {
                "query": query,
                "status": "ok",
                "top": [
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "source_id": item.get("source_id"),
                        "channel_id": item.get("channel_id"),
                        "url": item.get("url"),
                        "score_reason": item.get("score_reason"),
                    }
                    for item in top
                ],
            }
        )

    payload = {
        "passed": not failures,
        "query_count": len(REPRESENTATIVE_QUERIES),
        "failure_count": len(failures),
        "failures": failures,
        "queries": rows,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
