import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
cases_file = os.path.join(BASE_DIR, 'eval', 'search_cases.json')

with open(cases_file, 'r', encoding='utf-8') as f:
    cases = json.load(f)

for c in cases:
    if c['query'] == "\u6bd5\u4e1a\u8bbe\u8ba1": # 毕业设计
        c['route'] = "graduation_search"

with open(cases_file, 'w', encoding='utf-8') as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)

fixtures_file = os.path.join(BASE_DIR, 'tests', 'search_router_fixtures.json')
if os.path.exists(fixtures_file):
    with open(fixtures_file, 'r', encoding='utf-8') as f:
        fixtures = json.load(f)
    for c in fixtures:
        if c['query'] == "\u6bd5\u4e1a\u8bbe\u8ba1":
            c['expected_route'] = "graduation_search"
    with open(fixtures_file, 'w', encoding='utf-8') as f:
        json.dump(fixtures, f, ensure_ascii=False, indent=2)
