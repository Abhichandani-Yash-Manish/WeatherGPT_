/* The spectrum's one hard promise: AA holds everywhere, not just at the four old anchors.
   ============================================================================
   spectrum.ts replaced a four-step palette with a continuous one, and a continuous function can fail a
   contrast floor at some THIRD instant that a test written against 'night', 'daybreak', 'noon' and 'golden'
   would never sample. So this samples the day itself — every fifteen solar minutes, across three latitudes
   that span the country (near the southern tip, near the geographic centre, and up at Leh, where a winter
   day is short enough to spend a much larger share of it in twilight than the other two ever do) and both
   solstices, so the twilight band this module treats specially is actually exercised at its widest.

   The luminance and contrast formulas are WCAG's own (relative luminance, then (L1+0.05)/(L2+0.05) with the
   lighter colour first) — the same arithmetic a browser's own accessibility tooling runs, reimplemented here
   because jsdom has no layout engine to run that tooling against (frontend/src/a11y/a11y.test.tsx explains
   why the axe run disables the colour-contrast rule for exactly this reason). This does not replace the
   in-browser axe run; it proves the one thing that run cannot prove about a value that changes every minute
   of the day — that it never dips below the floor between the instants a human would think to check.

   WHAT THIS FILE GOT WRONG, and why the first three checks now measure a gradient as well as a token.
   ============================================================================
   It checked `--g-paper` against `--g-bg`, and `--g-bg` is the bottom of the page's own gradient, computed
   from the SAME regime as the ink. So the ink was being measured against its own shadow: the two agreed with
   each other by construction, and the check passed while the page did not. The ground a reader's text sits on
   is `.g-field-sky` — a radial fade over a linear gradient drawn from `--g-sky-1`, `--g-sky-2` and `--g-bg` —
   and the ink was measured against none of them.

   A minute-resolution sweep over three places and both solstices, run against the band instead, found 22,619
   readings under 4.5:1 before the repair, the worst of them 1.001:1: near-black ink on a sky that had already
   gone to dusk's violet at 18:00 IST on 21 June at Nagpur, because the ground's clock was the hour angle
   while the ink's was the solar altitude. docs/134 records the measurement and the repair.

   So `groundAt` below composites the two gradients ground.css actually draws, at the points on the page where
   text is drawn, and those checks run against THAT. The token pairs are checked as well — both are true of
   the page and neither implies the other. */

import { describe, expect, it } from 'vitest';
import { solarPosition } from './fieldPaint';
import { spectrumAt, type Scheme, type Spectrum } from './spectrum';

type RGB = [number, number, number];

function parseHex(hex: string): RGB {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function relativeLuminanceRgb(rgb: RGB): number {
  const channel = (byte: number) => {
    const v = byte / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2]);
}

export function contrastRgb(a: RGB, b: RGB): number {
  const x = relativeLuminanceRgb(a);
  const y = relativeLuminanceRgb(b);
  const [lighter, darker] = x >= y ? [x, y] : [y, x];
  return (lighter + 0.05) / (darker + 0.05);
}

const contrastRatio = (a: string, b: string) => contrastRgb(parseHex(a), parseHex(b));
const mixRgb = (a: RGB, b: RGB, t: number): RGB => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

/** The ground under a point on the page, from the two gradients `.g-field-sky` is painted with:
      radial-gradient(120% 80% at 50% 0%, sky-1 0%, transparent 66%),
      linear-gradient(178deg, sky-1 0%, sky-2 58%, bg 100%)
    The radial fades `sky-1` in over the top of the page; the linear carries it down to `--g-bg`. `fx` and `fy`
    are fractions of the viewport. */
export function groundAt(spectrum: Spectrum, fx: number, fy: number): RGB {
  const sky1 = parseHex(spectrum['--g-sky-1']);
  const sky2 = parseHex(spectrum['--g-sky-2']);
  const bg = parseHex(spectrum['--g-bg']);
  const base = fy <= 0.58 ? mixRgb(sky1, sky2, fy / 0.58) : mixRgb(sky2, bg, (fy - 0.58) / 0.42);
  const dx = (fx - 0.5) / 1.20;
  const dy = fy / 0.80;
  const fade = Math.max(0, 1 - Math.hypot(dx, dy) / 0.66);
  return mixRgb(base, sky1, fade);
}

/* Three places, two solstices: Kanyakumari never sees a long twilight, Leh in December does — the case the
   old four-band design under-served most, per fieldPaint.test.ts's own note that the previous banding put
   most of an Indian morning into a dusk palette. */
