/* The UI/UX harness: one place to screenshot, audit and pixel-compare the running workspace.

   The app is served by the Python workspace (no dev proxy, the session token comes from the served page), so
   these tests do not start a server of their own. Point them at one with UI_BASE_URL; the default is the
   application on 8765. Reference images for a design-replication pass live in UI_REFERENCE_DIR, named
   <route>@<width>.png, and are compared by tools/fidelity.mjs. */
import { defineConfig, devices } from '@playwright/test';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';
/* UI_CHANNEL=chrome uses the browser installed on this machine; without it Playwright's own Chromium is used.
   Both are fine for this work; the installed Chrome is what the reader actually looks at. */
const CHANNEL = process.env.UI_CHANNEL || undefined;

/* The four widths the project's own brief names, plus the two colour schemes the app ships. */
export const VIEWPORTS = [
  { name: 'desktop-1440', width: 1440, height: 833 },
  { name: 'laptop-1024', width: 1024, height: 768 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'phone-390', width: 390, height: 844 },
];

export default defineConfig({
  testDir: './tests/ui',
  timeout: 90_000,
  expect: { timeout: 15_000, toHaveScreenshot: { maxDiffPixelRatio: 0.002, animations: 'disabled' } },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: '../research/implementation/ui-evidence/playwright-report.json' }]],
  use: {
    baseURL: BASE,
    ...(CHANNEL ? { channel: CHANNEL } : {}),
    locale: 'en-IN',
    timezoneId: 'Asia/Kolkata',
    colorScheme: 'light',
    deviceScaleFactor: 1,
    /* Animations and the aurora field move; a screenshot must not depend on when it was taken. */
    reducedMotion: 'reduce',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    ...VIEWPORTS.map(view => ({ name: view.name, use: { ...devices['Desktop Chrome'], viewport: { width: view.width, height: view.height } } })),
  ],
});
