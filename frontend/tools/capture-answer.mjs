/* Capture an answer as a reader meets it.
   ============================================================================
   tools/capture.mjs shoots routes at rest and tools/capture-working-turn.mjs shoots the wait; neither sees
   the thing this batch is about - the answer card after a real question against the running engine. This
   asks the question, waits for the card, and shoots the first screen and the card itself, so the shape can
   be looked at rather than asserted.

     UI_BASE_URL=http://127.0.0.1:8790 UI_EVIDENCE_DIR=/abs/path node tools/capture-answer.mjs
     UI_QUESTION="Will it rain in Ahmedabad tomorrow?" UI_TAG=before node tools/capture-answer.mjs

   The workspace must already be running: the page carries a per-process session token. */
import AxeBuilder from '@axe-core/playwright';
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8790';
const OUT = path.resolve(process.env.UI_EVIDENCE_DIR || '../research/reviews/final-overhaul-20260921/chat');
const TAG = process.env.UI_TAG || 'answer';
const QUESTION = process.env.UI_QUESTION || 'Will it rain in Ahmedabad tomorrow?';
const FOLLOW = process.env.UI_FOLLOW || '';
const WIDTHS = (process.env.UI_WIDTHS || '1440,390').split(',').map(Number);
const SCHEME = process.env.UI_SCHEME || 'dark';

const browser = await chromium.launch();
const report = [];
for (const width of WIDTHS) {
  const context = await browser.newContext({
    viewport: { width, height: width > 500 ? 900 : 844 }, deviceScaleFactor: 1,
    colorScheme: SCHEME, reducedMotion: 'reduce', locale: 'en-IN', timezoneId: 'Asia/Kolkata',
  });
  const page = await context.newPage();
  const failures = [];
  page.on('console', message => { if (message.type() === 'error') failures.push('console: ' + message.text().slice(0, 160)); });
  page.on('response', response => { if (response.status() >= 400) failures.push(response.status() + ' ' + response.url().replace(BASE, '')); });
  await page.goto(BASE + '/#/assistant', { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Your question').fill(QUESTION);
  await page.getByTestId('send-question').click();
  const card = page.locator('.g-answer').last();
  await card.waitFor({ state: 'visible', timeout: 180_000 });
  await page.waitForTimeout(900);
  if (FOLLOW) {
    await page.getByLabel('Your question').fill(FOLLOW);
    await page.getByTestId('send-question').click();
    await page.locator('.g-answer').nth(1).waitFor({ state: 'visible', timeout: 180_000 });
    await page.waitForTimeout(900);
  }
  await mkdir(OUT, { recursive: true });
  /* The page scrolls itself to the newest turn; the first screen of an answer is only visible if the answer
     is put at the top deliberately. The question is left just above it, because that is what a reader sees. */
  await page.evaluate(() => {
    const cards = document.querySelectorAll('.g-answer');
    const last = cards[cards.length - 1];
    const question = last && last.previousElementSibling;
    const anchor = question && question.getBoundingClientRect().height < 200 ? question : last;
    if (!anchor) return;
    /* The transcript scrolls in an inner container, not the window, so every scrollable ancestor is walked. */
    for (let node = anchor.parentElement; node; node = node.parentElement) {
      if (node.scrollHeight > node.clientHeight + 4) {
        const delta = anchor.getBoundingClientRect().top - node.getBoundingClientRect().top;
        node.scrollTop += delta - 8;
      }
    }
    anchor.scrollIntoView({ block: 'start' });
  });
  await page.waitForTimeout(400);
  const file = path.join(OUT, TAG + '-' + width + '.png');
  await page.screenshot({ path: file, fullPage: false });
  const cardFile = path.join(OUT, TAG + '-card-' + width + '.png');
  await page.locator('.g-answer').last().screenshot({ path: cardFile });
  /* What the first screen actually holds, in the reader's own element order. */
  const outline = await page.evaluate(() => {
    const answer = document.querySelectorAll('.g-answer');
    const last = answer[answer.length - 1];
    if (!last) return null;
    const rows = [];
    for (const node of last.querySelectorAll('h2, p, summary, button, details, section, li')) {
      if (node.tagName === 'P' && node.closest('summary')) continue;
      if (node.tagName === 'LI' && node.closest('details')) continue;
      const own = Array.from(node.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
      if (!own && !['DETAILS', 'SECTION', 'BUTTON'].includes(node.tagName)) continue;
      const box = node.getBoundingClientRect();
      rows.push({ tag: node.tagName, cls: node.className.toString().slice(0, 44), text: (own || node.textContent.trim()).replace(/\s+/g, ' ').slice(0, 110), top: Math.round(box.top), h: Math.round(box.height) });
    }
    return rows.slice(0, 46);
  });
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']).analyze();
  const violations = axe.violations.map(v => v.id + ' (' + v.nodes.length + ')');
  console.log(String(width).padStart(4), '| axe', violations.length ? violations.join(', ') : 'clean', '| failures', failures.length);
  report.push({ width, question: QUESTION, follow: FOLLOW || null, file, cardFile, axe: violations, failures, outline });
  await context.close();
}
await browser.close();
await writeFile(path.join(OUT, TAG + '-report.json'), JSON.stringify(report, null, 1));
for (const row of report) {
  console.log('\n=== ' + row.width + ' ===');
  for (const node of row.outline || []) console.log(String(node.top).padStart(5), node.tag.padEnd(7), node.cls.padEnd(46), node.text);
}
