# 档案馆 Source Audit

- base_url: `https://dag.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 服务指南、用档指南、归档指南、档案法规、档案编研、参观指南、下载专栏、通知公告。
- 学生相关栏目: archives_guide, archives_notice, archives_download
- list_url: 1259/list.htm、1261/list.htm、1277/list.htm、1270/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent fallback`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages
- 敏感风险: 档案、成绩单、个人证明办理信息
- 建议接入 channel: archives_guide, archives_notice, archives_download
- 保留关键词: 档案、证明、用档、指南、下载、寒假、暑假、办理
- 过滤关键词: 馆内会议、非学生展陈
