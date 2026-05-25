import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from search.vertical_ranker import vertical_rank_documents
from search.query_router import route_query, load_query_routes

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def evaluate_cases():
    index_dir = os.path.join(BASE_DIR, "public", "index")
    documents = load_json(os.path.join(index_dir, "documents.json"))
    hybrid_index = load_json(os.path.join(index_dir, "hybrid_index.json"))
    query_aliases = load_json(os.path.join(BASE_DIR, "config", "query_aliases.json"))
    ranking_weights = load_json(os.path.join(BASE_DIR, "config", "ranking_weights.json"))
    routes = load_query_routes(os.path.join(BASE_DIR, "config", "query_routes.json"))
    
    cases = load_json(os.path.join(BASE_DIR, "eval", "search_cases.json"))
    
    total = len(cases)
    route_correct = 0
    bad_top5_rate = 0
    blocked_source_violations = 0
    blocked_domain_violations = 0
    
    errors = []
    
    from datetime import datetime
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_cases": total,
        "route_accuracy": 0,
        "bad_top5_rate": 0,
        "blocked_source_violations": 0,
        "blocked_domain_violations": 0,
        "errors": [],
        "case_details": []
    }
    
    for case in cases:
        query = case["query"]
        expected_route = case.get("route")
        
        # Check Route Accuracy
        route_obj = route_query(query, routes)
        if expected_route and route_obj["query_type"] == expected_route:
            route_correct += 1
        elif expected_route:
            errors.append(f"Route mismatch for '{query}': expected {expected_route}, got {route_obj['query_type']}")
            
        ranked = vertical_rank_documents(query, documents, hybrid_index, query_aliases, ranking_weights, limit=5)
        top5 = ranked[:5]
        top1 = ranked[0] if ranked else None
        
        top1_must_domain = set(case.get("top1_must_domain_any", []))
        top1_must_source = case.get("top1_must_source")
        top5_must_include_source = set(case.get("top5_must_include_source_any", []))
        top5_must_include_domain = set(case.get("top5_must_include_domain_any", []))
        top5_must_not_source = set(case.get("top5_must_not_source_any", []))
        top5_must_not_domain = set(case.get("top5_must_not_domain_any", []))
        
        case_failed = False
        
        if top1_must_domain and top1:
            if top1.get("domain") not in top1_must_domain:
                errors.append(f"Query '{query}': top1 domain {top1.get('domain')} not in {top1_must_domain}")
                case_failed = True
                
        if top1_must_source and top1:
            if top1.get("source") != top1_must_source and top1.get("source_id") != top1_must_source:
                errors.append(f"Query '{query}': top1 source {top1.get('source')} != {top1_must_source}")
                case_failed = True
                
        if top5_must_include_source:
            found = any(doc.get("source") in top5_must_include_source or doc.get("source_id") in top5_must_include_source for doc in top5)
            if not found:
                errors.append(f"Query '{query}': top5 missing required sources {top5_must_include_source}")
                case_failed = True
                
        if top5_must_include_domain:
            found = any(doc.get("domain") in top5_must_include_domain for doc in top5)
            if not found:
                errors.append(f"Query '{query}': top5 missing required domains {top5_must_include_domain}")
                case_failed = True
                
        # Hard blocks
        for doc in top5:
            if top5_must_not_source and (doc.get("source") in top5_must_not_source or doc.get("source_id") in top5_must_not_source):
                blocked_source_violations += 1
                errors.append(f"Query '{query}': top5 contains blocked source '{doc.get('source')}' - {doc.get('title')}")
                case_failed = True
            if top5_must_not_domain and doc.get("domain") in top5_must_not_domain:
                blocked_domain_violations += 1
                errors.append(f"Query '{query}': top5 contains blocked domain '{doc.get('domain')}' - {doc.get('title')}")
                case_failed = True
                
        if case_failed:
            bad_top5_rate += 1
            
        report["case_details"].append({
            "query": query,
            "route_obj": route_obj,
            "top5": [
                {"id": doc.get("id"), "title": doc.get("title"), "domain": doc.get("domain"), "source": doc.get("source")}
                for doc in top5
            ],
            "passed": not case_failed
        })

    report["route_accuracy"] = route_correct / total if total else 0
    report["bad_top5_rate"] = bad_top5_rate / total if total else 0
    report["blocked_source_violations"] = blocked_source_violations
    report["blocked_domain_violations"] = blocked_domain_violations
    report["errors"] = errors
    
    reports_dir = os.path.join(BASE_DIR, "eval", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, "product_search_latest.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=== Product Search Gate Results ===")
    print(f"Total Cases: {total}")
    print(f"Route Accuracy: {route_correct}/{total} ({(report['route_accuracy'])*100:.1f}%)")
    print(f"Bad Top5 Count: {bad_top5_rate}")
    print(f"Blocked Source Violations: {blocked_source_violations}")
    print(f"Blocked Domain Violations: {blocked_domain_violations}")
    print(f"Report saved to: {report_path}")
    
    if errors:
        print("\nErrors Found:")
        for err in errors:
            print(f" - {err}")
            
    if bad_top5_rate > 0 or blocked_source_violations > 0 or blocked_domain_violations > 0 or route_correct < total:
        print("\n[FAILED] CI Gate failed due to quality violations or route mismatches.")
        sys.exit(1)
    
    print("\n[PASS] Product Search Quality Gate passed successfully.")

if __name__ == "__main__":
    evaluate_cases()
