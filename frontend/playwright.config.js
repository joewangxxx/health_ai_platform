import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

const frontendRoot = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(frontendRoot, '..')
const liveBackendDbDir = path.join(frontendRoot, '.tmp')
const liveBackendDbPath = path.join(liveBackendDbDir, 'playwright-live-e2e.db')
const pythonShimDir = path.join(frontendRoot, 'tests', 'python-shims')

fs.mkdirSync(liveBackendDbDir, { recursive: true })
fs.mkdirSync(pythonShimDir, { recursive: true })

const sqliteUrl = `sqlite:///${liveBackendDbPath.replace(/\\/g, '/')}`

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: 'python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000',
      cwd: repoRoot,
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: true,
      timeout: 180000,
      stdout: 'ignore',
      stderr: 'pipe',
      env: {
        PYTHONUTF8: '1',
        PYTHONPATH: pythonShimDir,
        OPENAI_API_KEY: '',
        SQLALCHEMY_DATABASE_URI: sqliteUrl,
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 4173',
      cwd: frontendRoot,
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: true,
      timeout: 120000,
      stdout: 'ignore',
      stderr: 'pipe',
      env: {
        VITE_API_BASE_URL: 'http://127.0.0.1:8000',
      },
    },
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], channel: 'msedge' },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
})
