/* The locale the interface formats in.
   ============================================================================
   F6d asks for an interface that is localised in its labels, its dates and its numerals. The labels were
   already translated (four catalogues, held by i18n.test.ts); the dates and the numbers were not, because
   lib/time.ts hardcoded 'en-GB' and lib/format.ts formatted nothing at all. These specs hold the other two
   thirds, and they hold them the way this product holds anything: by the invariant that must survive.

   The invariant is that FORMATTING changes and the VALUE does not. A Tamil interface may name the month in
   Tamil; it may not move the instant, drop the zone, or round a retrieved number. So the checks below are
   mostly about what does NOT change, and the one about what does (the month is no longer English) is what
   makes the rest of them mean something. */

import { afterEach, describe, expect, it } from 'vitest';
import { count, number } from './format';
import { setLocale } from './locale';
import { istClock, istStamp, istWindow, monthName } from './time';

const INSTANT = '2026-09-18T00:30:00+05:30';
const LANGUAGES = ['hi', 'gu', 'ta'] as const;

afterEach(() => setLocale('en'));

describe('an instant, in the four languages the chrome speaks', () => {
  it('is byte-identical in the default rendering, because every recorded example says so', () => {
    expect(istStamp(INSTANT)).toBe('18 Sep 2026, 00:30 IST');
    expect(istWindow(INSTANT, '2026-09-18T03:30:00+05:30')).toBe('18 Sep 2026 00:30-03:30 IST');
    expect(istClock(INSTANT)).toBe('00:30');
  });

  it('keeps the leading zero on a single-digit day, which the product has always printed', () => {
    expect(istStamp('2026-09-04T00:30:00+05:30')).toBe('04 Sep 2026, 00:30 IST');
  });

  it.each(LANGUAGES)('names the month in %s rather than in English', language => {
    setLocale(language);
    const label = istStamp(INSTANT);
    /* The check that makes this suite worth having: if the locale is ignored anywhere on the path - the
       setter, the formatter cache, the i18n hook - this is the assertion that fails. */
    expect(label).not.toBe('18 Sep 2026, 00:30 IST');
    expect(label).toMatch(/[^\x00-\x7F]/);
  });

  it.each(LANGUAGES)('leaves the instant, the zone and the day untouched in %s', language => {
    setLocale(language);
    const label = istStamp(INSTANT);
    expect(label).toContain('00:30');
    expect(label).toContain('IST');
    expect(label).toContain('2026');
    expect(label).toContain('18');
    /* A localized day is still the same day: the instant is the source's, and only its rendering moved. */
    expect(istClock(INSTANT)).toBe('00:30');
  });

  it('goes back to the product\u2019s own rendering when the language goes back', () => {
    setLocale('hi');
    expect(istStamp(INSTANT)).not.toBe('18 Sep 2026, 00:30 IST');
    setLocale('en');
    expect(istStamp(INSTANT)).toBe('18 Sep 2026, 00:30 IST');
  });

  it('answers a language it has no formatter for with the default rather than with nothing', () => {
    setLocale('kn');
    expect(istStamp(INSTANT)).toBe('18 Sep 2026, 00:30 IST');
  });

  it('says a missing instant is not supplied in every language', () => {
    setLocale('ta');
    expect(istStamp(null)).toBe('Time not supplied');
    expect(istWindow(null, INSTANT)).toBe('Window not stated');
  });
});

describe('a month by number, for a caller that holds a publisher\u2019s date string', () => {
  it('names the month the reader reads it in', () => {
    expect(monthName(9)).toBe('Sep');
    setLocale('ta');
    expect(monthName(9)).not.toBe('Sep');
    expect(monthName(9)).toMatch(/[^\x00-\x7F]/);
  });

  it('answers an impossible month with nothing rather than throwing', () => {
    expect(monthName(0)).toBe('');
    expect(monthName(13)).toBe('');
    expect(monthName(Number.NaN)).toBe('');
    setLocale('gu');
    expect(monthName(Number.NaN)).toBe('');
    expect(monthName(99)).toBe('');
  });
});

describe('a number, in the reader\u2019s convention', () => {
  it('is never rounded to fit a format', () => {
    /* Intl's default is maximumFractionDigits: 3, which turns 1234.5678 into "1,234.568". Measured on this
       ICU, 20 September 2026. A retrieved value the product cannot reproduce is worse than an unformatted
       one, so this is the assertion that fails if that ceiling is ever dropped. */
    expect(number(1234.5678)).toBe('1,234.5678');
    expect(number(0.3)).toBe('0.3');
    expect(number(38.1)).toBe('38.1');
  });

  it('states absence instead of inventing a zero', () => {
    expect(number(null)).toBe('value not recorded');
    expect(number(undefined)).toBe('value not recorded');
    expect(number(Number.NaN)).toBe('value not recorded');
    expect(count(null, 'task')).toBe('count not recorded');
  });

  it('groups a large count in the Indian convention rather than the English one', () => {
    /* en-IN groups 12,34,567 and en-GB groups 1,234,567; the product is about India, so the first is the
       reader's convention. This is the numeral half of F6d, and it is a difference in grouping and never in
       the value: the four languages the chrome speaks all read digits in Latin numerals. */
    expect(number(1234567)).toBe('12,34,567');
  });

  it('still states a count in words around the number', () => {
    expect(count(1, 'fact')).toBe('1 fact');
    expect(count(3, 'fact')).toBe('3 facts');
    expect(count(1234567, 'fact')).toBe('12,34,567 facts');
  });
});
