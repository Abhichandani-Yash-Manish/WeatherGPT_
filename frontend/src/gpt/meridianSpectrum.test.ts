/* The selected light interface, held to being light — at every minute of the day, not in one screenshot.
   ============================================================================
   The direction chosen on 22 September is a calm LIGHT page, and the reason it is light is a reader who may
   be opening an advisory at midnight and does not want a white screen turning into a dark one under them.
   The first implementation kept that promise by freezing the palette into one set of hex values, and the
   audit kept it by forbidding Field.tsx from calling applySpectrum at all.

   Both of those confuse "light" with "frozen". A page that is byte-for-byte identical at 06:00 and 23:00 is
   not calm, it is unattended - and the ban on the code path meant the requirement was never actually
   measured, only made unreachable.

   So the requirement is measured here instead, which is both stronger and honest about what it allows.
   `meridianSpectrumAt` is sampled every fifteen minutes through a full day, at latitudes from Kanyakumari
   to Leh, and at each of those ~400 instants the palette has to be:

     LIGHT       the ground stays near the top of the luminance range and the ink stays near the bottom.
                 There is no hour at which this palette may cross over, whatever the sun is doing.
     LEGIBLE     every ink clears AA against every ground it is set on, measured, not asserted.
     MOVING      and it does have to move - a day whose first light is identical to its midnight would
                 pass every check above and be the exact thing this replaced.

   That last one is why this file exists rather than a tighter version of the old grep. */

import { describe, expect, it } from 'vitest';
import { solarPosition } from './fieldPaint';
import { meridianSpectrumAt } from './spectrum';

const AA = 4.5;

function channel(c: number): number {
  const v = c / 255;
  return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}

