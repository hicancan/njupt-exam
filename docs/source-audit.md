# njupt-search 源站审计记录

本文件记录公开源接入前的页面结构证据。运行时爬虫仍使用 `requests` 与 BeautifulSoup；Chrome DevTools MCP 用于确认页面模板、列表位置和网络行为。

## 总体判断

- 当前索引已从 10 个硬编码校园源扩展为 `config/campus_sources.json` 注册表。
- 源范围来自南邮公开入口页，包括学校官网通知、教学机构、党政群部门、科研机构、直属单位和其他公开站点。
- 登录态系统、统一身份认证、智慧校园、校内 IP 限制页面不绕过；只能保留标题和原文链接。

## DevTools 抽样证据

| 页面 | 结构结论 | 关键选择器 | 网络结论 | 样本 |
| --- | --- | --- | --- | --- |
| `https://www.njupt.edu.cn/72/list.htm` | 通知列表为服务端渲染 HTML | `.wp_paging` 存在；通告链接为普通 `a[href]` | 未发现 XHR/fetch 数据接口 | “关于遴选第十四批‘南邮-紫金科创学生创业基金’资助项目的通知” |
| `https://cs.njupt.edu.cn/tzgg/list.htm` | 学院通知列表为服务端渲染 HTML | `.news_title`、`.news_meta`、`.news_list`、`.wp_paging` | 未发现 XHR/fetch 数据接口 | 学院通知、招生、创新竞赛、学生工作入口 |
| `https://xsc.njupt.edu.cn/` | 首页聚合多个学生事务模块 | 首页卡片类名包括 `m3title`、`m2title`、`day`、`year` | 未发现 XHR/fetch 数据接口 | 奖助管理、宿舍管理、就业指导、学生手册、心理健康 |

部分学院公网访问 `/tzgg/list.htm` 会返回提示页，但学院首页仍公开聚合学生工作、答辩、竞赛和项目通知。因此第一批学院源采用“首页 + 通知页”组合；列表受限时不推断正文，只抓公开首页中的有效详情页链接。

## 官方入口覆盖

| 官方入口 | 作用 | 当前策略 |
| --- | --- | --- |
| `https://www.njupt.edu.cn/72/list.htm` | 校级通知通告 | Tier 1 接入，强学生相关过滤 |
| `https://www.njupt.edu.cn/jxjg/list.htm` | 教学机构和学院站清单 | 用于源发现和学院站优先级 |
| `https://www.njupt.edu.cn/17352/list.htm` | 党政群部门 | 只接学生强相关部门，其余延后或排除 |
| `https://www.njupt.edu.cn/kyjg/list.htm` | 科研机构 | 默认不进主搜索高位 |
| `https://www.njupt.edu.cn/17354/list.htm` | 直属单位和其他 | 图书馆、档案馆等按服务价值接入 |

## 接入原则

- `central_admin`、`central_notice`、`job_platform`：高权重，默认进入主搜索。
- `college`：只抓通知公告前 1-2 页，学院新闻不作为主结果高位。
- `central_news`、`research_admin`、`policy`：默认低权重。科学技术处、社会科学处、学科建设办公室、产业合作处等只在存在学生动作、截止时间、讲座、项目、竞赛、政策价值时才靠前。
- `github_resource`：不按 365 天公告生命周期删除，只降低新鲜度。
- 受限正文、低证据正文、敏感名单只保留元数据摘要，不生成未经证据支持的行动建议。
