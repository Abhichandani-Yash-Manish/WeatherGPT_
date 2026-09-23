/* The dial says what time the sun rises. That is a checkable claim, so it is checked.
   ============================================================================
   Everything else on the welcome screen carries a source line. This one carries astronomy instead, which
   is only better if it is right - a dial that is confidently ten minutes out is worse than no dial, because
   nothing on screen would ever tell the reader. So the two crossings are pinned against published almanac
   times, and the tolerance is stated rather than fitted: the solver here uses the same low-precision solar
   position the ground has always been painted from, which ignores refraction and the sun's own diameter,
   and those two together are worth a few minutes at the horizon. Ten minutes is the band that approximation
   is honestly good to. It is not good to one minute and this test is not allowed to pretend otherwise. */

import { describe, expect, it } from 'vitest';
import { clockOf, daylightAt, istHour, spanOf } from './DayArc';

/** An IST wall-clock instant, as the Date the solver will be handed. */
function ist(year: number, month: number, day: number, hour = 12): Date {
  return new Date(Date.UTC(year, month - 1, day, hour - 5, -30));
}

/** How far apart two IST hours are, in minutes. */
function minutesApart(a: number | null, b: number): number {
  return a === null ? Infinity : Math.abs(a - b) * 60;
}

describe('the day the dial draws', () => {
  /* Published times for these places and dates. The equinox pair is the useful one: within a day of the
     equinox every place on earth gets close to twelve hours, so a solver with a sign error or a bad
     latitude term fails it loudly rather than subtly. */
  const cases: [string, number, number, Date, number, number][] = [
    // place,      lat,    lon,     date,               sunrise IST, sunset IST
    ['Pune',       18.52,  73.86,   ist(2026, 9, 23),   6.42,        18.50],
    ['New Delhi',  28.61,  77.21,   ist(2026, 9, 23),   6.18,        18.25],
    ['Kochi',       9.93,  76.26,   ist(2026, 9, 23),   6.25,        18.30],
    // Midwinter and midsummer in the north, where the day length has to actually move.
    ['Delhi mid-winter', 28.61, 77.21, ist(2026, 12, 21), 7.17,      17.48],
    ['Delhi mid-summer', 28.61, 77.21, ist(2026, 6, 21),  5.40,      19.37],
  ];

  it.each(cases)('%s crosses the horizon when the almanac says it does', (_name, lat, lon, date, rise, set) => {
    const day = daylightAt(lat, lon, date);
    expect(minutesApart(day.sunrise, rise)).toBeLessThan(10);
    expect(minutesApart(day.sunset, set)).toBeLessThan(10);
  });

  it('is about twelve hours everywhere at the equinox', () => {
    for (const latitude of [9.93, 18.52, 28.61, 34.08]) {
      const day = daylightAt(latitude, 77, ist(2026, 9, 23));
      expect(day.length).not.toBeNull();
      expect(Math.abs((day.length as number) - 12)).toBeLessThan(0.35);
    }
  });

  it('gives Delhi a longer day in June than in December', () => {
    const june = daylightAt(28.61, 77.21, ist(2026, 6, 21)).length as number;
    const december = daylightAt(28.61, 77.21, ist(2026, 12, 21)).length as number;
    expect(june).toBeGreaterThan(december + 3);
  });

  it('reads the IST hour off an instant', () => {
    /* 06:30 IST is 01:00 UTC. */
    expect(istHour(new Date(Date.UTC(2026, 8, 23, 1, 0)))).toBeCloseTo(6.5, 6);
    /* And the day wraps rather than going negative. */
    expect(istHour(new Date(Date.UTC(2026, 8, 23, 20, 0)))).toBeCloseTo(1.5, 6);
  });
});

describe('what the dial prints', () => {
  it('states a clock reading with both fields', () => {
    expect(clockOf(6.5)).toBe('06:30');
    expect(clockOf(18.25)).toBe('18:15');
    expect(clockOf(0)).toBe('00:00');
  });

  it('prints an absent crossing as absent rather than as midnight', () => {
    expect(clockOf(null)).toBe('--:--');
    expect(spanOf(null)).toBe('');
  });

  it('states a span in hours and minutes', () => {
    expect(spanOf(12.5)).toBe('12h 30m');
    expect(spanOf(11.0)).toBe('11h 00m');
  });
});
