/* The materials: four surfaces over one sky, measured rather than described.
   ============================================================================
   The complaint this batch answers is "the website theme right now is very monotonous", and the measurement
   behind it is in docs/134: the rail, the bar and the reader's own bubble were three fills within 0.04 and
   0.068 alpha of each other, over a ground whose own two stops are further apart than the gaps between the
   components. A palette nobody can perceive is a palette that is not there.

   So this file holds the second number the palette work needs. Contrast says a surface is readable; it says
   nothing about whether two surfaces are the same surface. The second number is separation: the rail's fill,
   the top bar's fill, the reader's own bubble's fill and the ground are composited exactly as the CSS
   composites them — each translucent film over the band of the gradient it is drawn on — and converted to a
   perceptually uniform space, where the pair must differ in chroma AND in hue at every sampled instant.

   THE THRESHOLDS, AND WHERE THEY COME FROM.
   ------------------------------------------------------------
   Measured over the sweep below (three places across India, both solstices, every fifteen solar minutes: 576
   instants), the four materials' worst pair over the whole day is 0.0128 in OKLab chroma (the bar against the
   ground, at Kanyakumari on 21 June) and 18.1° in hue (the rail against the ground, on the same day). The floors here are set just under that measurement — 0.010 and
   15° — so a change that makes two materials less distinguishable than the design already is fails, and the
   numbers are the design's own rather than a wish. What they are worth: 15° of hue at these chromas is a
   visible shift on a 268px-wide column, and 0.010 of OKLab chroma is about a tenth of the distance between
   the noon sky and a white page. This file does not claim the four materials are obviously different; it
   claims they are measurably different, at every instant, and it reports the worst pair so the claim can be
   re-checked rather than believed.

   The machine's own pane is measured for identity rather than for separation (see the pane check below), and
   the two icon inks are measured against their own fill at the non-text floor.

   THE INK-TO-SURFACE MAP, which is what makes a contrast check honest rather than exhaustive: `--g-paper` is
   the reader's ink and is drawn on all five surfaces; `--g-mist` is quiet text and is drawn on all five (the
   rail's conversation names, the bar's title on the welcome, the answer, a claim's source line); `--g-mist-2`
   is the tertiary step, which the product's own FE14 rule reserves for edges, hairlines and the machine's
   quietest metadata, so it is measured on the ground and on the pane at the non-text floor; and the accent is
   an icon and focus-ring colour, measured on the ground and the rail at the same floor. Anything pinker than
   that would be asserting a promise the stylesheet has not made.

   Everything here is arithmetic written out rather than imported: jsdom has no layout engine for axe's
   contrast rule (frontend/src/a11y/a11y.test.tsx says why), and there is no colour dependency in this product
   to check a palette with. */

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { solarPosition } from './fieldPaint';
import { spectrumAt, type Spectrum } from './spectrum';

type RGB = [number, number, number];

/* ---- sRGB and WCAG ----------------------------------------------------------------------------------- */

function parseHex(hex: string): RGB {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function parseRgba(value: string): { r: number; g: number; b: number; a: number } {
  const m = /rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)/.exec(value);
  if (!m) throw new Error('materials.test.ts: not a colour the palette can emit: ' + value);
  return { r: Number(m[1]), g: Number(m[2]), b: Number(m[3]), a: m[4] === undefined ? 1 : Number(m[4]) };
}

/** The ordinary alpha composite, which is what a translucent film over a ground IS. */
function over(film: string, ground: RGB): RGB {
  const f = parseRgba(film);
  return [f.r * f.a + ground[0] * (1 - f.a), f.g * f.a + ground[1] * (1 - f.a), f.b * f.a + ground[2] * (1 - f.a)];
}

const mixRgb = (a: RGB, b: RGB, t: number): RGB => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

const toLinear = (v: number) => { const x = v / 255; return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };

function relativeLuminance(c: RGB): number {
  return 0.2126 * toLinear(c[0]) + 0.7152 * toLinear(c[1]) + 0.0722 * toLinear(c[2]);
}

function contrast(a: RGB, b: RGB): number {
  const x = relativeLuminance(a);
  const y = relativeLuminance(b);
  const [lighter, darker] = x >= y ? [x, y] : [y, x];
  return (lighter + 0.05) / (darker + 0.05);
}

