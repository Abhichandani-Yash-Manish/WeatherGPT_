/* Formatting helpers that state absence instead of inventing a value. Every one of them is used to
   render tool-owned data; none of them derives a number the engine did not return.

   Numbers are formatted in the reader's locale (lib/locale.ts) and are never rounded: see the ceiling below,
   which exists because Intl's default would change a retrieved value. */

import { currentLocale } from './locale';

/* Intl's ceiling, and it is here for exactly one reason: the default maximumFractionDigits is 3, so
   formatting 1234.5678 without this option returns "1,234.568" - a value rounded to fit a format. A number
   the product cannot reproduce is worse than one it does not format at all. Verified with the ICU this
   workspace runs, 20 September 2026: with the ceiling, 0.3 stays "0.3" and 1234.5678 stays "1,234.5678". */
const MAX_FRACTION_DIGITS = 20;

const numberFormats = new Map<string, Intl.NumberFormat>();

function numberFormat(locale: string): Intl.NumberFormat {
  let format = numberFormats.get(locale);
  if (!format) {
    format = new Intl.NumberFormat(locale, { maximumFractionDigits: MAX_FRACTION_DIGITS });
    numberFormats.set(locale, format);
  }
  return format;
}

/* A number for presentation: a count, a tally, an index. NOT a retrieved measurement - a measurement is
   rendered as the source stated it, and this formatter's job is the reader's convention (Indian grouping),
   not the value. */
export function number(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'value not recorded';
  return numberFormat(currentLocale()).format(value);
}

export function orNot(value: unknown, fallback = 'not recorded'): string {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return text === '' ? fallback : text;
}

export function count(count: number | undefined | null, one: string, many = one + 's'): string {
  if (count === null || count === undefined || !Number.isFinite(count)) return 'count not recorded';
  return number(count) + ' ' + (count === 1 ? one : many);
}

export function worstColour(tally?: Record<string, number>): { colour: string; count: number } | null {
  if (!tally) return null;
  for (const colour of ['red', 'orange', 'yellow', 'green']) {
    const value = tally[colour];
    if (typeof value === 'number' && value > 0) return { colour, count: value };
  }
  return null;
}

export function shortHash(value?: string | null, length = 12): string {
  if (!value) return 'not recorded';
  return value.length <= length ? value : value.slice(0, length) + '\u2026';
}

export function titleCase(value?: string | null): string {
  if (!value) return '';
  return value.replace(/[_-]+/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase());
}

export function listInWords(values?: (string | undefined | null)[]): string {
  const items = (values || []).filter((item): item is string => Boolean(item && String(item).trim()));
  if (!items.length) return '';
  if (items.length === 1) return items[0];
  return items.slice(0, -1).join(', ') + ' and ' + items[items.length - 1];
}
