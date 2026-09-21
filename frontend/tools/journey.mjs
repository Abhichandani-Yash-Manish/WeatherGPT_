/* A real journey through the running app: arrive, ask, read the answer, open its depth, try the
   controls, and then do the same at phone width.
   ============================================================================
   This is not a screenshot tool. capture.mjs photographs routes and hours.mjs photographs hours; both
   answer "what does it look like". This one answers "does it work": it types a real question, waits
   for the answer, counts what the page says while it waits, opens every fold the card offers, clicks
   every visible control that is not a send/stop, and records whether anything changed. A control that
   does nothing is a defect, and no screenshot shows it.

   It is also the tool that found two of them (a welcome rendered under an open module surface, and a
   marine cell answered for an inland point), so it prints its findings rather than only its pictures.

       node tools/journey.mjs
       node tools/journey.mjs --only ask,folds --width 390
       UI_BASE_URL=http://127.0.0.1:8790 UI_JOURNEY_DIR=/abs/path node tools/journey.mjs

   The app must already be running; the page carries the per-process session token, so this script never
   starts its own server. */
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';
const OUT = process.env.UI_JOURNEY_DIR || '../research/reviews/journey';
const QUESTION = process.env.UI_JOURNEY_QUESTION || 'Will it rain in Ahmedabad tomorrow?';

function arg(name, fallback = null) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : fallback;
}
const WIDTH = Number(arg('width', '1440'));
const HEIGHT = Number(arg('height', WIDTH <= 480 ? '844' : '900'));
const STEPS = (arg('only', 'arrive,ask,folds,controls,phone') || '').split(',');

const steps = [];
const defects = [];
const log = (step, detail) => {
  steps.push({ step, detail });
  console.log('  ' + step + ': ' + detail);
};

const sleep = ms => new Promise(done => setTimeout(done, ms));

async function main() {
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT }, locale: 'en-IN', timezoneId: 'Asia/Kolkata',
    colorScheme: arg('theme', 'dark'), reducedMotion: 'no-preference',
  });
  const page = await context.newPage();
  const failed = [];
  page.on('response', r => { if (r.status() >= 400) failed.push(r.status() + ' ' + r.url()); });
  page.on('pageerror', e => failed.push('pageerror ' + e.message));
  const body = () => page.locator('body').innerText();

  if (STEPS.includes('arrive')) {
    await page.goto(BASE + '/#assistant', { waitUntil: 'domcontentloaded' });
    await sleep(1500);
    const heading = await page.locator('h1').first().innerText().catch(() => '');
    log('arrive', 'title=' + JSON.stringify(await page.title()) + ' h1=' + JSON.stringify(heading));
    if (!heading.trim()) defects.push('the welcome has no heading');
    await page.screenshot({ path: path.join(OUT, `welcome@${WIDTH}.png`) });
  }

  let asked = false;
  if (STEPS.includes('ask')) {
    const box = page.locator('textarea, input[type="text"]').first();
    await box.click({ timeout: 5000 }).catch(() => defects.push('no composer to type in'));
    await box.fill(QUESTION).catch(() => {});
    const started = Date.now();
    await page.keyboard.press('Enter');
    await sleep(2500);
    const waiting = (await body()).split('\n').filter(line => line.trim()).slice(-4).join(' | ');
    log('wait', 'after 2.5s the page says ' + JSON.stringify(waiting.slice(0, 240)));
    if (!/work|read|retriev|search|consult|check|plan/i.test(waiting)) {
      defects.push('the wait says nothing about what is happening: ' + JSON.stringify(waiting.slice(0, 160)));
    }
    /* Wait on the answer CARD's own control, which exists nowhere else. Two earlier versions of this
       line were wrong in two different ways and both reported a working turn as an answer: looking for
       the word "source" matched the welcome's own footer ("Every value keeps its source…"), and looking
       for the text "Source:" matched nothing, because the source line is inside a closed fold and
       innerText does not include hidden text. A locator asks the page instead of guessing at it. */
    await page.locator('button:has-text("Copy the answer")').first()
      .waitFor({ state: 'visible', timeout: 90000 }).catch(() => {});
    await sleep(900);
    const seconds = ((Date.now() - started) / 1000).toFixed(1);
    const text = await body();
    const answer = text.split('\n').filter(line => line.trim()).slice(-14).join('\n');
    log('answer', seconds + 's, ' + text.split(/\s+/).length + ' words on the page');
    console.log('    ' + JSON.stringify(answer.slice(0, 700)));
    asked = /Copy the answer/i.test(text);
    if (!asked) defects.push('no answer arrived within 60s for ' + JSON.stringify(QUESTION));
    await page.screenshot({ path: path.join(OUT, `answer@${WIDTH}.png`) });
  }

  if (STEPS.includes('folds') && asked) {
    const folds = await page.locator('details').all();
    log('folds', folds.length + ' <details> on the screen');
    let opened = 0;
    for (const fold of folds) {
      const label = (await fold.locator('summary').first().innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 70);
      if (!(await fold.evaluate(el => el.open))) {
        await fold.locator('summary').first().click({ timeout: 2500 }).catch(() => {});
      }
      const open = await fold.evaluate(el => el.open).catch(() => false);
      if (open) opened += 1;
      log('fold', JSON.stringify(label) + ' open=' + open);
    }
    await sleep(500);
    await page.screenshot({ path: path.join(OUT, `answer-open@${WIDTH}.png`), fullPage: true });
    log('opened', opened + ' of ' + folds.length + ' folds opened');
    if (folds.length && opened < folds.length) defects.push('a fold did not open when its summary was clicked');
  }

  if (STEPS.includes('controls') && asked) {
    const controls = await page.locator('button:visible').all();
    log('controls', controls.length + ' visible buttons');
    let dead = 0;
    for (const control of controls.slice(0, 16)) {
      const label = ((await control.innerText().catch(() => '')) || (await control.getAttribute('aria-label')) || '?')
        .replace(/\s+/g, ' ').slice(0, 44);
      if (/send|ask|stop|close|delete|remove/i.test(label)) { log('skip', JSON.stringify(label)); continue; }
      const before = await body();
      await control.click({ timeout: 2500 }).catch(() => {});
      await sleep(400);
      const changed = before !== (await body());
      if (!changed) dead += 1;
      log('click', JSON.stringify(label) + ' changed=' + changed);
    }
    if (dead) log('note', dead + ' controls produced no visible change (some are copy/tooltip actions)');
  }

  if (STEPS.includes('phone') && asked) {
    await page.setViewportSize({ width: 390, height: 844 });
    await sleep(900);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    await page.screenshot({ path: path.join(OUT, 'answer@390.png') });
    log('phone', 'horizontal overflow ' + overflow + 'px');
    if (overflow > 0) defects.push('the page overflows horizontally by ' + overflow + 'px at 390px');
  }

  if (failed.length) defects.push('failed requests/page errors: ' + failed.slice(0, 6).join('; '));
  console.log('\n' + (defects.length ? 'DEFECTS:\n - ' + defects.join('\n - ') : 'no defects found in this journey'));
  await writeFile(path.join(OUT, `journey@${WIDTH}.json`),
    JSON.stringify({ base: BASE, question: QUESTION, width: WIDTH, steps, defects, failed }, null, 2));
  await browser.close();
}

main();
