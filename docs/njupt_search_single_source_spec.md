# njupt-search 唯一源文档

版本：v1.0  
作者：hicancan  
目标读者：Code Agent / 未来协作者 / 项目维护者  
项目定位：南邮学生信息雷达与公开信息智能检索系统

---

## 0. 本文档的作用

本文档是 njupt-search 后续开发的唯一事实源。Code Agent 在实现功能时应优先遵循本文档，而不是根据零散聊天记录自行推断。

本文档覆盖：

1. 项目最终目标；
2. 许可证与所有权策略；
3. 系统架构；
4. 数据源与数据治理；
5. LLM 标注与小模型蒸馏路线；
6. Hugging Face 模型托管；
7. GitHub Actions 离线推理；
8. 静态前端搜索；
9. 论文/保研导向的实验设计；
10. 分阶段任务清单；
11. 验收标准。

---

## 1. 项目一句话定义

njupt-search 是一个面向南京邮电大学学生的公开信息智能检索系统。它自动聚合南邮公开网页、考试安排、GitHub 学习资料、hicancan 个人内容，并通过规则系统、LLM 标注、小模型蒸馏和混合检索，把分散信息转成学生可理解、可搜索、可行动的结构化索引。

核心目标不是做“校园版小 Google”，而是做：

> 南邮学生信息雷达：帮学生判断一条信息和自己有什么关系、是否需要行动、截止时间是什么、应看哪个附件、原文来自哪里。

---

## 2. 产品最终目标

### 2.1 用户目标

学生应能用 njupt-search 快速完成这些任务：

- 搜考试安排；
- 查班级考试并导出日历；
- 搜奖学金、助学金、评优、公示；
- 搜竞赛、大创、挑战杯、蓝桥杯；
- 搜转专业、推免、保研、实验班；
- 搜就业宣讲、招聘会、实习；
- 搜讲座、社团、志愿服务；
- 搜图书馆开放、停水停电、班车、校园安全；
- 搜南邮 GitHub 资料库、课程资料、项目模板；
- 搜 hicancan 的高数、离散数学、项目、博客、视频资源。

### 2.2 系统目标

系统应做到：

- 自动化：每 6 小时自动更新；
- 零在线 LLM API 成本：部署期不调用 Gemini、DeepSeek、OpenAI、Claude 等在线 LLM；
- 零自建后端：不需要长期运行服务器；
- 静态优先：数据生成在构建期完成，用户访问时只读静态资源；
- 可复现：模型、配置、评测、数据样例可复现；
- 可解释：搜索结果显示来源、分类、二级分类、行动事项、截止时间、附件数量、敏感标记；
- 可控：受限页面、敏感信息、访问异常不得由模型自由推断；
- 可持续：核心依赖免费公共额度和本地训练，不依赖持续付费服务。

---

## 3. 许可证与所有权策略

### 3.1 核心判断

如果要“真正开源”，不能禁止商用、不能禁止竞品、不能限制特定用途。开源许可证必须允许自由再分发、修改和商业使用。

因此：

- 如果目标是 OSI 意义上的开源，同时希望尽可能防止别人闭源拿去做服务，推荐：AGPL-3.0-or-later。
- 如果目标是“不希望别人拿走、部署、商用、做竞品”，那就不是严格开源，而是 Source-Available，应使用自定义限制性许可证或 PolyForm Noncommercial 这类许可证。

### 3.2 推荐策略

本项目建议采用“双层保护”：

#### A. 代码层：AGPL-3.0-or-later

适用于前端、爬虫、索引脚本、模型推理脚本等原创代码。

原因：

- AGPL 是强 copyleft；
- 如果别人修改并通过网络提供服务，也需要向用户提供对应源码；
- 能防止别人闭源改造后直接做 SaaS；
- 仍然是正式开源许可证；
- 对论文、保研、开源展示更友好。

限制：

- AGPL 不能禁止别人商用；
- AGPL 不能禁止别人做竞品；
- 只要他们遵守开源义务，他们可以部署。

#### B. 品牌层：保留商标和名称权利

AGPL 只授权代码，不授权品牌。

必须明确保留：

- njupt-search 名称；
- hicancan 名称；
- hicancan.top 域名；
- njupt.hicancan.top 域名；
- logo、图标、界面品牌表达；
- “南邮学生信息雷达”等项目标识。

