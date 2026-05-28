# NJUPT Search 数据驱动排序深度调研

调研日期：2026-05-28

调研对象：

- 权威源包：`D:/code/github/hicancan/njupt-site-graph/data/sites/{jwc,xsc,cxcy}/index`
- 运行时集合：`apps/web/public/generated/collections/njupt-public`

核心结论：校园搜索的终局方案应该是数据驱动的“意图分层排序”，不是单一全局权重。当前数据强烈支持“标题 + 时间”作为通知类、考试类、竞赛报名类查询的最高权重组合；但系统入口、规章制度、表格下载、班级考试等场景必须使用不同的排序 profile。当前项目总体架构适合作为终局底座，但搜索质量文件架构还不是终局，需要把硬编码排序函数升级为可评测、可配置、可解释的意图驱动排序系统。

## 1. 调研方法

本次调研读取本地完整运行时数据，而不是只看 manifest：

- 集合 manifest：`apps/web/public/generated/collections/njupt-public/manifest.json`
- 全量 full shards：501 个 shard
- 全量运行时文档：9888 条
- 兄弟仓库审计源包：`njupt-site-graph/data/sites/{jwc,xsc,cxcy}/index`
- 查询审计：55 个学生高频任务查询
- 搜索实现审计：
  - `packages/search-core/src/sitegraphSearch.ts`
  - `tools/collection-indexer/src/njupt_search_indexer/build_sitegraph_index.py`
  - `tools/search-eval/src/njupt_search_eval/sitegraph_search.py`

辅助统计文件保存在本地 `cache/` 下：

- `cache/search-ranking-data-research-summary.json`
- `cache/search-ranking-query-audit.json`
- `cache/search-source-package-research-summary.json`

`cache/` 是本地临时分析目录，不作为产品运行时数据来源。

### 1.1 源包和运行时集合的权威边界

上一版报告主要基于本仓库编译后的运行时集合统计。这个口径适合回答“用户在浏览器里实际会搜到什么”，但不是最高权威的数据口径。

更权威的统计基准应该是兄弟仓库 `njupt-site-graph` 的审计源包，原因是：

- 源包保留站点级 source truth，包括 `detail_pages.jsonl`、`attachments.jsonl`、`external_links.jsonl`、`edges.jsonl`、`sections.json`、`manifest.json`。
- 源包是“发现了什么、抽取了什么、每个 URL 的 outcome 是什么”的事实来源。
- 运行时集合是产品编译结果，会把 detail、attachment、external、utility 重新组织成浏览器搜索文档。
- 运行时集合可能丢失或弱化部分源信息，例如当前 full document 没有结构化 `source_id` 字段，只能从 `id` 前缀推断。
- 运行时集合会引入产品策略，例如 attachment metadata only、external record only、shard strategy、field code、query aliases。

所以终局调研应该采用双口径：

```text
源包统计：判断数据真实分布、字段质量、来源权威、爬取/抽取完整性。
运行时统计：判断用户实际搜索体验、排序失败模式、索引结构是否支持目标排序。
```

本次补充源包统计后，结论没有被推翻，反而更强：`jwc` 源包历史数据体量极大，`xsc/cxcy` 体量较小但在学生事务和创新创业上更权威，因此搜索必须有 query intent 和 source authority。

### 1.2 源包统计摘要

| 来源 | detail_pages | attachments | external_links | list_pages | edges | url_outcomes |
|---|---:|---:|---:|---:|---:|---:|
| `jwc` | 6884 | 7905 | 426 | 661 | 16311 | 19089 |
| `xsc` | 1589 | 17 | 75 | 233 | 1878 | 6414 |
| `cxcy` | 612 | 205 | 60 | 83 | 1101 | 1311 |

源包 detail page 时间分布：

