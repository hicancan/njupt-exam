# Search Contract

`config/search_contract.json` is the canonical contract for production search data.

It defines allowed values for:

- `document_kinds`
- `categories`
- `domains`
- `intents`
- `source_types`
- `lifecycles`
- `semantic_modes`
- `task_frame_source_modes`
- `task_types`

Python reads it through `scripts/models/search_contract.py`. TypeScript mirrors the same values in strict Zod schemas in `src/types/index.ts`; tests and index validation catch drift.

## Strict Fields

Production validation fails on invalid:

- `kind`
- `category`
- `domain`
- `intent`
- `source_type`
- `lifecycle`
- `semantic_mode`
- TaskFrame `source_mode`
- TaskFrame `task_type`
- TaskFrame `time.lifecycle`

Validation errors include the file path, document or task id, field, invalid value, and allowed values.

## Fallback Rules

Fallback is only allowed before production output:

- Missing domain -> `news`
- Missing intent -> `read`
- Unknown source type -> `central_admin`
- Unknown lifecycle -> `unknown`

Guarded/restricted/sensitive/low-evidence content must not emit concrete TaskFrames.

## Commands

```powershell
uv run python scripts/utils/validate_search_index.py
uv run python scripts/utils/validate_query_routes.py
uv run python -m pytest tests/test_search_contract.py -q
```
