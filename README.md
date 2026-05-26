# njupt-search

<div align="center">

<img src="public/assets/logo.png" height="80" alt="njupt-search logo" />

**南邮本科生教务搜索和考试查询静态应用。**

[在线使用](https://njupt.hicancan.top) · [报告 Bug](https://github.com/hicancan/njupt-search/issues)

</div>

## 项目定位

`njupt-search` 当前只有两条生产数据路径：

1. JWC 公开搜索：只消费 `njupt-site-graph` 已审计的 JWC sitegraph 包，生成纯静态索引，用纯代码倒排召回和排序。
2. 考试垂直频道：保留 `public/data/all_exams.json` 和 `public/data/data_summary.json`，支持班级考试查询、课程选择和 `.ics` 日历导出。

非考试搜索不再运行旧校园源爬虫、学习资料源、意图路由或模型补全链路。核心搜索路径不调用模型，不保留 `llm_provider`、`semantic_mode`、`task_frames` 等旧字段。

```text
njupt-site-graph/data/sites/jwc/index
-> scripts/build_sitegraph_index.py
-> public/index/manifest.json
-> public/index/doc_meta.json + inverted_index.json
-> public/index/sitegraph/jwc/documents.*.json
-> src/utils/searchIndex.ts
-> React UI
```

## Sitegraph 契约

本地默认读取兄弟仓库：

```text
D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index
```

CI checkout `hicancan/njupt-site-graph` 后读取：

```text
_sitegraph/njupt-site-graph/data/sites/jwc/index
```

生成文件：

```text
public/index/manifest.json
public/index/doc_meta.json
public/index/inverted_index.json
public/index/section_index.json
public/index/attachment_index.json
public/index/external_index.json
public/index/query_aliases.json
public/index/sitegraph/jwc/outcomes.json
public/index/sitegraph/jwc/documents.000.json
```

首屏只加载 manifest、轻量元数据、倒排索引、附件/外链轻索引和 query aliases；全文 shards 只在搜索候选确定后按需加载。

## 本地开发

需要 Node.js >= 20，Windows 建议 PowerShell 7。

```powershell
npm ci
npm run dev
```

质量检查：

```powershell
npm test
npm run typecheck
npm run build
uv run python -m pytest
```

更新考试数据：

```powershell
uv run python scripts\auto_update_exam_data.py
uv run python scripts\analyze_and_update.py
```

更新 JWC sitegraph 搜索索引：

```powershell
uv run python scripts\validate_sitegraph_index.py --sitegraph-index D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index --skip-output
uv run python scripts\build_sitegraph_index.py --sitegraph-index D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index
uv run python scripts\validate_sitegraph_index.py --sitegraph-index D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index
uv run python scripts\utils\validate_search_index.py
uv run python scripts\eval\sitegraph_query_smoke_test.py
```

代表查询覆盖：校历、慕课考试、期末考试、转专业、规章制度、办事流程、学生相关文件及表格、教务管理系统、大创、推免、成绩、附件1、xlsx。

## 自动更新

`.github/workflows/auto-update.yml` 每 6 小时更新考试数据，然后消费 JWC sitegraph 包并生成 `public/index`。workflow 会校验：

- 上游 manifest 无错误，所有发现 URL 都有 outcome；
- 附件策略为 metadata only，外链策略为 record only；
- detail pages、attachments、external links、edges 数量上下游一致；
- 旧搜索 artifact 和旧字段不存在；
- 代表查询都有结果；
- `npm test`、`npm run typecheck`、`npm run build` 通过。

## 项目结构

```text
public/data/            # 考试垂直频道数据
public/index/           # JWC sitegraph 静态搜索索引
scripts/                # 考试更新、sitegraph build/validate/search smoke
src/                    # React/Vite/PWA 前端
tests/                  # Python sitegraph contract tests
```

## License

[AGPL-3.0](LICENSE)
