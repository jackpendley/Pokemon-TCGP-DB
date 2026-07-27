import { defineConfig, devices } from "@playwright/test";

const PORT = 3210;

/**
 * E2E smoke tests.
 *
 * Runs against `next build && next start` rather than `next dev`, because the
 * things worth guarding here are production behaviours: PPR static shells,
 * streaming boundaries, and the cached reads. Dev renders differently.
 *
 * DATA_SOURCE is left unset so the app reads local-json artifacts — no Supabase
 * and no owner session, which means these cover the public read path only.
 * Authenticated flows (sync, deck writes) need a seeded test user and are a
 * documented follow-up.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "line" : "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    // iPhone viewport + touch, but on Chromium: the mobile UI under test is
    // layout and gesture behaviour, not WebKit quirks, and this keeps CI to a
    // single browser download.
    {
      name: "mobile",
      use: { ...devices["iPhone 14"], browserName: "chromium" },
    },
  ],
  webServer: {
    command: `npm run build && npx next start --port ${PORT}`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
