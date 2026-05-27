# Contracts Package

Runtime and generated-artifact contract package.

It owns:

- exam data types and schemas used by `packages/exam-core`;
- source-sitegraph input contracts;
- search collection manifests and search index artifact contracts;
- shared runtime types used by the web app, search core, tests, and quality gates.

The current web app still imports shared types through `apps/web/src/types/index.ts` until the app is split in later milestones.
