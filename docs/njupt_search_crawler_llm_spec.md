# njupt-search 当前阶段技术文档：爬虫 + LLM 离线清洗版

版本：v1.0  
作者：hicancan  
阶段定位：MVP+ / Phase 1  
当前约束：暂不训练小模型，暂不引入在线后端，暂不做实时 LLM 搜索  
目标读者：Code Agent / 项目维护者 / 未来论文或大创材料整理者

---

## 0. 当前阶段一句话目标

当前阶段的 njupt-search 不追求训练小模型，也不追求实时 AI 问答，而是先构建一个稳定、可信、可自动更新的校园公开信息索引系统：

> GitHub Actions 每 6 小时抓取南邮公开信息源，规则系统先做安全与质量过滤，再调用 LLM 对新增/变化公告进行离线结构化清洗，最终生成静态搜索索引供前端使用。

当前阶段的核心目标是：

> 先把“数据源抓准、公告理解准、搜索结果可信、前端展示有用”做好。

小模型蒸馏、Hugging Face 模型托管、部署期零 LLM API 成本，是下一阶段目标，不在本文档当前实现范围内。

---

## 1. 当前阶段的最终产品形态

当前阶段完成后，用户应可以通过 njupt-search：

- 搜考试安排；
- 输入班级号查看考试日程；
- 导出考试日历；
- 搜竞赛、大创、挑战杯、蓝桥杯；
- 搜奖学金、助学金、评优、公示；
- 搜转专业、推免、保研、实验班；
- 搜就业宣讲、招聘会、实习；
- 搜图书馆开放、停水停电、校园安全、后勤通知；
- 搜公开 GitHub 资料源和 hicancan 学习资源；
- 在搜索结果中看到分类、二级分类、学生摘要、是否需要行动、行动类型、截止时间、附件、来源和敏感标记。

当前阶段的产品口号可以是：

> 南邮学生信息雷达：考试、竞赛、奖助、就业、讲座、资料，一个地方搜。

---

## 2. 当前阶段不做什么

为了避免过早复杂化，当前阶段明确不做以下事情：

1. 不训练小模型；
2. 不把模型上传 Hugging Face；
3. 不做浏览器端 embedding 模型；
4. 不做实时 LLM 问答；
5. 不做用户登录；
6. 不做个性化推荐；
7. 不做需要登录的教务系统爬取；
8. 不绕过内外网隔离；
9. 不抓取私密群聊和非授权公众号后台；
10. 不把敏感附件全文送入免费 LLM API；
11. 不让 LLM 修改考试时间、考试地点等权威结构化数据；
12. 不把所有源站全量无脑爬取。

当前阶段只做：

> 公开网页抓取 + 规则过滤 + LLM 离线清洗 + 静态索引 + 前端搜索。

---

## 3. 当前阶段总体架构

```text
南邮公开站点 / GitHub 资料源 / hicancan 内容源
        ↓
GitHub Actions 定时触发，每 6 小时运行
        ↓
爬虫抓取候选链接、详情页、附件 metadata
        ↓
规则层处理：去重、受限页面检测、敏感信息检测、过期判断、来源权重
        ↓
仅对新增/变化且低敏的文档调用 LLM
        ↓
LLM 输出结构化字段
        ↓
Pydantic schema 校验
        ↓
失败则回退规则结果，成功则合并到 SearchDocument
        ↓
生成 public/index/documents.json 和 manifest.json
        ↓
前端加载静态 JSON 执行搜索和展示
```

---

## 4. 当前阶段核心成功标准

当前阶段完成后，应满足以下验收标准：

