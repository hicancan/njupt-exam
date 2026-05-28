# ADR 0010: Isolate Exam Source Acquisition

## Status

Accepted.

## Context

`exam` is a product vertical in `njupt-search`, not a `sitegraph` source package. The current exam pipeline still discovers JWC exam notices and downloads spreadsheet attachments before producing generated exam artifacts.

## Decision

Keep the current JWC exam discovery and download code isolated inside `tools/exam-pipeline` as a temporary acquisition adapter. It may write only generated exam artifacts under `apps/web/public/generated/exam`. It must not feed the collection compiler, change source-of-truth ownership for sitegraph packages, or become part of browser runtime search.

Future work should move exam source discovery and audit ownership upstream or expose it as an audited source package. `njupt-search` should then consume that package and keep only transformation, validation, UI, search, and calendar export responsibilities.

## Consequences

- The collection path remains audited source package -> collection compiler -> browser runtime artifacts.
- Exam source discovery remains explicitly quarantined until it can be upstreamed.
- Documentation and workflows must describe exam as a vertical and not as a `sitegraph` source.
