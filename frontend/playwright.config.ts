import { defineConfig, devices } from '@playwright/test';
import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = dirname(__filename);

// Load BACKEND_PORT and other vars from root .env (written by uvicorn on startup).
// No external dotenv dependency — simple KEY=VALUE parser.
const envPath = resolve(__dirname, '../.env');
if (existsSync(envPath)) {
  for (const line of readFileSync(envPath, 'utf-8').split('\n')) {
    const m = line.match(/^([A-Z_]+)=(.+)$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].trim();
  }
}

const BACKEND_PORT  = process.env.BACKEND_PORT  ?? '8001';
const FRONTEND_PORT = process.env.FRONTEND_PORT ?? '5173';

// Fail loudly if BACKEND_PORT is missing (no silent wrong-port tests)
if (!process.env.BACKEND_PORT) {
  console.warn('[playwright] BACKEND_PORT not found in .env — using default 8001');
}

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
