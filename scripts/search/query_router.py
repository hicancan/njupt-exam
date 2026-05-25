import json
import re
import os
from typing import Any, Dict, List

def load_query_routes(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)

def route_query(raw_query: str, routes: List[Dict[str, Any]]) -> Dict[str, Any]:
    normalized_query = re.sub(r"\s+", " ", str(raw_query or "")).strip()
    
    # Default fallback route
    best_route = {
        "id": "general_search",
        "query_type": "general_search",
        "must_domains": [],
        "preferred_domains": [],
        "preferred_sources": [],
        "preferred_channels": [],
        "preferred_intents": [],
        "blocked_domains_for_top5": [],
        "blocked_sources_for_top5": [],
        "allow_resource_top5": True,
        "freshness_preference": "none"
    }
    
    confidence = 0.0
    
    # Find matching route
    for route in routes:
        triggers = route.get("triggers", [])
        if any(trigger.lower() in normalized_query.lower() for trigger in triggers):
            best_route = route
            confidence = 0.95
            break
            
    # Also check if class ID pattern (e.g. B250403)
    if re.search(r"^[A-Za-z]\d{6,8}$", normalized_query):
        class_route = next((r for r in routes if r.get("id") == "class_exam_lookup"), None)
        if class_route:
            best_route = class_route
            confidence = 0.99
            
    return {
        "raw_query": raw_query,
        "normalized_query": normalized_query,
        "query_type": best_route.get("query_type", "general_search"),
        "route_confidence": confidence,
        "route_source": "query_routes",
        "target_domains": best_route.get("must_domains", []) + best_route.get("preferred_domains", []),
        "target_intents": best_route.get("preferred_intents", []),
        "preferred_sources": best_route.get("preferred_sources", []),
        "preferred_channels": best_route.get("preferred_channels", []),
        "blocked_domains_for_top5": best_route.get("blocked_domains_for_top5", []),
        "blocked_sources_for_top5": best_route.get("blocked_sources_for_top5", []),
        "allow_resource_top5": best_route.get("allow_resource_top5", True),
        "freshness_preference": best_route.get("freshness_preference", "none")
    }
