# Sitegraph Search Architecture

`njupt-search` no longer uses the old multi-source recall architecture for non-exam search. The current product path is:

```text
JWC sitegraph package
-> scripts/build_sitegraph_index.py
-> manifest/doc_meta/inverted_index/section_index/attachment_index/external_index
-> full shards loaded on demand
-> src/utils/searchIndex.ts deterministic ranking
```

## Claim Boundary

- Only the JWC sitegraph package is the non-exam public search source.
- Attachments are metadata-only records; binaries are not downloaded.
- External links are record-only entries; they are not recursively crawled.
- Core ranking is deterministic code and does not call model APIs.
- Exam search remains a separate vertical backed by `public/data/all_exams.json`.

## Frontend Experience

The frontend exposes sitegraph facets instead of old domain/intent tabs:

- 全部
- 通知文章
- 政策制度
- 办事流程
- 下载资源
- 系统入口
- 考试相关
- 教务快讯
- 外部链接

Cards show title, URL, source, section/nav path, date, attachment count, provenance, and score reason.
