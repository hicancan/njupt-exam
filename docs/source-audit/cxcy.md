# 创新创业教育学院 Source Audit

- base_url: `https://cxcy.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 大创项目、相关通知、立项公示、学科竞赛、下载中心、创业基金。
- 学生相关栏目: cxcy_project, cxcy_competition, cxcy_fund, cxcy_publicity, cxcy_download
- list_url: 首页、15464/list.htm、15493/list.htm、15494/list.htm、15465/list.htm、15495/list.htm、15468/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages
- 敏感风险: 参赛队员、获奖名单、项目成员、学号
- 建议接入 channel: cxcy_project, cxcy_competition, cxcy_fund, cxcy_publicity, cxcy_download
- 保留关键词: 大创、创新创业、竞赛、项目申报、挑战杯、互联网+
- 过滤关键词: 采购、招标
