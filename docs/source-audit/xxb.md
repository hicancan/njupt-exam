# 信息化建设与管理办公室 Source Audit

- base_url: `https://xxb.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 表格下载、服务指南、公共平台服务、统一身份认证、网络信息服务、域名服务、VPN、数字教学服务、常见问题、下载中心。
- 学生相关栏目: xxb_network, xxb_identity, xxb_platform, xxb_download
- list_url: wlxxfw/list.htm、18380/list.htm、cjwt/list.htm、tysfrz/list.htm、fwznnew/list.htm、ggptfw/list.htm、5248/list.htm、bgxz/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent fallback`
- 附件 selector: `a[href] documents/PDF`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages; campus self-service links may require login and remain outbound only
- 敏感风险: 账号、认证、网络服务申请材料
- 建议接入 channel: xxb_network, xxb_identity, xxb_platform, xxb_download
- 保留关键词: 校园网、VPN、统一身份、邮箱、智慧校园、下载、表格
- 过滤关键词: 党建、内部会议
