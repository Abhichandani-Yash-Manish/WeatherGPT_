/* Observations: what connected stations reported near one point, and the wider single network read.
   A station describes itself with its own instant, age, distance and the values it reported; it is not a
   district average and not a forecast. A stale row reads as stale, an unrecorded staleness flag is not
   treated as current, a reported zero stays a zero, and a unit the read did not state is stated as
   unstated rather than borrowed from another station or parameter. */
import { useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import { DataTable, EvidenceFooter, Failure, Facts, NO_ROW, NOT_RECORDED, PlacePicker, Reading, SurfaceShell, type PlaceChoice } from './Evidence';

type StationParameter = {
  field?: string | null;
  value?: unknown;
  unit?: string | null;
  unit_stated_by_source?: boolean;
};

type StationRow = {
  kind?: string;
  name?: string | null;
  station_code?: string | null;
  distance_km?: number | null;
  observed_at_utc?: string | null;
  age_minutes?: number | null;
  stale?: boolean;
  source_id?: string | null;
  network?: string;
  parameters?: StationParameter[];
};

type NearData = { networks?: Record<string, StationRow[]>; stations?: StationRow[]; rejected?: { reason?: string }[] };
type NetworkData = { kind?: string; stations?: StationRow[]; rejected?: { index?: number; reason?: string }[] };

export const intents: string[] = (viewById('observations')?.intents ?? []).concat([
  'Which stations of the wider network reported near this point?',
]);

function stationName(station: StationRow): string {
  return orNot(station.name || station.station_code, 'station name not recorded');
}

function staleness(station: StationRow): JSX.Element {
  if (station.stale === true) return <span className="chip is-stale">stale</span>;
  if (station.stale === false) return <span className="chip is-current">current</span>;
  return <span className="chip is-unknown">staleness not recorded</span>;
}

function distance(station: StationRow): string {
  return station.distance_km === null || station.distance_km === undefined ? NOT_RECORDED : station.distance_km + ' km';
}

function age(station: StationRow): string {
  return station.age_minutes === null || station.age_minutes === undefined
    ? NOT_RECORDED
    : station.age_minutes + ' minutes before retrieval';
}

/* A value the read stated is printed as it arrived: a zero is a value and never 'not recorded'. A unit
   the read did not state is named as unstated; it is never taken from another parameter or station row. */
function parameterWords(parameter: StationParameter): string {
  const value = parameter.value;
  const shown = value === null || value === undefined || value === '' ? 'value not recorded' : String(value);
  const unit = typeof parameter.unit === 'string' && parameter.unit.trim() ? parameter.unit.trim() : 'unit not stated';
  return orNot(parameter.field, 'field not recorded') + ' ' + shown + ' (' + unit + ')';
}

function reported(station: StationRow): string {
  const parameters = station.parameters || [];
  return parameters.length ? parameters.map(parameterWords).join('; ') : NOT_RECORDED;
}

function stationRows(stations: StationRow[], network: string): ReactNode[][] {
  return stations.map(station => [
    stationName(station),
    network || orNot(station.network),
    orNot(station.kind),
    distance(station),
    station.observed_at_utc ? istStamp(station.observed_at_utc) : NOT_RECORDED,
    age(station),
    orNot(station.source_id),
    staleness(station),
    reported(station),
  ]);
}

const STATION_COLUMNS = ['Station', 'Network', 'Kind', 'Distance', 'Observed at', 'Age at retrieval', 'Source', 'State of the report', 'What the station reported'];

export function Surface(): JSX.Element {
  const [place, setPlace] = useState<PlaceChoice | null>(null);
  const point = { lat: place?.latitude, lon: place?.longitude };

  const near = useQuery({
    queryKey: ['observations-near', point.lat, point.lon],
    queryFn: () => getJson<Envelope<NearData>>(withQuery('/api/observations/near', point)),
    enabled: place !== null,
    retry: false,
  });
  const network = useQuery({
    queryKey: ['observations-network', point.lat, point.lon],
    queryFn: () => getJson<Envelope<NetworkData>>(withQuery('/api/observations/network', { ...point, kind: 'metar' })),
    enabled: place !== null,
    retry: false,
  });

  const nearData = near.data?.data;
  const networkData = network.data?.data;
  const byNetwork = Object.entries(nearData?.networks || {});
  const nearRows = byNetwork.length
    ? byNetwork.flatMap(([kind, rows]) => stationRows(rows || [], kind))
    : stationRows(nearData?.stations || [], '');

  return (
    <SurfaceShell
      title="Observations"
      lead="Station reports near one point, with each station's own instant, age and distance. A station describes itself; it is not a district average and not a forecast."
      what="the station networks"
      envelope={place ? near.data : undefined}
      busy={place !== null && near.isPending}
      error={place ? near.error : undefined}
      onRetry={() => near.refetch()}
      intents={intents}
    >
      <section className="module-section">
        <h2>The point</h2>
        <PlacePicker onPick={setPlace} hint="Name a place and choose a row; stations are then found by great-circle distance from those coordinates." />
        {!place ? (
          <p className="module-note">No point was named, so no station layer was searched.</p>
        ) : (
          <Facts
            testId="observations-point"
            rows={[
              ['Place named', place.label ? place.label : 'label not recorded'],
              ['Coordinates read', place.latitude + ', ' + place.longitude],
            ]}
          />
        )}
      </section>

      {place && !near.isPending && !near.isError ? (
        <section className="module-section">
          <h2>Stations near this point</h2>
          <p className="module-note" data-testid="observations-near-count" role="status">
            {count(nearRows.length, 'station row')} returned by the near read{byNetwork.length ? ' across ' + count(byNetwork.length, 'network') : ''}.
          </p>
          <DataTable
            testId="observations-near"
            caption="Every station row the near read returned, with the fields this surface states."
            columns={STATION_COLUMNS}
            rows={nearRows}
          />
          {nearData?.rejected?.length ? (
            <p className="module-note">{count(nearData.rejected.length, 'source feature')} were rejected by the reader and are not listed: {nearData.rejected.map(item => orNot(item.reason)).join('; ')}</p>
          ) : null}
        </section>
      ) : null}

      {place ? (
        <section className="module-section">
          <h2>The wider network</h2>
          <p className="module-note">
            One named station layer, read on its own: {orNot(networkData?.kind, NO_ROW)}. A station in this layer is a
            different product from the near read, and the two are not merged into one count.
          </p>
          {network.isPending ? (
            <Reading what="the wider station network" />
          ) : network.isError ? (
            <Failure error={network.error} what="wider station network" onRetry={() => network.refetch()} />
          ) : (
            <>
              <p className="module-note" role="status">
                {count((networkData?.stations || []).length, 'station row')} returned by the network read.
              </p>
              <DataTable
                testId="observations-network"
                caption="Every station row the network read returned, with the same fields the near read carries."
                columns={STATION_COLUMNS}
                rows={stationRows(networkData?.stations || [], orNot(networkData?.kind, ''))}
              />
              {network.data ? <EvidenceFooter envelope={network.data} /> : null}
            </>
          )}
        </section>
      ) : null}
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