| 来源 | 0-30 天 | 31-180 天 | 181-365 天 | 1-2 年 | 2-5 年 | 5 年以上 | 缺失 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `jwc` | 14 | 104 | 123 | 311 | 748 | 5581 | 3 |
| `xsc` | 16 | 33 | 145 | 329 | 791 | 272 | 3 |
| `cxcy` | 6 | 52 | 31 | 118 | 143 | 240 | 22 |

这和运行时统计的差异也很重要：运行时里 `external/system` 记录的 `published_at` 很多来自 `recorded_at`，因此会显得“很新”。如果排序把这种时间当作真实发布时间，系统/外链会被错误抬高。终局必须显式区分：

```text
published_at: 页面/文章发布时间
updated_at: 页面更新时间
recorded_at: 源包记录/爬取时间
version_date: 表格、附件、制度标题里的版本日期
deadline: 报名/申请截止日期
valid_until: 结果仍然有效到什么时候
```

### 1.3 查询集合文件

本次新增可持续维护的学生任务查询集合：

```text
tools/search-eval/queries/student_task_queries.json
```

当前包含 10 个任务类、153 条查询：

| 类别 | 查询数 |
|---|---:|
| `exam_schedule` | 16 |
| `academic_calendar` | 11 |
| `system_entry` | 13 |
| `form_download` | 21 |
| `academic_policy` | 17 |
| `course_grade_credit` | 13 |
| `scholarship_aid` | 13 |
| `student_affairs` | 18 |
| `innovation_entrepreneurship` | 20 |
| `broad_exploratory` | 11 |

这个文件不是“所有可能词汇”的死列表，而是一个活的任务语料库。它应该被源包数据、搜索失败样例、用户反馈和校园时间节点持续反哺。

## 2. 数据分布

### 2.1 来源分布

当前集合已经合并 3 个站点：

| 来源 | 文档数 | 占比 | 数据性质 |
|---|---:|---:|---|
| `jwc` 本科生院 / 教务处 | 7534 | 76.2% | 教务、考试、表格、规章、历史通知主体 |
| `xsc` 学生工作部（处） | 1669 | 16.9% | 奖助、辅导员、心理、就业、宿舍、征兵 |
| `cxcy` 创新创业教育学院 | 685 | 6.9% | 创新创业、竞赛、双创系统、项目通知 |

这个分布有一个直接后果：如果排序只按词频、字段命中、全文命中做全局打分，`jwc` 会天然压制 `xsc` 和 `cxcy`。所以三站点接入之后，搜索不能只靠统一倒排分数，必须加入“查询意图 -> 权威来源”的 source prior。

### 2.2 Facet 分布

| Facet | 文档数 | 占比 | 搜索含义 |
|---|---:|---:|---|
| `exam` | 2848 | 28.8% | 考试、教学运行、部分被误分的教务通知 |
| `notice_article` | 2240 | 22.7% | 通知、公示、报名、工作安排 |
| `news` | 1536 | 15.5% | 新闻动态、学院风采 |
| `workflow` | 998 | 10.1% | 流程、指南、部分表格类内容 |
| `download` | 924 | 9.3% | 表格、附件、下载资源 |
| `policy` | 781 | 7.9% | 规章制度、管理办法 |
| `external` | 546 | 5.5% | 外链、系统链接、附件外链 |
| `system` | 15 | 0.2% | 官方系统入口 |

这说明校园搜索不是普通网页搜索。它的主要任务是：

1. 找最新通知或公示。
2. 找官方入口。
3. 找可下载表格。
4. 找规章制度的现行版本。
5. 找考试、选课、学籍等强时效教务事项。

因此，最终排序不应该只优化“全文相关”，而应该优化“学生下一步能不能点对”。

### 2.3 时间分布

整体时间分布：

| 时间桶 | 文档数 | 占比 |
|---|---:|---:|
| 0-30 天 | 597 | 6.0% |
| 31-90 天 | 107 | 1.1% |
| 91-180 天 | 82 | 0.8% |
| 181-365 天 | 299 | 3.0% |
| 1-2 年 | 758 | 7.7% |
| 2-5 年 | 1682 | 17.0% |
| 5 年以上 | 6093 | 61.6% |
| 日期缺失 | 270 | 2.7% |