1. 每 6 小时自动更新；
2. 至少 10 个核心公开信息源可抓取；
3. 每个源在 manifest 中有状态记录；
4. 每条文档有统一 SearchDocument 结构；
5. LLM 输出必须经过 Pydantic 校验；
6. 访问受限页面不会被 LLM 幻觉生成行动事项；
7. 敏感信息不会直接展示；
8. 搜索结果能显示行动事项、截止时间、二级分类和来源；
9. 数据构建失败时不会破坏上次可用索引；
10. README 清楚说明非官方、以官网为准；
11. 有基础搜索评测集和数据质量报告；
12. 可作为后续训练小模型的数据积累基础。

---

## 5. 数据源范围

### 5.1 Phase 1 必须接入的公开源

优先接入以下源：

1. 本科生院 / 教务处；
2. 学生工作处；
3. 研究生院；
4. 研究生工作部；
5. 团委 / 青春南邮；
6. 创新创业教育学院；
7. 就业信息网；
8. 图书馆；
9. 保卫处；
10. 后勤管理处。

这些源覆盖学生高价值场景：考试、选课、转专业、推免、奖助、公示、竞赛、大创、就业、图书馆、停水停电、校园安全和生活服务。

### 5.2 可选补充源

当前阶段可逐步加入：

- 学校官网通知；
- 新闻网重要通知；
- 部分重点学院官网；
- GitHub 课程资料仓库；
- hicancan.top 博客 metadata；
- B站视频 metadata；
- 公开微信公众号文章链接。

### 5.3 禁止源

当前阶段禁止：

- 需要账号登录的系统；
- 需要绕过内外网限制的系统；
- 非公开接口；
- 私密群聊；
- 未授权公众号后台；
- 涉及个人隐私的大规模附件全文。

---

## 6. 数据结构设计

### 6.1 SearchDocument

最终前端消费的统一文档结构：

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
  content: string;
  summary: string;
  search_text: string;
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

### 6.2 SearchAttachment

```ts
interface SearchAttachment {
  name: string;
  url: string;
  type: 'pdf' | 'doc' | 'docx' | 'xls' | 'xlsx' | 'ppt' | 'pptx' | 'zip' | 'rar' | 'other';
  role?: string | null;
  sensitive?: boolean;
}
```

### 6.3 分类枚举

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

### 6.4 行动类型枚举

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

## 7. 爬虫设计

### 7.1 爬虫目标

爬虫只负责获取事实信息，不负责高级理解。

爬虫应输出：

- title；
- url；
- source；
- source_domain；
- published_at；
- raw_content；
- cleaned_content；
- attachments；
- source metadata；
- crawl status。

### 7.2 通用站点适配器

建议抽象：

```python
class SiteAdapter:
    source_id: str
    source_name: str
    base_url: str
    list_urls: list[str]
    source_weight: float

    def collect_candidates(self) -> list[Candidate]:
        ...

    def fetch_detail(self, candidate: Candidate) -> RawDocument:
        ...

    def extract_date(self, html: str, url: str) -> str | None:
        ...

    def extract_attachments(self, html: str, base_url: str) -> list[Attachment]:
        ...
```

### 7.3 Candidate 结构

```python
class Candidate(BaseModel):
    title: str
    url: str
    source_id: str
    source_name: str
    published_at: str | None
    list_url: str | None
```

### 7.4 RawDocument 结构

```python
class RawDocument(BaseModel):
    candidate: Candidate
    raw_html: str
    raw_text: str
    cleaned_text: str
    attachments: list[Attachment]
    fetch_status: str
    error: str | None = None
```

### 7.5 抓取策略

默认策略：

- 每个源抓列表前 1-3 页；
- 对新 URL 或内容 hash 变化的 URL 抓详情；
- 旧 URL 命中缓存则不重复 LLM；
- 详情页失败记录到 manifest；
- 单个源失败不影响全局构建。

### 7.6 去重策略

组合去重：

- URL 规范化；
- 标题归一化；
- 正文 hash；
- 附件名 hash；
- 相同标题 + 相近发布时间。

保留优先级：

1. 官方源优先；
2. 原发源优先；
3. 有附件源优先；
4. 新发布时间优先；
5. 学院转发降权。

