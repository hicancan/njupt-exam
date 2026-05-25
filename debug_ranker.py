import sys, os, json
BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from search.vertical_ranker import vertical_rank_documents
from search.query_router import route_query, load_query_routes

routes = load_query_routes(os.path.join(BASE_DIR, 'config', 'query_routes.json'))
documents = json.load(open(os.path.join(BASE_DIR, 'public', 'index', 'documents.json'), 'r', encoding='utf-8'))
hybrid_index = json.load(open(os.path.join(BASE_DIR, 'public', 'index', 'hybrid_index.json'), 'r', encoding='utf-8'))
query_aliases = json.load(open(os.path.join(BASE_DIR, 'config', 'query_aliases.json'), 'r', encoding='utf-8'))
ranking_weights = json.load(open(os.path.join(BASE_DIR, 'config', 'ranking_weights.json'), 'r', encoding='utf-8'))

route = route_query('论文答辩', routes)
results = vertical_rank_documents('论文答辩', documents, route, hybrid_index, query_aliases, ranking_weights)

for r in results[:5]:
    print(r.get('title'), r.get('source_id'), r.get('is_blocked_for_top5'))
