# 📊 Data Inventory & Quality Report

> **Generated on:** 2026-04-15 21:06:44 (Beijing Time)
>
> This report provides complete visibility into raw Excel data and processing results.
> You do NOT need to open the original Excel files - all information is captured here.

## 📋 Executive Summary

| Metric | Value |
|--------|-------|
| Total Files Processed | 1 |
| Total Records Extracted | 1,261 |
| Parse Success Rate | 0/1261 (0.0%) |
| Date Range (All Files) | N/A |
| Unique Classes | ~0 |
| Unique Courses | ~0 |

---

## ⚠️ File: `2025-2026学年第二学期课程结束考试组织单位一览表.xlsx`

**Rows:** 1,261 | **Columns:** 5 | **Parse Success:** 0/1261 | **Date Range:** N/A

### 🔹 Part A: Raw Excel Analysis

#### Original Column Names (as in Excel)

| # | Excel Column Name | Data Type | Non-Null % | Unique Values | Sample Values |
|---|-------------------|-----------|------------|---------------|---------------|
| 1 | `2025-2026学年第二学期课程结束考试组织单位一览表` | object | 100.0% | 28 | 开课学院, 波特兰学院, 材料科学与工程学院 |
| 2 | `Unnamed: 1` | object | 100.0% | 1,261 | 课程代码, P1401062S, PI310400S |
| 3 | `Unnamed: 2` | object | 100.0% | 919 | 课程名称, 通信系统与设计（全英文）, 批判性思维（全英文） |
| 4 | `Unnamed: 3` | object | 100.0% | 3 | 组织单位, 学院, 学校 |
| 5 | `Unnamed: 4` | object | 100.0% | 4 | 考试时间段, 非集中考试周, 集中考试周2 |

#### Column Mapping (Excel → Standard Field)

| Standard Field | Excel Column | Status |
|----------------|--------------|--------|
| `campus` | _(tried: 校区, 校区名称)_ | ❌ Not Found |
| `course_name` | _(tried: 课程名称, 课程, 考试课程)_ | ❌ Not Found |
| `course_code` | _(tried: 课程代码, 选课课号)_ | ❌ Not Found |
| `class_name` | _(tried: 班级名称, 班级, 班级代码)_ | ❌ Not Found |
| `teacher` | _(tried: 任课教师, 教师, 监考教师)_ | ❌ Not Found |
| `location` | _(tried: 考试教室, 教室名称, 地点)_ | ❌ Not Found |
| `raw_time` | _(tried: 考试时间, 时间)_ | ❌ Not Found |
| `count` | _(tried: 人数, 学生人数, 考试人数)_ | ❌ Not Found |
| `school` | _(tried: 开课学院, 学院)_ | ❌ Not Found |
| `student_school` | _(tried: 学生所在学院, 所在学院)_ | ❌ Not Found |
| `major` | _(tried: 专业名称, 专业)_ | ❌ Not Found |
| `grade` | _(tried: 年级)_ | ❌ Not Found |
| `notes` | _(tried: 备注)_ | ❌ Not Found |

#### Raw Data Sample (First 3 Rows, Unprocessed)

| 2025-2026学年第二学期 | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 |
| --- | --- | --- | --- | --- |
| 开课学院 | 课程代码 | 课程名称 | 组织单位 | 考试时间段 |
| 波特兰学院 | P1401062S | 通信系统与设计（全英文） | 学院 | 非集中考试周 |
| 波特兰学院 | PI310400S | 批判性思维（全英文） | 学院 | 非集中考试周 |

### 🔹 Part B: Processing Results

#### Processing Statistics

| Metric | Value |
|--------|-------|
| Records Processed | 1,261 |
| Time Parse Success | 0 |
| Time Parse Failed | 1,261 |
| Unique Classes | 0 |
| Unique Courses | 0 |
| Avg Exam Duration | 0 min |

#### ⚠️ Validation Warnings

Found **1261** rows with parsing issues:

- Row 2: Missing time data (Raw: '')
- Row 3: Missing time data (Raw: '')
- Row 4: Missing time data (Raw: '')
- Row 5: Missing time data (Raw: '')
- Row 6: Missing time data (Raw: '')
- Row 7: Missing time data (Raw: '')
- Row 8: Missing time data (Raw: '')
- Row 9: Missing time data (Raw: '')
- Row 10: Missing time data (Raw: '')
- Row 11: Missing time data (Raw: '')
- _...and 1251 more_

#### Processed Data Sample (First 3 Rows)

| class_name | course_name | campus | start_timestamp | location | teacher | count |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  | None |  |  | 0 |
|  |  |  | None |  |  | 0 |
|  |  |  | None |  |  | 0 |

---

## 📚 Appendix

### A. Field Mapping Reference

The following table shows how Excel column names are mapped to standard field names:

| Standard Field | Possible Excel Column Names |
|----------------|----------------------------|
| `campus` | 校区, 校区名称 |
| `course_name` | 课程名称, 课程, 考试课程 |
| `course_code` | 课程代码, 选课课号 |
| `class_name` | 班级名称, 班级, 班级代码, 行政班级 |
| `teacher` | 任课教师, 教师, 监考教师 |
| `location` | 考试教室, 教室名称, 地点, 考试地点 |
| `raw_time` | 考试时间, 时间 |
| `count` | 人数, 学生人数, 考试人数 |
| `school` | 开课学院, 学院 |
| `student_school` | 学生所在学院, 所在学院 |
| `major` | 专业名称, 专业 |
| `grade` | 年级 |
| `notes` | 备注 |

### B. Supported Time Formats

The system can parse the following time formats:

| Format | Example | Regex Pattern |
|--------|---------|---------------|
| Chinese Date | `2025年11月15日(10:25-12:15)` | `(\d{4})年(\d{1,2})月(\d{1,2})日.*?(\d{1,2}:\d{2})\s*[-~至]\s*(\d{1,2}:\d{2})` |
| ISO Date | `第11周周2(2025-11-18) 13:30-15:20` | `\(?(\d{4}-\d{1,2}-\d{1,2})\)?.*?(\d{1,2}:\d{2})\s*[-~至]\s*(\d{1,2}:\d{2})` |

### C. Output JSON Fields

The processed `all_exams.json` contains these fields per record:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (filename-row) |
| `class_name` | string | Class identifier (e.g., B240402) |
| `course_name` | string | Course name |
| `course_code` | string | Course code |
| `campus` | string | Campus name |
| `teacher` | string | Teacher name |
| `location` | string | Exam location |
| `raw_time` | string | Original time string from Excel |
| `start_timestamp` | string | Parsed ISO datetime |
| `end_timestamp` | string | Parsed ISO datetime |
| `duration_minutes` | integer | Exam duration in minutes |
| `count` | integer | Number of students |
| `notes` | string | Additional notes |

---

*End of Report*