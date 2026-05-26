# Product Search Quality Gate

The product gate protects the static JWC sitegraph search path that users see in the browser.

## Required Commands

```powershell
uv run python scripts\validate_sitegraph_index.py --sitegraph-index D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index --skip-output
uv run python scripts\build_sitegraph_index.py --sitegraph-index D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index
uv run python scripts\validate_sitegraph_index.py --sitegraph-index D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index
uv run python scripts\utils\validate_search_index.py
uv run python scripts\eval\sitegraph_query_smoke_test.py
npm test
npm run typecheck
npm run build
```

## Blocking Invariants

- upstream package has `errors=0`;
- every discovered URL has an outcome;
- attachments are `metadata_only`;
- external links are `record_only`;
- generated detail page, attachment, external link, and edge counts match upstream truth counts;
- `public/index/documents.json`, `public/index/task_frames.json`, and `public/index/ontology.json` are absent;
- core index files contain no old model/semantic/task-frame fields;
- representative queries return results.