按来源：

| 来源 | 0-30 天 | 31-180 天 | 181-365 天 | 1-2 年 | 2-5 年 | 5 年以上 | 缺失 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `jwc` | 440 | 104 | 123 | 311 | 748 | 5581 | 227 |
| `xsc` | 91 | 33 | 145 | 329 | 791 | 272 | 8 |
| `cxcy` | 66 | 52 | 31 | 118 | 143 | 240 | 35 |

关键判断：

- `jwc` 体量最大，同时历史数据极多，5 年以上文档占 `jwc` 的约 74%。
- `xsc`、`cxcy` 体量小，但很多学生事务和创新创业查询必须优先相信它们。
- 如果通知类查询不强加时间权重，历史教务标题会非常容易压住最近通知。
- 如果系统入口类查询强加时间权重，爬取时间新的外链会压住真正入口，因此必须区分 `published_at`、`crawled_at`、`updated_at` 和 `valid_until`。

### 2.4 字段覆盖

| 字段 | 非空覆盖 | 中位长度 | 备注 |
|---|---:|---:|---|
| `title` | 100.0% | 30 | 标题质量高，必须是最高权重字段 |
| `url` | 100.0% | 56 | 对系统入口、附件有价值 |
| `section` | 100.0% | 8 | 可做来源语义和栏目权威判断 |
| `nav_path_text` | 100.0% | 9 | 可做栏目路径权重 |
| `summary` | 100.0% | 180 | 适合召回，不适合高权重排序 |
| `content` | 100.0% | 573 | 适合深度召回，排序权重应低 |
| `published_at` | 97.27% | 10 | 可用，但需要日期类型和置信度 |
| `attachments` | 31.46% | 2 | 表格/下载类查询关键 |
| `tags` | 100.0% | 4 | 可作为辅助 facet |
| `source_id` | 0.0% | 0 | 运行时 full docs 缺源 id，只能从 `id` 前缀推断 |

`source_id` 缺失是一个架构缺口。manifest 里有 sources，doc id 也带 `jwc-`、`xsc-`、`cxcy-` 前缀，但排序器不能直接读取结构化 `source_id`。终局结构应该把 `source_id` 写入 `doc_meta_light` 和 full document，避免排序逻辑依赖字符串前缀。

### 2.5 附件分布

当前集合中嵌入附件引用 8127 个，3111 条文档带附件。

| 扩展名 | 数量 |
|---|---:|
| `doc` | 3657 |
| `xls` | 2513 |
| `docx` | 813 |
| `pdf` | 711 |
| `xlsx` | 527 |
| `rar` | 75 |
| `ppt` | 36 |
| `zip` | 21 |
| `pptx` | 15 |

这说明“表格/申请表/xlsx/doc/pdf”不是边缘需求，而是校园搜索的核心任务之一。表格类排序应有独立 profile：附件名精确命中、表格版本日期、所属栏目、官方来源应该强于正文命中。

## 3. 学生关心的关键词族

基于标题、栏目、路径、摘要中的校园语义词，本地数据可分成以下高频任务族：

