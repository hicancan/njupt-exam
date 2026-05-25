# Product Search Quality Gate

## Objective
To ensure zero regressions in critical student-facing search journeys (exams, scholarships, grades) before any continuous deployment.

## Gate Criteria

1. **`bad_top5_rate`**
   - Must be strictly `0.0`. 
   - No top-5 results may contain restricted, sensitive, or drastically irrelevant content based on known query benchmarks.

2. **`source_violations`**
   - Must be `0`.
   - The query router must not drop critical priority targets (e.g., query "B250403" must always hit `exam_vertical`).

3. **Source Coverage**
   - Manifest MUST prove that documents for critical channels exist or provide explicit `filtered` reasons.
   - CI will abruptly fail (sys.exit 1) if any criteria are missed.

## Reporting
- Reports are persisted to `eval/reports/product_search_latest.json`.
- The format ensures full auditability across all pipeline runs.
