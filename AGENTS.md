# AGENTS.md

## Repository Role

`njupt-search` is the downstream public search product for NJUPT student-facing information lookup. It consumes audited source packages and generated exam data, compiles browser runtime artifacts, and owns the React/PWA user experience.

Do not move upstream crawling, source discovery, or source-truth audit ownership into this repository. Do not reintroduce LLM search, task-frame search, provider fields, server-side runtime search, or obsolete semantic production fields.

## Product Boundaries

- Use `collection` as the product abstraction. The current generated public collection is `njupt-public`.
- `jwc` is a source package id, not the product boundary.
- `exam` is a product vertical with generated data under `apps/web/public/generated/exam/`.
- Generated JSON artifacts are compiled runtime data. Update generators or source inputs; do not manually edit generated artifacts.
- The old `docs/` tree is ignored and must not drive implementation decisions. Use current code, tests, generated manifests, workflows, and `tools/search-eval/queries/representative_queries.json` as the authoritative project state.

## Local Commands

Run from the repository root in PowerShell:

```powershell
npm test
npm run typecheck
npm run lint
npm run build
uv run python -m pytest
uv run python tools\quality-gates\scripts\validate_search_index.py
uv run python tools\quality-gates\scripts\check_public_artifact_sizes.py
uv run python -m njupt_search_eval run-smoke-queries --collection apps\web\public\generated\collections\njupt-public
```

Current generated-artifact rebuild path:

```powershell
uv run python -m njupt_search_indexer validate --source-package <path-to-njupt-site-graph-jwc-index> --skip-output
uv run python -m njupt_search_indexer build --collection-id njupt-public --source-package <path-to-njupt-site-graph-jwc-index> --out apps\web\public\generated\collections\njupt-public
uv run python -m njupt_search_indexer validate --source-package <path-to-njupt-site-graph-jwc-index> --collection apps\web\public\generated\collections\njupt-public
```

## Browser Acceptance

Run browser acceptance for changes touching routing, React pages, search UI, exam UI/data, Worker behavior, public paths, PWA caching, generated artifact layout, deployment output, or final release acceptance.

Minimum manual queries:

```text
校历
期末考试
教务管理系统
学生相关文件及表格
xlsx
B250403
```
