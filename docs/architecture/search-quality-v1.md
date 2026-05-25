# Search Quality v1.0 Architecture

## Overview
Search Quality v1.0 introduces a deterministic hybrid search architecture with semantic scoring and explicit intent routing. The system is designed to provide highly relevant, student-facing information by combining lexical, semantic, and rule-based evaluation.

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