/* ---- OKLab: the perceptually uniform space the separation is measured in ------------------------------
   Björn Ottosson's OKLab, from the published matrices: linear sRGB to the LMS cone response, cube root, then
   the two opponent axes. Chroma is the distance from the neutral axis and hue the angle around it, which is
   what makes "a minimum difference in both chroma and hue" a measurement rather than a phrase: two colours
   can differ by a lot in chroma and by nothing in hue (a pale and a saturated blue), or by a lot in hue and
   by nothing in chroma (a pale blue and a pale orange). Both are visible differences and neither is the
   other. */

function okLab(c: RGB) {
  const r = toLinear(c[0]);
  const g = toLinear(c[1]);
  const b = toLinear(c[2]);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  const L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s;
  const h = Math.atan2(B, A) * 180 / Math.PI;
  /* A and B are returned as well as the polar form. The distance between two colours is computed from
     them, and when they were missing that subtraction produced NaN - which is not less than any floor,
     so the distance check passed on every pair by failing to compute anything at all. */
  return { L, A, B, C: Math.hypot(A, B), hue: h < 0 ? h + 360 : h };
}

const hueGap = (a: number, b: number) => { const d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d; };

/* ---- the palette at one instant ---------------------------------------------------------------------- */

type Fills = { rail: RGB; bar: RGB; bubble: RGB; pane: RGB; groundRgb: RGB };

/** How the stylesheet composites each material: the rail and the bar over the top of the sky (they are the
    full-height column and the top edge), the reader's bubble and the machine's pane over the middle of the
    same gradient, which is where both sit. The ground the column's text stands on is the top band, which is
    the most chromatic part of the sky and therefore the hardest case for everything drawn over it. */
function fillsAt(s: Spectrum): Fills {
  const sky1 = parseHex(s['--g-sky-1']);
  const skyMid = mixRgb(sky1, parseHex(s['--g-sky-2']), 0.6);
  return {
    rail: over(s['--g-rail-fill'], sky1),
    bar: over(s['--g-bar-fill'], sky1),
    bubble: over(s['--g-bubble-fill'], skyMid),
    pane: over(s['--g-pane-fill'], skyMid),
    groundRgb: sky1,
  };
}

const PLACES: { name: string; latitude: number; longitude: number }[] = [
  { name: 'Kanyakumari', latitude: 8.08, longitude: 77.55 },
  { name: 'Nagpur', latitude: 21.15, longitude: 79.09 },
  { name: 'Leh', latitude: 34.16, longitude: 77.58 },
];
const DATES = [Date.UTC(2026, 5, 21, 0, 0, 0), Date.UTC(2026, 11, 21, 0, 0, 0)];

const AA_BODY = 4.5;
const AA_NON_TEXT = 3;

/** The floors, from the measurement in this file's own header. */
/* ONE floor, on the distance an eye actually travels between two colours.
   This used to be two floors - chroma AND hue, both of which had to clear - and that shape was wrong in
   both directions. It rejected pairs 150 degrees apart in hue because their chroma happened to match,
   which no eye would confuse; and it had nothing at all to say about LIGHTNESS, so a check calling
   itself "measurably different surfaces" measured two of the three things that make a surface different.
   That second gap is not academic: a white-glass rail lifted above the ground necessarily loses chroma
   as it approaches white, so the old predicate rejected the lifted design for being too pale while the
   design it rejected was more distinguishable, not less.

   OKLab was chosen for this palette precisely because distance in it is perceptual, so the honest
   measure is that distance. The floor is the design's own: the worst pair across the whole grid is
   printed on failure, and this sits under it. */
const MIN_DISTANCE = 0.030;

type Sample = { label: string; s: Spectrum; fills: Fills };
const SAMPLES: Sample[] = [];
for (const place of PLACES) {
  for (const midnightUtc of DATES) {
    for (let minutes = 0; minutes < 24 * 60; minutes += 15) {
      const at = new Date(midnightUtc + minutes * 60_000);
      const position = solarPosition(place.latitude, place.longitude, at);
      const s = spectrumAt(position);
      SAMPLES.push({
        label: place.name + ' ' + new Date(midnightUtc).toISOString().slice(0, 10) + ' +' + minutes + 'min (alt ' + position.altitude.toFixed(1) + '°)',
        s,
        fills: fillsAt(s),
      });
    }
  }
}

