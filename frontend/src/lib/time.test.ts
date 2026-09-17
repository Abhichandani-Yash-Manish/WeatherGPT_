/* One instant is not a window. An hourly value (air quality, hourly forecast) states the instant it
   is valid for, so start equals end; rendering that as '00:30-00:30' reads as a zero-length window and
   was measured on 17 September 2026 summarising a whole day of hourly air-quality facts. */

import { describe, expect, it } from 'vitest';
import { istWindow } from './time';

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
