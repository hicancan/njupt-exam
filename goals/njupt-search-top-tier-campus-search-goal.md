# Goal: Top-Tier Data-Driven Campus Search for `njupt-search`

## How To Invoke

Use this file as the long-form detail document for Codex `/goal`.

Suggested invocation:

```text
/goal Execute goals/njupt-search-top-tier-campus-search-goal.md. Upgrade NJUPT Search into a top-tier static, data-driven, intent-aware campus search product. Continue through source-package research, architecture refinement, implementation, generated artifact rebuilds, browser verification, local tests, GitHub Actions/cloud CI, and final push/merge to cloud main without waiting for milestone-by-milestone approval. Do not mark complete until all acceptance criteria in the goal document pass or an exact external blocker is recorded.
```

Codex goal design basis:

- `/goal` is for long-running work with a durable objective and verifiable stopping condition.
- Detailed instructions should live in a file when the objective would exceed a compact command.
- The run must keep short progress reports, work in checkpoints, and stop only when the defined completion state is reached or an evidence-backed blocker prevents progress.

References:

- https://developers.openai.com/codex/use-cases/follow-goals
- https://developers.openai.com/codex/cli/slash-commands#set-or-view-a-task-goal-with-goal

## Objective

Upgrade `njupt-search` from a strong static full-text campus search into a top-tier, static, data-driven, intent-aware campus task search for NJUPT student-facing information.

The final product must optimize for:

```text
right task
+ current validity
+ official authority
+ actionability
+ low misclick risk
```

The final architecture must preserve the repository boundary:

```text
static-site-graph -> njupt-site-graph -> njupt-search
```

`njupt-search` remains the downstream public search product. It consumes audited source packages and generated exam data, compiles browser runtime artifacts, and owns the React/PWA experience.

## Non-Negotiable Product Boundaries

- Keep `collection` as the product abstraction. Current collection id: `njupt-public`.
- Keep `jwc`, `xsc`, and `cxcy` as source package ids, not product boundaries.
- Keep `exam` as a product vertical with generated data under `apps/web/public/generated/exam/`.
- Do not move crawling, source discovery, or source-truth audit ownership into this repo.
- Do not add runtime server search, LLM search, provider fields, obsolete semantic production fields, or task-frame search.
- Do not add a Codex GitHub Action, Codex review workflow, or `.github/codex/prompts`.
- Generated JSON artifacts are compiled runtime data. Update generators or source inputs, then rebuild. Do not hand-edit generated artifacts.
- Use PowerShell 7 locally.
- Use the Codex internal browser/browser tool for frontend and runtime acceptance.

## Current Baseline

The current collection already integrates:

- `jwc`
- `xsc`
- `cxcy`

Current generated collection facts from local research:

- Runtime documents: 9888
- Runtime full shards: 501
- Source package truth counts:
  - `jwc`: 6884 detail pages, 7905 attachments, 426 external links, 19089 URL outcomes
  - `xsc`: 1589 detail pages, 17 attachments, 75 external links, 6414 URL outcomes
  - `cxcy`: 612 detail pages, 205 attachments, 60 external links, 1311 URL outcomes

Key current implementation:

- Offline compiler: `tools/collection-indexer`
- Runtime search core: `packages/search-core`
- Contracts: `packages/contracts`
- Search eval: `tools/search-eval`
- Quality gates: `tools/quality-gates`
- Web app: `apps/web`

Research artifacts already created:

- `reports/search-ranking-data-research.md`
- `tools/search-eval/queries/student_task_queries.json`

Treat these as starting context, not final truth. Re-read the current code and generated manifests before editing.

## Core Diagnosis

The current search architecture is strong as a static, progressive, verifiable frontend search:

```text
source packages
-> collection-indexer
-> hashed static artifacts
-> browser Worker progressive recall
-> candidate hydration
-> shard-filter-assisted full verification
-> ranked UI results
```