别人可以 fork 代码，但不能冒充官方 njupt-search，也不能使用 hicancan 品牌。

#### C. 数据层：自定义数据许可证

不建议把完整数据、标注集、训练集、搜索日志、模型训练样本全部按 AGPL 放出。

建议：

- 公开样例数据；
- 公开评测集的脱敏版本；
- 完整训练集可先私有；
- 用户行为数据不公开；
- 敏感字段永不公开；
- 官网原文不声称拥有版权，只保存链接、摘要和结构化 metadata。

#### D. 模型层：独立模型许可证

Hugging Face 模型仓库单独声明许可证。

可选：

- 若希望开源模型：AGPL-3.0-or-later 或 CC-BY-NC-4.0；
- 若希望限制商用：CC-BY-NC-4.0 或自定义模型许可证；
- 若希望最大保护：只公开推理接口或小模型，不公开训练数据。

推荐：模型先使用 `cc-by-nc-4.0` 或自定义“Research and Non-commercial Use Only”。注意这不是 OSI 开源，但更符合“防止拿走”的目标。

### 3.3 仓库应添加的文件

根目录添加：

```text
LICENSE
NOTICE
TRADEMARKS.md
DATA_LICENSE.md
MODEL_LICENSE.md
CONTRIBUTING.md
SECURITY.md
```

### 3.4 package.json

如果采用 AGPL：

```json
{
  "license": "AGPL-3.0-or-later"
}
```

如果采用 source-available：

```json
{
  "license": "UNLICENSED"
}
```

注意：不要写 `Unlicense`。Unlicense 代表放弃版权/接近公有领域，和项目目标相反。

### 3.5 README 许可声明建议

```md
## License

The source code of this project is licensed under AGPL-3.0-or-later unless otherwise stated.

The names, logos, domains, branding, generated indexes, datasets, prompts, model weights, model configurations, and evaluation data may be subject to separate terms. See NOTICE, TRADEMARKS.md, DATA_LICENSE.md, and MODEL_LICENSE.md.

This project is not an official service of Nanjing University of Posts and Telecommunications. Official information should always be verified against the original source websites.
```

---

## 4. 系统总架构

### 4.1 架构概览

```text
本地 RTX 5060 8GB
  ├─ 训练/微调轻量模型
  ├─ 评测模型
  └─ 上传模型到 Hugging Face Hub

Hugging Face Hub
  └─ 托管 njupt-campus-tagger 模型和版本

GitHub Actions
  ├─ 每 6 小时触发
  ├─ 抓取南邮公开数据源
  ├─ 读取考试 Excel 并生成考试数据
  ├─ 拉取 Hugging Face 小模型
  ├─ CPU 推理打标签
  ├─ 构建搜索索引
  ├─ 运行数据契约测试
  └─ 发布静态资源

Cloudflare / GitHub Pages
  └─ 分发静态前端和 JSON 索引

浏览器
  ├─ 加载静态索引
  ├─ 执行关键词/标签/向量混合搜索
  └─ 展示搜索结果、行动卡片、考试日历导出
```

### 4.2 核心原则

- 训练在本地；
- 模型放 Hugging Face；
- GitHub Actions 只做爬取、推理、索引构建、部署；
- 用户访问不触发后端；
- 用户搜索不触发 LLM API；
- 所有核心输出静态化。

---

## 5. 数据源设计

### 5.1 Phase 1 官方公开源

必须支持：

- 本科生院 / 教务处；
- 学生工作处；
- 研究生院；
- 研究生工作部；
- 团委 / 青春南邮；
- 创新创业教育学院；
- 就业信息网；
- 图书馆；
- 保卫处；
- 后勤管理处。

### 5.2 Phase 2 扩展源

后续支持：

- 学校官网通知；
- 新闻网；
- 重点学院官网；
- 公开微信公众号链接；
- GitHub 资料仓库；
- hicancan.top 博客；
- B站视频 metadata；
- 课程资料源。

### 5.3 禁止接入

不得接入：

- 需要登录的教务系统；
- 需要绕过内网隔离的内容；
- 私密群聊内容；
- 未授权公众号后台内容；
- 含大量个人敏感信息的附件全文；
- 需要账号密码爬取的服务。

