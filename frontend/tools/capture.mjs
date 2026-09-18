/* Capture every registered route at the four widths the brief names, as evidence and as references for a
   design-replication pass.

     node tools/capture.mjs                     # all routes, all widths -> UI_EVIDENCE_DIR
     node tools/capture.mjs --only overview,map  # a subset
     node tools/capture.mjs --out research/design-references --light-only

   The app must already be running (python3 -m weathergpt_data.workspace --port 8765): the page carries the
   per-process session token, so this script never starts its own server. */
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';
const OUT = process.env.UI_EVIDENCE_DIR || '../research/implementation/ui-evidence';
const VIEWPORTS = [
  { name: '1440', width: 1440, height: 833 },
  { name: '1024', width: 1024, height: 768 },
  { name: '768', width: 768, height: 1024 },
  { name: '390', width: 390, height: 844 },
];

/* The registry is the route list: a surface that is registered is a surface this tool knows about. */
const ROUTES = ['assistant', 'workspace', 'overview', 'warnings', 'map', 'forecast', 'observations', 'changes',
  'climate', 'advisories', 'air-quality', 'aviation', 'ensemble', 'verification', 'compare', 'marine',
  'documents', 'briefcase', 'settings'];

function arg(name, fallback = null) {
  const index = process.argv.indexOf('--' + name);
  return index === -1 ? fallback : (process.argv[index + 1] ?? true);
}

const only = String(arg('only', '') || '').split(',').map(part => part.trim()).filter(Boolean);
const outDir = path.resolve(String(arg('out', OUT)));
const colourSchemes = arg('light-only', false) ? ['light'] : ['light', 'dark'];
const routes = only.length ? ROUTES.filter(route => only.includes(route)) : ROUTES;

/* UI_CHANNEL=chrome drives the browser installed on this machine; otherwise Playwright's own Chromium. */
const CHANNEL = process.env.UI_CHANNEL || undefined;
const browser = await chromium.launch(CHANNEL ? { channel: CHANNEL } : {});
const report = [];
for (const scheme of colourSchemes) {
  for (const view of VIEWPORTS) {
    const context = await browser.newContext({
      viewport: { width: view.width, height: view.height }, deviceScaleFactor: 1,
      colorScheme: scheme, reducedMotion: 'reduce', locale: 'en-IN', timezoneId: 'Asia/Kolkata',
    });
    const page = await context.newPage();
    const failures = [];
    page.on('console', message => { if (message.type() === 'error') failures.push('console: ' + message.text().slice(0, 120)); });
    page.on('response', response => { if (response.status() >= 400) failures.push(response.status() + ' ' + response.url().replace(BASE, '')); });
    for (const route of routes) {
      await page.goto(BASE + '/#/' + route, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('main', { timeout: 30_000 }).catch(() => {});
      await page.waitForTimeout(1200);
      /* The workspace reads some sections only as they near the screen; a full-page shot must show them. */
      await page.evaluate(async () => {
        const step = Math.round(window.innerHeight * 0.8);
        const height = document.documentElement.scrollHeight;
        for (let y = 0; y < height; y += step) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); }
        window.scrollTo(0, 0);
      });
      await page.waitForTimeout(600);
      const file = path.join(outDir, scheme + '-' + route + '@' + view.name + '.png');
      await mkdir(path.dirname(file), { recursive: true });
      await page.screenshot({ path: file, fullPage: false });
      const metrics = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        heading: (document.querySelector('main h1') || {}).textContent || null,
        sections: document.querySelectorAll('main section').length,
      }));
      const overflow = metrics.scrollWidth - metrics.clientWidth;
      report.push({ scheme, width: view.width, route, file, overflow, heading: (metrics.heading || '').slice(0, 40), sections: metrics.sections, failures });
      console.log(scheme.padEnd(5), String(view.width).padStart(4), route.padEnd(13), 'overflow', String(overflow).padStart(3), '| sections', String(metrics.sections).padStart(2), '| failures', failures.length);
    }
    await context.close();
  }
}
await browser.close();
await mkdir(outDir, { recursive: true });
await writeFile(path.join(outDir, 'capture-report.json'), JSON.stringify(report, null, 1));
const bad = report.filter(row => row.overflow > 0 || row.failures.length);
console.log('\ncaptures:', report.length, '| with overflow or a failed request:', bad.length);
process.exit(bad.length ? 1 : 0);
