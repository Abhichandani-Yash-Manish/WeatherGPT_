/* The payloads the served chart engine takes, built from the reads this build already makes.

   These are ports of the builders the vanilla frontend used (`web/panels.js` before commit 486c403), so the figures
   draw the same products from the same fields. Nothing is computed that the source did not return: a parameter the
   read did not carry is absent from the drawing and from its exact-value table, never estimated from another
   parameter or from the previous hour. */
import { istStamp } from '../lib/time';

type Point = { t?: string | null; v?: number | string | null; source_locator?: string | null };
type Series = { unit?: string | null; points?: Point[] };
type Parameters = Record<string, Series | undefined>;

export type MeteogramHour = {
  t: string;
  label: string;
  evidence: Record<string, string>;
  temperature?: number | string | null;
  rain?: number | string | null;
  wind_speed?: number | string | null;
  humidity?: number | string | null;
  wind_direction?: number | string | null;
  night?: boolean;
};

/* Three independent series on one axis: temperature, rain and wind, with humidity and wind direction where the read
   carried them. An hour is night when its IST clock falls before 06:00 or at or after 19:00. */
export function meteogramSpec(parameters: Parameters, title?: string): Record<string, unknown> | null {
  const temperature = parameters.temperature_2m || parameters.apparent_temperature || null;
  const rain = parameters.precipitation || parameters.rain || null;
  const wind = parameters.wind_speed_10m || parameters.wind_speed || null;
  const humidity = parameters.relative_humidity_2m || parameters.relative_humidity || null;
  if (!temperature && !rain && !wind) return null;

  const hours: MeteogramHour[] = [];
  const index = new Map<string, MeteogramHour>();
  const collect = (bucket: Series | null, field: 'temperature' | 'rain' | 'wind_speed' | 'humidity', evidenceKey: string) => {
    (bucket?.points || []).forEach(point => {
      if (!point.t) return;
      let entry = index.get(point.t);
      if (!entry) {
        entry = { t: point.t, label: istStamp(point.t), evidence: {} };
        index.set(point.t, entry);
        hours.push(entry);
      }
      entry[field] = point.v;
      if (point.source_locator) entry.evidence[evidenceKey] = point.source_locator;
    });
  };
  collect(temperature, 'temperature', 'temperature');
  collect(rain, 'rain', 'rain');
  collect(wind, 'wind_speed', 'wind');
  collect(humidity, 'humidity', 'humidity');

  const direction = parameters.wind_direction_10m || parameters.wind_direction || null;
  (direction?.points || []).forEach(point => {
    const entry = point.t ? index.get(point.t) : undefined;
    if (entry) entry.wind_direction = point.v;
  });
  if (!hours.length) return null;

  hours.sort((left, right) => Date.parse(left.t) - Date.parse(right.t));
  hours.forEach(hour => {
    const ist = new Date(Date.parse(hour.t) + 5.5 * 3600 * 1000);
    const clock = ist.getUTCHours();
    hour.night = clock < 6 || clock >= 19;
  });

  return {
    title: title || 'Meteogram · ' + hours.length + ' hour(s)',
    temperature_unit: temperature?.unit || '',
    rain_unit: rain?.unit || '',
    wind_unit: wind?.unit || '',
    hours,
  };
}

/* The three lanes of one right-now reading: what a station observed (an instant), what the district product published
   (a window) and what the model holds next (model output). A lane is built only when its part carried a timestamp. */
type StationParameter = { field?: string; name?: string; value?: number | string | null };
type Station = { name?: string; station_code?: string; distance_km?: number | null; observed_at_utc?: string; source_id?: string; parameters?: StationParameter[] };
type InForce = { status?: string; starts_utc?: string; ends_utc?: string; colour?: string | null; status_line?: string; source_id?: string };
type HourRow = { at?: string; temperature_2m?: number | null };
type Reading = {
  observed?: { stations?: Station[] };
  in_force?: InForce;
  next_hours?: { rows?: HourRow[]; source_id?: string };
  generated_at_utc?: string;
};

export function nowLanes(reading: Reading): Record<string, unknown>[] {
  const lanes: Record<string, unknown>[] = [];
  const station = (reading.observed?.stations || [])[0] || null;
  const day = reading.in_force || {};
  const hours = reading.next_hours?.rows || [];

  if (station && station.observed_at_utc) {
    lanes.push({
      key: 'observed', label: 'Observed', kind: 'observed', from: station.observed_at_utc,
      detail: [
        station.name || station.station_code,
        station.distance_km === null || station.distance_km === undefined ? null : Math.round(station.distance_km * 10) / 10 + ' km away',
        (station.parameters || []).slice(0, 2).map(entry => (entry.field || entry.name) + ' ' + entry.value).join(', '),
      ].filter(Boolean).join(' · '),
      source: station.source_id || 'source not stated',
    });
  }
  if (day.status === 'ok' && day.starts_utc && day.ends_utc) {
    lanes.push({
      key: 'published', label: 'Published', kind: 'published', from: day.starts_utc, to: day.ends_utc,
      colour: day.colour, detail: day.status_line || 'the product stated a colour without wording', source: day.source_id || 'source not stated',
    });
  }
  if (hours.length) {
    const first = hours[0];
    const last = hours[hours.length - 1];
    const at = (row: HourRow) => (row.temperature_2m === undefined || row.temperature_2m === null ? 'temperature not returned' : row.temperature_2m + ' °C');
    lanes.push({
      key: 'model', label: 'Model next', kind: 'model', from: first.at, to: last.at,
      detail: hours.length + ' hour(s) returned, ' + at(first) + ' at the first hour and ' + at(last) + ' at the last',
      source: reading.next_hours?.source_id || 'source not stated',
    });
  }
  return lanes;
}

