import { describeNational, editionLabel, readClock } from './overview';

/* The national picture, described once and printed in three places — the Warnings home's landing surface,
   the board's tiles, and the count behind the "Today across India" way in.
   ----------------------------------------------------------------------------
   It used to be the headline of the front door, and these were the front door's tests. The welcome screen no
   longer briefs a reader who asked nothing (docs/112), so the rules travelled with the picture rather than
   being deleted with the screen. Nothing here is a render: these are the four ways the description can lie,
   and each is checked where the sentence is built. */

type Overview = Parameters<typeof describeNational>[0];

function read(national: Record<string, unknown> | undefined, generatedAt: string | null = '2026-09-19T06:30:00+00:00') {
  return {
    data: {
      schema_version: 'product-view-v1',
      view: 'overview',
      status: 'ok',
      generated_at_utc: generatedAt,
      data: { national, radar: { stations: 39, reported: 39 }, places: [] },
      sources: [],
    },
  } as unknown as Overview;
}

describe('the national picture', () => {
  it('never reads an absent today block as a quiet day', () => {
    const picture = describeNational(read({ districts: 756, bulletin_date: '2026-09-15' }));
    expect(picture.statedToday).toBe(false);
    /* And it does not print a zero where nothing was stated: the counts stay at nothing. */
    expect(picture.severe).toBe(0);
    expect(picture.yellow).toBe(0);
    expect(picture.green).toBe(0);
  });

  it('treats an empty count block as unstated too', () => {
    expect(describeNational(read({ districts: 756, today: { counts: {} } })).statedToday).toBe(false);
  });

  it('prints the counts a read stated, zeros included', () => {
    const picture = describeNational(read({
      districts: 756,
      today: { counts: { red: 0, orange: 3, yellow: 298, green: 445 }, districts_with_no_day_covering_today: 5 },
      bulletin_date: '2026-09-15',
      newest_bulletin_date_in_this_read: '2026-09-15',
      districts_behind_the_newest_edition: 14,
    }));
    expect(picture.statedToday).toBe(true);
    expect(picture.severe).toBe(3);
    expect(picture.yellow).toBe(298);
    expect(picture.green).toBe(445);
    expect(picture.behind).toBe(14);
    expect(picture.noDay).toBe(5);
  });

  it('carries the read time on the provenance line, in IST', () => {
    const picture = describeNational(read({ districts: 756, today: { counts: { yellow: 1 } }, bulletin_date: '2026-09-15' }));
    expect(picture.readAt).toBe('12:00 IST');
    expect(picture.sourceLine).toContain('read 12:00 IST');
    /* The edition is printed only where the read stated one. */
    expect(picture.sourceLine).toContain('15 Sep edition');
    const unstated = describeNational(read({ districts: 756, today: { counts: { yellow: 1 } }, bulletin_date: null }));
    expect(unstated.sourceLine).toContain('edition not stated');
    expect(unstated.sourceLine).not.toContain('null');
  });

  it('prints no provenance at all before a read has answered', () => {
    expect(describeNational({ data: undefined } as unknown as Overview).sourceLine).toBeNull();
  });

  it('formats an edition and a clock only from values it was given', () => {
    expect(editionLabel(null)).toBeNull();
    expect(editionLabel('2026-09-15')).toBe('15 Sep');
    expect(readClock('not a date')).toBeNull();
    expect(readClock('2026-09-19T06:30:00+00:00')).toBe('12:00 IST');
  });
});
