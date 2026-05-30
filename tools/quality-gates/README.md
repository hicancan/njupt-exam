# Quality Gates

This directory owns deterministic generated-artifact and contract gates.

Purpose:

- validate the generated public search contract, including obsolete-field rejection;
- enforce public artifact size budgets;
- enforce routed-search startup budgets, so first-screen readiness stays limited to `source_registry`, `global_query_directory`, and `query_aliases`;
- keep deployment blocked when generated artifacts or contracts fail validation.

Quality gates must remain deterministic and must not depend on Codex or other AI review workflows.

```powershell
uv run python tools\quality-gates\scripts\validate_search_index.py
uv run python tools\quality-gates\scripts\check_public_artifact_sizes.py
```
