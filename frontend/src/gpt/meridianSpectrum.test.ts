/* Station: a white room, a black rail, and one lit instrument — measured across a day, not asserted.
   ============================================================================
   The direction went through several revisions. Three of them were rejected for the same reason: warm
   near-white paper with a clay accent, which is the commonest tell of machine-made design. A fourth
   inverted the whole product - dark shell, white pages - which got the ranking right and the emphasis
   wrong, making the room the subject and leaving the conversation lying in it.

   The room is white and quiet; the rail is black; and the CONVERSATION - the composer, an answer, every
   readout - is the dark instrument in the middle of it. In a white room the lit thing is the thing you are
   working with, and on this product that is the conversation.

   What is measured here, every fifteen minutes through a full day at four latitudes from Kanyakumari to
   Leh, is the pair of promises that structure makes:

     THE ROOM STAYS LIGHT    and the rail and the instrument stay dark. Neither may drift toward the
                             other, at any hour or latitude, or the ranking collapses.
     EVERY INK CLEARS AA     on the plane it is ACTUALLY set on. The room's dark inks are measured against
                             the room; the instrument's and the rail's light inks are declared in
                             meridian.css and measured against their own planes by FE14. Pairing a room ink
                             with the instrument would measure a combination that never appears on screen.
     THE ROOM STILL MOVES    faintly cooler at midnight, faintly warmer at first light. A room that is
                             byte-for-byte identical at 03:00 and 13:00 is a room nothing is looking after,
                             which is the complaint this whole line of work started from.
     THE INSTRUMENT DOES NOT an instrument that changed colour through the day is one you could not read a
                             receipt off and compare against yesterday's. */

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
  if (!/^#[0-9a-f]{6}$/i.test(value.trim())) return null;
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

describe('the room stays light and the instrument stays dark', () => {
  it('keeps every plane in its own band at every hour and latitude', () => {
    const crossed: string[] = [];
    for (const { label, spectrum } of DAY) {
      const rail = luminance(spectrum['--g-rail-fill']);
      const bar = luminance(spectrum['--g-bar-fill']);
      const room = luminance(spectrum['--g-bg']);
      const raise = luminance(spectrum['--g-raise']);
      const instrument = luminance(spectrum['--g-pane-fill']);
      const ink = luminance(spectrum['--g-paper']);
      if (rail === null || bar === null || room === null || raise === null || instrument === null || ink === null) {
        crossed.push(label + ' unparseable');
        continue;
      }
      if (rail > 0.02) crossed.push(label + ' rail ' + rail.toFixed(4));
      if (instrument > 0.03) crossed.push(label + ' instrument ' + instrument.toFixed(4));
      if (room < 0.85) crossed.push(label + ' room ' + room.toFixed(3));
      if (bar < 0.75) crossed.push(label + ' bar ' + bar.toFixed(3));
      if (raise < 0.95) crossed.push(label + ' raise ' + raise.toFixed(3));
      if (ink > 0.02) crossed.push(label + ' ink ' + ink.toFixed(4));
      /* And the ranking holds: the room is an order of magnitude off both dark planes. */
      if (room - instrument < 0.8) crossed.push(label + ' room/instrument too close');
      if (bar > room) crossed.push(label + ' bar is lighter than the room');
    }
    expect(crossed.slice(0, 6)).toEqual([]);
  });

  it('clears AA for every room ink on every room ground', () => {
    const short: string[] = [];
    const inks = ['--g-paper', '--g-mist', '--g-mist-2', '--g-accent', '--g-accent-2'] as const;
    const grounds = ['--g-bg', '--g-raise', '--g-raise-2', '--g-bar-fill'] as const;
    for (const { label, spectrum } of DAY) {
      for (const ink of inks) {
        for (const ground of grounds) {
          const measured = contrast(spectrum[ink], spectrum[ground]);
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

describe('the room moves and the instrument does not', () => {
  const at = (hour: number) =>
    meridianSpectrumAt(solarPosition(18.52, 73.86, new Date(Date.UTC(2026, 5, 21, hour - 5, -30))));

  it('lights the room differently at midnight, dawn, noon and dusk', () => {
    const grounds = [at(0), at(6), at(12), at(18)].map(s => s['--g-bg']);
    expect(new Set(grounds).size).toBe(4);
    const spread = grounds.map(g => luminance(g) as number);
    expect(Math.max(...spread) - Math.min(...spread)).toBeGreaterThan(0.002);
  });

  it('never lets the instrument or the ink drift, at any hour', () => {
    for (const { label, spectrum } of DAY) {
      expect(spectrum['--g-pane-fill'], label).toBe('#151b24');
      expect(spectrum['--g-raise'], label).toBe('#ffffff');
      expect(spectrum['--g-paper'], label).toBe('#0b0e13');
      expect(spectrum['--g-accent'], label).toBe('#0c6e5c');
    }
  });

  it('is the authored anchor itself at high sun', () => {
    /* The hour the palette is authored at, and the one the static fallback in meridian.css copies. If the
       two drift apart, a reader with JavaScript off gets a different product. */
    const noon = meridianSpectrumAt({ altitude: 80, hourAngle: 0 });
    expect(noon['--g-rail-fill']).toBe('#0c1017');
    expect(noon['--g-bar-fill']).toBe('#eef1f5');
    expect(noon['--g-bg']).toBe('#f6f8fa');
  });
});