---

## 8. 规则层设计

规则层必须在 LLM 前执行。

### 8.1 访问受限检测

如果正文命中以下模式：

```text
当前ip并非校内地址
仅允许校内地址访问
无权访问
请登录
登录后查看
访问受限
信息仅允许校内地址访问
```

必须直接标记：

```json
{
  "restricted": true,
  "action_required": false,
  "summary": "该页面访问受限，请点击原文在允许的网络环境下查看。",
  "confidence": 1.0
}
```

禁止把这类页面交给 LLM 生成行动建议。

### 8.2 敏感信息检测

规则检测以下内容：

- 手机号；
- 身份证号；
- 学号；
- 邮箱；
- 银行卡；
- 大规模名单；
- 成绩；
- 处分；
- 家庭经济困难信息；
- 个人联系方式。

命中后：

- `sensitive=true`；
- 前端不展示敏感正文片段；
- 免费 LLM 不处理敏感附件全文；
- 附件仅索引文件名、类型、来源。

### 8.3 过期判断

公告类：

- 明确截止时间已过，可降权但不一定删除；
- 超过 365 天的普通公告默认降权或归档；
- 奖助、公示、考试、报名类过期后应明显标记。

资料类：

- GitHub 资料、课程资料、模板类资源不能简单按一年过期删除；
- 只降低 freshness_score。

### 8.4 考试数据保护

考试时间、地点、课程、班级来自教务 Excel 解析结果。

LLM 不允许修改考试时间、地点、班级号。

---

## 9. LLM 离线清洗设计

### 9.1 LLM 在当前阶段的角色

LLM 是离线清洗器，不是在线问答服务。

用途：

- 判断是否学生相关；
- 分类和二级分类；
- 提取适用对象；
- 生成学生视角摘要；
- 判断是否需要行动；
- 提取行动类型和行动说明；
- 提取截止时间；
- 标注附件角色；
- 标注敏感性；
- 生成 tags。

### 9.2 LLM 不应该做的事情

LLM 不应：

- 修改原文 URL；
- 编造原文没有的截止时间；
- 编造报名流程；
- 访问受限页面自由推断；
- 处理敏感附件全文；
- 修改考试 Excel 中的时间地点；
- 直接决定删除文档。

### 9.3 调用策略

只对以下文档调用 LLM：

- 新增文档；
- hash 变化文档；
- LLM schema version 变化文档；
- 规则低置信度文档；
- 重点源高价值文档。

不调用 LLM：

- 访问受限页面；
- 敏感正文或敏感附件全文；
- 纯重复文档；
- 缓存命中文档；
- 明显无关的行政/采购/教师通知。

### 9.4 LLM Prompt 约束

Prompt 核心要求：

```text
你是南京邮电大学学生信息清洗助手。
请根据标题、来源、正文和附件列表，判断该信息对学生是否有用，并提取结构化字段。

要求：
1. 不要编造原文没有的信息。
2. 截止时间、地点、对象必须来自原文。
3. 如果不确定，填 null，并降低 confidence。
4. 如果正文是访问受限、请登录、仅校内 IP 访问，不要推断行动事项。
5. 如果包含姓名、学号、手机号、身份证号、成绩、困难认定等个人信息，标记 sensitive。
6. 输出必须是合法 JSON。
```

### 9.5 LLM 输入格式

```json
{
  "id": "jwc-xxx",
  "title": "...",
  "source": "本科生院 / 教务处",
  "source_domain": "jwc.njupt.edu.cn",
  "published_at": "2026-05-01",
  "content": "正文前 1500-3000 字",
  "attachments": [
    {"name": "申请表.docx", "type": "docx"}
  ]
}
```

### 9.6 LLM 输出格式