export function nowBandSpec(reading: Reading, place: string | null, note: string): Record<string, unknown> | null {
  const lanes = nowLanes(reading);
  if (!lanes.length) return null;
  return { title: 'Now', place, read_at: reading.generated_at_utc, note, lanes };
}

/* The published days at a place, with the model hours counted into the IST day their timestamp falls in and the
   station that reported on one of them. The days are the product's own; no boundary is invented. */
export function dayTimelineSpec(days: unknown[], reading: Reading | null, title: string): Record<string, unknown> | null {
  if (!days || !days.length) return null;
  const station = (reading?.observed?.stations || [])[0] || null;
  return {
    title,
    days,
    hours: reading?.next_hours?.rows || [],
    observed: station && station.observed_at_utc
      ? {
          label: (station.name || station.station_code || 'a station') +
            (station.distance_km === null || station.distance_km === undefined ? '' : ', ' + Math.round(station.distance_km * 10) / 10 + ' km away'),
          at: station.observed_at_utc,
        }
      : null,
    read_at: reading?.generated_at_utc || null,
  };
}

/* The published product as a grid: rows ordered by the colour the source printed (its own rank, never a score), then
   by name. Only the first `limit` rows are drawn; the table below the figure still lists every district. */
const COLOUR_RANK: Record<string, number> = { red: 4, orange: 3, yellow: 2, green: 1 };

type MatrixDay = { day?: number | string; date_utc?: string; date_local?: string; colour?: string | null };
type MatrixRow = { district?: string; state?: string; days?: MatrixDay[] };

export function warningMatrixSpec(districts: MatrixRow[], limit: number, onOpen?: (row: MatrixRow) => void): Record<string, unknown> | null {
  if (!districts.length) return null;
  const worst = (row: MatrixRow) => (row.days || []).reduce((best, day) => Math.max(best, COLOUR_RANK[String(day.colour || '').toLowerCase()] || 0), 0);
  const ranked = districts.slice().sort((left, right) => (worst(right) - worst(left)) || String(left.district).localeCompare(String(right.district)));
  const header = (districts[0].days || []).map(day => ({ key: day.day, label: 'Day ' + day.day, date: day.date_utc || day.date_local }));
  if (!header.length) return null;
  return {
    title: 'Colour printed per district-day',
    days: header,
    rows: ranked.slice(0, limit),
    onOpen,
    footnote: 'Showing the ' + Math.min(limit, ranked.length) + ' district(s) with the strongest published colour first, then by name. ' +
      'The table below lists every district this read returned. A cell is the colour the product printed, not a verdict, and never an all-clear.',
  };
}

/* The ensemble members as a distribution: the band is p10 to p90, the heavy line the median, the whiskers min to max.
   Built only from the statistics the read returned for the chosen variable. */
export function ensembleFanSpec(parameters: Parameters, variable: string, model: string | null, memberTotal: number | undefined, statistics: unknown): Record<string, unknown> | null {
  const kinds = ['p10', 'p50', 'p90', 'mean', 'min', 'max'];
  if (!kinds.some(kind => parameters[variable + '_' + kind])) return null;
  const pointsOf = (key: string) => (parameters[key]?.points || []).map(point => ({
    t: point.t, label: point.t ? istStamp(point.t) : '', value: point.v, source_locator: point.source_locator,
  }));
  const unit = parameters[variable + '_p50']?.unit || parameters[variable + '_mean']?.unit || '';
  return {
    title: variable.replace(/_/g, ' ') + ' member distribution · ' + (model || 'model not stated'),
    note: 'The returned members as a distribution: the shaded band is p10 to p90, the heavy line the median, the thin whiskers min to max. ' +
      'Spread is not a probability or a skill score.',
    unit,
    p10: pointsOf(variable + '_p10'), p50: pointsOf(variable + '_p50'), p90: pointsOf(variable + '_p90'),
    mean: pointsOf(variable + '_mean'), min: pointsOf(variable + '_min'), max: pointsOf(variable + '_max'),
    member_total: memberTotal, statistics,
  };
}

/* The indexed editions as cards: what each one is, when it was printed, how much text it carries and whether the
   saved body is still held. */
export function libraryCardsSpec(documents: unknown[], limit: number, onOpen?: (document: unknown) => void): Record<string, unknown> | null {
  if (!documents.length) return null;
  return {
    title: 'The library',
    note: 'The editions on this page as cards: what it is, when it was printed, how much text it carries and whether the saved body is still held.',
    documents: documents.slice(0, limit),
    onOpen,
  };
}
