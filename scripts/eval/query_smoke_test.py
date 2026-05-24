import json
import os
import sys
from typing import Any

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(SCRIPTS_DIR)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from core.hybrid_ranker import rank_documents
from eval_search import build_exam_documents, read_json


REQUIRED_QUERIES = {
    "保研",
    "推免",
    "奖学金",
    "助学金",
    "困难认定",
    "大创",
    "挑战杯",
    "蓝桥杯",
    "宣讲会",
    "实习",
    "停电",
    "停水",
    "图书馆开放",
    "四六级",
    "补考",
    "转专业",
    "毕业设计",
    "论文答辩",
    "海外交流",
    "校园网",
    "医保",
    "档案",
    "B250403",
    "高数",
    "离散数学",
}


def main() -> None:
    documents = read_json(os.path.join(BASE_DIR, "public", "index", "documents.json"))
    documents.extend(build_exam_documents(read_json(os.path.join(BASE_DIR, "public", "data", "all_exams.json"))))
    hybrid_index = read_json(os.path.join(BASE_DIR, "public", "index", "hybrid_index.json"))
    query_aliases = read_json(os.path.join(BASE_DIR, "public", "index", "query_aliases.json"))
    ranking_weights = read_json(os.path.join(BASE_DIR, "config", "ranking_weights.json"))
    queries = read_json(os.path.join(BASE_DIR, "eval", "queries.json"))
    query_texts = [str(item.get("query") or "") for item in queries]

    missing = sorted(REQUIRED_QUERIES.difference(query_texts))
    failures: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    if missing:
        failures.append({"type": "missing_query", "queries": missing})

    for query in query_texts:
        ranked = rank_documents(query, documents, hybrid_index, query_aliases, ranking_weights, limit=5)
        top = ranked[:5]
        if not top:
            failures.append({"type": "empty_top5", "query": query})
            rows.append({"query": query, "top_ids": [], "status": "fail"})
            continue

        if any(not item.get("score_reason") for item in top):
            failures.append({"type": "missing_score_reason", "query": query})
        if len({item.get("id") for item in top}) != len(top):
            failures.append({"type": "duplicate_top5", "query": query})
        if query == "B250403" and not any(str(item.get("source_id")) == "exam_vertical" for item in top):
            failures.append({"type": "exam_not_top5", "query": query, "top_ids": [item.get("id") for item in top]})

        github_first = str(top[0].get("source_type")) == "github_resource"
        official_in_top = any(str(item.get("source_type")) in {"central_admin", "central_notice", "service_unit", "job_platform", "policy", "exam_vertical"} for item in top)
        if github_first and official_in_top and query not in {"高数", "离散数学", "毕业设计"}:
            failures.append({"type": "resource_over_official", "query": query, "top_ids": [item.get("id") for item in top]})

        if any((item.get("rule_guard") or {}).get("restricted") and not item.get("review_required") for item in top):
            failures.append({"type": "restricted_without_review", "query": query})
        if all(float(item.get("score", 0) or 0) <= 0 for item in top):
            failures.append({"type": "non_positive_scores", "query": query})

        rows.append({
            "query": query,
            "top_ids": [item.get("id") for item in top],
            "top_sources": [item.get("source_id") for item in top],
            "status": "ok",
        })

    payload = {
        "query_count": len(query_texts),
        "passed": not failures,
        "failure_count": len(failures),
        "failures": failures,
        "queries": rows,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