| 关键词族 | `jwc` | `xsc` | `cxcy` | 排序含义 |
|---|---:|---:|---:|---|
| 考试 | 1993 | 103 | 5 | 强时效，JWC 权威，标题 + 学期/年份最重要 |
| 校历/学期 | 2190 | 142 | 27 | JWC 权威，最新学年强优先 |
| 选课/课程 | 1928 | 40 | 36 | JWC 权威，系统/通知/表格需要分开 |
| 系统/入口 | 1145 | 157 | 122 | 系统入口优先，时间不应压过入口 |
| 表格/下载 | 1330 | 33 | 37 | 附件名和版本日期优先 |
| 成绩/学分 | 762 | 54 | 94 | JWC 权威，可能是通知、表格或系统 |
| 学籍/证明 | 513 | 35 | 8 | JWC 权威，表格和流程优先 |
| 毕业/培养 | 1078 | 162 | 13 | JWC 权威，政策/培养方案需版本判断 |
| 转专业/推免 | 148 | 14 | 0 | JWC 权威，政策和年度通知并列重要 |
| 奖助/资助 | 90 | 132 | 5 | XSC 权威，最新公示/通知优先 |
| 辅导员/思政 | 122 | 924 | 0 | XSC 权威，栏目强相关 |
| 心理/安全 | 303 | 312 | 49 | XSC 权威，系统入口和通知分开 |
| 就业/征兵 | 140 | 125 | 5 | XSC 权威，系统入口强优先 |
| 创新创业 | 1034 | 41 | 567 | CXCY 权威，但 JWC 有大量历史竞赛/大创遗留 |
| 党建/团学 | 78 | 219 | 9 | XSC 权威 |

这张表直接证明：搜索排序不能用一个全局公式。学生输入“奖学金”时，`xsc` 应该有来源先验；输入“大创 / 互联网+ / 双创”时，`cxcy` 应该有来源先验；输入“期末考试 / 校历 / 转专业 / 申请表”时，`jwc` 应该有来源先验。

## 4. 当前搜索逻辑

当前前端 Worker 的检索链路是：

1. 初始加载 `doc_meta_light`、`light_inverted_index`、`query_aliases`。
2. query aliases 扩展查询词。
3. light inverted index 召回标题、栏目、路径、标签、附件、系统、外链字段。
4. hydrate 少量候选 shard，产生 quick results。
5. 加载 `body_inverted_index`，补充 summary/content 召回。
6. hydrate 更多候选 shard。
7. 加载 `shard_filter`。
8. 用 Bloom filter 跳过可证明不命中的 shard。
9. 对剩余 shard 做完整扫描，保证覆盖。
10. `rankDocument` 统一打分并排序。

当前字段权重位于 `packages/search-core/src/sitegraphSearch.ts`：

| 字段代码 | 字段 | 当前权重 |
|---|---|---:|
| `t` | title | 120 |
| `a` | attachment | 95 |
| `e` | external | 95 |
| `y` | system | 95 |
| `s` | section | 60 |
| `n` | nav_path | 55 |
| `g` | tags | 45 |
| `m` | summary | 16 |
| `c` | content | 10 |

排序函数还会给以下条件加分：

- 标题精确：+5000
- 标题包含：+520
- 附件名命中：+360
- 外部入口命中：+360
- URL 命中：+220
- 栏目路径命中：+180
- 正文命中：+120
- 系统入口：+1500
- 政策制度：+900
- 办事流程：+900
- 考试相关：+650
- 新鲜度：notice/exam/news 最多 +600，10 年线性衰减

这个设计方向是对的：它是纯前端、可验证、可覆盖、可解释的静态搜索。但它目前仍然是一个“全局排序函数”，没有根据学生任务切换排序 profile。

## 5. 查询审计结论

本次跑了 55 个学生任务查询。结果显示，当前搜索已经能处理一批强命名查询，但在时间、来源、宽泛词、去重、表格版本上有明显问题。

### 5.1 表现较好的查询

| 查询 | Top1 | 判断 |
|---|---|---|
| `校历` | `2025-2026学年校历` | 正确，标题和最新学年都命中 |
| `教务管理系统` | `教务管理系统` | 正确，系统入口 profile 生效 |
| `双创信息管理系统` | `双创信息管理系统` | 正确，CXCY 系统入口命中 |
| `奖学金` | XSC 奖学金公示 | 正确，来源和标题都合理 |
| `心理健康` | XSC 心理健康系统入口 | 正确 |
| `补考` | 2026 补考、缓考通知 | 正确 |
| `成绩复核申请表` | 学生成绩复核申请表 | 正确 |
| `退选课程申请表` | 学生退选课程申请表 | 正确 |
| `复学申请表` | 复学申请表 | 正确 |

