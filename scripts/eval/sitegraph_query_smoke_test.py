from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from sitegraph_search import recall_documents  # noqa: E402


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


def main() -> None:
    failures: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for query in REPRESENTATIVE_QUERIES:
        top = recall_documents(query, limit=5)
        if not top:
            failures.append({"query": query, "reason": "empty_top5"})
            rows.append({"query": query, "status": "fail", "top": []})
            continue
        if query == "教务管理系统" and not any("教务管理系统" in str(item.get("title") or "") for item in top):
            failures.append({"query": query, "reason": "system_entry_not_visible"})
        rows.append(
            {
                "query": query,
                "status": "ok",
                "top": [
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "record_type": item.get("record_type"),
                        "facet": item.get("facet"),
                        "url": item.get("url"),
                        "score": item.get("score"),
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
