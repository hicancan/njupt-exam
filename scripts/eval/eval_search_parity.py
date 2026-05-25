"""Search Parity Check: validates Python route results against fixtures, and
compares Python vs TS ranking top5 when TS results are available.

Usage:
  python scripts/eval/eval_search_parity.py
  python scripts/eval/eval_search_parity.py --ts-results eval/reports/ts_search_results.json
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from search.query_router import route_query, load_query_routes


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_route_parity() -> dict:
    """Python router passes all route fixtures."""
    fixtures_path = os.path.join(BASE_DIR, "tests", "search_router_fixtures.json")
    if not os.path.exists(fixtures_path):
        return {"route_fixture_count": 0, "route_passed": 0, "route_failed": 0, "route_errors": ["Fixtures file not found"]}

    fixtures = load_json(fixtures_path)
    routes = load_query_routes(os.path.join(BASE_DIR, "config", "query_routes.json"))

    errors = []
    passes = 0
    for fixture in fixtures:
        query = fixture["query"]
        expected_type = fixture["expected_query_type"]
        expected_top1_exact = fixture.get("expected_top1_exact")

        result = route_query(query, routes)
        actual_type = result["query_type"]
        actual_top1_exact = result["top1_prefer_exact_title"]

        route_ok = actual_type == expected_type
        top1_exact_ok = expected_top1_exact is None or actual_top1_exact == expected_top1_exact

        if route_ok and top1_exact_ok:
            passes += 1
        else:
            msg_parts = []
            if not route_ok:
                msg_parts.append(f"route: expected {expected_type}, got {actual_type}")
            if not top1_exact_ok:
                msg_parts.append(f"top1_exact: expected {expected_top1_exact}, got {actual_top1_exact}")
            errors.append({"query": query, "errors": msg_parts})

    return {
        "route_fixture_count": len(fixtures),
        "route_passed": passes,
        "route_failed": len(fixtures) - passes,
        "route_errors": errors,
    }


def evaluate_ranking_parity(ts_results_path: str | None = None) -> dict:
    """Compare Python vs TS top5 when TS results are available."""
    if not ts_results_path or not os.path.exists(ts_results_path):
        return {"parity_available": False, "note": "TS search results not provided. Run eval_frontend_search.[mjs|ts] and pass --ts-results."}

    ts_results = load_json(ts_results_path)
    index_dir = os.path.join(BASE_DIR, "public", "index")
    if not os.path.exists(os.path.join(index_dir, "documents.json")):
        return {"parity_available": False, "note": "Index not built. Run update_search_index.py first."}

    from search.vertical_ranker import vertical_rank_documents

    documents = load_json(os.path.join(index_dir, "documents.json"))
    hybrid_index = load_json(os.path.join(index_dir, "hybrid_index.json"))
    query_aliases = load_json(os.path.join(BASE_DIR, "config", "query_aliases.json"))
    ranking_weights = load_json(os.path.join(BASE_DIR, "config", "ranking_weights.json"))

    total = 0
    top1_match = 0
    jaccard_sum = 0.0
    kendall_sum = 0.0
    details = []

    for ts_case in ts_results:
        query = ts_case["query"]
        if not query.strip():
            continue
        total += 1

        py_ranked = vertical_rank_documents(query, documents, hybrid_index, query_aliases, ranking_weights, limit=5)
        py_top5_ids = [str(doc.get("id", "")) for doc in py_ranked[:5]]
        ts_top5_ids = ts_case.get("top5_ids", [])

        # Jaccard
        py_set = set(py_top5_ids)
        ts_set = set(ts_top5_ids)
        union = py_set | ts_set
        intersection = py_set & ts_set
        jaccard = len(intersection) / len(union) if union else 0.0
        jaccard_sum += jaccard

        # Top1 match
        py_top1 = py_top5_ids[0] if py_top5_ids else ""
        ts_top1 = ts_top5_ids[0] if ts_top5_ids else ""
        if py_top1 and ts_top1 and py_top1 == ts_top1:
            top1_match += 1

        # Kendall tau approximation (rank correlation)
        all_ids = list(dict.fromkeys(py_top5_ids + ts_top5_ids))
        kendall = 0.0
        if len(all_ids) >= 2:
            concordant = 0
            discordant = 0
            for i in range(len(all_ids)):
                for j in range(i + 1, len(all_ids)):
                    a_i = py_top5_ids.index(all_ids[i]) if all_ids[i] in py_top5_ids else 99
                    a_j = py_top5_ids.index(all_ids[j]) if all_ids[j] in py_top5_ids else 99
                    b_i = ts_top5_ids.index(all_ids[i]) if all_ids[i] in ts_top5_ids else 99
                    b_j = ts_top5_ids.index(all_ids[j]) if all_ids[j] in ts_top5_ids else 99
                    if (a_i - a_j) * (b_i - b_j) > 0:
                        concordant += 1
                    elif (a_i - a_j) * (b_i - b_j) < 0:
                        discordant += 1
            pairs = concordant + discordant
            kendall = (concordant - discordant) / pairs if pairs else 0.0
        kendall_sum += kendall

        details.append({
            "query": query,
            "py_top5": py_top5_ids,
            "ts_top5": ts_top5_ids,
            "jaccard": round(jaccard, 4),
            "top1_match": py_top1 == ts_top1,
            "kendall_tau": round(kendall, 4),
        })

    return {
        "parity_available": True,
        "total_queries": total,
        "top1_match_count": top1_match,
        "top1_match_rate": round(top1_match / total, 4) if total else 0,
        "avg_jaccard": round(jaccard_sum / total, 4) if total else 0,
        "avg_kendall_tau": round(kendall_sum / total, 4) if total else 0,
        "details": details,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Search Parity Check")
    parser.add_argument("--ts-results", type=str, default=None, help="Path to TS search results JSON")
    args = parser.parse_args()

    route_parity = evaluate_route_parity()
    ranking_parity = evaluate_ranking_parity(args.ts_results)

    report = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "route_parity": route_parity,
        "ranking_parity": ranking_parity,
    }

    reports_dir = os.path.join(BASE_DIR, "eval", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, "search_parity_latest.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=== Search Parity Results ===")
    print(f"Route Fixture: {route_parity['route_passed']}/{route_parity['route_fixture_count']} passed")
    if route_parity["route_errors"]:
        for err in route_parity["route_errors"]:
            query = err["query"]
            for e in err["errors"]:
                print(f"  [FAIL] {query}: {e}")

    if ranking_parity["parity_available"]:
        print(f"Ranking Parity: top1_match={ranking_parity['top1_match_rate']}, avg_jaccard={ranking_parity['avg_jaccard']}, avg_kendall={ranking_parity['avg_kendall_tau']}")
    else:
        print(f"Ranking Parity: {ranking_parity.get('note', 'Not available')}")

    print(f"Report saved to: {report_path}")

    if route_parity["route_failed"] > 0:
        print("\n[FAILED] Search Parity Gate: route fixture mismatch.")
        sys.exit(1)

    print("\n[PASS] Search Parity Gate passed.")


if __name__ == "__main__":
    main()