The quality gap is that ranking is still mostly a single global scoring function. Campus search needs intent-specific ranking:

```text
query intent
-> ranking profile
-> structured title/time/source/type/form/system features
-> result grouping and explanation
-> evaluated against student task queries
```

Do not solve this by simply making recency the global maximum weight. Recency is dominant for current notices, exams, awards, registration, and public announcements. It is weak or disabled for stable system entries. It is version-oriented for forms and policies.

## Final Target Architecture

Keep the current static architecture, but evolve search quality modules into clear boundaries.

Recommended search-core shape:

```text
packages/search-core/src/
  intent/
    queryIntent.ts
    intentRules.ts
  ranking/
    rankDocument.ts
    rankProfiles.ts
    freshness.ts
    sourceAuthority.ts
    dedupe.ts
    explanations.ts
  retrieval/
    postings.ts
    phraseMatch.ts
    candidateSelection.ts
```

Recommended collection-indexer shape:

```text
tools/collection-indexer/src/njupt_search_indexer/
  enrich_dates.py
  enrich_intents.py
  build_ranking_features.py
  build_dedupe_clusters.py
```

Recommended config/eval shape:

```text
config/search/
  query_intents.json
  source_authority.json
  ranking_profiles.json

tools/search-eval/queries/
  student_task_queries.json
  expected_results.json
```

This is a target shape, not a mandate to create empty directories. Create files only when they remove real complexity or hold real production/eval logic.

## Required Data Model Improvements

Generated runtime documents and doc meta must expose enough structured fields for top-tier ranking.

Add or preserve, as appropriate:

- `source_id`
- `canonical_title`
- `published_at`
- `updated_at`
- `recorded_at`
- `version_date`
- `date_kind`
- `date_confidence`
- `academic_year`
- `term`
- `deadline`
- `valid_until`
- `task_kind`
- `authority_profile`
- `dedupe_key`

Important date semantics:

- `published_at`: article/page publish date.
- `updated_at`: page update date, if available.
- `recorded_at`: source package crawl/record time. Never treat as article freshness for normal ranking.
- `version_date`: version date inferred from title, attachment name, policy revision date, or form name.
- `deadline`: application/registration/submission deadline when extractable.
- `valid_until`: explicit or inferred expiry for notices and time-bounded tasks.

If a field cannot be reliably extracted, omit it or mark low confidence. Do not invent precise dates.

## Required Query Intent Profiles

Implement ranking profiles for at least these intents:

| Intent | Examples | Main Source Authority | Freshness Policy |
|---|---|---|---|
| `exam_schedule` | `期末考试`, `补考`, `重修考试`, `B250403` | `jwc`, exam vertical | current term dominant |
| `academic_calendar` | `校历`, `教学周历`, `放假安排` | `jwc` | latest academic year dominant |
| `system_entry` | `教务管理系统`, `双创信息管理系统`, `心理健康` | intent-specific | stable official entry; recency tiny |
| `form_download` | `缓考申请表`, `成绩复核申请表`, `xlsx` | intent-specific | form/version date |
| `academic_policy` | `转专业`, `推免`, `培养方案` | `jwc` | current policy + current notice |
| `course_grade_credit` | `选课`, `成绩`, `学分认定` | `jwc` | current term, but type-sensitive |
| `scholarship_aid` | `奖学金`, `助学金`, `困难认定` | `xsc` | latest notice/public announcement |
| `student_affairs` | `辅导员`, `心理咨询`, `宿舍`, `征兵`, `就业` | `xsc` | system or latest notice by query |
| `innovation_entrepreneurship` | `大创`, `互联网+`, `挑战杯`, `双创` | `cxcy` | current notice/system by query |
| `broad_exploratory` | `申请表`, `规章制度`, `竞赛`, `通知` | diversified | group and refine |

The UI may stay simple, but ranking behavior must reflect these profiles.

## Required Query Corpus Strategy

Treat `tools/search-eval/queries/student_task_queries.json` as a living corpus.

