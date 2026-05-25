import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
routes_file = os.path.join(BASE_DIR, 'config', 'query_routes.json')

with open(routes_file, 'r', encoding='utf-8') as f:
    routes = json.load(f)

for r in routes:
    if r['id'] == 'service_search':
        r['triggers'].extend(["\u53c2\u4fdd", "\u62a5\u9500"]) # 参保, 报销
        r['must_include_terms_for_top_results'] = ["\u533b\u4fdd", "\u533b\u7597", "\u53c2\u4fdd", "\u62a5\u9500", "\u6821\u56ed\u7f51", "\u7535"]
    elif r['id'] == 'official_notice_search':
        r['must_include_terms_for_top_results'] = ["\u8f6c\u4e13\u4e1a", "\u4f11\u5b66", "\u9000\u5b66"] # 转专业, 休学, 退学

with open(routes_file, 'w', encoding='utf-8') as f:
    json.dump(routes, f, ensure_ascii=False, indent=2)
