/* Capture one route across the whole day, at hours the sun actually stands at those altitudes.
   ============================================================================
   The palette is a continuous function of the sun's position, so a screenshot at the hour this machine
   happens to be in proves nothing about the other twenty-three. This tool installs a fixed clock in the
   page (Playwright's clock API, which replaces Date and setInterval before the bundle boots), so the
   spectrum is computed for the solar position at the instant asked for rather than for the instant the
   capture runs.

   Read the output rather than trusting it: every frame records the colours the elements themselves compute and
   whether they agree with the root, so a frame that does not differ from its neighbour is visible as a
   repeated colour state, and a palette that is written on one element and painted from another is visible as
   DIVERGENT.

       node tools/hours.mjs                                  # #/assistant, every two hours, local day
       node tools/hours.mjs --route overview --hours 6,12,18
       node tools/hours.mjs --place 9.93,76.26 --theme both
       node tools/hours.mjs --out ../research/reviews/x/hours

   The app must already be running; the page carries the per-process session token, so this script never
   starts its own server, exactly like capture.mjs. */
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';
const OUT = process.env.UI_HOURS_DIR || '../research/reviews/hours';

function arg(name, fallback = null) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : fallback;
}
const flag = name => process.argv.includes('--' + name);

const ROUTE = arg('route', 'assistant');
const THEMES = (arg('theme', 'dark') === 'both' ? ['dark', 'light'] : [arg('theme', 'dark')]);
const WIDTH = Number(arg('width', '1440'));
const HEIGHT = Number(arg('height', '900'));
const PLACE = arg('place', null);
const HOURS = (arg('hours', null) || Array.from({ length: 12 }, (_, i) => String(i * 2))).split(',').map(Number);

/* The date the sweep is drawn for. Fixed rather than today so two runs of this tool are comparable:
   a July sweep and a January sweep stand the sun at genuinely different altitudes at the same clock
   hour, and the evidence is worth more when it says which one it is. */
const DATE = arg('date', '2026-09-21');
const TZ = arg('tz', 'Asia/Kolkata');

function address() {
  const hash = '#' + ROUTE + (PLACE ? `?place=${encodeURIComponent(arg('place-name', 'Held place'))}&plat=${PLACE.split(',')[0]}&plon=${PLACE.split(',')[1]}` : '');
  return BASE + '/' + hash;
}

/* Asia/Kolkata is UTC+05:30 all year, and the sweep is drawn for that offset so "12" means noon in
   the place the product is built for rather than noon on the machine that ran the capture. */
function instantAt(hour) {
  const hh = String(hour).padStart(2, '0');
  return new Date(`${DATE}T${hh}:00:00+05:30`);
}

const sleep = ms => new Promise(done => setTimeout(done, ms));

