/**
 * Browser journeys on the local stack: the built frontend, the real backend
 * over HTTP and local Supabase, with deterministic stand-ins for the model
 * provider and the public geocoders. How to run them: docs/deployment.md,
 * "Local end-to-end checks".
 */

import { defineConfig, devices } from "@playwright/test";
import { API_URL, APP_URL, loadStatus } from "./e2e/stack";

const statusPath = process.env.E2E_SUPABASE_STATUS_ENV;
const status = loadStatus(statusPath);
const inherited = Object.fromEntries(
  Object.entries(process.env).filter((entry): entry is [string, string] => entry[1] !== undefined),
);

export default defineConfig({
  testDir: "e2e",
  testMatch: "**/*.e2e.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 120_000,
  reporter: [["list"]],
  use: { ...devices["Desktop Chrome"], baseURL: APP_URL, trace: "retain-on-failure" },
  webServer: [
    {
      command: ".venv/bin/python -m tests.e2e.serve",
      cwd: "../backend",
      url: `${API_URL}/api/health`,
      env: { ...inherited, SUPABASE_STATUS_ENV: statusPath as string },
      timeout: 120_000,
      reuseExistingServer: false,
      stdout: "pipe",
    },
    {
      command: "npm run build && npx vite preview --host 127.0.0.1 --port 4173 --strictPort",
      url: APP_URL,
      env: {
        ...inherited,
        VITE_API_URL: API_URL,
        VITE_SUPABASE_URL: status.API_URL,
        VITE_SUPABASE_ANON_KEY: status.ANON_KEY,
      },
      timeout: 180_000,
      reuseExistingServer: false,
    },
  ],
});
