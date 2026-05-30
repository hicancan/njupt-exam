# Collection Indexer

This tool builds and validates generated collection runtime artifacts.

Current purpose:

- consume one or more audited source package paths through CLI arguments instead of implicit sibling paths;
- produce routed static-search artifacts for `collection_id: njupt-public`;
- keep startup artifacts small by emitting `source_registry`, `global_query_directory`, and query-planned local indexes instead of global first-screen indexes;
- emit source-scoped full shards plus shard filters for proof-based exhaustive verification.

CLI:

```powershell
uv run python -m njupt_search_indexer build --collection-id njupt-public --source-kind sitegraph --source-package <jwc-index> --source-package <xsc-index> --source-package <cxcy-index> --out apps\web\public\generated\collections\njupt-public
uv run python -m njupt_search_indexer validate --source-package <jwc-index> --source-package <xsc-index> --source-package <cxcy-index> --collection apps\web\public\generated\collections\njupt-public
```
