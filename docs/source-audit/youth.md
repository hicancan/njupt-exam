# 团委 / 青春南邮 Source Audit

- base_url: `https://youth.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 团委发文、下载专区、专题活动、挑战杯、志愿服务、团学组织。
- 学生相关栏目: youth_competition, youth_volunteer, youth_organization, youth_download
- list_url: 首页、7515/list.htm、7516/list.htm、7522/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages
- 敏感风险: 参赛名单、获奖名单
- 建议接入 channel: youth_competition, youth_volunteer, youth_organization, youth_download
- 保留关键词: 挑战杯、竞赛、社团、志愿、活动、报名
- 过滤关键词: 会议纪要
