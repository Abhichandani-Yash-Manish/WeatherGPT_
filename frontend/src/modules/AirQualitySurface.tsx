/* Air quality: what the CAMS delivery models for one grid cell, parameter by parameter, with the unit
   the source returned and the cell the values describe. A model value is not a monitor measurement and
   not an observation; an index is not a concentration; a parameter the payload returned without a value
   is 'not recorded for this cell', never a zero and never clean air. The cell distance is the payload's
   own value, and a distance the payload does not state is not recorded here rather than computed.

   Who this surface is for, and the line it may not cross: a reader who has one number — an index — and
   wants it interpreted, in a product that is not allowed to turn it into health advice. So the reading
   names every index the source itself publishes for this cell, prints the source's own category word
   whenever the payload carries one, and puts the concentrations the same hour was built from beside it.
   Measured against the live read on 21 September 2026: the payload returns us_aqi 160 and european_aqi 68
   for Delhi and carries no category field at all, so a line built around a single index and a single
   category could only ever answer "the source states no category for this reading" — honest, and no
   interpretation for a reader who came for one. What is added is the source's own other index and its own
   concentrations; what is NOT added is a band, a risk word, an action or any "should". */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { viewById } from '../shell/views';
import {
  Awaiting, DataTable, Facts, Meaning, NO_ROW, NOT_RECORDED, PlacePicker, ReadingFor, SurfaceShell,
  readWorkingPlace, type PlaceChoice,
} from './Evidence';

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

/* The first-screen reading: every index the source itself publishes for this cell at the read's current
   hour, the source's own category word wherever the payload carries one, and the concentrations the same
   hour was built from. This is the line X1 forbids this surface from writing itself — "report the index
   and the provider's own category, never health advice or a protective action" — so a category appears
   only when the payload states one, and a reading with none says so rather than inventing a
   plain-language band. Naming MORE THAN one index is not decoration: measured on the live read, this
   payload returns a US index and a European index for the same cell and the same hour, and a reader shown
   one number would take it for the air rather than for one provider's scale. */
function list(words: string[]): string {
  if (words.length <= 1) return words[0] || '';
  return words.slice(0, -1).join(', ') + ' and ' + words[words.length - 1];
}

function indexHeadline(names: string[], data: AirData | undefined, cellValue: (name: string) => string,
  distance: number | null | undefined, model: string | null | undefined): { statement: string; source: string } {
  const source = 'model ' + orNot(model) + ' · domain ' + orNot(data?.domain) + ' · cell ' + pair(data?.grid)
    + ' · distance as returned: ' + (typeof distance === 'number' ? distance + ' km' : NOT_RECORDED)
    + ' · time basis ' + orNot(data?.time_basis);
  if (!names.length) return { statement: 'This read returned no air-quality parameter for this cell.', source };

  const category = (name: string) => {
    const stated = data?.parameters?.[name]?.category;
    return typeof stated === 'string' && stated.trim() ? stated.trim() : '';
  };
  const withUnit = (name: string) => {
    const value = cellValue(name);
    if (value === CELL_MISSING) return name + ' ' + value;
    const unit = data?.parameters?.[name]?.unit;
    return name + ' ' + value + (unit ? ' ' + unit : '');
  };

  const indices = names.filter(name => /aqi/i.test(name));
  if (!indices.length) {
    return {
      statement: 'This read returned no index for this cell. The parameters it returned are ' + list(names.slice(0, 4)) + '.',
      source,
    };
  }
  const statedIndices = indices.map(name => {
    const word = category(name);
    return withUnit(name) + (word ? ' (the source’s own category for it: “' + word + '”)' : '');
  });
  const concentrations = names.filter(name => !/aqi/i.test(name)).slice(0, 3).map(withUnit);
  const anyCategory = indices.some(name => Boolean(category(name)));

  return {
    statement: 'For this cell at the read’s current hour the source returns ' + list(statedIndices) + '.'
      + (concentrations.length ? ' The concentrations it returns for the same hour are ' + list(concentrations) + '.' : '')
      + (anyCategory ? '' : ' The source states no category for this reading, so none is printed here and this product adds none.'),
    source,
  };
}

export function Surface(): JSX.Element {
  const [place, setPlace] = useState<PlaceChoice | null>(() => readWorkingPlace());
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

  const answered = place !== null && !read.isPending && !read.isError;
  const headline = answered ? indexHeadline(names, data, cellValue, typeof stated === 'number' ? stated : null, data?.parameters?.[names[0]]?.model) : null;

  /* The controls a reader used to ask for this read. They are rendered in every state — while the read is
     in flight and after it has failed — so the place a reader just chose cannot disappear from under them
     at the moment they act. */
  const ask = (
    <section className="module-section">
      <h2>The point and the cell</h2>
      {place ? <ReadingFor place={place} /> : null}
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
        <Awaiting testId="air-quality-awaiting">
          Nothing has been read yet. Name a place below and this surface reads the air-quality cell that answers it: the
          index the source itself publishes for that cell, the concentrations it returns with it, and how far the cell is
          from your point.
        </Awaiting>
      ) : null}
      {/* The control block survives a read in flight, so the facts below it are drawn only once this read has
          answered: a cell printed while the read is working would be an absence this surface has not
          established. */}
      {place && !read.isPending && !read.isError ? (
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
        </>
      ) : null}
    </section>
  );

  return (
    <SurfaceShell
      title="Air quality"
      lead="What the air-quality model states for the grid cell that answers your point: the source's own indices, its own concentrations, and the cell they describe."
      what="the modelled air-quality read" envelope={place ? read.data : undefined} busy={place !== null && read.isPending}
      error={place ? read.error : undefined} onRetry={() => read.refetch()} intents={intents}
      reading={headline ? { testId: 'air-quality-headline', statement: headline.statement, source: headline.source } : undefined}
      hold={ask}
    >
      {place && !read.isPending && !read.isError ? (
        <section className="module-section">
          <h2>The parameters</h2>
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

      {/* Under the numbers, folded: the one paragraph this surface must say in its own voice, unchanged,
          plus the two boundaries that used to sit in the middle of the first screen. */}
      <Meaning
        testId="air-quality-model-not-monitor"
        summary="What these values are, and what this surface will not do with them"
        lines={[
          { text: MODEL_NOT_MONITOR },
          { text: 'The cell identity and its distance are the payload\u2019s own values. A distance this read does not state is recorded as absent here; it is never computed from the two coordinate pairs.' },
        ]}
      />
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
