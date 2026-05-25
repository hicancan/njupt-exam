"""Validate query_routes.json against SearchDomain/SearchIntent enums.

Usage:
  python scripts/utils/validate_query_routes.py
  python scripts/utils/validate_query_routes.py --write-report
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from models.search_contract import SEARCH_DOMAINS, SEARCH_INTENTS

SEARCH_DOMAIN_SET = set(SEARCH_DOMAINS)
SEARCH_INTENT_SET = set(SEARCH_INTENTS)


def validate():
    routes_path = os.path.join(BASE_DIR, "config", "query_routes.json")
    if not os.path.exists(routes_path):
        print(f"[FAIL] query_routes.json not found at {routes_path}")
        sys.exit(1)

    with open(routes_path, encoding="utf-8") as f:
        routes = json.load(f)

    errors = []
    warnings = []

    for route in routes:
        route_id = route.get("id", "unknown")
        query_type = route.get("query_type", "unknown")

        # Check required fields
        if not route.get("explanation"):
            warnings.append(f"{route_id}: missing explanation")
        if not route.get("route_examples"):
            warnings.append(f"{route_id}: missing route_examples")

        # Validate domains
        for field in ["must_domains", "preferred_domains", "blocked_domains_for_top5"]:
            values = route.get(field, [])
            for v in values:
                if v not in SEARCH_DOMAIN_SET:
                    errors.append(f"{route_id}: invalid domain '{v}' in {field}")

        # Validate intents
        for field in ["preferred_intents"]:
            values = route.get(field, [])
            for v in values:
                if v not in SEARCH_INTENT_SET:
                    errors.append(f"{route_id}: invalid intent '{v}' in {field}")

        # Check duplicates
        for field in ["blocked_domains_for_top5", "blocked_sources_for_top5", "preferred_domains", "preferred_sources"]:
            values = route.get(field, [])
            seen = set()
            dups = set()
            for v in values:
                if v in seen:
                    dups.add(v)
                seen.add(v)
            if dups:
                errors.append(f"{route_id}: duplicate values in {field}: {dups}")

        # Check triggers/triggers dedup
        triggers = route.get("triggers", [])
        seen_t = set()
        for t in triggers:
            if t in seen_t:
                errors.append(f"{route_id}: duplicate trigger '{t}'")
            seen_t.add(t)

        # route_examples must not conflict with must_include_terms
        must_include = [t.lower() for t in route.get("must_include_terms_for_top_results", [])]
        if must_include:
            for ex in route.get("route_examples", []):
                ex_lower = ex.lower()
                has_any = any(mi in ex_lower for mi in must_include)
                if not has_any:
                    warnings.append(f"{route_id}: route_example '{ex}' does not contain any must_include term {must_include}")

    total = len(routes)
    err_count = len(errors)
    warn_count = len(warnings)

    print(f"=== Query Routes Validation ===")
    print(f"Routes: {total}")
    print(f"Errors: {err_count}")
    print(f"Warnings: {warn_count}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  [ERROR] {e}")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  [WARN] {w}")

    report = {
        "total_routes": total,
        "error_count": err_count,
        "warning_count": warn_count,
        "errors": errors,
        "warnings": warnings,
    }

    reports_dir = os.path.join(BASE_DIR, "eval", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    with open(os.path.join(reports_dir, "query_routes_validation.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if err_count > 0:
        print(f"\n[FAIL] query_routes.json validation failed with {err_count} error(s).")
        sys.exit(1)

    print(f"\n[PASS] query_routes.json validation passed.")


if __name__ == "__main__":
    validate()
