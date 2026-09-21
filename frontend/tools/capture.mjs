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

/* The place's own page is a shell route rather than a surface (docs/122): it is reached by an address that
   names a place, it has no rail row, and the registry above cannot derive it. It is named here by address,
   in both the states a reader can land on, because a page the evidence tool cannot see is a page with no
   evidence - and this one is the destination every place link in the product points at.

   An entry is a hash fragment plus the name its files take: an address carries a question mark and a file
   name should not. */
/* What "still reading" looks like on any surface: the shared skeleton the Evidence module draws, and the
   district map's own pending frame, which is a different element because it waits on geometry rather than
   on a reading. A capture waits for both to leave the page. */
const PENDING = '[data-testid="skeleton"], [data-testid="risk-map-pending"]';

const ADDRESSES = [
  { name: 'place', hash: 'place?place=Kochi,%20Kerala&plat=9.93&plon=76.26' },
  { name: 'place-refused', hash: 'place?place=Kochi,%20Kerala&plat=9.93' },
  /* An ANSWERED TURN. Every other entry here photographs a surface at rest, so until now the one
     thing this product actually is - a question with an answer under it - had no picture anywhere in
     the evidence, and two sessions in a row reported a colour change they could not check against
     the reader's own bubble or the answer's claims. `ask=` is the same seeding address every place
     link and every surface's "Ask instead" row already uses, so this captures the real path.

     It costs a live turn: the model plans it, the tools retrieve it and the model writes it, which
     is why this one entry waits for a claim to appear rather than for a fixed delay. */
  { name: 'answer', hash: 'assistant?ask=' + encodeURIComponent('Will it rain in Ahmedabad tomorrow?'),
    /* Both, in this order: the turn stops working, and THEN the answer finishes being written onto the
       page. An answer arrives whole and checked and is revealed at reading pace, so waiting only for the
       working state to detach photographs a sentence caught halfway through. */
    settleGone: '.g-working, [data-revealing]' },
];

function arg(name, fallback = null) {
  const index = process.argv.indexOf('--' + name);
  return index === -1 ? fallback : (process.argv[index + 1] ?? true);
}