const PLACES: { name: string; latitude: number; longitude: number }[] = [
  { name: 'Kanyakumari', latitude: 8.08, longitude: 77.55 },
  { name: 'Nagpur', latitude: 21.15, longitude: 79.09 },
  { name: 'Leh', latitude: 34.16, longitude: 77.58 },
];
const DATES = [Date.UTC(2026, 5, 21, 0, 0, 0), Date.UTC(2026, 11, 21, 0, 0, 0)];

const AA_NORMAL_TEXT = 4.5;
/* Non-text UI (icon strokes, focus rings) only has to clear the lower AA floor — WCAG 1.4.11, not 1.4.3. */
const AA_NON_TEXT = 3;

/** Where text is drawn on the bare ground: the column's centre and the rail's edge, down the whole page. */
export const GROUND_POINTS: [number, number][] = [0.5, 0.08].flatMap(fx =>
  [0.0, 0.03, 0.10, 0.25, 0.45, 0.62, 0.80, 1.0].map(fy => [fx, fy] as [number, number]));

type Sample = { label: string; spectrum: Spectrum };

function sampleDay(stepMinutes: number, scheme: Scheme = 'system'): Sample[] {
  const samples: Sample[] = [];
  for (const place of PLACES) {
    for (const midnightUtc of DATES) {
      for (let minutes = 0; minutes < 24 * 60; minutes += stepMinutes) {
        const at = new Date(midnightUtc + minutes * 60_000);
        const position = solarPosition(place.latitude, place.longitude, at);
        samples.push({
          label: place.name + ' ' + new Date(midnightUtc).toISOString().slice(0, 10) + ' +' + minutes + 'min (alt ' + position.altitude.toFixed(1) + '°)',
          spectrum: spectrumAt(position, scheme),
        });
      }
    }
  }
  return samples;
}

const SAMPLES = sampleDay(15);

/** The AA floors this module has to hold everywhere, at any scheme: paper and mist readable on the gradient
    itself, both inks readable on the two raised surfaces, the accent usable as an icon and a focus ring, and
    no published hazard colour ever touched. Run once for 'system' (the describe block below, which also holds
    the two checks unique to it: the deliberate ink snap at dawn and dusk, and the regime-flip sweep — neither
    is a meaningful question of a forced scheme, which has no regime to flip) and again, at the same
    ninety-six-samples-per-place-and-date resolution, for 'dark' and 'light' below. */
