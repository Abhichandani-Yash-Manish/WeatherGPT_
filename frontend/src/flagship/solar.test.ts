import { describe, expect, it } from 'vitest';
import { glowPoint, glowStrength, phaseOf, solarPosition } from './solar';

/* The atmosphere is computed, so its facts can be asserted rather than eyeballed. Every case below names the place
   and instant it is about, because that is the only input the sun has. */
const at = (iso: string) => new Date(iso);

describe('the sun', () => {
  it('is above the horizon at local noon and below it at local midnight', () => {
    /* Patna: 25.6 N, 85.1 E. 06:30 UTC is 12:00 IST. */
    expect(solarPosition(25.6, 85.1, at('2026-09-18T06:30:00Z')).altitude).toBeGreaterThan(50);
    expect(solarPosition(25.6, 85.1, at('2026-09-18T18:30:00Z')).altitude).toBeLessThan(-50);
  });

  it('carries latitude, so a northern and a southern place differ at the same instant', () => {
    const north = solarPosition(34.0, 77.0, at('2026-09-18T06:30:00Z')).altitude;
    const south = solarPosition(8.0, 77.0, at('2026-09-18T06:30:00Z')).altitude;
    expect(Math.abs(north - south)).toBeGreaterThan(2);
  });

  it('rises in the east and sets in the west', () => {
    expect(solarPosition(25.6, 85.1, at('2026-09-18T00:30:00Z')).azimuth).toBeLessThan(180);
    expect(solarPosition(25.6, 85.1, at('2026-09-18T12:30:00Z')).azimuth).toBeGreaterThan(180);
  });

  it('resolves the four phases from the sun rather than from the clock', () => {
    expect(phaseOf({ altitude: -20, azimuth: 40 })).toBe('night');
    expect(phaseOf({ altitude: 2, azimuth: 95 })).toBe('dawn');
    expect(phaseOf({ altitude: 2, azimuth: 265 })).toBe('dusk');
    expect(phaseOf({ altitude: 42, azimuth: 180 })).toBe('day');
  });

  it('keeps the glow on the page and its strength honest', () => {
    for (const altitude of [-30, -6, 0, 8, 30, 60, 90]) {
      for (const azimuth of [0, 90, 180, 270, 359]) {
        const point = glowPoint({ altitude, azimuth });
        expect(point.x).toBeGreaterThanOrEqual(0);
        expect(point.x).toBeLessThanOrEqual(1);
        expect(point.y).toBeGreaterThanOrEqual(0);
        expect(point.y).toBeLessThanOrEqual(1);
      }
    }
    expect(glowStrength({ altitude: 0, azimuth: 90 })).toBeGreaterThan(glowStrength({ altitude: 40, azimuth: 180 }));
    expect(glowStrength({ altitude: -20, azimuth: 20 })).toBe(0);
  });
});