---

## 6. 文档数据结构

每条搜索文档统一为：

```ts
interface SearchDocument {
  id: string;
  kind: 'notice' | 'exam' | 'resource';
  title: string;
  url: string;
  source: string;
  source_domain: string;
  category: SearchCategory;
  sub_category?: string | null;
  audience: string[];
  published_at: string | null;
  deadline?: string | null;
  action_required?: boolean;
  action_type?: string | null;
  action_summary?: string | null;
  summary?: string;
  content: string;
  search_text: string;
  embedding_text?: string;
  attachments: SearchAttachment[];
  student_score: number;
  freshness_score: number;
  importance_score: number;
  source_weight: number;
  tags: string[];
  sensitive: boolean;
  restricted: boolean;
  confidence?: number;
  hash: string;
}
```

### 6.1 分类枚举

```text
考试
选课
竞赛
奖助
就业
讲座
生活
学院
研究生
项目
资料
公告
```

### 6.2 行动类型枚举

```text
无
报名
提交材料
查看公示
参加活动
下载附件
缴费
填写表格
联系学院
加入会议
导入日历
```

---

## 7. 规则层设计

规则层优先级高于模型。以下情况不得交给模型自由推断。

### 7.1 访问受限检测

命中以下文本时：

```text
当前ip并非校内地址
仅允许校内地址访问
无权访问
请登录
登录后查看
访问受限
```

处理：

```json
{
  "restricted": true,
  "action_required": false,
  "summary": "该页面访问受限，请点击原文在允许的网络环境下查看。",
  "confidence": 1.0
}
```

不得根据标题生成行动建议。

### 7.2 敏感信息检测

规则检测：

- 手机号；
- 身份证号；
- 学号；
- 邮箱；
- 成绩；
- 家庭经济信息；
- 处分信息；
- 大规模名单。

处理：

- `sensitive=true`；
- 不展示敏感正文片段；
- 不送免费 LLM API；
- 附件只索引文件名和来源，不索引全文。

### 7.3 日期与截止时间

日期抽取优先规则：

1. 明确 ISO 日期；
2. 中文日期；
3. 页面发布时间；
4. URL 中日期；
5. LLM/小模型辅助判断。

截止时间必须保留证据片段。没有明确截止时间时填 `null`。

---

## 8. LLM 教师标注路线

### 8.1 LLM 作用

LLM 只做训练期/标注期教师模型，不作为长期线上依赖。

用于：

- 生成伪标签；
- 生成学生摘要；
- 提取行动事项；
- 辅助构建训练集；
- 处理低置信度样本；
- 为论文实验提供 teacher baseline。

### 8.2 LLM 输入

输入限制：

```text
标题 + 来源 + 发布时间 + 正文前 1500~3000 字 + 附件名
```

不得输入：

- 敏感附件全文；
- 大规模名单；
- 需要登录的信息；
- 访问受限页面正文。

### 8.3 LLM 输出 schema

```json
{
  "is_student_facing": true,
  "student_relevance": 0.92,
  "category": "奖助",
  "sub_category": "奖学金评选",
  "audience": ["本科生"],
  "tags": ["奖学金", "评优", "本科生"],
  "importance_score": 0.85,
  "deadline": "2026-06-01T17:00:00+08:00",
  "action_required": true,
  "action_type": "提交材料",
  "action_summary": "符合条件的学生需在截止前提交申请材料。",
  "student_summary": "本通知面向本科生奖学金评选，需按要求提交材料。",
  "sensitive": false,
  "restricted": false,
  "confidence": 0.88
}
```

### 8.4 校验

LLM 输出必须通过 Pydantic 校验。失败则回退规则系统。

---

## 9. 小模型蒸馏路线

### 9.1 目标

使用 LLM 伪标签 + 人工校验数据，训练一个本地轻量模型 `njupt-campus-tagger`，用于部署期替代 LLM。

部署期要求：

- 不调用 Gemini/DeepSeek/OpenAI/Claude；
- GitHub Actions CPU 可推理；
- 模型从 Hugging Face Hub 下载；
- 模型输出稳定 JSON 字段；
- 低置信度进入 review queue。

### 9.2 模型任务

小模型负责：

