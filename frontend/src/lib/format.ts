/* Formatting helpers that state absence instead of inventing a value. Every one of them is used to
   render tool-owned data; none of them derives a number the engine did not return. */

export function orNot(value: unknown, fallback = 'not recorded'): string {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return text === '' ? fallback : text;
}

export function count(count: number | undefined | null, one: string, many = one + 's'): string {
  if (count === null || count === undefined || !Number.isFinite(count)) return 'count not recorded';
  return count + ' ' + (count === 1 ? one : many);
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
