# 图书馆 Source Audit

- base_url: `https://lib.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 开放时间、数据库、读者服务、研读室、阅读活动、VPN 访问提示。
- 学生相关栏目: lib_opening, lib_resource, lib_study_space, lib_activity
- list_url: 首页、1384/list.htm、1387/list.htm、1395/list.htm、1402/list.htm、1408/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: Chaoxing robot-check XHR observed but not used for crawling
- 访问限制: public pages
- 敏感风险: low; resource links may leave official site
- 建议接入 channel: lib_opening, lib_resource, lib_study_space, lib_activity
- 保留关键词: 开放、图书馆、数据库、研读室、借阅、活动
- 过滤关键词: 采购、招标
