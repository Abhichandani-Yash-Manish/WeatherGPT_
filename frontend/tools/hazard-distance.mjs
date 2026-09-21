/* How far the interface's own materials stand from the four published hazard colours, hour by hour.
   ============================================================================
   The product's rule is that red, orange, yellow and green reach a reader only through a value a source
   printed, and that interface state never borrows them. The spectrum proves it never READS those tokens;
   this measures the other half, which a token check cannot: whether a material the reader sees next to a
   warning chip is close enough to one of the four to be mistaken for it. Colour distance is computed in
   OKLab and reported as ΔE (×100), with the hue angle, because a yellow film at dawn and the IMD yellow
   can be far apart in one and near in the other.

       node tools/hazard-distance.mjs                      # every hour, dark and light
       node tools/hazard-distance.mjs --route warnings --hours 5,6,7,18

   The app must already be running. Exit code is 0 always: this prints evidence, it does not gate. */
import { chromium } from '@playwright/test';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';

function arg(name, fallback = null) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : fallback;
}
const ROUTE = arg('route', 'assistant');
const HOURS = (arg('hours', null) || Array.from({ length: 24 }, (_, i) => String(i))).split(',').map(Number);
const DATE = arg('date', '2026-09-21');

/* OKLab, from the published conversion; written out rather than imported so this tool has no dependency
   on the code it is checking. */
function srgbToLinear(c) {
  const v = c / 255;
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
}
function hexToRgb(hex) {
  const h = hex.trim().replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
function rgba(text) {
  const m = /rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,/\s]+([\d.]+))?\)/.exec(text || '');
  if (!m) return null;
  return { rgb: [Number(m[1]), Number(m[2]), Number(m[3])], a: m[4] === undefined ? 1 : Number(m[4]) };
}
/** A translucent film composited over what is behind it. Comparing a film's own RGB to a solid colour
    is the mistake this function exists to prevent. */
function over(film, ground) {
  if (!film) return null;
  return film.rgb.map((c, i) => c * film.a + ground[i] * (1 - film.a));
}
function oklab(rgb) {
  const [r, g, b] = rgb.map(srgbToLinear);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
          1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
          0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
}
const deltaE = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]) * 100;
const chroma = lab => Math.hypot(lab[1], lab[2]) * 100;
const hue = lab => (Math.atan2(lab[2], lab[1]) * 180) / Math.PI;

async function main() {
  const browser = await chromium.launch();
  const worst = [];
  console.log('hour  ground      material   closest hazard      dE     dChroma  dHue');
  for (const theme of ['dark', 'light']) {
    for (const hour of HOURS) {
      const context = await browser.newContext({
        viewport: { width: 1440, height: 900 }, colorScheme: theme, locale: 'en-IN',
        timezoneId: 'Asia/Kolkata', reducedMotion: 'reduce',
      });
      const page = await context.newPage();
      await page.clock.install({ time: new Date(`${DATE}T${String(hour).padStart(2, '0')}:00:00+05:30`) });
      await page.goto(BASE + '/#' + ROUTE, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(900);
      await page.clock.runFor(2000);
      const read = await page.evaluate(() => {
        const root = getComputedStyle(document.documentElement);
        const g = n => root.getPropertyValue(n).trim();
        const field = document.querySelector('.g-field-sky');
        const rail = document.querySelector('.g-rail, .g-rail-scroll, .g-rail-nav');
        const bar = document.querySelector('.g-topbar, .g-bar');
        const bubble = document.querySelector('.g-bubble-user, .g-bubble');
        const own = el => (el ? getComputedStyle(el) : root);
        const grab = (el, names) => names.map(n => own(el).getPropertyValue(n).trim()).find(v => v) || '';
        return {
          hour: document.documentElement.getAttribute('data-hour'),
          bg: g('--g-bg'), paper: g('--g-paper'),
          sky: grab(field, ['--g-sky-1']) || g('--g-sky-1'),
          rail: grab(rail, ['--g-rail-fill', '--g-rail-tint']),
          bar: grab(bar, ['--g-bar-fill', '--g-bar-tint']),
          bubble: grab(bubble, ['--g-bubble-fill', '--g-bubble-tint']),
          hazard: { red: g('--g-red'), orange: g('--g-orange'), yellow: g('--g-yellow'), green: g('--g-green') },
        };
      });
      const ground = hexToRgb(read.bg || '#000000');
      const materials = { rail: read.rail, bar: read.bar, bubble: read.bubble };
      for (const [name, value] of Object.entries(materials)) {
        const solid = over(rgba(value), ground);
        if (!solid) continue;
        const lab = oklab(solid);
        let best = null;
        for (const [hazard, hex] of Object.entries(read.hazard)) {
          const h = oklab(hexToRgb(hex));
          const d = deltaE(lab, h);
          if (!best || d < best.d) best = { hazard, d, dC: Math.abs(chroma(lab) - chroma(h)), dH: Math.abs(hue(lab) - hue(h)) };
        }
        worst.push({ theme, hour, hour_band: read.hour, material: name, ...best, colour: solid.map(Math.round) });
        if (best.d < 25 || (best.dC < 8 && best.dH < 20)) {
          console.log(`${String(hour).padStart(2, '0')}:00 ${theme.padEnd(5)} ground=${read.bg} ${name.padEnd(7)} ${best.hazard.padEnd(6)} `
            + `dE=${best.d.toFixed(1)} dC=${best.dC.toFixed(1)} dH=${best.dH.toFixed(1)} rgba(${solid.map(Math.round).join(',')})`);
        }
      }
      await context.close();
    }
  }
  await browser.close();
  const exact = worst.filter(w => w.d < 10);
  const tilted = worst.filter(w => w.dC < 8 && w.dH < 20);
  console.log(`\n${worst.length} material-hours measured`);
  console.log(`within 10 dE of a published hazard colour: ${exact.length}` + (exact.length
    ? ' — ' + exact.map(w => `${w.theme} ${String(w.hour).padStart(2, '0')}:00 ${w.material}~${w.hazard} dE=${w.d.toFixed(1)}`).join('; ') : ''));
  console.log(`same chroma AND hue family as one (dC<8, dH<20): ${tilted.length}` + (tilted.length
    ? ' — ' + tilted.map(w => `${w.theme} ${String(w.hour).padStart(2, '0')}:00 ${w.material}~${w.hazard} dC=${w.dC.toFixed(1)} dH=${w.dH.toFixed(1)}`).join('; ') : ''));
  const closest = worst.sort((a, b) => a.d - b.d).slice(0, 5);
  console.log('closest five overall:');
  for (const w of closest) console.log(`  ${w.theme} ${String(w.hour).padStart(2, '0')}:00 ${w.material} ~ ${w.hazard} dE=${w.d.toFixed(1)} rgba(${w.colour.join(',')})`);
}

main();
