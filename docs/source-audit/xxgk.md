# 信息公开 Source Audit

- base_url: `https://xxgk.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 信息公开指南、信息公开目录、招生考试信息、财务资产收费、教学质量、学生管理服务、学位学科、最新公开信息、依申请公开。
- 学生相关栏目: xxgk_policy, xxgk_student_service, xxgk_fee_degree
- list_url: xxgkml/list.htm、zxgkxx/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.main on homepage, .wp_articlecontent fallback for detail`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages; contains generic portal links
- 敏感风险: 收费、学生管理、名单类公开信息
- 建议接入 channel: xxgk_policy, xxgk_student_service, xxgk_fee_degree
- 保留关键词: 学生管理、服务、奖助、学籍、收费、教学质量、学位、招生考试
- 过滤关键词: 采购、资产
