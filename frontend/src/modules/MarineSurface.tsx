/* Sea and rivers: modelled waves for the sea cell answering one point, and modelled river discharge for
   the river cell answering another, each fetched by its own route read. The cell, the distance the
   payload states, the model, the unit and the source rows stay with the read that returned them. A wave
   value is modelled sea state, not an observation or a bulletin; a discharge is modelled volume flow. */
import { useState } from 'react';
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import { DataTable, EvidenceFooter, Facts, Failure, Headline, NO_ROW, NOT_RECORDED, PlacePicker, Reading, SurfaceShell, type Fact, type PlaceChoice } from './Evidence';

type SeriesPoint = { t?: string | null; v?: number | string | null };
type Series = { unit?: string | null; model?: string | null; points?: SeriesPoint[]; quality_flags?: string[] };
type Cell = { latitude?: number | null; longitude?: number | null } | null | undefined;
type MarineData = { parameters?: Record<string, Series>; days?: number | null; grid?: Cell; grid_distance_km?: number | null };
type MarineEnvelope = Envelope<MarineData>;

export const intents: string[] = (viewById('marine')?.intents ?? []).concat([
  'Which sea cell answered, and what distance did the payload state for it?',
  'What river discharge is modelled for this river point?',
  'Are the official sea-area and coastal bulletins connected here?',
]);

const placeName = (place: PlaceChoice | null): string => orNot(place?.label, 'place label not recorded');

function cellText(cell: Cell): string {
  if (!cell || [cell.latitude, cell.longitude].some(value => value === null || value === undefined)) return NOT_RECORDED;
  return 'latitude ' + cell.latitude + ', longitude ' + cell.longitude;
}
/* Only a distance the payload states is ever drawn: an absent or null distance reads as not recorded,
   and is never computed here from the requested point and the returned cell. */
function distanceText(value?: number | null): string {
  return value === null || value === undefined ? NOT_RECORDED : value + ' km';
}

function cellsDiffer(waveCell: Cell, riverCell: Cell): boolean {
  return Boolean(waveCell && riverCell && typeof waveCell.latitude === 'number' && typeof waveCell.longitude === 'number' &&
    typeof riverCell.latitude === 'number' && typeof riverCell.longitude === 'number' &&
    (waveCell.latitude !== riverCell.latitude || waveCell.longitude !== riverCell.longitude));
}

/* The first-screen reading: the most recent value this read stated for its first-named parameter — waves
   for the sea read, discharge for the river read — in the read's own unit, with the cell and the distance
   the payload states. A coastal reader opens this surface for one number: what the sea or the river is
   doing right now, as this model states it. Never an observation, never a bulletin, never a warning. */
function latestValueHeadline(data: MarineData | undefined): { statement: string; source: string } {
  const [name, series] = Object.entries(data?.parameters || {})[0] || [];
  const source = orNot(series?.model) + ' · cell ' + cellText(data?.grid) + ' · distance ' + distanceText(data?.grid_distance_km);
  if (!name) return { statement: 'This read returned no parameter series for its answering cell.', source };
  const point = (series.points || []).find(p => p.v !== null && p.v !== undefined);
  if (!point) return { statement: 'This read named ' + name + ' but stated no value for it in the points it returned.', source };
  return {
    statement: 'The most recent modelled ' + name.replace(/_/g, ' ') + ' this read states is ' + point.v
      + (series.unit ? ' ' + series.unit : '') + ', at ' + (point.t ? istStamp(point.t) : NOT_RECORDED) + '.',
    source,
  };
}

function seriesNote(series: Series): string {
  const flags = series.quality_flags || [];
  const points = Array.isArray(series.points) ? count(series.points.length, 'point') + ' returned' : 'points not recorded in this read';
  return 'Model as returned: ' + orNot(series.model) + ' · ' + points + (flags.length ? ' · quality flags as returned: ' + flags.join(', ') : '');
}

function ParameterSeries({ data, testIdPrefix }: { data?: MarineData; testIdPrefix: string }): JSX.Element {
  const entries = Object.entries(data?.parameters || {});
  if (!entries.length) return <p className="module-note">{NO_ROW}: this read returned no parameter series for its answering cell.</p>;
  return (
    <>
      {entries.map(([name, series]) => {
        const points = Array.isArray(series.points) ? series.points : [];
        return (
          <div key={name}>
            <h3>{name} ({orNot(series.unit, 'unit not stated')})</h3>
            <p className="module-note" data-testid={testIdPrefix + '-model-' + name}>{seriesNote(series)}</p>
            <DataTable
              testId={testIdPrefix + '-series-' + name}
              caption={'Every point this read returned for ' + name + ', as returned. A point with no value is a gap, never a zero.'}
              columns={['Valid at (IST)', 'Value as returned']}
              rows={points.map(point => [point.t ? istStamp(point.t) : NOT_RECORDED,
                point.v === null || point.v === undefined ? 'no value returned for this point' : String(point.v)])}
            />
          </div>
        );
      })}
    </>
  );
}

