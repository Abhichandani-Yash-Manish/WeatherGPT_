/* The atmosphere claims to be weather-shaped. That claim is checkable, so it is checked.
   ============================================================================
   The field and the flow are decoration, and nothing in this file argues otherwise. What it pins is the
   two properties that make the decoration honest rather than arbitrary:

   1. The field is a function of its inputs and nothing else. No Math.random, no Date.now, no per-frame
      jitter. Two captures of this page a second apart have to differ by a second of motion and by nothing
      else, or the background cannot be reviewed, diffed or screenshotted as evidence. */

import { describe, expect, it } from 'vitest';
import { fieldAt, RESTING, spark } from './skyfield';

describe('the array fires deterministically', () => {
  it('gives the same cell the same spark for the same tick, and a different one next tick', () => {
    /* No Math.random anywhere in the loop: a background that differs between two captures of the same
       second cannot be reviewed, diffed or held as evidence. */
    for (let i = 0; i < 50; i += 1) expect(spark(7, 3)).toBe(spark(7, 3));
    expect(spark(7, 3)).not.toBe(spark(7, 4));
    expect(spark(7, 3)).not.toBe(spark(8, 3));
  });

  it('spreads across the unit interval rather than clustering', () => {
    const buckets = [0, 0, 0, 0];
    for (let cell = 0; cell < 400; cell += 1) buckets[Math.min(3, Math.floor(spark(cell, 11) * 4))] += 1;
    /* Every quarter gets a real share; a hash that piled into one bucket would fire the same cells always. */
    buckets.forEach(count => expect(count).toBeGreaterThan(40));
  });
});

describe('the field is a function of its inputs', () => {
  it('gives the same value for the same point, phase and bearing', () => {
    const once = fieldAt(0.31, 0.62, 1.77, 0.5);
    for (let i = 0; i < 40; i += 1) expect(fieldAt(0.31, 0.62, 1.77, 0.5)).toBe(once);
  });

  it('is continuous in time rather than reseeded per frame', () => {
    /* A thousandth of a phase-turn may not move the field more than a hair. A per-frame reseed would fail
       this by orders of magnitude, which is exactly the failure that makes contours shimmer. */
    const a = fieldAt(0.42, 0.33, 1.2, 0.2);
    const b = fieldAt(0.42, 0.33, 1.2 + 0.001, 0.2);
    expect(Math.abs(a - b)).toBeLessThan(0.01);
  });

  it('turns with the bearing, so the sun\'s own hour angle actually reaches it', () => {
    expect(fieldAt(0.9, 0.5, 1.0, 0)).not.toBeCloseTo(fieldAt(0.9, 0.5, 1.0, Math.PI / 2), 4);
  });

  it('rests at unit pace and full strength, and rests with no surge', () => {
    /* The surge is a transient tied to the reader pressing send. Resting means nothing was pressed. */
    expect(RESTING).toEqual({ pace: 1, tension: 1, strength: 1, bearing: 0, surge: 0 });
  });
});
