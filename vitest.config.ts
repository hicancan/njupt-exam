import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'url';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './apps/web/src'),
      '@njupt-search/contracts/exam': path.resolve(__dirname, './packages/contracts/src/exam/index.ts'),
      '@njupt-search/contracts/search-index': path.resolve(__dirname, './packages/contracts/src/search-index/index.ts'),
      '@njupt-search/contracts/source-sitegraph': path.resolve(__dirname, './packages/contracts/src/source-sitegraph/index.ts'),
      '@njupt-search/contracts': path.resolve(__dirname, './packages/contracts/src/index.ts'),
      '@njupt-search/exam-core/calendar': path.resolve(__dirname, './packages/exam-core/src/calendar/index.ts'),
      '@njupt-search/exam-core/contract': path.resolve(__dirname, './packages/exam-core/src/contract/index.ts'),
      '@njupt-search/exam-core/search': path.resolve(__dirname, './packages/exam-core/src/search/index.ts'),
      '@njupt-search/exam-core': path.resolve(__dirname, './packages/exam-core/src/index.ts'),
      '@njupt-search/search-core': path.resolve(__dirname, './packages/search-core/src/index.ts'),
    },
  },
  test: {
    include: [
      'apps/web/src/**/*.test.{ts,tsx}',
      'packages/**/*.test.{ts,tsx}',
    ],
  },
});
