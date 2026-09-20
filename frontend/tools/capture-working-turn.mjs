/* Capture the wait: a real turn in flight, so the orb is seen rather than asserted.
   ============================================================================
   tools/capture.mjs captures routes at rest. A working turn is not a route - it exists only between a reader's
   question and the answer - so it needs its own capture: ask a question, wait for the working turn to appear,
   and shoot the whole column while the engine is still reading. Two modes, because the orb's accessible
   behaviour is one of the things worth seeing: the default (animated) and prefers-reduced-motion (a static
   representative frame, which is what the library promises and what this proves).

     UI_BASE_URL=http://127.0.0.1:8781 node tools/capture-working-turn.mjs
     UI_BASE_URL=... UI_REDUCED_MOTION=reduce node tools/capture-working-turn.mjs

   The workspace must already be running: the page carries a per-process session token, so this never starts
   its own server. */
import AxeBuilder from '@axe-core/playwright';
import { chromium } from '@playwright/test';
import { createHash } from 'node:crypto';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';
const OUT = path.resolve(process.env.UI_EVIDENCE_DIR || '../research/implementation/ui-evidence');
const MOTION = process.env.UI_REDUCED_MOTION === 'reduce' ? 'reduce' : 'no-preference';
const QUESTION = process.env.UI_QUESTION || 'Will it rain in Kochi tomorrow morning?';
const WIDTHS = [1440, 390];

const browser = await chromium.launch();
const report = [];
for (const width of WIDTHS) {
  const context = await browser.newContext({
    viewport: { width, height: width > 500 ? 833 : 844 }, deviceScaleFactor: 1,
    colorScheme: 'dark', reducedMotion: MOTION, locale: 'en-IN', timezoneId: 'Asia/Kolkata',
  });
  const page = await context.newPage();
  const failures = [];
  page.on('console', message => { if (message.type() === 'error') failures.push('console: ' + message.text().slice(0, 120)); });
  await page.goto(BASE + '/#/assistant', { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Your question').fill(QUESTION);
  await page.getByTestId('send-question').click();
  const working = page.getByTestId('working-turn');
  await working.waitFor({ state: 'visible', timeout: 20_000 });
  /* The orb is a canvas inside .g-orb; its presence and its box are what is being checked, not its pixels. */
  await page.locator('.g-orb canvas').first().waitFor({ state: 'visible', timeout: 10_000 });
  const orbBox = await page.locator('.g-orb canvas').first().boundingBox();
  const stage = (await page.locator('.g-working-stage').first().textContent()) || '';
  await mkdir(OUT, { recursive: true });
  const file = path.join(OUT, 'working-turn-' + (MOTION === 'reduce' ? 'reduced' : 'animated') + '@' + width + '.png');
  await page.screenshot({ path: file, fullPage: false });

  /* The library promises two opposite behaviours, and both are checkable rather than assertable: under the */
  /* default preference the orb animates, and under reduce it draws ONE static representative frame. Two */
  /* clipped shots of the orb tell them apart - a moving orb changes between them, a static one cannot. */
  const digest = async () => createHash('sha256')
    .update(await page.locator('.g-orb canvas').first().screenshot())
    .digest('hex').slice(0, 16);
  const first = await digest();
  await page.waitForTimeout(450);
  const second = await digest();

  /* Accessibility during the wait, which no route-level pass can see: the orb exists only between a question
     and its answer. The canvas is aria-hidden on purpose (the stage word beside it is the live region, so the
     stage is announced once), and this is what checks that the pair of them is clean while a turn runs. */
  const axe = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
    .analyze();
  const violations = axe.violations.map(violation => violation.id + ' (' + violation.nodes.length + ')');
  const moved = first !== second;
  const wanted = MOTION === 'reduce' ? false : true;
  const behaviour = moved === wanted ? 'as promised' : 'NOT as promised';
  report.push({ width, motion: MOTION, stage: stage.trim(), orb: orbBox && { w: orbBox.width, h: orbBox.height }, moved, violations, file, failures });
  console.log(String(width).padStart(4), 'stage "' + stage.trim() + '"', '| orb', orbBox ? orbBox.width + 'x' + orbBox.height : 'MISSING',
    '| frames', moved ? 'differ' : 'identical', '->', behaviour,
    '| axe', violations.length ? violations.join(', ') : 'clean', '| failures', failures.length);
  await context.close();
}
await browser.close();
const bad = report.filter(row => !row.orb || row.failures.length || row.moved !== (MOTION !== 'reduce') || row.violations.length);
console.log('captures:', report.length, '| without an orb, with a failure, or moving against the preference:', bad.length);
console.log(MOTION === 'reduce'
  ? 'reduce asked: every frame must be identical - a static representative frame, not a frozen animation'
  : 'no preference asked: every frame must differ - an orb that never moves is a still image in a wait');
process.exit(bad.length ? 1 : 0);