async function main() {
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch();
  const rows = [];
  for (const theme of THEMES) {
    for (const hour of HOURS) {
      const context = await browser.newContext({
        viewport: { width: WIDTH, height: HEIGHT },
        deviceScaleFactor: 1,
        colorScheme: theme,
        locale: 'en-IN',
        timezoneId: TZ,
        reducedMotion: 'reduce',
      });
      const page = await context.newPage();
      /* install() must run before the bundle: it replaces Date, setTimeout and setInterval in the page,
         so the spectrum's own minute timer and its first paint both run at the instant asked for. */
      await page.clock.install({ time: instantAt(hour) });
      await page.goto(address(), { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1200);
      await page.clock.runFor(2000);
      /* The page's own computed values, read from the element that actually PAINTS each property rather than
         from the document element. A custom property can be declared on any element, and a declaration on a
         descendant beats the inline style on `<html>`: this tool used to read the root, so it reported a
         continuous drift that no reader could see while `.g` re-declared every value from the static hour
         block (docs/134). Both readings are printed, so a divergence between the writer and the page shows up
         in this tool's own output instead of only in a browser. */
      const measured = await page.evaluate(() => {
        const rootStyle = getComputedStyle(document.documentElement);
        const at = (selector) => {
          const el = document.querySelector(selector);
          return el ? getComputedStyle(el) : null;
        };
        const readOn = (el, name) => (el ? el.getPropertyValue(name).trim() : '');
        const readRoot = name => rootStyle.getPropertyValue(name).trim();
        const field = at('.g-field-sky');
        const rail = at('.g-rail');
        const bar = at('.g-top');
        const side = at('.g-panel-side');
        const hour = document.documentElement.getAttribute('data-hour');
        const gAttr = document.querySelector('.g')?.getAttribute('data-hour') ?? null;
        const painted = name => readOn(field, name) || readOn(rail, name) || readRoot(name);
        const divergent = [
          ['--g-sky-1', readRoot('--g-sky-1'), painted('--g-sky-1')],
          ['--g-rail-fill', readRoot('--g-rail-fill'), readOn(rail, '--g-rail-fill') || readRoot('--g-rail-fill')],
          ['--g-bar-fill', readRoot('--g-bar-fill'), readOn(bar, '--g-bar-fill') || readRoot('--g-bar-fill')],
          ['--g-paper', readRoot('--g-paper'), readRoot('--g-paper')],
        ].filter(([, wrote, shows]) => wrote !== shows).map(([name, wrote, shows]) => `${name}: root ${wrote} vs page ${shows}`);
        return {
          dataHour: hour,
          gDataHour: gAttr,
          bg: readRoot('--g-bg'),
          paper: readRoot('--g-paper'),
          mist: readRoot('--g-mist'),
          accent: readRoot('--g-accent'),
          sky: painted('--g-sky-1'),
          skyPainted: readOn(field, '--g-sky-1'),
          railFill: readOn(rail, '--g-rail-fill'),
          barFill: readOn(bar, '--g-bar-fill'),
          bubbleFill: readRoot('--g-bubble-fill'),
          paneFill: readRoot('--g-pane-fill'),
          sideFill: readOn(side, '--g-rail-fill'),
          halo: readRoot('--g-halo-x') + ' ' + readRoot('--g-halo-y'),
          divergent,
          title: document.title,
        };
      });
      const name = `${ROUTE}@${WIDTH}-${String(hour).padStart(2, '0')}-${theme}.png`;
      await page.screenshot({ path: path.join(OUT, name), animations: 'disabled' });
      rows.push({ hour, theme, file: name, ...measured });
      const warn = measured.divergent.length ? '  DIVERGENT(' + measured.divergent.join('; ') + ')' : '';
      console.log(`${theme} ${String(hour).padStart(2, '0')}:00  ${ROUTE}  hour=${measured.dataHour}  sky=${measured.sky}  bg=${measured.bg}  accent=${measured.accent}`)
      console.log(`         rail=${measured.railFill}  bar=${measured.barFill}  bubble=${measured.bubbleFill}${warn}`);
      await context.close();
    }
  }
  await browser.close();
  await writeFile(path.join(OUT, 'hours-report.json'),
    JSON.stringify({ base: BASE, route: ROUTE, place: PLACE, date: DATE, timezone: TZ, frames: rows }, null, 2));
  const state = r => [r.sky, r.bg, r.accent, r.railFill, r.barFill, r.bubbleFill].join('|');
  const distinct = new Set(rows.map(state));
  const diverged = rows.filter(r => r.divergent.length);
  console.log(`\nframes: ${rows.length} | distinct colour states: ${distinct.size}`);
  if (distinct.size !== rows.length) console.log('NOTE: some frames repeat a state - check the hours before quoting this as a drift.');
  console.log(diverged.length
    ? `NOTE: ${diverged.length} frame(s) where the root and the painted element disagree - the reader is not seeing the spectrum there.`
    : 'root and painted element agree at every frame.');
  if (!flag('quiet')) console.log('written to ' + path.resolve(OUT));
}

main();