### 5.2 典型失败或风险查询

| 查询 | 当前 Top1 | 问题 | 应有策略 |
|---|---|---|---|
| `期末考试` | 2013-2014 学年期末考试安排 | 老结果压住新结果 | 考试类必须按学年/发布时间强排序，旧学期降权 |
| `考试安排` | 2013-2014 学年期末考试安排 | 同上 | 同上 |
| `重修考试` | 2019 重修考试安排 | 旧考试安排靠前 | 年份/学期强约束 |
| `大创` | 2013 JWC 大学生创新训练计划表 | CXCY 当前权威被 JWC 历史表格压制 | `cxcy` 来源先验 + 年份 + 去重 |
| `创新创业` | 2013 JWC 大创表格 | 同上 | `cxcy` profile，JWC 历史表格降权 |
| `竞赛报名` | 2010 飞思卡尔竞赛报名 | 极旧报名通知排前 | 报名/竞赛类时间权重必须非常强 |
| `互联网+` | 2023 CXCY 校赛成绩公示 | 可接受但偏旧 | 如果有当前报名/通知，应优先当前 |
| `信息门户` | CXCY 党政联席会议信息 | “信息”被单字/泛词误召回 | 需要短语/入口 intent；泛词不能单独强召回 |
| `申请表` | CXCY/JWC 外部附件链接 | 过宽，且外链被爬取时间抬高 | 表格类应按附件标题、栏目、版本日期排序 |
| `学生相关文件及表格` | 多个 JWC 表格同分，2015 表格可排第一 | 表格缺 `published_at`，标题内日期未结构化 | 提取 `version_date`，同分按版本日期排 |
| `转专业` | 2013 “转专业”栏目页 | 标题精确过强，盖过 2025 管理办法和 2026 通知 | “短标题栏目页”需要降权或作为聚合入口 |
| `推免` | 2021 推免通知 | 2025/2026 工作方案排后 | 别名召回后要保留 query intent，最新年度强优先 |
| `困难认定` | 学业困难帮扶新闻 | 与“家庭经济困难认定”意图不匹配 | 需要 phrase intent 和 XSC 资助来源先验 |
| `B250403` | sitegraph 无结果 | 该查询属于 exam vertical，不属于 sitegraph | query-router 必须优先路由 exam vertical |

这个审计结果支持一个判断：当前“标题 + 时间”不只是主观感觉，而是被数据验证的需求。尤其在通知、报名、考试、公示类查询中，旧文档数量太大，当前 +600 的线性新鲜度不够。

## 6. 第一性原理判断

学生使用校园搜索时不是在做百科检索，而是在完成任务：

```text
我要现在去哪里、点哪个、交什么、看哪份最新通知。
```

所以排序目标应该是：

```text
好结果 = 对题 + 当前有效 + 官方权威 + 可行动 + 少误点
```

对应到数据字段：

| 原则 | 字段/特征 |
|---|---|
| 对题 | title phrase、exact title、attachment title、system title |
| 当前有效 | published_at、version_date、academic_year、term、deadline、valid_until |
| 官方权威 | source_id、section、nav_path、facet |
| 可行动 | system entry、attachment download、workflow、notice |
| 少误点 | dedupe、过期降权、泛词降权、外链类型控制 |

因此，数据分布决定搜索设计：

- 标题 100% 覆盖且语义强，必须最高权重。
- 61.6% 文档超过 5 年，通知/考试/竞赛报名必须强时间排序。
- `jwc` 占 76.2%，`xsc/cxcy` 需要来源先验，否则小站点会被淹没。
- 附件引用 8127 个，表格/下载必须独立建模。
- 系统入口只有 15 条，应该走强 exact/system profile，不应被新闻或正文结果挤掉。
- 正文覆盖完整但噪声大，应该用于召回和兜底，不应该在多数任务里压过标题/时间/来源。

