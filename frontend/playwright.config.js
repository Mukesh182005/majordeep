// Browser end-to-end tests (npm run e2e). See e2e/README in the project README.
//
// By default this starts its own backend (uvicorn, SQLite, analysis inline, a fresh temporary
// storage tree) on port 8100 and the Vite dev server on port 3100, so it never touches the
// development database or a running app. Set E2E_BASE_URL to test an already running site
// instead (for example the docker stack: E2E_BASE_URL=http://localhost:8080).
import { defineConfig, devices } from '@playwright/test'
import os from 'node:os'
import path from 'node:path'

const external = process.env.E2E_BASE_URL
const tmp = path.join(os.tmpdir(), `deepsentinel-e2e-${process.pid}`)
const python = process.env.E2E_PYTHON
  || path.join('..', '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')

const backendEnv = {
  ...process.env,
  ENVIRONMENT: 'development',
  DATABASE_URL: `sqlite:///${path.join(tmp, 'e2e.db').replace(/\\/g, '/')}`,
  STORAGE_DIR: path.join(tmp, 'uploads'),
  EVIDENCE_DIR: path.join(tmp, 'evidence'),
  REPORT_DIR: path.join(tmp, 'reports'),
  CELERY_BROKER_URL: '',
  CELERY_RESULT_BACKEND: '',
  JWT_SECRET_KEY: 'e2e-secret-not-for-production',
  MAX_UPLOAD_MB: '5',
  UPLOAD_RATE_LIMIT_PER_HOUR: '1000',
  GUEST_RATE_LIMIT_PER_HOUR: '1000',
  DEVICE: process.env.DEVICE || 'cpu',
  HF_HUB_DISABLE_SYMLINKS_WARNING: '1',
}

export default defineConfig({
  testDir: './e2e',
  timeout: 10 * 60 * 1000,
  expect: { timeout: 15 * 1000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: external || 'http://127.0.0.1:3100',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: external
    ? undefined
    : [
        {
          command: `"${python}" -m uvicorn app.main:app --host 127.0.0.1 --port 8100`,
          cwd: path.join('..', 'backend'),
          url: 'http://127.0.0.1:8100/api/health',
          env: backendEnv,
          timeout: 5 * 60 * 1000,
          reuseExistingServer: false,
          stdout: 'ignore',
          stderr: 'pipe',
        },
        {
          command: 'npm run dev -- --port 3100 --strictPort --host 127.0.0.1',
          url: 'http://127.0.0.1:3100',
          env: { ...process.env, VITE_API_TARGET: 'http://127.0.0.1:8100' },
          timeout: 2 * 60 * 1000,
          reuseExistingServer: false,
        },
      ],
})