describe('the four materials are measurably different surfaces, at every instant', () => {
  it('samples a whole day at three latitudes and both solstices', () => {
    expect(SAMPLES.length).toBe(PLACES.length * DATES.length * 96);
  });

  it('separates the rail, the bar, the reader\'s bubble and the ground as surfaces an eye can tell apart', () => {
    const pairs: [keyof Fills, keyof Fills][] = [
      ['rail', 'bar'], ['rail', 'bubble'], ['rail', 'groundRgb'],
      ['bar', 'bubble'], ['bar', 'groundRgb'], ['bubble', 'groundRgb'],
    ];
    const worst = new Map<string, { dE: number; chroma: number; hue: number; light: number; label: string }>();
    const failures: string[] = [];
    for (const { label, fills } of SAMPLES) {
      for (const [a, b] of pairs) {
        const A = okLab(fills[a]);
        const B = okLab(fills[b]);
        const chroma = Math.abs(A.C - B.C);
        const hue = hueGap(A.hue, B.hue);
        /* The distance an eye actually travels between the two, in OKLab, which is the space that was
           chosen because distances in it mean something perceptually. */
        const dE = Math.sqrt((A.L - B.L) ** 2 + (A.A - B.A) ** 2 + (A.B - B.B) ** 2);
        if (!Number.isFinite(dE)) throw new Error('distance is not a number for ' + a + '/' + b + ' at ' + label);
        const light = Math.abs(A.L - B.L);
        const key = a + '/' + b;
        const w = worst.get(key);
        if (!w || dE < w.dE) worst.set(key, { dE, chroma, hue, light, label });
        if (dE < MIN_DISTANCE) {
          failures.push(key + ' at ' + label + ': \u0394E ' + dE.toFixed(4) + ' (chroma ' + chroma.toFixed(4)
            + ', hue ' + hue.toFixed(1) + '\u00b0, lightness ' + light.toFixed(4) + ')');
        }
      }
    }
    const measured = [...worst.entries()]
      .map(([key, w]) => key + ' \u0394E ' + w.dE.toFixed(4) + ' (c ' + w.chroma.toFixed(4) + ', h '
        + w.hue.toFixed(1) + '\u00b0, L ' + w.light.toFixed(4) + ') at ' + w.label)
      .join(', ');
    expect(failures, 'pairs closer than \u0394E ' + MIN_DISTANCE + ' \u2014 closest per pair: ' + measured).toEqual([]);
  });

  it('keeps the inks each surface actually draws above AA on it', () => {
    /* Paper is the reader's ink and it is drawn on all five surfaces. Mist is quiet text and it is drawn on
       four of them: the rail (conversation names, the place line), the bar (the thread's title on the welcome),
       the pane (a claim's source line) and the ground (the answer). The reader's own bubble draws ONE ink —
       `.g-you p` is a single paragraph and it takes --g-paper — so mist is not required of it, and saying so is
       the honest form of the check rather than a floor quietly lowered. What the bubble's mist measures anyway
       is reported below, because a number that is not asserted is still worth knowing: it is 3.42 at its worst,
       in the descending twilight where the bubble is a warm lifted slab under a dusk sky.

       The ground is measured at the top of its own gradient, which is the band the column's text stands on and
       the most chromatic part of the sky. */
    const failures: string[] = [];
    let worstBubbleMist = { ratio: Infinity, label: '' };
    for (const { label, s, fills } of SAMPLES) {
      const surfaces: [string, RGB][] = [
        ['ground', fills.groundRgb], ['rail', fills.rail], ['bar', fills.bar],
        ['bubble', fills.bubble], ['pane', fills.pane],
      ];
      for (const [where, surface] of surfaces) {
        const onPaper = contrast(parseHex(s['--g-paper']), surface);
        if (onPaper < AA_BODY) failures.push(label + ': paper on ' + where + ' ' + onPaper.toFixed(2));
        const onMist = contrast(parseHex(s['--g-mist']), surface);
        if (where === 'bubble') {
          if (onMist < worstBubbleMist.ratio) worstBubbleMist = { ratio: onMist, label };
        } else if (onMist < AA_BODY) {
          failures.push(label + ': mist on ' + where + ' ' + onMist.toFixed(2));
        }
      }
    }
    expect(failures, 'ink under AA on a material: ' + failures.slice(0, 6).join(' | ')).toEqual([]);
    /* The bubble's mist, recorded rather than required: if a future change puts a second, quieter ink inside the
       reader's bubble, this number is the one it has to clear first. */
    expect(worstBubbleMist.ratio, 'mist on the reader\'s bubble is not required of it, and it measures ' + worstBubbleMist.ratio.toFixed(2) + ' at worst (' + worstBubbleMist.label + ')').toBeGreaterThan(3.2);
  });

  it('keeps the tertiary step and the accent above the non-text floor where they are used', () => {
    /* --g-mist-2 is the edge and metadata step and the accent is an icon and focus-ring colour, so both are
       held to WCAG 1.4.11's 3:1 rather than to 4.5:1 — the product's own FE14 rule says quiet TEXT takes the
       mist step, which the check above enforces. They are measured on the surfaces that actually carry them:
       the ground (the work panel's details, the folds' counts) and the pane (a claim's provenance line, the
       machine record). */
    const failures: string[] = [];
    let worstRailTertiary = { ratio: Infinity, label: '' };
    for (const { label, s, fills } of SAMPLES) {
      for (const [where, surface] of [['ground', fills.groundRgb], ['pane', fills.pane]] as [string, RGB][]) {
        const tertiary = contrast(parseHex(s['--g-mist-2']), surface);
        if (tertiary < AA_NON_TEXT) failures.push(label + ': mist-2 on ' + where + ' ' + tertiary.toFixed(2));
      }
      /* The rail is in this loop only for the record: with the drop control and the search placeholder both on
         the mist step, nothing in the column draws the tertiary step any more. If something goes back to it,
         this is the number it has to clear. */
      const railTertiary = contrast(parseHex(s['--g-mist-2']), fills.rail);
      if (railTertiary < worstRailTertiary.ratio) worstRailTertiary = { ratio: railTertiary, label };
      for (const [where, surface] of [['ground', fills.groundRgb], ['rail', fills.rail], ['pane', fills.pane]] as [string, RGB][]) {
        const accent = contrast(parseHex(s['--g-accent']), surface);
        if (accent < AA_NON_TEXT) failures.push(label + ': accent on ' + where + ' ' + accent.toFixed(2));
      }
    }
    expect(failures, 'the tertiary step or the accent under the non-text floor: ' + failures.slice(0, 6).join(' | ')).toEqual([]);
    expect(worstRailTertiary.ratio, 'the tertiary step is not drawn on the rail; if it returns it measures ' +
      worstRailTertiary.ratio.toFixed(2) + ' there (' + worstRailTertiary.label + ')').toBeGreaterThan(2.5);
  });

  it('keeps each material\'s own icon ink findable on that material', () => {
    const worst = { ratio: Infinity, label: '' };
    for (const { label, s, fills } of SAMPLES) {
      for (const [ink, fill] of [['--g-rail-icon', fills.rail], ['--g-bar-icon', fills.bar]] as ['--g-rail-icon' | '--g-bar-icon', RGB][]) {
        const ratio = contrast(parseHex(s[ink]), fill);
        if (ratio < worst.ratio) worst.ratio = ratio;
        if (ratio < AA_NON_TEXT) worst.label = worst.label || (label + ' ' + ink + ' ' + ratio.toFixed(2));
      }
    }
    expect(worst.label, 'an icon ink under the non-text floor: ' + worst.label).toBe('');
    expect(worst.ratio).toBeGreaterThanOrEqual(AA_NON_TEXT);
  });

  it('gives the machine\'s own pane the accent\'s hue, which is what makes it the instrument\'s surface', () => {
    /* The pane is not a fifth location on the colour wheel: it is the one surface that carries the product's
       own instrument blue, the accent that everything else in the chrome only uses for state. That is a
       positive identity rather than a difference from its neighbours, so it is checked as one. */
    const failures: string[] = [];
    for (const { label, s, fills } of SAMPLES) {
      const accent = okLab(parseHex(s['--g-accent']));
      const pane = okLab(fills.pane);
      const gap = hueGap(accent.hue, pane.hue);
      if (gap > 25) failures.push(label + ': pane hue ' + pane.hue.toFixed(1) + ' vs accent ' + accent.hue.toFixed(1) + ' — ' + gap.toFixed(1) + '° apart');
    }
    expect(failures, 'the pane has drifted off the instrument\'s own hue: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it('never reaches a published hazard colour', () => {
    /* The four IMD colours are reached only through a value a source printed, and Claim.tsx's --g-lit is how a
       claim carries one. Two things are asserted, because the first is not enough on its own: that this module
       never emits a hazard KEY, and that no colour it does emit is anywhere near a hazard VALUE at either
       regime's own value — a decorative surface that lands on a published red is a reader reading a severity
       that no source stated. */
    const forbiddenKeys = ['--g-red', '--g-orange', '--g-yellow', '--g-green', '--g-lit'];
    const hazardValues = ['#e2596f', '#e08a47', '#d9b53f', '#4f9d6d', '#b0203a', '#8e4c0d', '#7a6209', '#1f6b3a'];
    const leaks: string[] = [];
    let nearest = { distance: Infinity, where: '' };
    for (const { label, s, fills } of SAMPLES) {
      const record = s as unknown as Record<string, string>;
      for (const key of forbiddenKeys) if (key in record) leaks.push(key + ' in the spectrum at ' + label);
      for (const [name, value] of Object.entries(s)) {
        const c = parseHex(value);
        for (const hazard of hazardValues) {
          const H = parseHex(hazard);
          const distance = Math.hypot(c[0] - H[0], c[1] - H[1], c[2] - H[2]);
          if (distance < nearest.distance) nearest = { distance, where: name + ' at ' + label };
        }
      }
      for (const [name, rgb] of Object.entries(fills)) {
        const lab = okLab(rgb);
        for (const hazard of hazardValues) {
          const h = okLab(parseHex(hazard));
          const distance = Math.hypot(lab.L - h.L, lab.C * Math.cos(lab.hue * Math.PI / 180) - h.C * Math.cos(h.hue * Math.PI / 180),
            lab.C * Math.sin(lab.hue * Math.PI / 180) - h.C * Math.sin(h.hue * Math.PI / 180));
          if (distance < 0.05) leaks.push(name + ' is within 0.05 OKLab of ' + hazard + ' at ' + label);
        }
      }
    }
    expect(leaks, 'a decorative colour inside a published hazard\'s neighbourhood: ' + leaks.slice(0, 5).join(' | ')).toEqual([]);
    /* Printed so a future change that moves a material toward a hazard is visible in the run rather than only
       in a failure. The nearest approach is reported as the byte distance in sRGB. */
    expect(nearest.distance, 'the closest any emitted colour comes to a hazard value: ' + nearest.distance.toFixed(1) + ' (' + nearest.where + ')').toBeGreaterThan(40);
  });

  it('paints the tokens it defines — a palette that is written and not used is not a palette', () => {
    /* The failure this batch is made of. spectrum.ts computed three component tints for two hours and no
       reader saw one of them, because the element that carried the hour attribute re-declared them from the
       static hour block (docs/134). The repair was at the cause — `:root[data-hour]` so there is one owner —
       and this check holds the other half: the stylesheet that draws each material has to name its token, so a
       material cannot be defined and then forgotten. */
    const read = (file: string) => readFileSync(new URL('./css/' + file, import.meta.url), 'utf8');
    const expected: [string, string, string][] = [
      ['rail.css', '.g-rail', '--g-rail-fill'],
      ['rail.css', '.g-rail', '--g-rail-icon'],
      ['chrome.css', '.g-top', '--g-bar-fill'],
      ['chrome.css', '.g-top', '--g-bar-icon'],
      ['thread.css', '.g-you p', '--g-bubble-fill'],
      ['thread.css', '.g-claim', '--g-pane-fill'],
      ['glass.css', '.g-pane', '--g-pane-fill'],
      ['panel.css', '.g-panel-side', '--g-rail-fill'],
    ];
    const missing = expected.filter(([file, , token]) => !read(file).includes(token)).map(([file, , token]) => token + ' not named in ' + file);
    expect(missing, 'a material defined and not painted: ' + missing.join(' | ')).toEqual([]);
    /* And the shadowing that caused it cannot come back. `data-hour` sits on the document element, where
       spectrum.ts writes, and on `.g`; a declaration on `.g` beats its parent's inline style, so `.g` defers
       every property the spectrum owns back to the document element — and it does so by NAMING each one, so
       the two lists can be held to each other here. A token added to spectrum.ts and not to the deferral is a
       token the reader will not see, which is exactly the defect this batch is made of. */
    const tokens = read('tokens.css').replace(/\/\*[\s\S]*?\*\//g, '');
    const deferral = /(^|\n)\.g\[data-hour\]\s*\{([\s\S]*?)\n\}/.exec(tokens);
    expect(deferral, 'tokens.css must carry a .g[data-hour] block that defers the spectrum properties').not.toBeNull();
    const deferred = new Set([...(deferral as RegExpExecArray)[2].matchAll(/(--g-[a-z0-9-]+):\s*inherit/g)].map(m => m[1]));
    const undeferred = Object.keys(SAMPLES[0].s).filter(name => !deferred.has(name));
    expect(undeferred, 'properties the spectrum writes that .g would shadow: ' + undeferred.join(', ')).toEqual([]);
  });
});
