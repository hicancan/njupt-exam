# Ranking

Ranking is route-aware hybrid retrieval.

Shared inputs:

- `config/query_routes.json`
- `config/ranking_weights.json`
- `public/index/hybrid_index.json`
- `public/index/query_aliases.json`

Runtime implementations:

- Frontend: `src/utils/searchIndex.ts`
- Python eval: `scripts/search/vertical_ranker.py`

The parity gate is `scripts/eval/eval_search_parity.py`.

## Components

- `bm25`: BM25 score computed from hybrid-index term frequencies, document lengths, average document length, and IDF.
- `field`: weighted overlap over title, tags, TaskFrame fields, evidence, materials, source, and content.
- `tag`: query overlap with document tags.
- `task_frame`: overlap with TaskFrame action/evidence text.
- `utility`: student score, importance score, and source weight.
- `risk_penalty`: sensitive, review-required, and restricted penalties.
- `tier`: route-derived A/B/C candidate tiers.

## Route Gating

Routes can define target domains/intents, preferred sources/channels, blocked domains/sources, required top-result terms, bad-result terms, and whether blocked fallback is allowed.

Medical-insurance queries use the `service_search` query type but a stricter route id to block campus-network and GitHub fallback. Official academic notices such as transfer-major queries disable blocked fallback so unrelated innovation-project documents do not fill top results.

## Commands

```powershell
npm exec -- tsx --tsconfig tsconfig.app.json scripts/eval/eval_frontend_search.ts --out eval/reports/ts_search_results.json
uv run python scripts/eval/eval_search_parity.py --ts-results eval/reports/ts_search_results.json
```
