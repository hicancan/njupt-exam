# 就业信息网 Source Audit

- base_url: `https://njupt.91job.org.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 就业平台首页、宣讲会、招聘会、双选会、岗位信息。
- 学生相关栏目: job_talk, job_fair, job_internship
- list_url: 就业平台公开首页和公开 JSON endpoint
- 分页方式: json_api
- 详情页正文 selector: `adapter extracts title/date/company/place`
- 附件 selector: `API payload links only, no attachment mirroring`
- 是否有 XHR / Fetch / JSON: public platform XHR/fetch observed for getHdrllb/getGglb/getWzmb style endpoints
- 访问限制: public platform; no login used
- 敏感风险: 企业联系人信息按公开招聘信息保留，不展开私密信息
- 建议接入 channel: job_talk, job_fair, job_internship
- 保留关键词: 宣讲会、招聘会、双选会、实习、就业
- 过滤关键词: none