所以，“数据是什么分布，索引和搜索就应该长成什么样”这个思想是正确的，也是顶级搜索系统的基本原则。但落地时不能简化成“时间最大”。正确表达应该是：

```text
数据分布 -> 查询意图 -> 排序 profile -> 字段权重/时间权重/来源权重
```

## 7. 终局排序方案

### 7.1 查询意图

终局必须先识别 query intent：

| Intent | 典型查询 | 权威来源 | 最高排序特征 |
|---|---|---|---|
| `exam_schedule` | 期末考试、补考、重修考试、B250403 | JWC + exam vertical | 班级/课程精确、学年学期、标题、时间 |
| `academic_calendar` | 校历、教学周历、放假安排 | JWC | 最新学年、标题精确、发布时间 |
| `system_entry` | 教务系统、双创系统、心理健康、征兵 | 对应站点 | system facet、标题精确、官方 URL |
| `form_download` | 缓考申请表、成绩复核申请表、xlsx | JWC/XSC/CXCY | 附件标题、版本日期、栏目、扩展名 |
| `policy_current` | 转专业管理办法、推免办法、规章制度 | JWC | 标题、修订日期、policy facet |
| `notice_current` | 奖学金、公示、报名、竞赛 | 对应站点 | 标题 + 最新时间 + 来源 |
| `student_affairs` | 辅导员、心理、宿舍、就业、征兵 | XSC | XSC 来源、系统/通知区分 |
| `innovation` | 大创、互联网+、挑战杯、双创 | CXCY | CXCY 来源、报名/通知时间、系统入口 |
| `broad_explore` | 申请表、规章制度、竞赛 | 多源 | 聚合、分组、引导细化 |

### 7.2 排序 profiles

不要一个公式排所有查询。建议使用 profile：

#### 通知/公示/报名 profile

适用：`奖学金`、`互联网+`、`竞赛报名`、`期末考试`、`补考`、`推免`。

排序：

```text
title_phrase
+ title_exact_or_contains
+ source_authority_for_intent
+ recency_strong
+ academic_year_or_deadline
+ section_match
+ attachment_match
+ body_match_low
```

时间权重应该强到可以让 2025/2026 的同题通知压过 2010/2013 的历史通知。

#### 系统入口 profile

适用：`教务管理系统`、`双创信息管理系统`、`自主学分系统`、`心理健康`、`征兵`、`就业`。

排序：

```text
system_facet
+ exact_title
+ official_domain_or_known_url
+ source_authority
+ section_match
+ recency_tiny_or_disabled
```

系统入口是长期有效资源，不能让最新新闻因为时间新而排到前面。

#### 表格下载 profile

适用：`缓考申请表`、`成绩复核申请表`、`退选课程申请表`、`xlsx`。

排序：

```text
attachment_title_exact
+ document_title_exact
+ extension_match
+ form_version_date
+ source_authority
+ section/forms_path
+ published_at
```

当前很多 download 文档 `published_at = null`，但标题里有 `2026-04-16`。终局必须把这种日期提取为结构化 `version_date`。

#### 政策/制度 profile

适用：`转专业`、`推免`、`培养方案`、`规章制度`、`学分认定`。

排序：

```text
title_policy_phrase
+ policy_facet
+ revision_date/version_date
+ source_authority
+ latest_notice_if_query_implies_current_process
+ body_match_low
```

`转专业` 这种查询不能只把 2013 的短标题栏目页放第一。更合理的第一屏应该同时出现：

1. 当前管理办法。
2. 当前学期转专业通知。
3. 当前学期学院细则。
4. 表格/课程替代申请。

#### 创新创业 profile

适用：`大创`、`创新创业`、`互联网+`、`挑战杯`、`双创`。

排序：

```text
cxcy_source_boost
+ title_phrase
+ current_notice_or_registration
+ system_entry_if_system_query
+ competition_name
+ recency_strong
+ jwc_legacy_downrank
```