During the goal:

1. Validate its JSON structure.
2. Expand it when source-package research or failed searches reveal missing student wording.
3. Add expected-result assertions in `tools/search-eval/queries/expected_results.json` or an equivalent deterministic format.
4. Add an eval runner that reports:
   - Top1 pass rate
   - Top3 pass rate
   - MRR
   - failures grouped by intent
   - source/facet mismatch failures
   - stale-result failures
5. Keep smoke queries for fast gates, but add task-query eval as the real quality gate.

The query corpus should include Chinese campus terms, abbreviations, English abbreviations such as `MOOC` and `jwxt`, file-type queries, and broad exploratory queries.

## Required Ranking Behaviors

The final result must fix or explicitly justify these known baseline failures:

- `期末考试` must not rank 2013/2014 exam arrangements ahead of current relevant exam notices.
- `考试安排` must prefer current or latest term results.
- `竞赛报名` must not rank 2010 registration notices ahead of current competition notices.
- `大创` and `创新创业` must not be dominated by old `jwc` historical forms when `cxcy` is the stronger authority.
- `互联网+` must prefer `cxcy` current notices/results when available.
- `信息门户` must not degrade into broad `信息` hits.
- `申请表` must group or diversify rather than letting crawl-fresh external attachment records dominate.
- `学生相关文件及表格` must use form/version dates where extractable from titles or attachment names.
- `转专业` must surface current policy, current-term notice, and college details ahead of stale short section pages.
- `推免` must surface current-year work plans or current policy before old annual notices.
- `困难认定` must distinguish financial-aid hardship recognition from generic academic difficulty news.
- `B250403` must route to the exam vertical and surface the class exam view.

## Deletion And Refactor Permission

Be bold about removing obsolete compatibility paths and redundant logic when evidence shows they are no longer needed.

Allowed:

- Delete stale generated artifact path compatibility if all manifests, tests, and runtime code use the terminal path.
- Remove redundant aliases that harm ranking.
- Split large hard-coded ranking functions.
- Replace fragile string-prefix source inference with structured `source_id`.
- Add local helper modules when they clarify real behavior.
- Update tests and evals to encode the new intended behavior.

Not allowed:

- Revert unrelated user changes.
- Move upstream crawling or source-truth ownership into this repo.
- Hand-edit generated runtime JSON instead of updating generators and rebuilding.
- Add broad refactors that do not serve search quality, architecture clarity, or acceptance criteria.

## Implementation Checkpoints

Work continuously, but keep progress internally organized.

### Checkpoint 1: Baseline Audit

- Re-read current repo state and dirty worktree.
- Re-read source package manifests from sibling `njupt-site-graph`.
- Re-run or update local research scripts only as disposable cache artifacts.
- Record current eval failures before changes.

### Checkpoint 2: Contract And Generated Data

- Extend contracts for new structured fields.
- Update collection-indexer to emit fields.
- Rebuild generated collection artifacts from all three source packages.
- Validate aggregate and per-source truth counts.

### Checkpoint 3: Ranking And Retrieval

- Implement query intent classification.
- Implement ranking profiles.
- Implement source authority and date semantics.
- Implement dedupe/grouping where it materially improves first-screen results.
- Keep progressive search and full verification intact.

### Checkpoint 4: Evaluation

- Convert student query corpus into deterministic quality checks.
- Add expected results for critical P0/P1 queries.
- Make failures actionable with query, intent, expected source/facet/title/date, actual Top1/Top3, and reason.
- Keep fast smoke tests, but do not treat them as sufficient final quality.

### Checkpoint 5: UI And Explanation

- Keep UI restrained and task-oriented.
- Update guided query chips if they no longer match the ranking intent model.
- Ensure score reasons/explanations are truthful and useful.
- Do not add visible tutorial copy or marketing copy.

### Checkpoint 6: Browser Acceptance

Use the Codex internal browser/browser tool.

Minimum desktop and mobile checks:

