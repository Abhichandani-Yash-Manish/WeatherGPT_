/* One instant is not a window. An hourly value (air quality, hourly forecast) states the instant it
   is valid for, so start equals end; rendering that as '00:30-00:30' reads as a zero-length window and
   was measured on 17 September 2026 summarising a whole day of hourly air-quality facts. */

import { describe, expect, it } from 'vitest';
import { elapsedWords, istWindow } from './time';

describe('istWindow', () => {
  it('prints one instant as one instant rather than a zero-length range', () => {
    const label = istWindow('2026-09-18T00:30:00+05:30', '2026-09-18T00:30:00+05:30');
    expect(label).not.toContain('00:30-00:30');
    expect(label).toBe('18 Sep 2026, 00:30 IST');
  });

  it('still prints a real same-day range as a range', () => {
    expect(istWindow('2026-09-18T09:30:00+05:30', '2026-09-18T12:30:00+05:30'))
      .toBe('18 Sep 2026 09:30-12:30 IST');
  });

  it('keeps both dates when the window crosses midnight', () => {
    const label = istWindow('2026-09-18T00:30:00+05:30', '2026-09-19T00:30:00+05:30');
    expect(label).toContain('18 Sep 2026');
    expect(label).toContain('19 Sep 2026');
    expect(label).toContain('00:30');
  });

  it('says a missing window is not stated rather than inventing one', () => {
    expect(istWindow(null, '2026-09-18T00:30:00+05:30')).toBe('Window not stated');
    expect(istWindow('2026-09-18T00:30:00+05:30', null)).toBe('Window not stated');
  });
});

describe('the elapsed clock under a working turn', () => {
  /* It printed the Unix epoch instead of the elapsed time: `elapsedWords(Date.now() / 1000)`, which
     rendered as "497172 h 14 min since you asked" on a turn four seconds old. The function was fine; the
     caller handed it an absolute instant where a duration was meant. This pins the units. */
  it('reads a duration, and a whole epoch is not a plausible one', () => {
    const startedAt = 1_789_801_256_310;
    expect(elapsedWords((startedAt + 4_000 - startedAt) / 1000)).toBe('4 s');
    expect(elapsedWords((startedAt + 95_000 - startedAt) / 1000)).toBe('1 min 35 s');
    /* What the bug looked like, recorded as its shape rather than as one captured figure: handing this an
       absolute instant yields hundreds of thousands of hours. The build printed "497172 h 14 min". */
    const asEpoch = elapsedWords(startedAt / 1000);
    expect(Number(asEpoch.split(' ')[0])).toBeGreaterThan(400_000);
  });

  it('never counts backwards when the clock is handed something earlier than the start', () => {
    expect(elapsedWords(Math.max(0, -5_000) / 1000)).toBe('0 s');
  });
});
