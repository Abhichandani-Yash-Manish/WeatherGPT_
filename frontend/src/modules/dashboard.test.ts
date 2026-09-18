import { currentIndex, dayRows, istDate, windowOf } from './dashboard';
import { districtState, defaultDate, publishedDates } from './IndiaWarningMap';

const hours = (values: (number | null)[], start = '2026-09-17T12:00:00Z') =>
  values.map((v, index) => ({ t: new Date(Date.parse(start) + index * 3600_000).toISOString(), v }));

describe('dashboard series helpers', () => {
  it('dates an instant in IST, so 19:00 UTC is already the next day', () => {
    expect(istDate('2026-09-17T18:29:00Z')).toBe('2026-09-17');
    expect(istDate('2026-09-17T18:30:00Z')).toBe('2026-09-18');
    expect(istDate('not a time')).toBe('');
  });

  it('picks the hour that has begun, and the first hour when every hour is later', () => {
    const points = hours([1, 2, 3]);
    expect(currentIndex(points, Date.parse('2026-09-17T13:30:00Z'))).toBe(1);
    expect(currentIndex(points, Date.parse('2026-09-17T08:00:00Z'))).toBe(0);
    expect(currentIndex([], Date.now())).toBe(-1);
  });

  it('groups by IST date, selects returned hours only, and never turns a gap into a value', () => {
    const temperature = { unit: '°C', points: hours([24, null, 30, 22, 21, 20, 19], '2026-09-17T16:00:00Z') };
    const rain = { unit: '%', points: hours([10, 90, null, 40, 5, 5, 5], '2026-09-17T16:00:00Z') };
    const rows = dayRows(temperature, rain);
    expect(rows.map(row => row.date)).toEqual(['2026-09-17', '2026-09-18']);
    expect(rows[0]).toMatchObject({ hours: 3, warmest: { v: 30 }, coolest: { v: 24 }, wettest: { v: 90 } });
    expect(rows[1]).toMatchObject({ hours: 4, warmest: { v: 22 }, coolest: { v: 19 }, wettest: { v: 40 } });
    expect(dayRows({ points: hours([null, null]) }, undefined)[0]).toMatchObject({ hours: 2, warmest: null, coolest: null });
  });

  it('windows the next hours from now, or one IST date', () => {
    const series = { points: hours([1, 2, 3, 4, 5]) };
    expect(windowOf(series, Date.parse('2026-09-17T13:10:00Z'), undefined, 2).map(point => point.v)).toEqual([2, 3]);
    expect(windowOf(series, 0, '2026-09-17').length).toBe(5);
  });
});

describe('district warning states on the map', () => {
  const row = {
    key: 'PUNE', district: 'PUNE', state: 'MAHARASHTRA', bulletin_date: '2026-09-15',
    days: [
      { day: 1, date_local: '2026-09-15', colour: 'yellow', hazards: ['Thunderstorm'] },
      { day: 3, date_local: '2026-09-17', colour: 'green', quiet: true, is_today: true },
      { day: 4, date_local: '2026-09-18', colour: null },
    ],
  };

  it('fills only a published colour, and states every other case in words', () => {
    expect(districtState(row, '2026-09-15')).toMatchObject({ tone: 'yellow', words: 'yellow · Thunderstorm' });
    expect(districtState(row, '2026-09-17')).toMatchObject({ tone: 'green', words: 'green · no warning in this product' });
    expect(districtState(row, '2026-09-18').tone).toBe('unset');
    expect(districtState(row, '2026-09-20').tone).toBe('uncovered');
    expect(districtState(undefined, '2026-09-17').tone).toBe('unmapped');
  });

  it('offers the published dates and opens on the date a bulletin marked as today', () => {
    const dates = publishedDates([row]);
    expect(dates).toEqual(['2026-09-15', '2026-09-17', '2026-09-18']);
    expect(defaultDate([row], dates)).toBe('2026-09-17');
    expect(defaultDate([], ['2026-09-01', '2026-09-02'])).toBe('2026-09-02');
  });
});
