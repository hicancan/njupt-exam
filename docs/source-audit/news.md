# 南邮新闻网 Source Audit

- base_url: `https://news.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: Chrome audit returned 502 Bad Gateway on 2026-05-24; keep low-priority skeleton and rely on crawler status/cache.
- 学生相关栏目: news_campus, news_activity
- list_url: homepage
- 分页方式: homepage_links when available
- 详情页正文 selector: `.wp_articlecontent fallback`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: not available due 502 during audit
- 访问限制: public endpoint, currently unstable
- 敏感风险: low; news may be non-actionable
- 建议接入 channel: news_campus, news_activity
- 保留关键词: 学生、讲座、报告、活动、竞赛、获奖
- 过滤关键词: 调研、会议、理论学习、领导