```json
{
  "is_student_facing": true,
  "student_relevance": 0.92,
  "category": "项目",
  "sub_category": "海外交流",
  "audience": ["本科生"],
  "tags": ["海外交流", "报名", "奖学金"],
  "importance_score": 0.86,
  "deadline": "2026-06-01T23:59:59+08:00",
  "action_required": true,
  "action_type": "报名",
  "action_summary": "符合条件的学生需在截止时间前提交申请材料。",
  "student_summary": "本科生可报名暑期海外交流项目，需在截止时间前向学院提交材料。",
  "sensitive": false,
  "restricted": false,
  "confidence": 0.88
}
```

---

## 10. Pydantic Schema 校验

所有 LLM 输出必须使用 Pydantic 校验。

### 10.1 校验要求

- `is_student_facing`: bool；
- `student_relevance`: 0 到 1；
- `category`: 枚举；
- `sub_category`: string 或 null；
- `audience`: string array；
- `tags`: string array，最多 12 个；
- `importance_score`: 0 到 1；
- `deadline`: ISO datetime 或 null；
- `action_required`: bool；
- `action_type`: 枚举或 null；
- `action_summary`: string 或 null，长度限制；
- `student_summary`: string，长度限制；
- `sensitive`: bool；
- `restricted`: bool；
- `confidence`: 0 到 1。

### 10.2 校验失败处理

如果 LLM 输出不合法：

1. 记录错误；
2. 将原始输出保存到 debug 日志；
3. 使用规则系统结果；
4. 该文档进入 review_queue；
5. 不阻塞整个索引构建。

---

## 11. 缓存与版本控制

### 11.1 文档 hash

每条文档计算：

```text
hash = sha1(title + url + cleaned_content + attachment_names)
```

### 11.2 LLM cache key

```text
llm_cache_key = document_hash + llm_schema_version + prompt_version + model_name
```

### 11.3 缓存命中

缓存命中时：

- 复用 LLM 结果；
- 只更新 freshness_score；
- 不重复调用 LLM。

### 11.4 schema version

必须设置：

```python
LLM_SCHEMA_VERSION = "v1"
PROMPT_VERSION = "v1"
```

当 schema 或 prompt 变更时，应强制重新处理部分或全部文档。

---

## 12. manifest.json 设计

`public/index/manifest.json` 应包含：

```json
{
  "generated_at": "2026-05-23T12:00:00+08:00",
  "strategy": "crawler-rule-llm-v1",
  "total_documents": 137,
  "llm_enabled": true,
  "llm_model": "gemini-xxx",
  "llm_schema_version": "v1",
  "prompt_version": "v1",
  "sources": [
    {
      "id": "jwc",
      "name": "本科生院 / 教务处",
      "status": "ok",
      "candidates": 20,
      "documents": 13,
      "filtered_out": 7,
      "restricted": 1,
      "sensitive": 0,
      "last_fetch_at": "...",
      "error": null
    }
  ],
  "quality": {
    "restricted_count": 3,
    "sensitive_count": 4,
    "action_required_count": 28,
    "llm_success_count": 100,
    "llm_failed_count": 5,
    "cache_hit_count": 60
  }
}
```

---

## 13. 前端展示要求

### 13.1 搜索结果卡片

每条结果应展示：

- 来源；
- 分类 / 二级分类；
- 标题；
- 发布时间；
- 摘要；
- tags；
- 是否需要行动；
- 行动类型；
- 行动说明；
- 截止时间；
- 附件数量；
- 敏感标记；
- 访问受限标记；
- 原文链接。

### 13.2 行动卡片

如果 `action_required=true`，结果卡片应高亮显示：

```text
需行动：报名
截止：2026-06-01 23:59
说明：符合条件的学生需在截止时间前提交申请材料。
```

### 13.3 访问受限卡片

如果 `restricted=true`，显示：

```text
该页面访问受限，请点击原文在允许的网络环境下查看。系统未解析具体流程。
```

### 13.4 敏感标记

如果 `sensitive=true`，显示：

```text
含敏感信息，仅展示摘要与原文链接。
```