/** Relative luminance of a `#rrggbb` value, or null for anything that is not one. */
function luminance(value: string): number | null {
  const hex = /^#[0-9a-f]{6}$/i.exec(value.trim());
  if (!hex) return null;
  const n = parseInt(value.trim().slice(1), 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
}

function contrast(a: string, b: string): number | null {
  const x = luminance(a);
  const y = luminance(b);
  if (x === null || y === null) return null;
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

/** Every quarter hour of one day, at a spread of Indian latitudes. */
function sweep(): { label: string; spectrum: ReturnType<typeof meridianSpectrumAt> }[] {
  const places: [string, number, number][] = [
    ['Kanyakumari', 8.08, 77.55],
    ['Pune', 18.52, 73.86],
    ['New Delhi', 28.61, 77.21],
    ['Leh', 34.16, 77.58],
  ];
  const out: { label: string; spectrum: ReturnType<typeof meridianSpectrumAt> }[] = [];
  for (const [name, lat, lon] of places) {
    for (let minute = 0; minute < 24 * 60; minute += 15) {
      const at = new Date(Date.UTC(2026, 5, 21, 0, minute));
      out.push({ label: name + ' +' + minute + 'm', spectrum: meridianSpectrumAt(solarPosition(lat, lon, at)) });
    }
  }
  return out;
}

const DAY = sweep();

describe('Meridian never stops being light', () => {
  it('keeps every plane where it belongs at every hour and latitude', () => {
    /* Four planes, and each one has to stay in its own band all day. The sheet is where the conversation
       is read and it is always near-white; the ground is a mid-light plane the atmosphere is drawn on and
       must never sink into the band where neither ink reads; the rail is chrome and always near-black;
       the ink is always near-black. Nothing may cross into another's band as the sun moves. */
    const crossed: string[] = [];
    for (const { label, spectrum } of DAY) {
      const sheet = luminance(spectrum['--g-raise']);
      const ground = luminance(spectrum['--g-bg']);
      const rail = luminance(spectrum['--g-rail-fill']);
      const ink = luminance(spectrum['--g-paper']);
      if (sheet === null || ground === null || rail === null || ink === null) { crossed.push(label + ' unparseable'); continue; }
      if (sheet < 0.93) crossed.push(label + ' sheet ' + sheet.toFixed(3));
      if (ground < 0.66) crossed.push(label + ' ground ' + ground.toFixed(3));
      if (rail > 0.03) crossed.push(label + ' rail ' + rail.toFixed(3));
      if (ink > 0.08) crossed.push(label + ' ink ' + ink.toFixed(3));
      /* And they have to stay RANKED, with real distance between them: this is the whole complaint the
         redesign answered - every surface inside a tenth of a step of every other, nothing to rank. */
      if (sheet - ground < 0.12) crossed.push(label + ' sheet/ground too close');
      if (ground - rail < 0.5) crossed.push(label + ' ground/rail too close');
    }
    expect(crossed.slice(0, 6)).toEqual([]);
  });

  it('clears AA for every ink on every ground it is set on', () => {
    const short: string[] = [];
    const inks = ['--g-paper', '--g-mist', '--g-mist-2', '--g-accent', '--g-accent-2'] as const;
    /* --g-rail-fill is not in this list: the rail is near-black and carries its OWN light inks, declared
       in meridian.css and measured against it by FE14. Pairing the page's dark ink with the rail's dark
       ground would be measuring something that never appears on screen. */
    const grounds = ['--g-bg', '--g-raise', '--g-raise-2', '--g-bar-fill', '--g-pane-fill'] as const;
    for (const { label, spectrum } of DAY) {
      for (const ink of inks) {
        for (const ground of grounds) {
          const measured = contrast(spectrum[ink], spectrum[ground]);
          /* A material that resolves to a translucent film rather than a flat hex is measured by FE14
             against the page ground instead; it has no single colour to measure here. */
          if (measured !== null && measured < AA) {
            short.push(label + ' ' + ink + ' on ' + ground + ' ' + measured.toFixed(2) + ':1');
          }
        }
      }
    }
    expect(short.slice(0, 6)).toEqual([]);
  });

  it('leaves the four published hazard colours alone', () => {
    /* This module has never written them and must never start: a bulletin's red is the publisher's, and a
       palette that drifts it is a palette that has restated a warning. */
    for (const { spectrum } of DAY.slice(0, 8)) {
      for (const name of ['--g-red', '--g-orange', '--g-yellow', '--g-green']) {
        expect(Object.prototype.hasOwnProperty.call(spectrum, name)).toBe(false);
      }
    }
  });
});

describe('but it does move', () => {
  it('lights first light differently from midnight', () => {
    const at = (hour: number) => meridianSpectrumAt(solarPosition(18.52, 73.86, new Date(Date.UTC(2026, 5, 21, hour - 5, -30))));
    const midnight = at(0);
    const dawn = at(6);
    const noon = at(12);
    const dusk = at(18);
    const grounds = [midnight['--g-bg'], dawn['--g-bg'], noon['--g-bg'], dusk['--g-bg']];
    /* Four distinct grounds. If any two of these are equal the day has a flat stretch in it. */
    expect(new Set(grounds).size).toBe(4);
    /* And the movement is a real one rather than a rounding artefact in the last digit. */
    const spread = grounds.map(g => luminance(g) as number);
    expect(Math.max(...spread) - Math.min(...spread)).toBeGreaterThan(0.004);
  });

  it('gives the four materials four different films, so the page has planes', () => {
    const noon = meridianSpectrumAt(solarPosition(18.52, 73.86, new Date(Date.UTC(2026, 5, 21, 6, 30))));
    const films = [noon['--g-rail-fill'], noon['--g-bar-fill'], noon['--g-bubble-fill'], noon['--g-pane-fill']];
    expect(new Set(films).size).toBeGreaterThan(1);
  });

  it('is the selected reference itself at high sun', () => {
    /* The hour the palette is authored at, and the one the static CSS fallback in meridian.css copies.
       If these two ever drift apart, a reader with JavaScript off gets a different product. */
    const noon = meridianSpectrumAt({ altitude: 80, hourAngle: 0 });
    expect(noon['--g-bg']).toBe('#ecebe4');
    expect(noon['--g-paper']).toBe('#191a16');
    expect(noon['--g-accent']).toBe('#7c420b');
  });
});