function registerAAFloorChecks(schemeLabel: string, samples: Sample[]) {
  it(schemeLabel + ': samples more than the four old anchors ever could', () => {
    /* Three places * two dates * ninety-six quarter-hours. If this number ever drops, the floor below it is
       being proven over a thinner day than it claims. */
    expect(samples.length).toBe(PLACES.length * DATES.length * 96);
  });

  it(schemeLabel + ': keeps the primary ink readable on the gradient band it is actually drawn on', () => {
    const failures = samples.flatMap(({ label, spectrum }) =>
      GROUND_POINTS.map(([fx, fy]) => ({ where: `at ${fx}×${fy}`, ratio: contrastRgb(parseHex(spectrum['--g-paper']), groundAt(spectrum, fx, fy)) }))
        .filter(({ ratio }) => ratio < AA_NORMAL_TEXT)
        .map(({ where, ratio }) => label + ' ' + where + ': ' + ratio.toFixed(3)));
    expect(failures, schemeLabel + ' — instants where --g-paper fails AA on the sky itself: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it(schemeLabel + ': keeps the quiet ink readable on the gradient band it is actually drawn on', () => {
    const failures = samples.flatMap(({ label, spectrum }) =>
      GROUND_POINTS.map(([fx, fy]) => ({ where: `at ${fx}×${fy}`, ratio: contrastRgb(parseHex(spectrum['--g-mist']), groundAt(spectrum, fx, fy)) }))
        .filter(({ ratio }) => ratio < AA_NORMAL_TEXT)
        .map(({ where, ratio }) => label + ' ' + where + ': ' + ratio.toFixed(3)));
    expect(failures, schemeLabel + ' — instants where --g-mist fails AA on the sky itself: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it(schemeLabel + ': keeps the primary and quiet inks readable on the raised surfaces', () => {
    const failures = samples.filter(({ spectrum }) => {
      const onRaised = contrastRatio(spectrum['--g-paper'], spectrum['--g-raise']);
      const onRaised2 = contrastRatio(spectrum['--g-paper'], spectrum['--g-raise-2']);
      const quiet = contrastRatio(spectrum['--g-mist'], spectrum['--g-raise']);
      return onRaised < AA_NORMAL_TEXT || onRaised2 < AA_NORMAL_TEXT || quiet < AA_NORMAL_TEXT;
    }).map(({ label, spectrum }) => label + ': paper/raise ' + contrastRatio(spectrum['--g-paper'], spectrum['--g-raise']).toFixed(2) +
      ', paper/raise-2 ' + contrastRatio(spectrum['--g-paper'], spectrum['--g-raise-2']).toFixed(2) +
      ', mist/raise ' + contrastRatio(spectrum['--g-mist'], spectrum['--g-raise']).toFixed(2));
    expect(failures, schemeLabel + ' — instants where the raised surfaces fail AA: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it(schemeLabel + ': keeps the accent usable as an icon and a focus ring against the ground and a raised surface', () => {
    const failures = samples.filter(({ spectrum }) => {
      const onGround = contrastRatio(spectrum['--g-accent'], spectrum['--g-bg']);
      const onRaised = contrastRatio(spectrum['--g-accent'], spectrum['--g-raise']);
      return onGround < AA_NON_TEXT || onRaised < AA_NON_TEXT;
    }).map(({ label }) => label);
    expect(failures, schemeLabel + ' — instants where --g-accent fails the non-text floor: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it(schemeLabel + ': never touches a published hazard colour', () => {
    const forbidden = ['--g-red', '--g-orange', '--g-yellow', '--g-green', '--g-lit'];
    const spectrum = samples[0].spectrum as unknown as Record<string, string>;
    const leaked = forbidden.filter(name => name in spectrum);
    expect(leaked).toEqual([]);
  });
}

describe('the continuous spectrum holds AA at every fifteen solar minutes of the day', () => {
  it('samples more than the four old anchors ever could', () => {
    /* Three places * two dates * ninety-six quarter-hours. If this number ever drops, the floor below it is
       being proven over a thinner day than it claims. */
    expect(SAMPLES.length).toBe(PLACES.length * DATES.length * 96);
  });

  it('keeps the primary ink readable on the gradient band it is actually drawn on', () => {
    /* The check the previous version of this file could not make. `--g-bg` is the bottom of the gradient and it
       is computed from the same regime the ink is, so an ink measured against it is measured against its own
       shadow; the band is what a reader sees. */
    const failures = SAMPLES.flatMap(({ label, spectrum }) =>
      GROUND_POINTS.map(([fx, fy]) => ({ where: `at ${fx}×${fy}`, ratio: contrastRgb(parseHex(spectrum['--g-paper']), groundAt(spectrum, fx, fy)) }))
        .filter(({ ratio }) => ratio < AA_NORMAL_TEXT)
        .map(({ where, ratio }) => label + ' ' + where + ': ' + ratio.toFixed(3)));
    expect(failures, 'instants where --g-paper fails AA on the sky itself: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it('keeps the quiet ink readable on the gradient band it is actually drawn on', () => {
    /* --g-mist is the ink surfaces.css names as the one quiet text actually uses (FE14): the tertiary step,
       --g-mist-2, is reserved for hairlines and dashes and carries no such promise. */
    const failures = SAMPLES.flatMap(({ label, spectrum }) =>
      GROUND_POINTS.map(([fx, fy]) => ({ where: `at ${fx}×${fy}`, ratio: contrastRgb(parseHex(spectrum['--g-mist']), groundAt(spectrum, fx, fy)) }))
        .filter(({ ratio }) => ratio < AA_NORMAL_TEXT)
        .map(({ where, ratio }) => label + ' ' + where + ': ' + ratio.toFixed(3)));
    expect(failures, 'instants where --g-mist fails AA on the sky itself: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it('keeps the primary and quiet inks readable on the raised surfaces', () => {
    const failures = SAMPLES.filter(({ spectrum }) => {
      const onRaised = contrastRatio(spectrum['--g-paper'], spectrum['--g-raise']);
      const onRaised2 = contrastRatio(spectrum['--g-paper'], spectrum['--g-raise-2']);
      const quiet = contrastRatio(spectrum['--g-mist'], spectrum['--g-raise']);
      return onRaised < AA_NORMAL_TEXT || onRaised2 < AA_NORMAL_TEXT || quiet < AA_NORMAL_TEXT;
    }).map(({ label, spectrum }) => label + ': paper/raise ' + contrastRatio(spectrum['--g-paper'], spectrum['--g-raise']).toFixed(2) +
      ', paper/raise-2 ' + contrastRatio(spectrum['--g-paper'], spectrum['--g-raise-2']).toFixed(2) +
      ', mist/raise ' + contrastRatio(spectrum['--g-mist'], spectrum['--g-raise']).toFixed(2));
    expect(failures, 'instants where the raised surfaces fail AA: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it('keeps the accent usable as an icon and a focus ring against the ground and a raised surface', () => {
    const failures = SAMPLES.filter(({ spectrum }) => {
      const onGround = contrastRatio(spectrum['--g-accent'], spectrum['--g-bg']);
      const onRaised = contrastRatio(spectrum['--g-accent'], spectrum['--g-raise']);
      return onGround < AA_NON_TEXT || onRaised < AA_NON_TEXT;
    }).map(({ label }) => label);
    expect(failures, 'instants where --g-accent fails the non-text floor: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it('never touches a published hazard colour', () => {
    /* The four IMD colours are reachable only through Claim.tsx's own --g-lit, set inline on the one element
       that carries a source. If this module ever started emitting one of these names, a decorative value could
       silently sit behind a reader's next --g-lit lookup. materials.test.ts holds the stronger form, on the
       computed values. */
    const forbidden = ['--g-red', '--g-orange', '--g-yellow', '--g-green', '--g-lit'];
    const spectrum = SAMPLES[0].spectrum as unknown as Record<string, string>;
    const leaked = forbidden.filter(name => name in spectrum);
    expect(leaked).toEqual([]);
  });

  it('snaps the ink family at dawn and dusk rather than passing it through grey', () => {
    /* The one deliberate discontinuity in this module: proof that it lands where designed (the same −6°/+8°
       fieldPaint.ts uses) and that it is a clean flip rather than a blend that spends even one sample as an
       unreadable midpoint. Nagpur, equinox-adjacent date, so the transition band is crossed within the day's
       own sampled minutes — and every minute of it, against the band the text sits on. */
    const day = Date.UTC(2026, 8, 19, 0, 0, 0);
    let worst = { ratio: Infinity, where: '' };
    for (let minutes = 0; minutes < 24 * 60; minutes += 1) {
      const at = new Date(day + minutes * 60_000);
      const spectrum = spectrumAt(solarPosition(21.15, 79.09, at));
      for (const [fx, fy] of GROUND_POINTS) {
        const ground = groundAt(spectrum, fx, fy);
        for (const ink of ['--g-paper', '--g-mist'] as const) {
          const ratio = contrastRgb(parseHex(spectrum[ink]), ground);
          if (ratio < worst.ratio) worst = { ratio, where: minutes + 'min ' + ink + ' at ' + fx + '×' + fy };
        }
      }
    }
    expect(worst.ratio, 'the worst reading on the equinox day, ' + worst.where + ': ' + worst.ratio.toFixed(3)).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
  });

  it('holds AA through both regime flips at one-minute resolution', () => {
    /* A flip is where a 1.001:1 sample lives: the ground changes family in one commit. So both flips — the dawn
       one at −6° climbing and the dusk one at +8° falling — are swept a minute at a time, at Leh in December
       (the slowest twilight in the sampled set) and at Nagpur. */
    const flips: string[] = [];
    for (const [place, latitude, longitude] of [['Leh', 34.16, 77.58], ['Nagpur', 21.15, 79.09]] as const) {
      for (const date of DATES) {
        for (let minutes = 0; minutes < 24 * 60; minutes += 1) {
          const at = new Date(date + minutes * 60_000);
          const position = solarPosition(latitude, longitude, at);
          const nearDawn = position.hourAngle < 0 && Math.abs(position.altitude + 6) < 1;
          const nearDusk = position.hourAngle > 0 && Math.abs(position.altitude - 8) < 1;
          if (!nearDawn && !nearDusk) continue;
          const spectrum = spectrumAt(position);
          for (const [fx, fy] of GROUND_POINTS) {
            const ground = groundAt(spectrum, fx, fy);
            for (const ink of ['--g-paper', '--g-mist'] as const) {
              const ratio = contrastRgb(parseHex(spectrum[ink]), ground);
              if (ratio < AA_NORMAL_TEXT) {
                flips.push(place + ' ' + new Date(date).toISOString().slice(0, 10) + ' +' + minutes + 'min alt ' + position.altitude.toFixed(2) +
                  ' ' + ink + ' ' + fx + '×' + fy + ': ' + ratio.toFixed(3));
              }
            }
          }
        }
      }
    }
    expect(flips, 'readings under AA around a regime flip: ' + flips.slice(0, 6).join(' | ')).toEqual([]);
  });
});

/* ---- the scheme axis: a reader's explicit dark or light choice, holding AA and its own family ---------
   'system' above is the sun alone, exactly as this module has always computed it — that describe block is
   untouched. A reader who told their OS or browser dark or light has made a stronger statement than the sun's
   position at one instant, so spectrumAt(position, 'dark') and spectrumAt(position, 'light') pick the family
   outright (spectrum.ts's own header, section 4) and let the sun drift inside it. Two things a forced scheme
   promises that 'system' does not, and both are checked below at the same resolution as every other check in
   this file: the family never flips — a dark reader never gets a white page at noon, nor a light reader a
   black one at midnight — and the page still visibly drifts across the day rather than sitting on one frozen
   frame with the sun's hour angle ignored. */

const DARK_SAMPLES = sampleDay(15, 'dark');
const LIGHT_SAMPLES = sampleDay(15, 'light');

describe('an explicit dark scheme holds AA at every fifteen solar minutes of the day, in the dark family throughout', () => {
  registerAAFloorChecks('dark', DARK_SAMPLES);

  it('dark: never lets the ground go light, at any hour of the sampled day', () => {
    /* The ink and the ground disagree at chroma-neutral if they land on the same side, so the cheapest,
       strongest proof the family never flipped is the ink's own token: --g-paper is the pale ink of the dark
       family (relative luminance well above the near-black light family ever reaches) at every sample, and
       --g-bg stays dark (relative luminance well below the near-white light family ever reaches). */
    const failures = DARK_SAMPLES.filter(({ spectrum }) =>
      relativeLuminanceRgb(parseHex(spectrum['--g-paper'])) < 0.6 || relativeLuminanceRgb(parseHex(spectrum['--g-bg'])) > 0.2,
    ).map(({ label, spectrum }) => label + ': paper L ' + relativeLuminanceRgb(parseHex(spectrum['--g-paper'])).toFixed(3) +
      ', bg L ' + relativeLuminanceRgb(parseHex(spectrum['--g-bg'])).toFixed(3));
    expect(failures, 'instants where a forced dark scheme drifted into the light family: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it('dark: still drifts — the sky is not the same colour all day', () => {
    /* One place, one day, every fifteen minutes: if a forced scheme were secretly frozen on its 'night' anchor
       (the failure mode the header's section 4 names: "so dark mode across a whole day would sit still"),
       every sample would share the same --g-sky-1. A continuous function sampled 96 times a day is not going
       to coincide by chance, so a low count here is the bug, not noise. */
    const oneDay = DARK_SAMPLES.filter(({ label }) => label.startsWith('Nagpur 2026-06-21'));
    const distinctSkies = new Set(oneDay.map(({ spectrum }) => spectrum['--g-sky-1']));
    expect(distinctSkies.size, 'a forced dark scheme sampled ' + oneDay.length + ' times across one day produced only ' + distinctSkies.size + ' distinct --g-sky-1 values').toBeGreaterThan(50);
  });
});

describe('an explicit light scheme holds AA at every fifteen solar minutes of the day, in the light family throughout', () => {
  registerAAFloorChecks('light', LIGHT_SAMPLES);

  it('light: never lets the ground go dark, at any hour of the sampled day', () => {
    const failures = LIGHT_SAMPLES.filter(({ spectrum }) =>
      relativeLuminanceRgb(parseHex(spectrum['--g-paper'])) > 0.2 || relativeLuminanceRgb(parseHex(spectrum['--g-bg'])) < 0.6,
    ).map(({ label, spectrum }) => label + ': paper L ' + relativeLuminanceRgb(parseHex(spectrum['--g-paper'])).toFixed(3) +
      ', bg L ' + relativeLuminanceRgb(parseHex(spectrum['--g-bg'])).toFixed(3));
    expect(failures, 'instants where a forced light scheme drifted into the dark family: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it('light: still drifts — the sky is not the same colour all day', () => {
    const oneDay = LIGHT_SAMPLES.filter(({ label }) => label.startsWith('Nagpur 2026-06-21'));
    const distinctSkies = new Set(oneDay.map(({ spectrum }) => spectrum['--g-sky-1']));
    expect(distinctSkies.size, 'a forced light scheme sampled ' + oneDay.length + ' times across one day produced only ' + distinctSkies.size + ' distinct --g-sky-1 values').toBeGreaterThan(50);
  });
});
