import { chromium } from '@playwright/test';

/* Does the drawn layer cost the reader anything?
   ----------------------------------------------------------------------------
   The chat face runs two animation loops — the printed field at twelve frames a second and the diorama at
   eight — so the question worth answering is not "is it pretty" but "does the browser still deliver frames".
   This counts the frames the browser actually paints over three seconds with the face open, at the two widths
   the brief names, and prints them. A number near sixty means the loops are not in the way; a number far below
   it means the motion is being paid for by the reader's scrolling and typing.

   Run against a served build:  node tools/motion-probe.mjs */
const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';
const browser = await chromium.launch({ channel: 'chrome' });
for (const width of [1440, 390]) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'no-preference' });
  const page = await context.newPage();
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);
  const frames = await page.evaluate(
    () =>
      new Promise(resolve => {
        let count = 0;
        const started = performance.now();
        const step = () => {
          count += 1;
          if (performance.now() - started < 3000) requestAnimationFrame(step);
          else resolve(count);
        };
        requestAnimationFrame(step);
      }),
  );
  console.log(width + 'px: ' + frames + ' frames in 3s (' + Math.round(frames / 3) + ' fps delivered)');
  await context.close();
}
await browser.close();
