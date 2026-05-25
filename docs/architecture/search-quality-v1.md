# Search Quality v1 Architecture

## Overview
Search Quality v1.0 introduces a deterministic hybrid search architecture with semantic scoring and explicit intent routing. The system is designed to provide highly relevant, student-facing information by combining lexical, semantic, and rule-based evaluation.

Search Quality v1.3 closes the product validation loop with **Frontend-as-Truth** gates. The TypeScript frontend ranking output is now generated before product and parity checks, and CI fails if the parity gate is run without that artifact.

## Key Components

1. **Query Router v2.1 (Intent Routing)**
   - Operates on a weighted scoring model (`priority`, `soft_terms`, `negative_terms`).
   - Ensures queries like "学校" or "教务处" do not falsely trigger hyper-specific channels unless specific `must_have_any` constraints are met.
   - Fallbacks to `general_search` seamlessly to prevent frontend application crashes (`TS18048`).

2. **Source Coverage Gates**
   - Enforces a zero-tolerance policy on missing critical source data (e.g. `jwc_exam`, `xsc_scholarship`).
   - Prevents stale or broken pipelines from polluting the production hybrid index.
   - Statuses like `warning_filtered_all` natively explain why a channel might have zero documents while maintaining compliance with quality checks.

3. **Data Quality & Fallbacks**
   - Implements `source_mode` and `semantic_mode` provenance tracking to guarantee search determinism.
   - Validates exam-specific vertical data using `exam_structured_data`.

4. **Frontend-as-Truth Gate**
   - `eval_frontend_search.ts` runs the same TypeScript ranking path used by the browser.
   - `eval_product_search.py --mode both` reports Python and frontend pass/fail fields, but blocks on frontend results.
   - `eval_search_parity.py --ts-results ...` quantifies Python/TS drift with hard thresholds for critical, non-data-gap cases.
   - Python `vertical_rank_documents` uses a frontend-compatible scoring path for regression analysis, so critical non-data-gap top1 parity is exact in v1.3.

5. **Data Gap Classification**
   - Search cases can declare `coverage_channels`.
   - If those channels are empty, filtered out, or contain no relevant document for the query terms, the case is `data_gap` instead of a false strict pass.
   - Current v1.3 data gap groups are CET notices, degree/defense notices, and specific competition notices.

## Current Claim Boundary

v1.3 does not claim dense retrieval, cross-encoder reranking, learning-to-rank, click feedback, or online personalization. It claims that the current deterministic hybrid search is protected by frontend-real product gates and explicit data-gap accounting.