- `student_facing` 二分类；
- `category` 多分类；
- `action_required` 二分类；
- `action_type` 多分类；
- `sensitive` 二分类；
- `importance_score` 粗评分；
- 标签推荐。

小模型不负责：

- 高质量自然语言长摘要；
- 复杂长文生成；
- 敏感附件全文理解；
- 权威事实判断。

### 9.3 第一版模型

优先实现：

```text
char n-gram TF-IDF + Logistic Regression / Linear SVM
```

优点：

- 文件小；
- CPU 快；
- 可直接在 GitHub Actions 使用；
- 适合中文公告关键词密集场景；
- 适合做 baseline。

### 9.4 第二版模型

实现：

```text
中文 embedding + Logistic Regression / LightGBM
```

可用 embedding：

- bge-small-zh；
- bge-base-zh；
- m3e；
- text2vec；
- bge-m3。

### 9.5 第三版模型

实现：

```text
小型 Transformer / MiniLM / MacBERT + 多任务分类头
```

本地 RTX 5060 8GB 训练注意：

- max_length 512 或 768；
- batch size 4~16；
- fp16；
- gradient accumulation；
- early stopping；
- 必要时 LoRA；
- 不训练大语言模型。

---

## 10. Hugging Face 模型托管

### 10.1 模型仓库

建议创建：

```text
hicancan/njupt-campus-tagger
```

### 10.2 文件结构

```text
njupt-campus-tagger/
├── README.md
├── model_card.md
├── metrics.json
├── label_map.json
├── vectorizer.joblib
├── student_clf.joblib
├── category_clf.joblib
├── action_required_clf.joblib
├── action_type_clf.joblib
├── sensitive_clf.joblib
└── VERSION
```

如果使用 ONNX：

```text
model.onnx
tokenizer.json
config.json
label_map.json
metrics.json
```

### 10.3 版本策略

必须锁定 revision：

```text
v0.1.0
v0.2.0
v1.0.0
```

GitHub Actions 不允许直接拉浮动 main。必须配置：

```text
MODEL_REPO=hicancan/njupt-campus-tagger
MODEL_REVISION=v0.1.0
```

### 10.4 GitHub Actions 缓存

缓存目录：

```text
models/njupt-campus-tagger
```

cache key：

```text
hf-model-njupt-campus-tagger-${MODEL_REVISION}
```

---

## 11. GitHub Actions 工作流

### 11.1 更新频率

默认每 6 小时：

```cron
0 */6 * * *
```

### 11.2 工作流步骤

```text
1. checkout
2. setup python
3. install dependencies
4. restore model cache
5. download HF model if missing
6. run exam crawler
7. process exam Excel
8. crawl public campus sources
9. detect restricted/sensitive documents
10. tag documents with local model
11. build search index
12. run contract tests
13. commit changed data
14. deploy static site
```

### 11.3 失败策略

- 某个数据源失败不应导致全站不可用；
- manifest 记录错误；
- 如果考试数据更新失败，保留上次可用数据；
- 如果模型下载失败，回退规则标签器；
- 如果数据契约测试失败，禁止部署。

---

## 12. 搜索架构

### 12.1 第一版搜索

使用：

- 标题包含；
- 标签匹配；
- 来源匹配；
- 正文匹配；
- 班级号精确匹配；
- 分类过滤；
- 新鲜度和重要性排序。

### 12.2 第二版搜索

加入：

- 同义词表；
- 本地语义词典；
- 标签扩展；
- LLM/小模型生成的 `search_text`。

同义词示例：

```json
{
  "保研": ["推免", "推荐免试"],
  "贫困补助": ["困难认定", "资助", "助学金"],
  "找工作": ["就业", "宣讲会", "招聘", "双选会"],
  "比赛": ["竞赛", "大创", "挑战杯", "蓝桥杯"],
  "考试表": ["考试安排", "期末", "考场"]
}
```

### 12.3 第三版搜索

加入向量检索：

- 文档 embedding 离线生成；
- query embedding 可后续通过前端小模型或预定义 intent 向量实现；
- 前期不强依赖实时 query embedding。

### 12.4 排序公式

初始排序：

