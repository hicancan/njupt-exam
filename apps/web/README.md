# Web App

This directory owns the React/Vite/PWA product after Milestone 5.

Current boundary:

- `src/` owns the current web UI, hooks, Worker integration, and temporary compatibility facades into `packages/*`.
- `index.html` and `vite.config.ts` are the Vite entry and PWA configuration.
- Root `public/` remains the public runtime directory until the generated artifact layout migration milestone. This preserves existing `/data/*` and `/index/*` URLs and current update workflows.
- Root `dist/` remains the build output consumed by GitHub Pages deployment.

Use the root npm scripts for development and validation so CI behavior remains stable.
