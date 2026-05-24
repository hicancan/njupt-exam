# 国际合作交流处 Source Audit

- base_url: `https://exchange.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 合作交流、合作项目、合作交流流程图、材料下载、合作办学、外专项目、留学南邮、文件下载、港澳台招生、招生简章。
- 学生相关栏目: exchange_notice, exchange_project, exchange_download, exchange_admission
- list_url: 首页、7442/list.htm、7449/list.htm、7450/list.htm、7454/list.htm、7462/list.htm、7459/list.htm、gjhcg/list.htm、16717/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.main on homepage, .wp_articlecontent fallback for detail`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages; online application link may require login and remains outbound only
- 敏感风险: 奖学金名单、出国境材料
- 建议接入 channel: exchange_notice, exchange_project, exchange_download, exchange_admission
- 保留关键词: 交流、访学、项目、报名、下载、表格、留学、港澳台
- 过滤关键词: 外事会议、非学生外专事务
