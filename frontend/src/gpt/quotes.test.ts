import { QUOTES, lineFor, linesFor, nextLine } from './quotes';

/* The corpus on the welcome screen, held to the two rules that make it quotable at all:
   ----------------------------------------------------------------------------
   1. Every line carries the edition its wording was checked against. The rule this file protects is the same
      one the source line under a reading protects: a value nobody can trace is an invented value, and a
      quotation remembered rather than checked is exactly that.
   2. Every line is short enough to sit under a greeting, and the pool a reader is shown always contains at
      least one line, whatever the hour and the month. */

const HOURS = ['daybreak', 'noon', 'golden', 'night'] as const;

describe('a line for the hour', () => {
  const at = new Date('2026-09-19T12:00:00+05:30');

  it('carries its source on every line', () => {
    const missing = QUOTES.filter(quote =>
      !quote.id || !quote.text.trim() || !quote.author.trim() || !quote.work.trim() ||
      !quote.year || !quote.basis.trim());
    expect(missing.map(quote => quote.id || '(no id)')).toEqual([]);
    const ids = QUOTES.map(quote => quote.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('keeps every line short enough for the screen it is printed on', () => {
    const long = QUOTES.filter(quote => quote.text.length > 130).map(quote => quote.id + ' (' + quote.text.length + ')');
    expect(long).toEqual([]);
  });

  it('always has a line for the hour and the month, all year round', () => {
    const empty: string[] = [];
    for (let month = 0; month < 12; month++) {
      for (const day of [1, 15, 28]) {
        for (const hour of HOURS) {
          const when = new Date(Date.UTC(2026, month, day, 6, 30));
          const pool = linesFor(when, hour);
          if (!pool.length || !lineFor(when, hour)) empty.push(month + 1 + '/' + day + ' ' + hour);
        }
      }
    }
    expect(empty).toEqual([]);
  });

  it('prefers a line that belongs to the hour, and falls back rather than failing', () => {
    /* September is monsoon, and a night in September has one line that names the hour. */
    const night = lineFor(at, 'night');
    expect(night.hours === undefined || night.hours.includes('night')).toBe(true);
    /* The same reader at the same hour on the same day sees the same line. */
    expect(lineFor(at, 'noon').id).toBe(lineFor(new Date(at), 'noon').id);
  });

  it('turns the line when a reader asks, and wraps around', () => {
    const first = lineFor(at, 'noon');
    const second = nextLine(first, at, 'noon');
    expect(second.id).not.toBe(first.id);
    let walked = first;
    for (let step = 1; step < linesFor(at, 'noon').length; step++) walked = nextLine(walked, at, 'noon');
    expect(nextLine(walked, at, 'noon').id).toBe(first.id);
  });

  it('never prints a line out of its own season', () => {
    /* "the rainy July" in January would be a lie about the page, not a poem about the weather. */
    const january = new Date('2026-01-15T12:00:00+05:30');
    for (const hour of HOURS) {
      for (const quote of linesFor(january, hour)) {
        if (quote.months) expect(quote.months).not.toContain(1);
        expect(quote.id).not.toBe('tagore-rainy-july');
      }
    }
  });
});
