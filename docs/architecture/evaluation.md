# Evaluation

Production non-exam search is evaluated as a pure JWC sitegraph index. The executable gate is:

```powershell
uv run python scripts\eval\sitegraph_query_smoke_test.py
```

The gate runs the same static index contract used by the frontend:

- manifest and light indexes load first;
- candidate documents are recalled from `inverted_index.json`;
- full records are loaded from `public/index/sitegraph/jwc/documents.*.json` only after candidate selection;
- ranking is deterministic code: title exact, title contains, attachment name, external system, section/nav path, body, tags, then light freshness for notice-like records.

Required representative queries:

```text
校历、慕课考试、期末考试、转专业、规章制度、办事流程、学生相关文件及表格、教务管理系统、大创、推免、成绩、附件1、xlsx
```

The Python contract tests in `tests/test_sitegraph_contract.py` additionally prove count parity and absence of old search artifacts.
