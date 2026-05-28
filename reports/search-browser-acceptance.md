# NJUPT Search Browser Acceptance

Date: 2026-05-28

Target: `http://127.0.0.1:4173/`

Runtime: production preview built from `npm run build`, served with `npm run preview -- --host 127.0.0.1 --port 4173`.

Acceptance method:

- Opened the app with the Codex in-app browser.
- Navigated real browser routes with `?q=<query>`.
- Waited for the Worker-backed progressive search to finish.
- Verified visible DOM result order, top result headings, source URLs, and no browser console errors.

## Query Results

| Query | Top visible result | Outcome |
|---|---|---|
| `校历` | `2025-2026学年校历` | Passed |
| `期末考试` | `【教务管理办公室】关于做好2025-2026学年第二学期期末考试工作安排的通知` | Passed |
| `教务管理系统` | `教务管理系统` | Passed |
| `学生相关文件及表格` | `南京邮电大学学生毕业申请表 2026-04-16` | Passed |
| `xlsx` | `关于举办第十二届全国大学生物理实验竞赛（创新）校内选拔赛的通知` | Passed |
| `大创` | `2024年度大学生创新创业训练计划项目结题验收成绩公示` | Passed |
| `困难认定` | `家庭经济困难学生认定工作实施办法` | Passed |
| `信息门户` | `...综合信息服务—教务管理系统...` | Passed |
| `转专业` | `南京邮电大学本科生转专业管理办法（2025年9月18日修订）` | Passed |
| `推免` | `2026年各学院推荐优秀应届本科毕业生免试攻读研究生工作方案` | Passed |
| `双创信息管理系统` | `双创信息管理系统` | Passed |
| `心理健康` | `心理健康` | Passed |
| `B250403` | `B250403 期末考试安排` | Passed |

Browser console:

```text
No warning or error logs.
```

Screenshot capture through the browser plugin succeeded on the final acceptance pass.
