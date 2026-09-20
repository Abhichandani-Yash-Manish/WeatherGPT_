/* What a printed answer carries, and why.
   ============================================================================
   A closed <details> is a click on screen and a missing paragraph on paper, and the rest of the answer is a
   closed fold (docs/136). This asks a real question, renders the page to PDF with Chromium's own print
   layout, and measures IN print media what the fold, the summary and a user-agent-only closed details do -
   because the claim is about a user agent's behaviour and not about the stylesheet's contents.

     UI_BASE_URL=http://127.0.0.1:8790 UI_EVIDENCE_DIR=/abs/path node tools/capture-print.mjs
     .venv/bin/python tmp/print-text.py <the pdf>      # the PDF's own text, with pypdf

   The workspace must already be running: the page carries a per-process session token. */
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8790';
const OUT = path.resolve(process.env.UI_EVIDENCE_DIR || '../research/reviews/final-overhaul-20260921/chat');
const QUESTION = process.env.UI_QUESTION || 'Will it rain in Ahmedabad tomorrow?';

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1024, height: 900 }, colorScheme: 'dark', locale: 'en-IN', timezoneId: 'Asia/Kolkata' });
const page = await context.newPage();
await page.goto(BASE + '/#/assistant', { waitUntil: 'domcontentloaded' });
await page.getByLabel('Your question').fill(QUESTION);
await page.getByTestId('send-question').click();
await page.locator('.g-answer').last().waitFor({ state: 'visible', timeout: 180_000 });
await page.waitForTimeout(1200);

await mkdir(OUT, { recursive: true });
const file = path.join(OUT, 'printed-answer.pdf');
await page.pdf({ path: file, format: 'a4' });

/* Print media, measured in the page. A user-agent-only closed fold is added beside the card so what the
   engine does by itself is separated from what chat.css asks for. */
await page.emulateMedia({ media: 'print' });
const report = await page.evaluate(() => {
  const card = document.querySelectorAll('.g-answer');
  const last = card[card.length - 1];
  const rest = last && last.querySelector('.answer-rest');
  const summary = rest && rest.querySelector('summary');
  const body = rest && rest.querySelector('.g-fold-body');
  const probe = document.createElement('details');
  probe.innerHTML = '<summary>a fold this card did not write</summary><div id="ua-only">the user agent owns this list</div>';
  document.body.appendChild(probe);
  const ua = document.getElementById('ua-only');
  const box = (node) => {
    if (!node) return null;
    const rect = node.getBoundingClientRect();
    return { display: getComputedStyle(node).display, width: Math.round(rect.width), height: Math.round(rect.height) };
  };
  const result = {
    summary: box(summary),
    foldBody: box(body),
    foldBodyContentVisibility: body ? getComputedStyle(body).contentVisibility : null,
    uaClosedFoldContent: box(ua),
    screenOnlyControls: box(last && last.querySelector('.no-print')),
    recordRendered: Boolean(last && last.querySelector('.machine-record')),
    lead: box(last && last.querySelector('.answer-lead')),
  };
  probe.remove();
  return result;
});
await page.emulateMedia({ media: null });
await writeFile(path.join(OUT, 'printed-answer.json'), JSON.stringify({ question: QUESTION, file, printMedia: report }, null, 1));
await browser.close();
console.log(JSON.stringify(report, null, 1));
