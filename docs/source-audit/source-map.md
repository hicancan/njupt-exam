# Source Map

`config/source_channels.json` is the production Source-Channel Graph. `campus_sources.json` is not used by the runtime path.

| Priority | Source | Production channels | Audit state | Notes |
| --- | ---: | ---: | --- | --- |
| P0 | `jwc` 本科生院 / 教务处 | 7 | Chrome audited, deepened | 考试、课程、推免、转专业、学位、下载、校历 |
| P0 | `xsc` 学生工作处 | 6 | Chrome audited, deepened | 奖学金、资助、宿舍、心理、事务服务、下载 |
| P0 | `pg` 研究生院 | 5 | Chrome audited, deepened | 培养、学位、下载、规章、毕业论文 |
| P0 | `ygb` 研究生工作部 | 4 | Chrome audited, deepened | 研究生奖助、实践、事务服务 |
| P0 | `youth` 团委 / 青春南邮 | 4 | Chrome audited, deepened | 挑战杯、志愿、团学组织、下载 |
| P0 | `cxcy` 创新创业教育学院 | 5 | Chrome audited, deepened | 大创、竞赛、创业基金、公示、下载 |
| P0 | `job` 就业信息网 | 3 | Chrome audited, adapter validated | 宣讲会、招聘会、实习岗位，公开 API adapter |
| P0 | `lib` 图书馆 | 4 | Chrome audited, deepened | 开放、数据库、研读室、阅读活动 |
| P0 | `bwc` 保卫处 | 4 | Chrome audited, deepened | 安全、户籍、交通、消防 |
| P0 | `hqc` 后勤管理处 | 5 | Chrome audited, deepened | 停水停电、维修、班车、医保、下载 |
| P1 | `njupt_notice` 校级通知 | 3 | Chrome audited | 校级通知、招生就业、智慧校园入口 |
| P1 | `news` 南邮新闻网 | 2 | Chrome probed, 502 observed | 保留低权重新闻骨架，依赖源站恢复 |
| P1 | `xxgk` 信息公开 | 3 | Chrome audited | 信息公开目录、学生服务、收费学位 |
| P1 | `exchange` 国际合作交流处 | 4 | Chrome audited | 交流项目、下载、留学/港澳台招生 |
| P1 | `yzb` 研究生招生 | 5 | Chrome audited | 硕士、推免、博士、历史数据、下载 |
| P1 | `xxb` 信息化建设与管理办公室 | 4 | Chrome audited | 校园网、VPN、统一身份、下载 |
| P1 | `cwc` 财务处 | 2 | Chrome probed, 502 observed | 保留低权重财务骨架 |
| P1 | `archives` 档案馆 | 3 | Chrome audited | 用档、通知、下载 |
| P1 | `pe` 体育部 | 4 | Chrome audited | 体育课程、晨跑体测、竞赛、下载 |
| P2 | 11 college sources | 22 | production skeleton | 学业通知 + 竞赛项目双通道 |

Current target: source_count >= 30, channel_count >= 60, production_channel_count >= 50, failed_channel_count = 0 or explained in manifest.
