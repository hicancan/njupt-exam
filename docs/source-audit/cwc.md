# 财务处 Source Audit

- base_url: `https://cwc.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: Chrome audit returned 502 Bad Gateway on 2026-05-24; keep low-priority skeleton for future public recovery.
- 学生相关栏目: cwc_notice, cwc_download
- list_url: homepage
- 分页方式: homepage_links when available
- 详情页正文 selector: `.wp_articlecontent fallback`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: not available due 502 during audit
- 访问限制: public endpoint, currently unstable
- 敏感风险: 缴费、收费、财务办理材料
- 建议接入 channel: cwc_notice, cwc_download
- 保留关键词: 缴费、收费、财务、学生、流程、下载
- 过滤关键词: 采购、资产