本地数据里 `jwc` 有 1034 条创新创业相关历史内容，`cxcy` 有 567 条更权威内容。没有来源 profile 时，`jwc` 历史表格会压制 `cxcy` 当前事项。

## 8. 终局索引设计

当前索引已有 light index、body index、shard、Bloom filter，这是好底座。终局需要增加“排序特征索引”，而不是引入后端或 LLM。

建议离线生成以下结构化字段：

| 字段 | 作用 |
|---|---|
| `source_id` | 源站点权威判断 |
| `canonical_title` | 去重、聚合、标题精确 |
| `title_terms` | 标题 BM25F / phrase matching |
| `academic_year` | 校历、考试、推免、转专业年度排序 |
| `term` | 学期排序 |
| `published_at` | 原始发布时间 |
| `updated_at` | 页面更新时间 |
| `crawled_at` | 爬取时间，不能替代发布时间 |
| `version_date` | 表格、制度、附件版本日期 |
| `deadline` | 报名、申请、提交截止时间 |
| `valid_until` | 过期判断 |
| `date_confidence` | 日期置信度 |
| `task_kind` | notice、form、system、policy、exam、news |
| `authority_profile` | jwc/xsc/cxcy 对不同 intent 的权威关系 |
| `dedupe_key` | 同标题/同附件/同通知聚合 |

建议新增索引/运行时 artifacts：

| Artifact | 用途 |
|---|---|
| `ranking_features` | 每篇文档的排序特征，初屏可加载精简版 |
| `source_bitsets` | 按来源快速过滤或加权 |
| `facet_bitsets` | 按 facet 快速过滤 |
| `recency_buckets` | 时间桶快速排序 |
| `phrase_index` | 标题短语和关键词精确召回 |
| `system_entry_index` | 15 个系统入口强保护 |
| `form_index` | 申请表、附件、扩展名、版本日期 |
| `dedupe_clusters` | 同题结果聚合 |
| `query_intents` | 查询模式、别名、来源先验、profile 配置 |

## 9. 当前架构是否合适

### 9.1 合适的部分

当前项目边界是正确的：

```text
upstream audited sitegraph packages
-> collection-indexer
-> hash-addressed static artifacts
-> browser Worker progressive search
-> React/PWA UI
```

这对 NJUPT Search 很合适：

- 不需要服务端。
- 可以静态部署。
- 可以缓存。
- 可以离线验证。
- 可以保护隐私。
- 可以把 source truth 和 product runtime 分开。
- 可以用浏览器 Worker 避免 UI 卡顿。
- 可以保留 full scan verification，证明覆盖完整。

### 9.2 不是终局的部分

当前搜索质量架构还不是终局：

1. `rankDocument` 是单一硬编码函数，缺少意图 profile。
2. query aliases 写在 Python 生成器中，搜索语义和索引生成耦合过紧。
3. 运行时 full docs 缺 `source_id`。
4. `published_at` 没有区分发布时间、版本日期、爬取时间。
5. 表格标题里的日期没有结构化。
6. 没有 dedupe clusters，重复标题和重复附件会挤占第一屏。
7. 没有 MRR/NDCG/Top1 评测集，只有 smoke query。
8. 宽泛词没有 clarification 或聚合视图，如 `申请表`、`规章制度`、`竞赛`。

### 9.3 建议文件架构

建议在现有架构内演进，不推倒重来。

搜索核心：

```text
packages/search-core/src/
  intent/
    queryIntent.ts
    intentRules.ts
  ranking/
    rankDocument.ts
    rankProfiles.ts
    freshness.ts
    sourceAuthority.ts
    dedupe.ts
    explanations.ts
  retrieval/
    postings.ts
    phraseMatch.ts
    candidateSelection.ts
```

索引生成：

```text
tools/collection-indexer/src/njupt_search_indexer/
  enrich_dates.py
  enrich_intents.py
  build_ranking_features.py
  build_dedupe_clusters.py
```

