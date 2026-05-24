# 学生工作处 Source Audit

- base_url: `https://xsc.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 服务指南、资助工作、心理健康、就业指导、一站式学生社区、下载专区、奖助管理、学籍管理。
- 学生相关栏目: xsc_scholarship, xsc_subsidy, xsc_dormitory, xsc_psychology, xsc_service, xsc_download
- list_url: 首页、1158/list.htm、1169/list.htm、jzgl/list.htm、xjgl/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent`
- 附件 selector: `a[href] documents and PDFs`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages; outbound systems may require login and stay as original links
- 敏感风险: 困难认定、获奖名单、学号、联系方式
- 建议接入 channel: xsc_scholarship, xsc_subsidy, xsc_dormitory, xsc_psychology, xsc_service, xsc_download
- 保留关键词: 奖学金、助学金、困难认定、评优、宿舍、心理、服务指南
- 过滤关键词: 党建、会议纪要
