/* Reading returned hourly series for the Workspace dashboard. Every helper here selects values the product
   returned; none computes a new one. A day's "warmest hour" is the returned hour with the highest value, named
   with its own instant, not a daily maximum the product published. */

export type SeriesPoint = { t?: string | null; v?: number | null; source_locator?: string };
export type Series = { unit?: string | null; points?: SeriesPoint[]; model?: string };

const IST_OFFSET_MS = 5.5 * 3600 * 1000;

/** The IST calendar date (YYYY-MM-DD) an instant falls in. */
export function istDate(value?: string | null): string {
  const at = Date.parse(String(value ?? ''));
  return Number.isFinite(at) ? new Date(at + IST_OFFSET_MS).toISOString().slice(0, 10) : '';
}

function valued(point: SeriesPoint): point is SeriesPoint & { v: number; t: string } {
  return typeof point.v === 'number' && Number.isFinite(point.v) && Boolean(point.t);
}

/** Index of the hour that has most recently begun at `now`; the first returned hour when all are later; -1 when empty. */
export function currentIndex(points: SeriesPoint[] | undefined, now: number): number {
  const list = points || [];
  let found = -1;
  list.forEach((point, index) => {
    const at = Date.parse(String(point.t ?? ''));
    if (Number.isFinite(at) && at <= now) found = index;
  });
  return found >= 0 ? found : list.length ? 0 : -1;
}

/** The point of a named series at an index, only when it holds a value. */
export function valueAt(series: Series | undefined, index: number): SeriesPoint | null {
  const point = series?.points?.[index];
  return point && valued(point) ? point : null;
}

export type DayRow = {
  date: string;
  hours: number;
  warmest: SeriesPoint | null;
  coolest: SeriesPoint | null;
  wettest: SeriesPoint | null;
};

/** One row per IST date the temperature series covers, in returned order. */
export function dayRows(temperature: Series | undefined, rainChance: Series | undefined): DayRow[] {
  const rows = new Map<string, DayRow>();
  (temperature?.points || []).forEach(point => {
    const date = istDate(point.t);
    if (!date) return;
    const row = rows.get(date) || { date, hours: 0, warmest: null, coolest: null, wettest: null };
    row.hours += 1;
    if (valued(point)) {
      if (!row.warmest || point.v > (row.warmest.v as number)) row.warmest = point;
      if (!row.coolest || point.v < (row.coolest.v as number)) row.coolest = point;
    }
    rows.set(date, row);
  });
  (rainChance?.points || []).forEach(point => {
    const row = rows.get(istDate(point.t));
    if (row && valued(point) && (!row.wettest || point.v > (row.wettest.v as number))) row.wettest = point;
  });
  return Array.from(rows.values());
}

/** The returned points from the current hour for `hours` entries, or the points of one IST date. */
export function windowOf(series: Series | undefined, now: number, date?: string, hours = 24): SeriesPoint[] {
  const points = series?.points || [];
  if (date) return points.filter(point => istDate(point.t) === date);
  const start = Math.max(0, currentIndex(points, now));
  return points.slice(start, start + hours);
}
