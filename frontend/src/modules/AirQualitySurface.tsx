/* Air quality: what the CAMS delivery models for one grid cell, parameter by parameter, with the unit
   the source returned and the cell the values describe. A model value is not a monitor measurement and
   not an observation; an index is not a concentration; a parameter the payload returned without a value
   is 'not recorded for this cell', never a zero and never clean air. The cell distance is the payload's
   own value, and a distance the payload does not state is not recorded here rather than computed. */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { viewById } from '../shell/views';
import { DataTable, Facts, NO_ROW, NOT_RECORDED, PlacePicker, SurfaceShell, type PlaceChoice } from './Evidence';

type Series = { unit?: string | null; aggregation?: string | null; model?: string | null; quality_flags?: string[]; category?: string | null;
  points?: { t?: string | null; v?: number | null }[] };
type AirData = {
  parameters?: Record<string, Series>; current?: Record<string, number | null> | null; domain?: string | null;
  grid?: { latitude?: number; longitude?: number } | null;
  requested?: { label?: string | null; latitude?: number; longitude?: number } | null;
  time_basis?: string | null; grid_distance_km?: number | null;
};

export const intents: string[] = (viewById('air-quality')?.intents ?? []).concat([
  'Which modelled parameters does this cell carry, and how far is the cell from the point I named?',
]);

const DAY_CHOICES = ['1', '2', '3'];
const CELL_MISSING = 'not recorded for this cell';
/* The one paragraph this surface must say in its own voice, whichever read answered. */
const MODEL_NOT_MONITOR = 'This is a model, not a monitor, and not an observation: the values are modelled output for a grid '
  + 'cell of that model. The cell is a grid cell, not the point you named, and its distance from the requested point is '
  + 'stated above — as the payload\u2019s own value, or as absent where the payload states none. No health or exposure advice '
  + 'is produced here. An AQI category is shown only where the payload itself states one, printed beside the value in the '
  + 'payload\u2019s own wording; a payload that states no category is shown with none.';

function pair(point?: { latitude?: number | null; longitude?: number | null } | null): string {
  if (!point || point.latitude === null || point.latitude === undefined) return NOT_RECORDED;
  if (point.longitude === null || point.longitude === undefined) return NOT_RECORDED;
  return point.latitude + ', ' + point.longitude;
}

export function Surface(): JSX.Element {
  const [place, setPlace] = useState<PlaceChoice | null>(null);
  const [days, setDays] = useState('3');
  const read = useQuery({
    queryKey: ['air-quality', place?.latitude, place?.longitude, days],
    queryFn: () => getJson<Envelope<AirData>>(withQuery('/api/air-quality', { lat: place?.latitude, lon: place?.longitude, days })),
    enabled: place !== null, retry: false,
  });

  const data = read.data?.data;
  const names = Array.from(new Set(Object.keys(data?.parameters || {}).concat(Object.keys(data?.current || {}))));
  /* The cell distance is a payload value; it is read from the view's own field or from the coverage the
     view passes through, and it is never derived from the two coordinate pairs here. */
  const stated = data?.grid_distance_km ?? read.data?.coverage?.grid_distance_km;

  function cellValue(name: string): string {
    const current = data?.current;
    if (!current || !(name in current)) return CELL_MISSING;
    const value = current[name];
    return value === null || value === undefined ? CELL_MISSING : String(value);
  }

  return (
    <SurfaceShell
      title="Air quality"
      lead="Modelled CAMS air quality for one grid cell: the parameters this read returned, in the source's own units, with the cell the values describe and its distance from the point you named."
      what="the modelled air-quality read" envelope={place ? read.data : undefined} busy={place !== null && read.isPending}
      error={place ? read.error : undefined} onRetry={() => read.refetch()} intents={intents}
    >
      <section className="module-section">
        <h2>The point and the cell</h2>
        <PlacePicker onPick={setPlace} hint="Name a place and choose a row; the air-quality model is then read for those coordinates." />
        <div className="module-controls">
          <label className="module-field" htmlFor="air-quality-days">
            <span>Days requested</span>
            <select id="air-quality-days" value={days} onChange={event => setDays(event.target.value)}>
              {DAY_CHOICES.map(value => <option key={value} value={value}>{value} day{value === '1' ? '' : 's'}</option>)}
            </select>
          </label>
        </div>
        {!place ? (
          <p className="module-note">No point was named, so no air-quality read was requested.</p>
        ) : (
          <>
            <Facts testId="air-quality-cell" rows={[
              ['Point named', place.label || 'label not recorded'],
              ['Requested coordinates', place.latitude + ', ' + place.longitude],
              ['Cell identity as returned', pair(data?.grid)],
              ['Requested point as the reading returned it', pair(data?.requested)],
              ['Cell distance from the requested point', typeof stated === 'number' ? stated + ' km' : NOT_RECORDED],
              ['Domain as returned', orNot(data?.domain)],
              ['Time basis', orNot(data?.time_basis)],
            ]} />
            <p className="module-note">
              The cell identity and its distance are the payload&rsquo;s own values. A distance this read does not state is
              recorded as absent here; it is never computed from the two coordinate pairs.
            </p>
          </>
        )}
      </section>

      {place && !read.isPending && !read.isError ? (
        <section className="module-section">
          <h2>The parameters</h2>
          <p className="module-note" data-testid="air-quality-model-not-monitor">{MODEL_NOT_MONITOR}</p>
          <p className="module-note" role="status" data-testid="air-quality-count">
            {count(names.length, 'parameter row')} returned for this cell. A parameter this payload returned without a value
            reads as &lsquo;{CELL_MISSING}&rsquo;: never a zero, and never clean air.
          </p>
          <DataTable testId="air-quality-table" caption="One row per parameter this read returned, in the unit the source stated, with the source's own current-instant value."
            columns={['Parameter', 'Unit as returned', 'Value at the source current hour', 'Points in the returned series', 'Points holding no value', 'Quality flags as returned']}
            rows={names.map(name => {
              const series = data?.parameters?.[name];
              const points = series?.points || [];
              const category = typeof series?.category === 'string' && series.category.trim() ? series.category.trim() : '';
              return [
                name,
                orNot(series?.unit, 'unit not stated by the source'),
                cellValue(name) + (category ? ' · category as stated: ' + category : ''),
                count(points.length, 'point'),
                String(points.filter(point => point.v === null || point.v === undefined).length),
                orNot((series?.quality_flags || []).join(', '), 'no flag returned'),
              ];
            })} />
          {names.length ? null : (
            <p className="module-note">
              {NO_ROW}: no air-quality parameter was returned for this cell. That is a missing reading, not clean air.
            </p>
          )}
        </section>
      ) : null}
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
