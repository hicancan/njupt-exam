# 后勤管理处 Source Audit

- base_url: `https://hqc.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 通知公告、下载专区、服务热线、班车时刻表。
- 学生相关栏目: hqc_logistics, hqc_repair, hqc_shuttle, hqc_medical, hqc_download
- list_url: 5002/list.htm、5033/list.htm、bcskb/list.htm、5004/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages
- 敏感风险: 医保、体检、宿舍维修可能含个人办理信息
- 建议接入 channel: hqc_logistics, hqc_repair, hqc_shuttle, hqc_medical, hqc_download
- 保留关键词: 停水、停电、维修、医保、体检、班车、后勤
- 过滤关键词: 采购、招标
