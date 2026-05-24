# 本科生院 / 教务处 Source Audit

- base_url: `https://jwc.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 本科生院、学生培养、考试工作、学生事务、学籍、选课、考试、推免生、毕业/结业/学位、常用下载、学生相关文件及表格、校历查询。
- 学生相关栏目: jwc_exam, jwc_course, jwc_degree, jwc_transfer, jwc_recommendation, jwc_download, jwc_calendar
- list_url: 1756/list.htm, 1505/list.htm, 1512/list.htm, 1503/list.htm, 1511/list.htm, 1690/list.htm, 校历 page。
- 分页方式: WP list + next_link where present
- 详情页正文 selector: `.wp_articlecontent`
- 附件 selector: `a[href] with office/pdf/archive extensions`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public list pages; details still checked by Rule Guard for login/campus-only text
- 敏感风险: 学号、成绩、考试名单、推免/学位公示附件
- 建议接入 channel: jwc_exam, jwc_course, jwc_degree, jwc_transfer, jwc_recommendation, jwc_download, jwc_calendar
- 保留关键词: 考试、选课、推免、转专业、学籍、毕业、学位、校历、下载
- 过滤关键词: 采购、招标、会议纪要
