/* The hour the page is in.
   ============================================================================
   This had no test at all, which is how the bands stayed wrong without anyone noticing: 'golden' used to
   claim everything from -6 up to 22 degrees of solar altitude, which at 23 degrees north is most of the
   morning and most of the afternoon. That was invisible while all four palettes were the same near-black.
   It stopped being invisible the moment two of the hours became light pages — it would have put
   ten o'clock in the morning into a dusk palette. */

import { hourOf, solarAltitude } from './fieldPaint';

/* Nagpur, near the centre of India, so the sun's timing is representative rather than extreme. */
const LAT = 21.15;
const LON = 79.09;
const IST = 5.5 * 3600_000;

/** A Date at the given IST clock time on 19 September 2026. */
const ist = (hours: number, minutes = 0) =>
  new Date(Date.UTC(2026, 8, 19, 0, 0, 0) + hours * 3600_000 + minutes * 60_000 - IST);

describe('the hour, from the sun', () => {
  it('calls the middle of the day noon, not golden', () => {
    /* The band this replaces would have returned 'golden' for most of these. */
    [9, 10, 11, 12, 13, 14, 15, 16].forEach(hour => {
      expect(hourOf(ist(hour), LAT, LON), hour + ':00 IST').toBe('noon');
    });
  });

  it('calls the middle of the night night', () => {
    [21, 23, 0, 2, 4].forEach(hour => {
      expect(hourOf(ist(hour), LAT, LON), hour + ':00 IST').toBe('night');
    });
  });

  it('separates dawn from dusk, which is the whole reason the sun is sampled twice', () => {
    /* Both are a low sun. Only the direction of travel tells them apart, and they are opposite palettes:
       one is becoming a light page and the other is leaving one. */
    expect(hourOf(ist(6, 15), LAT, LON)).toBe('daybreak');
    expect(hourOf(ist(18, 15), LAT, LON)).toBe('golden');
  });

  it('never returns a light hour while the sun is below civil twilight', () => {
    /* The safety property of the banding: the page cannot be a white sheet in the dark. */
    for (let minutes = 0; minutes < 24 * 60; minutes += 10) {
      const at = ist(0, minutes);
      const altitude = solarAltitude(LAT, LON, at);
      if (altitude < -6) {
        expect(hourOf(at, LAT, LON), 'altitude ' + altitude.toFixed(1)).toBe('night');
      }
    }
  });

  it('gives a southern and a northern place different hours at the same instant', () => {
    /* The reason the reader's own latitude is used rather than a clock: in December, Leh is dark while
       Kanyakumari still has the sun up. */
    const december = new Date(Date.UTC(2026, 11, 21, 12, 40, 0));
    expect(hourOf(december, 34.16, 77.58)).not.toBe(hourOf(december, 8.08, 77.55));
  });
});
