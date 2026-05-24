# 研究生工作部 Source Audit

- base_url: `https://ygb.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 事务管理、资助服务、学术科技实践、下载中心。
- 学生相关栏目: ygb_scholarship, ygb_subsidy, ygb_practice, ygb_service
- list_url: 首页、swgl/list.htm、zzfw/list.htm、xskjsj/list.htm、3788/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages
- 敏感风险: 研究生奖助名单、学号、联系方式
- 建议接入 channel: ygb_scholarship, ygb_subsidy, ygb_practice, ygb_service
- 保留关键词: 奖学金、助学金、评优、实践、学术、下载
- 过滤关键词: 党建、会议
