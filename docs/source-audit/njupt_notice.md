# 南邮官网通知通告 Source Audit

- base_url: `https://www.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 通知通告、招生就业、本科招生、研究生招生、留学生招生、就业信息网、信息公开、智慧校园。
- 学生相关栏目: njupt_notice_main, njupt_admission_employment, njupt_smart_campus
- list_url: 72/list.htm、46/list.htm
- 分页方式: WP list + next_link
- 详情页正文 selector: `generic WP detail; content selector fallback required`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public page; body contains generic portal/login words, Rule Guard still checks details
- 敏感风险: 名单、联系方式、校级公告附件
- 建议接入 channel: njupt_notice_main, njupt_admission_employment, njupt_smart_campus
- 保留关键词: 学生、讲座、活动、停水、停电、报名、开放、智慧校园
- 过滤关键词: 巡察、采购、招标、干部
