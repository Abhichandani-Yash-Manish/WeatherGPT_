/* Compare places: two point forecasts, each fetched by its own read of GET /api/forecast for its own
   place and the chosen window, held side by side. Each read keeps its own instant, coverage, limits and
   source rows; an absent parameter or point is stated for that read. Not a ranking or a skill claim. */
import { useState } from 'react';
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import { DataTable, EvidenceFooter, Facts, Failure, NO_ROW, NOT_RECORDED, PlacePicker, Reading, SurfaceShell, type PlaceChoice } from './Evidence';

type SeriesPoint = { t?: string | null; v?: number | string | null };
type Series = { unit?: string | null; model?: string | null; aggregation?: string | null; points?: SeriesPoint[]; quality_flags?: string[] };
type Grid = { latitude?: number | null; longitude?: number | null } | null | undefined;
type ForecastData = { requested?: Grid; grid?: Grid; parameters?: Record<string, Series>; days?: number | null;
  source_family?: string | null; time_basis?: string | null };
type ForecastEnvelope = Envelope<ForecastData>;
type ReadState = 'pending' | 'failed' | 'ok';
type Comparison = { key: string; t?: string | null; first?: SeriesPoint; second?: SeriesPoint };

export const intents: string[] = (viewById('compare')?.intents ?? []).concat([
  'Which parameter or point did one of the two reads not return?', 'Were the two point forecasts retrieved at the same time?',
]);

const DAY_CHOICES = ['1', '2', '3', '5', '7'];

const placeName = (place: PlaceChoice | null, ordinal: string): string => orNot(place?.label, ordinal + ' place label not recorded');
function coordinateText(block: Grid): string {
  if (!block || [block.latitude, block.longitude].some(value => value === null || value === undefined)) return NOT_RECORDED;
  return block.latitude + ', ' + block.longitude;
}

/* The union of the instants either read returned, in the order they first appeared. A point whose own
   instant was not recorded cannot be matched to the other read's, so it keeps a row of its own. */
function unionInstants(first: SeriesPoint[] | undefined, second: SeriesPoint[] | undefined): Comparison[] {
  const order: string[] = [];
  const rows = new Map<string, Comparison>();
  const add = (points: SeriesPoint[] | undefined, side: 'first' | 'second') => {
    let unnamed = 0;
    (Array.isArray(points) ? points : []).forEach(point => {
      const stated = typeof point.t === 'string' && point.t.trim() ? point.t : null;
      const key = stated || side + ':instant-not-recorded:' + unnamed++;
      const row = rows.get(key) || { key, t: stated };
      rows.set(key, row);
      if (!order.includes(key)) order.push(key);
      row[side] = point;
    });
  };
  add(first, 'first'); add(second, 'second');
  return order.map(key => rows.get(key) as Comparison);
}

function seriesLine(place: PlaceChoice | null, ordinal: string, series: Series | undefined, state: ReadState): string {
  const label = placeName(place, ordinal);
  if (state === 'pending') return label + ': this read has not answered yet';
  if (state === 'failed') return label + ': this read did not answer';
  if (!series) return label + ': ' + NO_ROW + ' for this parameter in this read';
  const flags = series.quality_flags || [];
  const tail = [series.model ? 'model ' + series.model : '', series.aggregation ? 'aggregation ' + series.aggregation : '',
    flags.length ? 'quality flags ' + flags.join(', ') : ''].filter(Boolean);
  const points = Array.isArray(series.points) ? count(series.points.length, 'point') + ' returned' : 'points not recorded in this read';
  return label + ': ' + points + ' · unit ' + (series.unit || NOT_RECORDED) + (tail.length ? ' · ' + tail.join(' · ') : '');
}

function valueText(point: SeriesPoint | undefined, series: Series | undefined, state: ReadState): string {
  if (state === 'pending' || state === 'failed') return state === 'pending' ? 'this read has not answered yet' : 'this read did not answer';
  if (!series) return NO_ROW + ' for this parameter in this read';
  if (!point) return 'no point returned for this instant';
  if (point.v === null || point.v === undefined) return 'no value returned for this point';
  return String(point.v) + (series.unit ? ' ' + series.unit : ' · unit ' + NOT_RECORDED);
}

