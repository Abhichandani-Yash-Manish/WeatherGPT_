import { chromium } from '@playwright/test';

/* Capture a route at the widths the brief names. The app must already be running
   (python3 -m weathergpt_data.workspace --port 8765): the page carries the per-process session token, so
   this script never starts its own server.

   A shot may carry "iso": an instant to pin the page's clock to. The light layer is a function of place and
   time, so a pinned clock is the only way to photograph dawn at noon. A pinned shot is a design render, not
   a claim about what the page looked like at that hour, and callers name the file accordingly. */
const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';
const OUT = process.env.OUT || '../research/design/ui-audit-20260918';
const shots = JSON.parse(process.env.SHOTS || '[]');

const browser = await chromium.launch({ channel: 'chrome' });
for (const shot of shots) {
  const context = await browser.newContext({
    viewport: { width: shot.width, height: shot.height },
    colorScheme: shot.scheme || 'light',
    locale: 'en-IN',
    timezoneId: 'Asia/Kolkata',
    /* Reduced motion is the default because a screenshot must not depend on when it was taken. A shot that
       wants to measure the animation asks for movement explicitly. */
    reducedMotion: shot.motion ? 'no-preference' : 'reduce',
  });
  if (shot.iso) {
    await context.addInitScript(({ iso }) => {
      const fixed = new Date(iso).getTime();
      const Real = Date;
      class Pinned extends Real {
        constructor(...args) {
          if (args.length === 0) super(fixed);
          else super(...args);
        }
        static now() {
          return fixed;
        }
      }
      window.Date = Pinned;
    }, { iso: shot.iso });
  }
  const page = await context.newPage();
  await page.goto(BASE + shot.path, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(shot.wait ?? 2600);
  /* A shot may place the pointer, or place it and click, so a capture can show a reactive field rather than
     assert one. */
  if (shot.pointer) {
    await page.mouse.move(shot.pointer.x, shot.pointer.y, { steps: 12 });
    await page.waitForTimeout(500);
  }
  /* A shot may ask a question, so the conversation state can be captured as it really is rather than styled
     into existence. It types into the page's own question box and presses Ask. */
  if (shot.ask) {
    /* The question box is whichever the shell mounts: the older surface labelled it "Your question", the
       flagship composer labels the placeholder and the send button. Both are accepted so a capture script is
       not a reason to keep a label. */
    const box = page.getByLabel('Your question');
    if (await box.count()) await box.fill(shot.ask);
    else await page.getByPlaceholder('Ask about a place and a time…').fill(shot.ask);
    const ask = page.getByRole('button', { name: 'Ask' });
    if (await ask.count()) await ask.click();
    else await page.getByRole('button', { name: 'Send' }).click();
    await page.waitForTimeout(shot.askWait ?? 9000);
  }
  if (shot.click) {
    await page.mouse.move(shot.click.x, shot.click.y, { steps: 8 });
    await page.mouse.down();
    await page.mouse.up();
    await page.waitForTimeout(shot.click.wait ?? 260);
  }
  await page.screenshot({ path: OUT + '/' + shot.name + '.png', fullPage: Boolean(shot.full) });
  await context.close();
  console.log('shot', shot.name, shot.iso ? '(clock pinned to ' + shot.iso + ')' : '(live clock)');
}
await browser.close();