配置与评测：

```text
config/search/
  query_intents.json
  source_authority.json
  ranking_profiles.json

tools/search-eval/queries/
  student_task_queries.json
  expected_results.json
```

生成 artifacts：

```text
apps/web/public/generated/collections/njupt-public/sitegraph/artifacts/
  ranking_features.<hash>.json
  recency_buckets.<hash>.json
  source_bitsets.<hash>.json
  facet_bitsets.<hash>.json
  dedupe_clusters.<hash>.json
```

这仍然是当前项目的自然延伸，不改变“下游 public search product”的边界。

## 10. 结论

“数据分布决定索引和搜索形态”这个思想是正确的，也是终局级搜索系统的核心原则。

对 NJUPT Search 来说，当前数据给出的结论非常明确：

1. 标题是最高质量字段，应作为主排序信号。
2. 时间在通知、考试、竞赛、奖助、公示、报名中必须是最高权重之一。
3. 时间不能无条件最大；系统入口、规章制度、表格下载、班级精确查询需要不同 profile。
4. 三站点数据不平衡，必须加 source authority，否则 `jwc` 历史数据会压制 `xsc/cxcy`。
5. 附件和表格是核心校园任务，必须独立建模。
6. 当前纯静态、前端 Worker、离线索引架构是正确底座。
7. 当前搜索质量实现还不是终局，应升级为“查询意图 + 排序 profile + 结构化时间 + 来源先验 + 去重聚合 + 评测闭环”。
8. 学生查询集合应该成为长期资产，由源包数据、运行时失败样例、用户反馈和校园时间节点持续反哺，而不是只维护少量 smoke queries。

最终方案不是简单的“标题 + 时间”或“时间最大”，而是：

```text
先判断学生想完成什么任务；
再用该任务对应的标题、时间、来源、类型、附件、系统入口权重；
最后用源包统计、运行时审计、真实学生查询评测集持续校正。
```

这才是面向校园场景的顶级方案。

## 11. 2026-05-28 落地审计

本轮已把调研结论落成可运行实现：

- 生成器新增 `source_id`、`canonical_title`、`published_at`、`updated_at`、`recorded_at`、`version_date`、`date_kind`、`date_confidence`、`academic_year`、`term`、`task_kind`、`authority_profile`、`dedupe_key`。
- 外链/系统入口不再把 `recorded_at` 写入 `published_at`，避免抓取时间冒充内容发布时间。
- 表格、附件、制度标题中的日期进入 `version_date`，例如 `学生缓考申请表 2026-04-16`。
- 浏览器 runtime 拆出 `packages/search-core/src/intent/queryIntent.ts` 和 `packages/search-core/src/ranking/rankDocument.ts`，实现意图识别、来源权威、任务匹配、时间 profile、历史内容降权。
- Python eval 与 TS runtime 同步了 phrase matching 和意图排序，避免评测与浏览器行为分裂。
- 新增 `tools/search-eval/queries/expected_results.json` 与 `python -m njupt_search_eval run-task-queries`，22 条关键任务期望全部通过。
- CI 已接入 `run-task-queries`，旧 smoke query 已更新为三站点权威后的正确期望。
- 重建后的 collection 仍为 9888 条文档，三站点 source truth counts 不变；full shard 数为 598；首屏 artifact budget 通过。

仍属于后续演进、未在本轮强行过度实现的项：

- 独立 `config/search/*.json` 配置化 profile。
- 独立 `ranking_features`、`dedupe_clusters`、`source_bitsets` 等新 artifact。
- UI 侧的宽泛查询分组/澄清视图，例如 `申请表`、`竞赛`、`通知`。
- 生产级 NDCG/MRR 评测。当前是 deterministic top-result/task expectation gate。

本轮选择先把字段语义、排序行为、评测闭环和 CI 门禁打通，这是当前架构下收益最高、风险最低的终局方向第一阶段。
