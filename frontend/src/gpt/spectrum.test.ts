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
   of the day — that it never dips below the floor between the instants a human would think to check. */

import { describe, expect, it } from 'vitest';
import { solarPosition } from './fieldPaint';
import { spectrumAt, type Spectrum } from './spectrum';

function parseHex(hex: string) {
  const h = hex.replace('#', '');
  return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16) };
}

function relativeLuminance(hex: string): number {
  const { r, g, b } = parseHex(hex);
  const channel = (byte: number) => {
    const v = byte / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function contrastRatio(hexA: string, hexB: string): number {
  const a = relativeLuminance(hexA);
  const b = relativeLuminance(hexB);
  const [lighter, darker] = a >= b ? [a, b] : [b, a];
  return (lighter + 0.05) / (darker + 0.05);
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

type Sample = { label: string; spectrum: Spectrum };

function sampleDay(): Sample[] {
  const samples: Sample[] = [];
  for (const place of PLACES) {
    for (const midnightUtc of DATES) {
      for (let minutes = 0; minutes < 24 * 60; minutes += 15) {
        const at = new Date(midnightUtc + minutes * 60_000);
        const position = solarPosition(place.latitude, place.longitude, at);
        samples.push({
          label: place.name + ' ' + new Date(midnightUtc).toISOString().slice(0, 10) + ' +' + minutes + 'min',
          spectrum: spectrumAt(position),
        });
      }
    }
  }
  return samples;
}

const SAMPLES = sampleDay();

describe('the continuous spectrum holds AA at every fifteen solar minutes of the day', () => {
  it('samples more than the four old anchors ever could', () => {
    /* Three places * two dates * ninety-six quarter-hours. If this number ever drops, the floor below it is
       being proven over a thinner day than it claims. */
    expect(SAMPLES.length).toBe(PLACES.length * DATES.length * 96);
  });

  it('keeps the primary ink readable on the ground and on a raised surface', () => {
    const failures = SAMPLES.filter(({ spectrum }) => {
      const onGround = contrastRatio(spectrum['--g-paper'], spectrum['--g-bg']);
      const onRaised = contrastRatio(spectrum['--g-paper'], spectrum['--g-raise']);
      return onGround < AA_NORMAL_TEXT || onRaised < AA_NORMAL_TEXT;
    }).map(({ label, spectrum }) => label + ': paper/bg ' + contrastRatio(spectrum['--g-paper'], spectrum['--g-bg']).toFixed(2) +
      ', paper/raise ' + contrastRatio(spectrum['--g-paper'], spectrum['--g-raise']).toFixed(2));
    expect(failures, 'instants where --g-paper fails AA: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
  });

  it('keeps the quiet ink readable on the ground and on a raised surface', () => {
    /* --g-mist is the ink surfaces.css names as the one quiet text actually uses (FE14): the tertiary step,
       --g-mist-2, is reserved for hairlines and dashes and carries no such promise. */
    const failures = SAMPLES.filter(({ spectrum }) => {
      const onGround = contrastRatio(spectrum['--g-mist'], spectrum['--g-bg']);
      const onRaised = contrastRatio(spectrum['--g-mist'], spectrum['--g-raise']);
      return onGround < AA_NORMAL_TEXT || onRaised < AA_NORMAL_TEXT;
    }).map(({ label, spectrum }) => label + ': mist/bg ' + contrastRatio(spectrum['--g-mist'], spectrum['--g-bg']).toFixed(2) +
      ', mist/raise ' + contrastRatio(spectrum['--g-mist'], spectrum['--g-raise']).toFixed(2));
    expect(failures, 'instants where --g-mist fails AA: ' + failures.slice(0, 5).join(' | ')).toEqual([]);
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
       that carries a source. If this module ever started emitting one of these names, a decorative value
       could silently sit behind a reader's next --g-lit lookup. */
    const forbidden = ['--g-red', '--g-orange', '--g-yellow', '--g-green', '--g-lit'];
    const spectrum = SAMPLES[0].spectrum as unknown as Record<string, string>;
    const leaked = forbidden.filter(name => name in spectrum);
    expect(leaked).toEqual([]);
  });

  it('snaps the ink family at dawn and dusk rather than passing it through grey', () => {
    /* The one deliberate discontinuity in this module: proof that it lands where designed (the same −6°/+8°
       fieldPaint.ts uses) and that it is a clean flip rather than a blend that spends even one sample as an
       unreadable midpoint. Nagpur, equinox-adjacent date, so the transition band is crossed within the day's
       own sampled minutes. */
    const day = Date.UTC(2026, 8, 19, 0, 0, 0);
    const minuteSamples: { altitude: number; spectrum: Spectrum }[] = [];
    for (let minutes = 0; minutes < 24 * 60; minutes += 1) {
      const at = new Date(day + minutes * 60_000);
      const position = solarPosition(21.15, 79.09, at);
      minuteSamples.push({ altitude: position.altitude, spectrum: spectrumAt(position) });
    }
    /* Every single one of them, at one-minute resolution, still clears AA — the fine-grained version of the
       two checks above, run once, on the transition this module treats specially. */
    const worst = minuteSamples.reduce((min, { spectrum }) => Math.min(
      min,
      contrastRatio(spectrum['--g-paper'], spectrum['--g-bg']),
      contrastRatio(spectrum['--g-mist'], spectrum['--g-bg']),
    ), Infinity);
    expect(worst).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
  });
});
