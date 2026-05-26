# njupt-search

<div align="center">

<img src="public/assets/logo.png" height="80" alt="njupt-search logo" />

**南邮学生事务的源审计、任务理解、混合检索与静态信息入口。**

[在线使用](https://njupt.hicancan.top) · [报告 Bug](https://github.com/hicancan/njupt-search/issues)

</div>

## 项目定位

`njupt-search` 不是普通公告聚合站，也不是单纯考试查询工具。当前生产公开搜索主架构是 JWC sitegraph-backed index：除考试垂直频道外，公开搜索数据只消费 `njupt-site-graph` 已审计的 JWC 结构化包，不再运行旧 Source-Channel 非考试爬虫、GitHub 资料源或 LLM 补全链路。

```text
JWC Sitegraph Package
-> Sitegraph Ingest
-> SearchDocument + provenance
-> Slim default index + full JWC shards
-> Query Understanding
-> Product UI
-> Static Deploy
```

考试查询保留为 `exam_vertical` 垂直频道：输入班级号可查看期末考试安排、勾选课程并导出 `.ics` 日历。非考试公开搜索只使用 JWC 官方 sitegraph；旧就业、图书馆、后勤、保卫、档案、体育、学院通知和 GitHub 学习资料不再属于生产公开搜索索引。

## 主配置

生产公开搜索主链路只使用 JWC sitegraph 包：

```text
D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index
```

本地默认按兄弟仓库路径读取；CI 通过 checkout `hicancan/njupt-site-graph` 后读取 `_sitegraph/njupt-site-graph/data/sites/jwc/index`。如果私有仓库 checkout 权限不足，需要配置 `NJUPT_SITEGRAPH_TOKEN`。TODO：后续可改为下载 njupt-site-graph 发布的 JWC package artifact，避免 CI 直接 checkout 兄弟仓库。

辅助配置：

```text
config/query_aliases.json
config/ontology.json
config/search_contract.json
```

生成索引：

```text
public/index/documents.json
public/index/task_frames.json
public/index/query_aliases.json
public/index/ontology.json
public/index/manifest.json
public/index/sitegraph/jwc/documents.000.json
public/index/sitegraph/jwc/outcomes.json
```

考试数据：

```text
public/data/all_exams.json
public/data/data_summary.json
```

## HyTask-RAG 组件

- Sitegraph Package：由 `njupt-site-graph` 生成并审计 JWC homepage、nav tree、list/detail、附件、外链、边和 URL outcome。
- Sitegraph Ingest：读取 JWC 包，把 6884 个 detail pages 转成 SearchDocument，并为 direct attachment、外部系统和必要首页入口生成 record/search record。
- Provenance：每条记录保留 `sitegraph_provenance`，包含 section_id、nav_path、content_status、url_outcome 和 source files。
- Attachment Metadata：只保存附件元数据，不下载二进制；附件名、扩展名、父页面、栏目路径都进入可搜索字段。
- TaskFrame：仅用安全规则生成，不调用 LLM。
- Slim + Shards：`public/index/documents.json` 是轻量默认索引，`public/index/sitegraph/jwc/documents.*.json` 是后台加载的全文 shards。
- Search Contract：`config/search_contract.json` 约束 kind、category、domain、intent、source_type、lifecycle、semantic_mode 和 TaskFrame 枚举，生产验证严格失败。
- Query Aliases：把“保研/推免”“大创”“校园网”等学生自然语言映射到领域、意图和语义扩展。
- Query Intent Router: 识别查询模式并将其路由到特定垂类意图（如考试查询、资源搜索、事务通知等）。
- Recall Search：搜索阶段只用查询、同义词、路由阻断和离线结构化字段做候选召回；命中候选严格按 `published_at` 倒序展示，不做语义排序或权重重排。
- Self Evaluation：`scripts/eval/eval_frontend_search.ts` 先生成浏览器真实 TypeScript top-5，`scripts/eval/eval_product_search.py --mode both` 以 frontend 结果作为产品真相，同时报告 Python 召回结果；`scripts/eval/eval_search_parity.py --ts-results ...` 量化 Python/TS drift。

## 安全边界

- 只抓公开网页和公开接口。
- 不登录学校系统。
- 不绕过校园网或统一身份认证限制。
- restricted 页面不生成具体任务。
- sensitive 页面不向 LLM 发送敏感正文，不展示敏感正文片段。
- JWC sitegraph 是非考试公开搜索唯一事实源；ingest 不调用 LLM。
- API key 只来自环境变量或 GitHub Actions secrets，不写入仓库。
- 本项目为非官方工具，请以官网原文为准。

## 本地开发

需要 Node.js >= 20，Windows 建议 PowerShell 7。

```powershell
npm ci
npm run dev
```

质量检查：

```powershell
npm run lint
npm test
npm run typecheck
npm run build
```

Python 依赖：

```powershell
uv pip install -r requirements.txt
```

更新考试数据：

```powershell
uv run python scripts\auto_update_exam_data.py
uv run python scripts\analyze_and_update.py
```

更新 JWC sitegraph-backed 搜索索引：

```powershell
uv run python scripts\validate_sitegraph_ingest.py --sitegraph-index D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index --skip-output
uv run python scripts\ingest_sitegraph.py --sitegraph-index D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index
uv run python scripts\validate_sitegraph_ingest.py --sitegraph-index D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index
```

校验与自评：

```powershell
uv run python scripts\utils\validate_search_index.py
uv run python scripts\utils\validate_query_routes.py
uv run python scripts\eval\sitegraph_query_smoke_test.py
```

代表查询覆盖：校历、慕课考试、期末考试、转专业、规章制度、办事流程、学生相关文件及表格、教务管理系统、大创、推免、成绩、附件1、xlsx。

## 自动更新

`.github/workflows/auto-update.yml` 每 6 小时先更新考试数据，再 checkout/消费 JWC sitegraph 包并生成 `public/index`。该 workflow 不再运行 Fetch High Star GitHub Repos，也不再运行旧 `scripts/update_search_index.py` 非考试构建。`.github/workflows/deploy.yml` 负责 lint、test、build 与 GitHub Pages 部署。

## 项目结构

```text
config/                 # ontology, aliases, contract; old source-channel config is not production
docs/architecture/      # HyTask-RAG, contract, recall, eval, source adapters
docs/operations/        # update/deploy runbook
docs/source-audit/      # Chrome DevTools MCP 公开源审计
docs/product/           # 产品冻结报告
eval/                   # 自动 query 集与报告
public/data/            # 考试垂直频道数据
public/index/           # sitegraph-backed 静态搜索索引
scripts/core/           # Rule Guard, tokenizer, query expansion, task extraction
scripts/models/         # CanonicalDocument, SourceGraph, TaskFrame, search contract
scripts/eval/           # eval_search and query smoke tests
src/                    # React/Vite/PWA 前端
```

## License

[AGPL-3.0](LICENSE)