function noRowsReason(firstState: ReadState, secondState: ReadState): string {
  const reasons = [firstState === 'pending' || secondState === 'pending' ? 'a read has not answered yet' : '',
    firstState === 'failed' || secondState === 'failed' ? 'a read did not answer' : ''].filter(Boolean);
  return reasons.length ? 'No parameter row is drawn: ' + reasons.join(' and ') + '.' : NO_ROW + ': neither read returned a parameter series.';
}

function ReadEvidence({ ordinal, testId, place, query, days, what }: { ordinal: string; testId: string; place: PlaceChoice; query: UseQueryResult<ForecastEnvelope, Error>; days: string; what: string }): JSX.Element {
  const envelope = query.data;
  const data = envelope?.data;
  return (
    <section className="module-section" data-testid={testId}>
      <h2>What the {ordinal} read returned</h2>
      <p className="module-note">
        This read is its own call to GET /api/forecast for {placeName(place, ordinal)}; it may have been retrieved at a different time from the other read, and its own generated_at_utc, limits and source rows are stated here.
      </p>
      {query.isPending ? (
        <Reading what={what} />
      ) : query.isError ? (
        <Failure error={query.error} what={what} onRetry={() => query.refetch()} />
      ) : (
        <>
          <Facts
            testId={testId + '-facts'}
            rows={[
              ['Place named for this read', placeName(place, ordinal)],
              ['Coordinates the surface asked with', place.latitude + ', ' + place.longitude],
              ['Coordinates as the reading returned them', coordinateText(data?.requested)],
              ['Grid as the reading returned it', coordinateText(data?.grid)],
              ['Days as the reading returned them', orNot(data?.days, days)],
              ['Time basis as returned', orNot(data?.time_basis)],
              ['Generated at, as returned', envelope?.generated_at_utc ? istStamp(envelope.generated_at_utc) : NOT_RECORDED],
              ['View and status as returned', orNot(envelope?.view) + ' · status ' + orNot(envelope?.status)],
              ['Source rows attached to this read', count(envelope?.sources?.length, 'source row')],
            ]}
          />
          {envelope ? <EvidenceFooter envelope={envelope} /> : null}
        </>
      )}
    </section>
  );
}

