import json
import os
import sys
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from search.vertical_ranker import vertical_rank_documents
from search.query_router import route_query, load_query_routes

BEIJING_TZ = timezone(timedelta(hours=8))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _days_from_now(date_like):
    if not date_like:
        return None
    try:
        dt = datetime.fromisoformat(str(date_like))
        return (datetime.now(BEIJING_TZ) - dt).total_seconds() / 86400
    except (ValueError, TypeError):
        return None


def _calc_freshness(date_like):
    days = _days_from_now(date_like)
    if days is None:
        return 0.45
    if days < -120:
        return 0.66
    if days < 0:
        return 0.95
    if days <= 3:
        return 1.0
    if days <= 7:
        return 0.92
    if days <= 30:
        return 0.78
    if days <= 180:
        return 0.58
    return 0.42


def build_exam_documents_py(exams):
    """Mirrors TypeScript buildExamDocuments in searchIndex.ts."""
    documents = []
    for exam in exams:
        title = f"{exam.get('class_name', '')} {exam.get('course_name', '')} 考试安排"
        content = " ".join(
            str(exam.get(k, "") or "")
            for k in ["class_name", "course_name", "course_code", "teacher", "location",
                       "raw_time", "campus", "school", "student_school", "major", "grade", "notes"]
        )
        raw_time = exam.get("raw_time") or ""
        location = exam.get("location") or ""
        exam_id = exam.get("id", "")
        published_at = exam.get("date") or exam.get("start_timestamp")

        documents.append({
            "id": f"exam-{exam_id}",
            "kind": "exam",
            "source_id": "exam_vertical",
            "channel_id": "exam_schedule",
            "channel": "考试安排",
            "title": title,
            "url": f"?class={exam.get('class_name', '')}",
            "source": "考试垂直频道",
            "source_domain": "jwc.njupt.edu.cn",
            "source_type": "exam_vertical",
            "category": "考试",
            "domain": "exam",
            "intent": "schedule",
            "lifecycle": "active",
            "evidence": [raw_time or location or title],
            "confidence": 0.6 if exam.get("parse_error") else 0.98,
            "sub_category": None,
            "deadline": None,
            "action_required": False,
            "action_type": None,
            "action_summary": None,
            "required_materials": [],
            "sensitive": False,
            "sensitive_types": [],
            "review_required": False,
            "risk_flags": [],
            "audience": ["本科生"],
            "published_at": published_at,
            "content": content or title,
            "summary": f"{raw_time or '时间待确认'} · {location or '地点待确认'}",
            "attachments": [],
            "student_score": 1.0,
            "freshness_score": _calc_freshness(exam.get("date") or exam.get("start_timestamp")),
            "importance_score": 0.94,
            "source_weight": 1.0,
            "tags": ["考试", "期末", exam.get("class_name", ""), exam.get("course_name", ""),
                      exam.get("campus", ""), exam.get("major", "")],
            "hash": exam_id,
            "class_name": exam.get("class_name"),
            "exam_id": exam_id,
        })
    return documents


