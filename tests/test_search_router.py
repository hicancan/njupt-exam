import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from search.query_router import route_query, load_query_routes

def test_search_router_fixtures():
    routes = load_query_routes(os.path.join(BASE_DIR, "config", "query_routes.json"))
    with open(os.path.join(BASE_DIR, "tests", "search_router_fixtures.json"), "r", encoding="utf-8") as f:
        cases = json.load(f)
        
    for case in cases:
        query = case["query"]
        expected = case["expected_query_type"]
        route = route_query(query, routes)
        assert route["query_type"] == expected, f"Query '{query}': expected {expected}, got {route['query_type']}"