function ReadSection({ heading, testId, place, query, what, route, timeBasisRow }: {
  heading: string; testId: string; place: PlaceChoice; query: UseQueryResult<MarineEnvelope, Error>;
  what: string; route: string; timeBasisRow?: Fact;
}): JSX.Element {
  const envelope = query.data;
  const data = envelope?.data;
  const rows: Fact[] = [
    ['Place named for this read', placeName(place)],
    ['Coordinates read', place.latitude + ', ' + place.longitude],
    ['Answering cell as returned', cellText(data?.grid)],
    ['Distance as returned for that cell', distanceText(data?.grid_distance_km)],
    ['Days as returned', orNot(data?.days)],
  ];
  if (timeBasisRow) rows.push(timeBasisRow);
  rows.push(['Generated at, as returned', envelope?.generated_at_utc ? istStamp(envelope.generated_at_utc) : NOT_RECORDED]);
  rows.push(['Source rows attached to this read', count(envelope?.sources?.length, 'source row')]);
  return (
    <section className="module-section" data-testid={testId}>
      <h2>{heading}</h2>
      <p className="module-note">
        This read is its own call to {route} for the point named for it; the answering cell, the distance it states, the model and the
        unit below are as this read returned them.
      </p>
      {query.isPending ? (
        <Reading what={what} />
      ) : query.isError ? (
        <Failure error={query.error} what={what} onRetry={() => query.refetch()} />
      ) : (
        <>
          <Facts testId={testId + '-facts'} rows={rows} />
          {(() => {
            const headline = latestValueHeadline(data);
            return <Headline testId={testId + '-headline'} statement={headline.statement} source={headline.source} />;
          })()}
          <ParameterSeries data={data} testIdPrefix={testId} />
          {envelope ? <EvidenceFooter envelope={envelope} /> : null}
        </>
      )}
    </section>
  );
}

export function Surface(): JSX.Element {
  const [seaPoint, setSeaPoint] = useState<PlaceChoice | null>(null);
  const [riverPoint, setRiverPoint] = useState<PlaceChoice | null>(null);

  const waveRead = useQuery({
    queryKey: ['marine-waves', seaPoint?.latitude, seaPoint?.longitude],
    queryFn: () => getJson<MarineEnvelope>(withQuery('/api/marine', { lat: seaPoint?.latitude, lon: seaPoint?.longitude })),
    enabled: seaPoint !== null,
    retry: false,
  });
  const riverRead = useQuery({
    queryKey: ['marine-river', riverPoint?.latitude, riverPoint?.longitude],
    queryFn: () => getJson<MarineEnvelope>(withQuery('/api/river', { lat: riverPoint?.latitude, lon: riverPoint?.longitude })),
    enabled: riverPoint !== null,
    retry: false,
  });

  const waveData = waveRead.data?.data;
  const riverData = riverRead.data?.data;
  const bothAnswered = seaPoint !== null && riverPoint !== null && waveRead.isSuccess && riverRead.isSuccess;
  const riverTimeBasisRow: Fact = ['Time basis as returned', orNot(riverRead.data?.coverage?.time_basis)];

  return (
    <SurfaceShell
      title="Sea and rivers"
      lead="Modelled waves for the sea cell answering one point, and modelled discharge for the river cell answering another: two separate reads, each with its own cell, the distance the payload states, model, unit and source rows. Neither is an observation, a bulletin or a warning."
      what="the wave and river reads"
      busy={false}
      intents={intents}
    >
      <section className="module-section">
        <h2>The two reads</h2>
        <p className="module-note">
          One point is named for the wave read and another for the river read; they are separate calls, and neither read answers for
          the other read's cell.
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--g-4)', alignItems: 'flex-start' }}>
          <div style={{ flex: '1 1 24rem', minWidth: 0 }}>
            <h3>Wave read · sea point</h3>
            <PlacePicker onPick={setSeaPoint} hint="Name a sea or coastal point and choose a row; GET /api/marine then answers for that point's sea cell." />
            {seaPoint ? <p className="module-note" role="status">Chosen for the wave read: {placeName(seaPoint)} · {seaPoint.latitude}, {seaPoint.longitude}</p>
              : <p className="module-note">No point has been chosen for the wave read, so no sea cell was requested.</p>}
          </div>
          <div style={{ flex: '1 1 24rem', minWidth: 0 }}>
            <h3>River read · river point</h3>
            <PlacePicker onPick={setRiverPoint} hint="Name a river point and choose a row; GET /api/river then answers for that point's river cell." />
            {riverPoint ? <p className="module-note" role="status">Chosen for the river read: {placeName(riverPoint)} · {riverPoint.latitude}, {riverPoint.longitude}</p>
              : <p className="module-note">No point has been chosen for the river read, so no river cell was requested.</p>}
          </div>
        </div>
        {bothAnswered ? (
          <p className="module-note" role="status" data-testid="marine-cells">
            The wave read answered for cell {cellText(waveData?.grid)}; the distance it stated is {distanceText(waveData?.grid_distance_km)}.
            The river read answered for cell {cellText(riverData?.grid)}; the distance it stated is {distanceText(riverData?.grid_distance_km)}.
            {cellsDiffer(waveData?.grid, riverData?.grid) ? ' They are two different cells: the wave values apply to the sea cell named first, and the discharge to the river cell named second.' : ''}
          </p>
        ) : null}
      </section>

      <section className="module-section" data-testid="marine-boundary">
        <h2>What these values are not</h2>
        <ul>
          <li>A wave height is a modelled sea-state value for a grid cell. It is not an observation, not a sea-area bulletin and not a coastal or marine safety warning.</li>
          <li>A discharge is modelled volume flow. It is not an observed water level, not a gauge reading, not a danger level, not an inundation extent or a flood warning.</li>
          <li>The official sea-area and coastal bulletins S58 and S59 are not connected here: this surface reads neither of them, and states no bulletin, advisory or warning from them.</li>
          <li>Where the payload states no distance for the answering cell, that distance reads as not recorded; this surface never computes one.</li>
        </ul>
      </section>

      {seaPoint ? <ReadSection heading="Modelled waves for the answering sea cell" testId="marine-wave" route="GET /api/marine" place={seaPoint} query={waveRead} what="waves" /> : null}
      {riverPoint ? <ReadSection heading="Modelled river discharge for the answering river cell" testId="marine-river" route="GET /api/river" place={riverPoint} query={riverRead} what="discharge" timeBasisRow={riverTimeBasisRow} /> : null}
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
