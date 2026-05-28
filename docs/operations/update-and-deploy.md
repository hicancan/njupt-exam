# Update And Deploy

## Local Validation

```powershell
npm ci
uv run python -m njupt_search_indexer validate --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index --skip-output
uv run python -m njupt_search_indexer build --collection-id njupt-public --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index --out apps\web\public\generated\collections\njupt-public
uv run python -m njupt_search_indexer validate --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index --collection apps\web\public\generated\collections\njupt-public
uv run python tools\quality-gates\scripts\validate_search_index.py
uv run python tools\quality-gates\scripts\check_no_obsolete_fields.py
uv run python tools\quality-gates\scripts\check_public_artifact_sizes.py
uv run python -m njupt_search_eval run-smoke-queries --collection apps\web\public\generated\collections\njupt-public
uv run python -m pytest
npm test
npm run typecheck
npm run lint
npm run build
```

## Deployment Contract

- Build `apps/web/public/generated/collections/njupt-public` only from audited source packages. Current production consumes the JWC sitegraph source package.
- Commit regenerated data only after validation and representative progressive search evaluation pass.
- The deployed app must show quick results first, then continue full coverage verification in the Worker.
- A completed search must be able to report `coverage.exhaustive_complete=true` with all shards and documents searched.

## CI Governance

`update-exam-data.yml` and `update-collection-index.yml` update their generated artifact directories independently. Deployment follows only after validation workflows, representative queries, Python checks, and frontend checks pass.