export function Surface(): JSX.Element {
  const [first, setFirst] = useState<PlaceChoice | null>(null);
  const [second, setSecond] = useState<PlaceChoice | null>(null);
  const [days, setDays] = useState('3');

  const firstRead = useQuery({
    queryKey: ['compare-forecast', 'first', first?.latitude, first?.longitude, days],
    queryFn: () => getJson<ForecastEnvelope>(withQuery('/api/forecast', { lat: first?.latitude, lon: first?.longitude, days })),
    enabled: first !== null,
    retry: false,
  });
  const secondRead = useQuery({
    queryKey: ['compare-forecast', 'second', second?.latitude, second?.longitude, days],
    queryFn: () => getJson<ForecastEnvelope>(withQuery('/api/forecast', { lat: second?.latitude, lon: second?.longitude, days })),
    enabled: second !== null,
    retry: false,
  });

  const firstState: ReadState = firstRead.isPending ? 'pending' : firstRead.isError ? 'failed' : 'ok';
  const secondState: ReadState = secondRead.isPending ? 'pending' : secondRead.isError ? 'failed' : 'ok';
  const firstData = firstRead.data?.data;
  const secondData = secondRead.data?.data;
  const names = Array.from(new Set([...Object.keys(firstData?.parameters || {}), ...Object.keys(secondData?.parameters || {})]));
  const bothChosen = first !== null && second !== null;

  return (
    <SurfaceShell
      title="Compare places"
      lead="Two model point forecasts from two separate reads, one per place, held side by side with each read's own instant, unit and source rows. Model hours are not observations. A comparison of two printed outputs, not a ranking and not a skill claim."
      what="the two point forecasts"
      busy={false}
    >
      <section className="module-section">
        <h2>The two reads</h2>
        <div className="module-controls">
          <label className="module-field" htmlFor="compare-days">
            <span>Days requested from each read</span>
            <select id="compare-days" value={days} onChange={event => setDays(event.target.value)}>
              {DAY_CHOICES.map(value => <option key={value} value={value}>{value} day{value === '1' ? '' : 's'}</option>)}
            </select>
          </label>
        </div>
        <p className="module-note" data-testid="compare-boundary">
          The two columns below come from two separate reads of GET /api/forecast, one per place, that may have been retrieved at
          different times; each read states its own generated_at_utc in its own section below. This is a comparison of two printed
          outputs. It is not a ranking, a recommendation, a better-or-worse judgement or a claim about forecast skill. Each value is
          the point-forecast product's own model output, not an observation. A parameter or an instant that one read did not return
          is stated as absent for that read, never omitted from the row and never filled with a zero.
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-4)', alignItems: 'flex-start' }}>
          <div style={{ flex: '1 1 24rem', minWidth: 0 }}>
            <h3>First read</h3>
            <PlacePicker onPick={setFirst} hint="Name the first place and choose a row; this read asks GET /api/forecast for that point alone." />
            {first ? <p className="module-note" role="status">Chosen for the first read: {placeName(first, 'first')} · {first.latitude}, {first.longitude}</p>
              : <p className="module-note">No place has been chosen for the first read, so no forecast was requested for it.</p>}
          </div>
          <div style={{ flex: '1 1 24rem', minWidth: 0 }}>
            <h3>Second read</h3>
            <PlacePicker onPick={setSecond} hint="Name the second place and choose a row; this read asks GET /api/forecast for that point alone." />
            {second ? <p className="module-note" role="status">Chosen for the second read: {placeName(second, 'second')} · {second.latitude}, {second.longitude}</p>
              : <p className="module-note">No place has been chosen for the second read, so no forecast was requested for it.</p>}
          </div>
        </div>
      </section>

      {bothChosen ? (
        <section className="module-section">
          <h2>Side by side, parameter by parameter</h2>
          <p className="module-note">
            Rows are every instant either read returned for that parameter. Each value keeps the unit its own read stated, and each read's own source rows are listed in its section below.
          </p>

          {names.length ? names.map(name => {
            const firstSeries = firstData?.parameters?.[name];
            const secondSeries = secondData?.parameters?.[name];
            const rows = unionInstants(firstSeries?.points, secondSeries?.points);
            return (
              <div key={name}>
                <h3>{name}</h3>
                <p className="module-note" role="status" data-testid={'compare-count-' + name}>
                  {seriesLine(first, 'first', firstSeries, firstState)} · {seriesLine(second, 'second', secondSeries, secondState)}
                </p>
                <DataTable
                  testId={'compare-parameter-' + name}
                  caption={'Every instant either read returned for ' + name + ', as each read printed it. A cell with no point states that absence for that read.'}
                  columns={['Valid at (IST)', 'First read · ' + placeName(first, 'first'), 'Second read · ' + placeName(second, 'second')]}
                  rows={rows.map(row => [row.t ? istStamp(row.t) : 'instant not recorded in this point',
                    valueText(row.first, firstSeries, firstState), valueText(row.second, secondSeries, secondState)])}
                />
              </div>
            );
          }) : (
            <p className="module-note" role="status">{noRowsReason(firstState, secondState)}</p>
          )}
        </section>
      ) : null}

      {first ? <ReadEvidence ordinal="first" testId="compare-read-first" place={first} query={firstRead} days={days} what="first point forecast" /> : null}
      {second ? <ReadEvidence ordinal="second" testId="compare-read-second" place={second} query={secondRead} days={days} what="second point forecast" /> : null}
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
