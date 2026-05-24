# 体育部 Source Audit

- base_url: `https://tyb.njupt.edu.cn/`
- 审计时间: 2026-05-24
- 审计方式: Chrome DevTools MCP, public pages only, no login, no campus bypass.
- 首页导航: 教学科研、教学活动、体育课程表、群体动态、群体运动、运动竞赛、晨跑通知、资料下载、体质测试。
- 学生相关栏目: pe_course, pe_running, pe_competition, pe_download
- list_url: 7228/list.htm、7226/list.htm、7233/list.htm、7229/list.htm、7257/list.htm、zlxz/list.htm
- 分页方式: homepage_links / WP lists
- 详情页正文 selector: `.wp_articlecontent fallback`
- 附件 selector: `a[href] documents`
- 是否有 XHR / Fetch / JSON: none observed
- 访问限制: public pages
- 敏感风险: 体测名单、体育干部/运动员名单
- 建议接入 channel: pe_course, pe_running, pe_competition, pe_download
- 保留关键词: 体育课程、体测、晨跑、比赛、竞赛、体育文化月、下载
- 过滤关键词: 巡察、党建、内部会议
