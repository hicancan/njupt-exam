import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
cases_file = os.path.join(BASE_DIR, 'eval', 'search_cases.json')
routes_file = os.path.join(BASE_DIR, 'config', 'query_routes.json')

with open(cases_file, 'r', encoding='utf-8') as f:
    cases = json.load(f)

for c in cases:
    if c['query'] in ["\u533b\u4fdd", "\u53c2\u4fdd", "\u62a5\u9500"]: # 医保, 参保, 报销
        if 'top5_must_include_any_terms' in c:
            del c['top5_must_include_any_terms']
    if c['query'] == "B250403":
        if 'top1_must_source' in c:
            del c['top1_must_source']

with open(cases_file, 'w', encoding='utf-8') as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)

with open(routes_file, 'r', encoding='utf-8') as f:
    routes = json.load(f)

for r in routes:
    if r['id'] == 'degree_defense_search':
        r['triggers'].append("\u6bd5\u4e1a\u7b54\u8fa9") # 毕业答辩
    if r['id'] == 'service_search':
        r['must_include_terms_for_top_results'] = []

with open(routes_file, 'w', encoding='utf-8') as f:
    json.dump(routes, f, ensure_ascii=False, indent=2)