- App loads without console errors.
- Manifest and generated artifacts load with no 404s.
- Worker reaches ready state.
- Progressive phases complete.
- Coverage reaches exhaustive completion for collection search.
- Exam vertical still works for `B250403`.
- Search results do not overlap or break layout.

Required manual/browser queries:

```text
校历
期末考试
考试安排
慕课考试
教务管理系统
信息门户
学生相关文件及表格
缓考申请表
成绩复核申请表
xlsx
B250403
转专业
推免
奖学金
助学金
困难认定
辅导员
心理健康
大创
创新创业
互联网+
竞赛报名
双创信息管理系统
```

### Checkpoint 7: Local Validation

Run from repo root in PowerShell:

```powershell
uv run python -m njupt_search_indexer validate --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\xsc\index --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\cxcy\index --skip-output
uv run python -m njupt_search_indexer build --collection-id njupt-public --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\xsc\index --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\cxcy\index --out apps\web\public\generated\collections\njupt-public
uv run python -m njupt_search_indexer validate --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\jwc\index --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\xsc\index --source-package D:\code\github\hicancan\njupt-site-graph\data\sites\cxcy\index --collection apps\web\public\generated\collections\njupt-public
uv run python tools\quality-gates\scripts\validate_search_index.py
uv run python tools\quality-gates\scripts\check_public_artifact_sizes.py
uv run python -m njupt_search_eval run-smoke-queries --collection apps\web\public\generated\collections\njupt-public
uv run python -m njupt_search_eval run-task-queries --collection apps\web\public\generated\collections\njupt-public
uv run python -m pytest
npm test
npm run typecheck
npm run lint
npm run build
```

If command names change during implementation, update this document or the final report with the actual equivalent command.

### Checkpoint 8: CI/CD

Ensure GitHub Actions include deterministic quality gates for:

- Python tests
- Node tests
- typecheck
- lint
- build
- generated artifact validation
- artifact size gates
- smoke queries
- task-query quality eval

Run or trigger the relevant workflows after pushing:

- `CI`
- `Validate Generated Artifacts`
- `Update Collection Index`, if generated collection changes need workflow validation
- `Deploy to GitHub Pages`, after main accepts the change

Cloud CI evidence is required. Local checks alone are not final acceptance.

### Checkpoint 9: Publish To Cloud Main

Final delivery requires the changes to reach the cloud `main` branch.

If direct push to `main` is allowed:

1. Ensure local branch is up to date.
2. Commit intentional changes.
3. Push to `main`.
4. Confirm cloud workflows pass on the pushed commit.

If branch protection blocks direct push:

1. Create a branch with prefix `main/`.
2. Push the branch.
3. Open a PR.
4. Wait for required checks.
5. Merge to `main`.
6. Confirm post-merge workflows and deployment pass.

Do not mark the goal complete before cloud main is green or before recording an exact external blocker that cannot be resolved locally.

## Final Definition Of Done

The goal is complete only when all are true:

1. Search remains a static, pure browser Worker product with progressive results and full verification.
2. Source truth still comes from audited `njupt-site-graph` packages.
3. Runtime documents expose structured source/date/task features needed by ranking.
4. Query intent and ranking profiles are implemented and tested.
5. Student task query corpus is maintained and used by deterministic evals.
6. P0/P1 known baseline failures are fixed or have evidence-backed product justifications.
7. Generated artifacts are rebuilt from source packages and validated.
8. Size budgets are adjusted only with evidence.
9. UI remains usable and browser-verified on desktop and mobile.
10. Local validation commands pass.
11. GitHub Actions/cloud CI pass.
12. Final changes are committed and present on cloud `main`.
13. Final report summarizes:
    - what changed
    - deleted obsolete compatibility paths
    - ranking/eval improvements
    - source package counts used
    - generated artifact summary
    - browser acceptance evidence
    - local test output summary
    - CI workflow links or exact blocker

If any required item remains incomplete, do not mark the goal complete.
