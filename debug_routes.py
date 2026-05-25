import sys, os, json
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from search.query_router import load_query_routes
routes = load_query_routes(os.path.join(BASE_DIR, 'config', 'query_routes.json'))
for r in routes:
    if r['id'] == 'degree_defense_search':
        print(json.dumps(r.get("blocked_sources_for_top5"), ensure_ascii=False))