```text
final_score =
  0.30 * keyword_score
+ 0.25 * tag_score
+ 0.15 * vector_score
+ 0.10 * student_score
+ 0.08 * freshness_score
+ 0.06 * importance_score
+ 0.04 * source_weight
+ 0.02 * action_bonus
```

权重后续通过评测集调参。

---

## 13. 前端要求

### 13.1 页面结构

- 首页：搜索框 + 快捷入口 + 今日更新；
- 结果页：分类 Tab + 搜索结果；
- 考试详情页：班级考试 + 勾选 + ICS 导出；
- 学习资源区：B站、博客、GitHub、课程资料；
- 数据说明页：来源、更新时间、免责声明。

### 13.2 搜索结果卡片

必须展示：

- 标题；
- 来源；
- 分类 / 二级分类；
- 发布时间；
- 摘要；
- 是否需要行动；
- 行动类型；
- 截止时间；
- 附件数量；
- 敏感标记；
- 访问受限标记；
- 原文链接。

### 13.3 重要提示

所有官方类通知必须显示：

```text
请以官网原文为准。
```

考试信息必须显示：

```text
考试安排以教务系统、准考证和学院通知为准。
```

---

## 14. 数据文件输出

```text
public/index/manifest.json
public/index/documents.json
public/index/documents-lite.json
public/index/synonyms.json
public/index/category_stats.json
public/index/eval_report.json
public/data/all_exams.json
public/data/data_summary.json
```

### 14.1 manifest.json

包含：

- generated_at；
- total_documents；
- strategy；
- model_repo；
- model_revision；
- sources；
- failed_sources；
- restricted_count；
- sensitive_count；
- action_required_count。

---

## 15. 评测体系

### 15.1 必须构建 eval set

文件：

```text
data/eval/eval_queries.json
```

格式：

```json
{
  "query": "保研",
  "relevant_doc_ids": ["jwc-xxx", "pg-xxx"],
  "category": "选课"
}
```

### 15.2 评测指标

搜索：

- Precision@5；
- Recall@10；
- MRR@10；
- NDCG@10。

分类：

- Accuracy；
- Macro-F1；
- Precision；
- Recall。

行动事项：

- action_required F1；
- action_type Accuracy；
- deadline exact match。

成本：

- GitHub Actions 运行时间；
- 模型下载时间；
- 推理时间；
- 索引大小；
- 前端加载时间；
- 在线 LLM API 调用数，应为 0。

---

## 16. 论文/保研方向

### 16.1 推荐论文题目

中文：

> 面向零在线 API 成本部署的高校公开信息智能检索系统

英文：

> CampusRadar: Distilling LLMs for Zero-API-Cost Student-Oriented Campus Information Retrieval

### 16.2 论文贡献点

1. 提出 free-tier-based、serverless-static 的校园信息检索架构；
2. 设计学生事务结构化 schema；
3. 使用 LLM 作为教师模型自动标注高校公告；
4. 蒸馏训练轻量本地模型，实现部署期零 LLM API 成本；
5. 构建真实校园公告搜索评测集；
6. 在真实南邮数据上验证混合检索优于规则 baseline。

### 16.3 实验对比

比较：

- 规则系统；
- LLM 直接标注；
- TF-IDF 小模型；
- Embedding + 分类器；
- 小模型 + 规则；
- 混合检索系统。

---

## 17. 分阶段开发计划

### Phase 0：许可与仓库治理

- 添加 LICENSE；
- 添加 NOTICE；
- 添加 TRADEMARKS.md；
- 添加 DATA_LICENSE.md；
- 添加 MODEL_LICENSE.md；
- README 更新许可证说明；
- package.json 设置 license。

验收：仓库首页清楚说明代码、品牌、数据、模型的授权边界。

### Phase 1：可靠索引构建

- 访问受限检测；
- 敏感信息检测；
- Pydantic schema；
- manifest 增强；
- 源站失败记录；
- 数据契约测试。

验收：受限页面不再被模型生成虚假行动建议。

### Phase 2：LLM 教师标注数据集

- 批量 LLM 标注；
- 生成 annotations.jsonl；
- 人工校验 300 条；
- 建 train/valid/test；
- 建 eval queries。

验收：有可训练、可评测的数据集。

### Phase 3：本地小模型训练

