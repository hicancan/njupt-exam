# 研究生招生 Source Audit

- base_url: `https://yzb.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 硕士招生、推免生、相关下载、博士招生、历史数据、硕士/博士信息公开、招生学院。
- 学生相关栏目: yzb_master, yzb_recommendation, yzb_doctor, yzb_data, yzb_download
- list_url: 7799/list.htm、7800/list.htm、7803/list.htm、7804/list.htm、7805/list.htm、7809/list.htm、7813/list.htm、7814/list.htm、ssxxgk/list.htm、bsxxgk/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent fallback`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages; result/publicity pages may contain names
- 敏感风险: 拟录取名单、调剂名单、学号/考生号
- 建议接入 channel: yzb_master, yzb_recommendation, yzb_doctor, yzb_data, yzb_download
- 保留关键词: 硕士、博士、推免、招生、复试、录取、分数线、下载
- 过滤关键词: 非招生新闻