### 13.5 官方信息提示

页面底部和结果详情处必须显示：

```text
本项目为非官方工具，信息来源于公开网页，具体事项请以官网原文为准。
```

考试频道必须显示：

```text
考试安排以教务系统、准考证和学院通知为准。
```

---

## 14. 搜索排序设计

当前阶段不做复杂向量检索，先使用关键词 + 标签 + LLM 字段的混合排序。

### 14.1 搜索字段

每条文档生成 `search_text`：

```text
标题 + 来源 + 分类 + 二级分类 + tags + 学生摘要 + 行动说明 + 附件名
```

### 14.2 同义词表

增加 `public/index/synonyms.json`：

```json
{
  "保研": ["推免", "推荐免试"],
  "贫困补助": ["困难认定", "资助", "助学金"],
  "找工作": ["就业", "宣讲会", "招聘", "双选会"],
  "比赛": ["竞赛", "大创", "挑战杯", "蓝桥杯"],
  "考试表": ["考试安排", "期末", "考场"]
}
```

### 14.3 排序公式

初始排序：

```text
final_score =
  0.35 * keyword_score
+ 0.20 * tag_score
+ 0.15 * student_score
+ 0.10 * freshness_score
+ 0.08 * importance_score
+ 0.07 * source_weight
+ 0.05 * action_bonus
```

`action_bonus`：

- 需要行动且未过期：+1；
- 快截止：额外加权；
- 已过期：降权。

---

## 15. GitHub Actions 工作流

### 15.1 触发方式

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:
  push:
    branches:
      - main