def evaluate_cases():
    index_dir = os.path.join(BASE_DIR, "public", "index")
    documents = load_json(os.path.join(index_dir, "documents.json"))
    hybrid_index = load_json(os.path.join(index_dir, "hybrid_index.json"))
    query_aliases = load_json(os.path.join(BASE_DIR, "config", "query_aliases.json"))
    ranking_weights = load_json(os.path.join(BASE_DIR, "config", "ranking_weights.json"))
    routes = load_query_routes(os.path.join(BASE_DIR, "config", "query_routes.json"))

    # Inject exam_vertical documents (mirrors frontend buildExamDocuments)
    exam_data_path = os.path.join(BASE_DIR, "public", "data", "all_exams.json")
    if os.path.exists(exam_data_path):
        exam_data = load_json(exam_data_path)
        exam_docs = build_exam_documents_py(exam_data)
        documents = documents + exam_docs

    cases = load_json(os.path.join(BASE_DIR, "eval", "search_cases.json"))
    
    total = len(cases)
    route_correct = 0
    bad_top5_count = 0
    blocked_source_violations = 0
    blocked_domain_violations = 0
    degraded_fallback_count = 0
    empty_result_violation_count = 0
    exam_vertical_top1_correct = 0
    exam_vertical_top1_total = 0

    errors = []

    from datetime import datetime

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_cases": total,
        "route_accuracy": 0,
        "bad_top5_rate": 0,
        "blocked_source_violations": 0,
        "blocked_domain_violations": 0,
        "degraded_fallback_count": 0,
        "empty_result_violation_count": 0,
        "exam_vertical_top1_accuracy": 0,
        "errors": [],
        "case_details": []
    }

    for case in cases:
        query = case["query"]
        expected_route = case.get("route")
        allow_empty = case.get("allow_empty", False)

        # Check Route Accuracy
        route_obj = route_query(query, routes)
        if expected_route and route_obj["query_type"] == expected_route:
            route_correct += 1
        elif expected_route:
            errors.append(f"Route mismatch for '{query}': expected {expected_route}, got {route_obj['query_type']}")

        ranked = vertical_rank_documents(query, documents, hybrid_index, query_aliases, ranking_weights, limit=5)
        top5 = ranked[:5]
        top3 = ranked[:3] if len(ranked) >= 3 else ranked
        top1 = ranked[0] if ranked else None

        top1_must_domain = set(case.get("top1_must_domain_any", []))
        top1_must_source = case.get("top1_must_source")
        top1_should_include_any_terms = case.get("top1_should_include_any_terms", [])

        top5_must_include_source = set(case.get("top5_must_include_source_any", []))
        top5_must_include_domain = set(case.get("top5_must_include_domain_any", []))
        top5_must_not_source = set(case.get("top5_must_not_source_any", []))
        top5_must_not_domain = set(case.get("top5_must_not_domain_any", []))

        top3_must_include_any_terms = case.get("top3_must_include_any_terms", [])
        top5_must_include_any_terms = case.get("top5_must_include_any_terms", [])
        top5_must_not_include_any_terms = case.get("top5_must_not_include_any_terms", [])

        allow_degraded_fallback = case.get("allow_degraded_fallback", True)

        case_failed = False

        # Empty check
        if not top5 and not allow_empty:
            empty_result_violation_count += 1
            errors.append(f"Query '{query}': top5 is empty but allow_empty=false")
            case_failed = True

        # Track exam_vertical top1 accuracy
        if expected_route == "class_exam_lookup" and top1:
            exam_vertical_top1_total += 1
            src = top1.get("source_id") or top1.get("source", "")
            if src == "exam_vertical":
                exam_vertical_top1_correct += 1
            else:
                errors.append(f"Query '{query}': top1 source '{src}' != exam_vertical")
                case_failed = True

        if top1_must_domain and top1:
            if top1.get("domain") not in top1_must_domain:
                errors.append(f"Query '{query}': top1 domain {top1.get('domain')} not in {top1_must_domain}")
                case_failed = True

        if top1_must_source and top1:
            if top1.get("source") != top1_must_source and top1.get("source_id") != top1_must_source:
                errors.append(f"Query '{query}': top1 source {top1.get('source')} != {top1_must_source}")
                case_failed = True

        if top1_should_include_any_terms and top1:
            text = (str(top1.get("title", "")) + " " + str(top1.get("content", ""))).lower()
            if not any(term.lower() in text for term in top1_should_include_any_terms):
                errors.append(f"Query '{query}': top1 text does not contain any of {top1_should_include_any_terms}")
                case_failed = True

        # top3_must_include_any_terms: AT LEAST one doc in top3 must include any term
        if top3_must_include_any_terms and top3:
            any_hit = False
            for doc in top3:
                text = (str(doc.get("title", "")) + " " + str(doc.get("content", ""))).lower()
                if any(term.lower() in text for term in top3_must_include_any_terms):
                    any_hit = True
                    break
            if not any_hit:
                errors.append(f"Query '{query}': top3 docs do not contain any of {top3_must_include_any_terms}")
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

        # top5_must_include_any_terms: AT LEAST one doc in top5 must include any term
        if top5_must_include_any_terms:
            any_hit = any(
                any(term.lower() in (str(doc.get("title", "")) + " " + str(doc.get("content", ""))).lower()
                    for term in top5_must_include_any_terms)
                for doc in top5
            )
            if not any_hit:
                errors.append(f"Query '{query}': no doc in top5 contains any of {top5_must_include_any_terms}")
                case_failed = True

        for doc in top5:
            text = (str(doc.get("title", "")) + " " + str(doc.get("content", ""))).lower()

            if top5_must_not_include_any_terms:
                for term in top5_must_not_include_any_terms:
                    if term.lower() in text:
                        errors.append(f"Query '{query}': doc '{doc.get('title')}' contains forbidden term '{term}'")
                        case_failed = True

            if top5_must_not_source and (doc.get("source") in top5_must_not_source or doc.get("source_id") in top5_must_not_source):
                blocked_source_violations += 1
                errors.append(f"Query '{query}': top5 contains blocked source '{doc.get('source')}' - {doc.get('title')}")
                case_failed = True

            if top5_must_not_domain and doc.get("domain") in top5_must_not_domain:
                blocked_domain_violations += 1
                errors.append(f"Query '{query}': top5 contains blocked domain '{doc.get('domain')}' - {doc.get('title')}")
                case_failed = True

            if doc.get("degraded_fallback"):
                degraded_fallback_count += 1
                if not allow_degraded_fallback:
                    errors.append(f"Query '{query}': degraded fallback not allowed, but doc '{doc.get('title')}' is fallback.")
                    case_failed = True

        if case_failed:
            bad_top5_count += 1

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
    report["bad_top5_rate"] = bad_top5_count / total if total else 0
    report["blocked_source_violations"] = blocked_source_violations
    report["blocked_domain_violations"] = blocked_domain_violations
    report["degraded_fallback_count"] = degraded_fallback_count
    report["empty_result_violation_count"] = empty_result_violation_count
    report["exam_vertical_top1_accuracy"] = exam_vertical_top1_correct / exam_vertical_top1_total if exam_vertical_top1_total else 1.0
    report["errors"] = errors
    
    reports_dir = os.path.join(BASE_DIR, "eval", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, "product_search_latest.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=== Product Search Gate Results ===")
    print(f"Total Cases: {total}")
    print(f"Route Accuracy: {route_correct}/{total} ({(report['route_accuracy'])*100:.1f}%)")
    print(f"Bad Top5 Count: {bad_top5_count}")
    print(f"Blocked Source Violations: {blocked_source_violations}")
    print(f"Blocked Domain Violations: {blocked_domain_violations}")
    print(f"Degraded Fallbacks: {degraded_fallback_count}")
    print(f"Empty Result Violations: {empty_result_violation_count}")
    print(f"Exam Vertical Top1 Accuracy: {report['exam_vertical_top1_accuracy']:.2f}")
    print(f"Report saved to: {report_path}")

    if errors:
        print("\nErrors Found:")
        for err in errors:
            print(f" - {err}")

    failed = (
        bad_top5_count > 0
        or blocked_source_violations > 0
        or blocked_domain_violations > 0
        or empty_result_violation_count > 0
        or route_correct < total
        or (exam_vertical_top1_total > 0 and exam_vertical_top1_correct < exam_vertical_top1_total)
    )
    if failed:
        print("\n[FAILED] Product Search Quality Gate: CI gate failed due to quality violations.")
        sys.exit(1)

    print("\n[PASS] Product Search Quality Gate passed successfully.")

if __name__ == "__main__":
    evaluate_cases()
