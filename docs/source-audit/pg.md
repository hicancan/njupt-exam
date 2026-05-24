# 研究生院 Source Audit

- base_url: `https://pg.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 招生工作、培养工作、培养方案、下载专区、学位工作、开题/中期检查、论文撰写与评审、论文答辩与公告、学位申请与授予、规章制度。
- 学生相关栏目: pg_training, pg_degree, pg_download, pg_policy, pg_graduation
- list_url: 首页、967/list.htm、975/list.htm、xzzq/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages; degree publicity can contain sensitive names and must be guarded
- 敏感风险: 名单、学号、成绩、学位公示
- 建议接入 channel: pg_training, pg_degree, pg_download, pg_policy, pg_graduation
- 保留关键词: 研究生、培养、学位、答辩、毕业、论文、下载
- 过滤关键词: 采购、招标