```

### 15.2 步骤

```text
1. checkout
2. setup python
3. install dependencies
4. run exam crawler
5. process exam Excel
6. fetch GitHub source metadata
7. build campus search index
8. run data contract tests
9. build frontend
10. deploy static site
11. commit changed data if any
```

### 15.3 环境变量

```text
GEMINI_API_KEYS
NJUPT_SEARCH_GITHUB_TOKEN
GITHUB_TOKEN
```

### 15.4 失败策略

- LLM 失败：回退规则结果；
- 某一源失败：manifest 记录 error，不影响其他源；
- 数据契约失败：阻止部署；
- 考试数据失败：保留上次数据；
- 搜索索引为空：阻止部署。

---

## 16. 测试与质量保障

### 16.1 数据契约测试

检查：

- `documents.json` 可解析；
- id 唯一；
- URL 合法；
- category 合法；
- score 在 0~1；
- deadline 格式合法；
- action_required 和 action_type 逻辑一致；
- sensitive/restricted 为 boolean；
- manifest 与 documents 数量一致。

### 16.2 LLM 输出测试

使用 fixture 测试：

- 正常报名通知；
- 奖学金公示；
- 停电通知；
- 就业宣讲；
- 访问受限页面；
- 含手机号页面；
- 无关行政通知。

### 16.3 搜索回归测试

建立 query 测试集：

```text
保研
推免
奖学金
蓝桥杯
大创
停电
图书馆开放
转专业
宣讲会
B250403
高数
离散数学
```

每个 query 指定期望至少命中的文档类别或 doc id。

---

## 17. 人工 review 队列

生成：

```text
public/index/review_queue.json
```

进入队列条件：

- LLM 校验失败；
- confidence < 0.65；
- 访问受限但标题高价值；
- 敏感信息命中；
- deadline 提取冲突；
- category 与规则分类冲突；
- action_required 为 true 但 action_summary 为空。

review_queue 用于：

- 人工修正；
- 后续训练小模型；
- 论文数据集；
- 搜索质量分析。

---

## 18. 当前阶段代码模块建议

```text
scripts/
├── update_search_index.py
├── indexer_config.py
├── indexer_scoring.py
├── llm_scorer.py
├── llm_schema.py
├── restricted_detector.py
├── sensitive_detector.py
├── crawler_adapters.py
├── document_cache.py
├── build_review_queue.py
├── validate_index.py
└── fetch_github_repos.py
```

### 18.1 llm_schema.py

定义 Pydantic 模型和枚举。

### 18.2 restricted_detector.py

实现访问受限文本检测。

### 18.3 sensitive_detector.py

实现敏感信息正则和关键词检测。

### 18.4 document_cache.py

负责 hash 缓存、LLM cache、schema version。

### 18.5 validate_index.py

构建后检查索引质量。

---

## 19. README 当前阶段应说明

README 必须说明：

1. 项目是非官方；
2. 信息来源于公开网页；
3. 以官网原文为准；
4. 不接入登录系统；
5. 不绕过内外网限制；
6. LLM 只用于离线清洗公开低敏信息；
7. 敏感信息不直接展示；
8. 当前阶段暂不训练小模型；
9. 后续计划包括小模型蒸馏、向量检索、个性化订阅。

---

## 20. 当前阶段任务清单

### P0：必须完成

1. 添加访问受限检测；
2. 添加敏感信息检测；
3. 添加 LLM schema version；
4. 添加 Pydantic 校验；
5. 缓存旧文档但支持 schema 版本强制刷新；
6. LLM 失败回退规则结果；
7. manifest 增加质量统计；
8. 前端展示 restricted 和 sensitive；
9. README 更新当前阶段说明；
10. 数据契约测试。

### P1：高优先级

1. 批量 LLM 调用；
2. review_queue；
3. 同义词表；
4. 搜索回归测试；
5. GitHub 资料源不过期删除，只降权；
6. 首页展示数据更新时间；
7. 结果页显示“以官网为准”。

### P2：增强项

1. 附件角色识别；
2. 截止时间证据片段；
3. 搜索结果高亮；
4. 今日更新页；
5. 最近 7 天重要通知；
6. B站/博客资源配置化；
7. 公开微信公众号链接投稿入口。

---

## 21. 当前阶段论文/保研价值

当前阶段如果完成，可以作为：

- 大创雏形；
- 软件工程实践项目；
- LLM 应用系统；
- 高校公开信息结构化检索系统；
- 后续小模型蒸馏论文的数据基础。

当前阶段可写的题目：

> 基于大语言模型的高校公开信息结构化聚合与检索系统设计

但当前阶段的论文创新主要是系统实践，不是模型算法创新。

如果要更强论文价值，后续应加入：

- 人工标注数据集；
- 小模型蒸馏；
- 混合检索实验；
- 搜索质量指标；
- 用户研究。

---

## 22. 当前阶段最终验收标准

当以下条件满足时，当前“爬虫 + LLM”阶段完成：

1. 10 个核心源正常入库；
2. 每 6 小时自动构建；
3. 访问受限页面被正确标记；
4. 敏感内容被正确标记；
5. LLM 输出字段稳定；
6. Pydantic 校验通过；
7. 前端展示行动事项、截止时间、二级分类；
8. 搜索“考试安排”“奖学金”“大创”“停电”“宣讲会”“转专业”“推免”有可用结果；
9. manifest 能说明每个源的抓取状态；
10. 数据出错时不会发布坏索引；
11. README 和免责声明完整；
12. review_queue 开始积累低置信度样本。

---

## 23. 最终总结

当前阶段最优目标不是训练模型，而是用爬虫和 LLM 建立高质量校园信息数据底座。

当前阶段成功的标志不是“模型很强”，而是：

- 数据源稳定；
- 清洗结果可信；
- 搜索结果有用；
- 行动事项清晰；
- 错误可追踪；
- 敏感信息可控；
- 未来可自然沉淀训练数据。

当这个阶段稳定运行后，再进入下一阶段：

> LLM 教师标注 → 人工校验 → 本地小模型蒸馏 → Hugging Face 托管 → GitHub Actions 本地模型推理 → 部署期零 LLM API 成本。