const only = String(arg('only', '') || '').split(',').map(part => part.trim()).filter(Boolean);
const outDir = path.resolve(String(arg('out', OUT)));
const colourSchemes = arg('light-only', false) ? ['light'] : ['light', 'dark'];
const targets = ROUTES.map(id => ({ name: id, hash: id })).concat(ADDRESSES);
const routes = only.length ? targets.filter(target => only.includes(target.name)) : targets;

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
    let failures = [];
    page.on('console', message => { if (message.type() === 'error') failures.push('console: ' + message.text().slice(0, 120)); });
    page.on('response', response => { if (response.status() >= 400) failures.push(response.status() + ' ' + response.url().replace(BASE, '')); });
    for (const route of routes) {
      failures = [];
      await page.goto(BASE + '/#/' + route.hash, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('main', { timeout: 30_000 }).catch(() => {
        failures.push('main did not appear within 30 seconds');
      });
      /* A route that names what it is waiting for waits for that. A turn takes as long as the model
         and the sources take, and a fixed delay photographs the thinking state instead - which is
         exactly what the first version of this did. It waits for the WORKING state to go away rather
         than for a claim to appear, because a restored conversation already has claims on the page
         and the wait returned instantly against one of those. */
      if (route.settleGone) {
        await page.waitForSelector(route.settleGone, { state: 'detached', timeout: 120_000 }).catch(() => {
          failures.push(route.settleGone + ' did not settle within 120 seconds');
        });
      }
      /* And EVERY route waits for its read to land, named or not. Measured 21 September 2026: the fixed
         1200 ms below is shorter than a surface's first read of the local store, so every module capture
         in the evidence directory - all eighteen of them, in both schemes and four widths - photographed
         the skeleton bars and the "Reading ... from the local store" line rather than the surface. Two
         sessions reviewed those files as if they showed the product.

         The short pause first is the point: `state: 'detached'` is satisfied by a selector that has not
         mounted YET, so checking the instant the route changes returns before React has rendered the
         pending state and waits for nothing. */
      await page.waitForTimeout(500);
      await page.waitForSelector(PENDING, { state: 'detached', timeout: 60_000 }).catch(() => {
        failures.push('pending state did not settle within 60 seconds');
      });
      await page.waitForTimeout(1200);
      /* The workspace reads some sections only as they near the screen; a full-page shot must show them. */
      await page.evaluate(async () => {
        const step = Math.round(window.innerHeight * 0.8);
        const height = document.documentElement.scrollHeight;
        for (let y = 0; y < height; y += step) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); }
        window.scrollTo(0, 0);
      });
      await page.waitForTimeout(600);
      const file = path.join(outDir, scheme + '-' + route.name + '@' + view.name + '.png');
      await mkdir(path.dirname(file), { recursive: true });
      await page.screenshot({ path: file, fullPage: false });
      const metrics = await page.evaluate(() => {
        const clientWidth = document.documentElement.clientWidth;
        /* The document's own scrollWidth is not enough, and believing it cost this product a broken phone
           layout for as long as the tool has existed. Measured 21 September 2026: `#main` is a flex item
           and a flex item's min-width is `auto`, so it refused to shrink under the district x day matrix
           and stood 812px wide inside a 390px viewport. It SCROLLS inside the viewport rather than pushing
           the document, so documentElement.scrollWidth equalled clientWidth and this line printed 0 while
           every sentence on the surface was cut off mid-word.

           So the measure is the widest right edge of anything the reader can see, counted against the
           viewport. Two things are not defects and are not counted. An element deliberately parked
           off-screen, hence the left >= 0 test. And a wide table inside a scroll box: it is SUPPOSED to
           extend past its container, that is what the box is for, and the reader scrolls it - so every
           right edge is first clipped by each ancestor the reader can SCROLL - `auto` or `scroll`, and
           only those.

           `hidden` and `clip` are deliberately not in that list, and the difference is the whole point of
           the measure. A scroll box means the reader can reach the rest of the table. A clipping ancestor
           means the rest is simply gone off the edge, which is the defect being looked for - the shell's
           own wrapper carries `overflow-x: clip`, so counting it as containment made this check report a
           clean zero for the exact broken layout it was written to catch. */
        let spill = 0;
        let widest = null;
        for (const node of document.querySelectorAll('main *')) {
          const box = node.getBoundingClientRect();
          if (box.width === 0 || box.height === 0 || box.left < 0) continue;
          let right = box.right;
          for (let parent = node.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
            const flow = getComputedStyle(parent).overflowX;
            if (flow !== 'auto' && flow !== 'scroll') continue;
            right = Math.min(right, parent.getBoundingClientRect().right);
          }
          const over = Math.round(right - clientWidth);
          if (over > spill) { spill = over; widest = node.tagName.toLowerCase() + '.' + String(node.className || '').slice(0, 40); }
        }
        return {
          clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
          spill, widest,
          heading: (document.querySelector('main h1') || {}).textContent || null,
          sections: document.querySelectorAll('main section').length,
        };
      });
      /* Whichever is worse: the document pushed wide, or content spilling past the edge inside it. */
      const overflow = Math.max(metrics.scrollWidth - metrics.clientWidth, metrics.spill);
      report.push({ scheme, width: view.width, route: route.name, file, overflow, spilledFrom: metrics.widest, heading: (metrics.heading || '').slice(0, 40), sections: metrics.sections, failures: [...failures] });
      console.log(scheme.padEnd(5), String(view.width).padStart(4), route.name.padEnd(13), 'overflow', String(overflow).padStart(4), '| sections', String(metrics.sections).padStart(2), '| failures', failures.length, overflow > 0 ? '| from ' + metrics.widest : '');
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
