# Source Adapters

Campus crawling is static-first and source-channel-aware.

## Config

Use `config/source_channels.json` for each source and channel.

Important source fields:

- `id`
- `base_url`
- `source_type`
- `authority`
- `adapter_kind`
- `include_patterns`
- `exclude_patterns`
- `allow_insecure_tls`
- `channels`

Important channel fields:

- `list_urls`
- `expected_domains`
- `expected_intents`
- `priority`
- `crawl_depth`
- `pagination`
- `selectors`
- `positive_keywords`
- `negative_keywords`

## Selectors

Supported selectors:

- `list_item`
- `title`
- `date`
- `link`
- `content`
- `attachments`

The crawler tries channel selectors first. If list selectors fail, the manifest records a warning and the crawler falls back to global anchor extraction. Detail content and attachment selector failures are recorded on the document crawler metadata.

## TLS

Requests verify TLS by default. A source must explicitly set `allow_insecure_tls: true` to relax TLS verification, and the manifest records that state. The exam crawler uses `NJUPT_JWC_VERIFY_TLS=false` only when a deployment explicitly opts into relaxed JWC TLS.

## Tests

```powershell
uv run python -m pytest tests/test_crawler_selectors.py -q
```