- 训练 TF-IDF + Logistic Regression baseline；
- 评测并输出 metrics.json；
- 保存模型文件；
- 上传 Hugging Face。

验收：模型能输出 student_facing、category、action_required、action_type、sensitive。

### Phase 4：GitHub Actions 使用小模型

- 添加 HF 下载脚本；
- 添加模型 cache；
- 添加本地推理脚本；
- 部署期取消 LLM API 调用；
- manifest 记录 model_revision。

验收：Actions 运行全流程，在线 LLM API 调用数为 0。

### Phase 5：混合搜索增强

- 同义词表；
- 标签扩展；
- search_text；
- 排序公式；
- 评测报告。

验收：搜索评测指标优于原规则系统。

### Phase 6：论文与展示

- 生成技术报告；
- 生成架构图；
- 生成实验表；
- 准备演示视频；
- 准备保研/大创材料。

验收：能向老师展示系统、代码、数据、模型、实验、用户价值。

---

## 18. Code Agent 实现约束

Code Agent 必须遵守：

1. 不引入付费云服务；
2. 不引入长期后端服务；
3. 不把 API key 写入代码；
4. 不把敏感数据提交仓库；
5. 不绕过内网或登录限制；
6. 不把大模型权重提交 GitHub 仓库；
7. 模型文件优先从 Hugging Face 下载；
8. 所有 LLM 输出必须 schema 校验；
9. 所有生成索引必须通过测试；
10. 不删除“以官网为准”的提示；
11. 不移除 hicancan 和 njupt-search 品牌声明；
12. 不把 Unlicense、MIT、Apache 等宽松许可证误加到仓库。

---

## 19. 立即执行任务清单

### 任务 1：许可证文件

创建：

```text
LICENSE
NOTICE
TRADEMARKS.md
DATA_LICENSE.md
MODEL_LICENSE.md
```

代码许可证建议 AGPL-3.0-or-later。

### 任务 2：受限页面检测

添加 `scripts/restricted_detector.py`。

### 任务 3：敏感信息检测

添加 `scripts/sensitive_detector.py`。

### 任务 4：LLM schema

添加 `scripts/llm_schema.py`，使用 Pydantic。

### 任务 5：本地模型训练目录

添加：

```text
training/
├── build_dataset.py
├── train_tagger.py
├── evaluate_tagger.py
├── export_model.py
└── README.md
```

### 任务 6：Hugging Face 下载与推理

添加：

```text
scripts/download_hf_model.py
scripts/tag_with_local_model.py
```

### 任务 7：Actions 集成

更新 `.github/workflows/auto-update.yml`：

- restore cache；
- download model；
- local tagger inference；
- build index；
- test；
- commit。

### 任务 8：前端展示增强

搜索卡片展示：

- `sub_category`；
- `action_required`；
- `deadline`；
- `action_summary`；
- `sensitive`；
- `restricted`。

### 任务 9：评测

添加：

```text
experiments/evaluate_search.py
experiments/evaluate_tagger.py
data/eval/eval_queries.json
```

---

## 20. 最终验收标准

项目达到以下标准时，可认为进入“极致低成本 + 专用智能检索”形态：

1. 每 6 小时自动更新；
2. 部署期不调用在线 LLM API；
3. GitHub Actions 能从 Hugging Face 拉取模型并 CPU 推理；
4. 所有数据输出为静态 JSON；
5. 前端无需后端即可搜索；
6. 搜索结果能展示行动事项和截止时间；
7. 受限页面不会被幻觉解析；
8. 敏感信息不会直接展示；
9. 有搜索评测集和自动评测报告；
10. 有模型版本和评测指标；
11. 有清晰 license、trademark、data、model 授权边界；
12. README 清楚说明非官方、以官网为准；
13. 可用于保研/大创/论文展示。

---

## 21. 最终愿景

njupt-search 的最终愿景是：

> 在不自建后端、不持续付费、不依赖在线 LLM API 的条件下，构建一个真实可用、可复现、可评测、可持续迭代的南邮学生信息雷达。

它不追求在所有任务上超过通用大模型，而是追求在南邮学生信息检索这个垂直任务上，通过真实数据、结构化规则、小模型蒸馏、混合检索和学生反馈，获得比裸用通用 LLM 更稳定、更低成本、更可信的效果。

