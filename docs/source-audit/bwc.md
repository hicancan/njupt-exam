# 保卫处 Source Audit

- base_url: `https://bwc.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 治安交通、校园消防、户籍事务、文件下载、服务链接。
- 学生相关栏目: bwc_security, bwc_household, bwc_traffic, bwc_fire
- list_url: 首页、zajt/list.htm、xyxf/list.htm、hjsw/list.htm、516/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages
- 敏感风险: 户籍、证件办理材料
- 建议接入 channel: bwc_security, bwc_household, bwc_traffic, bwc_fire
- 保留关键词: 交通、安全、消防、户籍、车贴、管制
- 过滤关键词: 采购、招标
