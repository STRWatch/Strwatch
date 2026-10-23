import { defineConfig, configDefaults } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['__tests__/setup.ts'],
    // Playwright specs live in e2e/ and must not be run by vitest.
    // Spread the defaults so node_modules/.next etc. stay excluded.
    exclude: [...configDefaults.exclude, 'e2e/**'],
    // No unit tests exist yet (the only one tested a deleted module); keep `npm test` green.
    passWithNoTests: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
