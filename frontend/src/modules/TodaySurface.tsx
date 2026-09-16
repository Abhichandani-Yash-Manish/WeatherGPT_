/* Today: the national picture a reader opens first, plus the composed right-now reading for a place
   they name. Three products, kept apart: the district warning product, the station network and the
   model hours. Each keeps its own status, its own instant and its own limits. */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope, NowReading } from '../api/types';
import { count, orNot, worstColour } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import {
  ColourTag, DataTable, EvidenceFooter, Failure, Facts, NO_ROW, NOT_RECORDED, PlacePicker, Reading,
  SurfaceShell, type PlaceChoice,
} from './Evidence';

type Tally = Record<string, number>;

type OverviewData = {
  national?: {
    districts?: number;
    skipped?: number;
    tally?: Tally;
    bulletin_date?: string | null;
    bulletin_dates?: Record<string, number>;
  };
  radar?: { stations?: number; reported?: number };
};

export const intents: string[] = (viewById('overview')?.intents ?? []).concat([
  'What is it like right now near a place I name?',
]);

const TALLY_KEYS = ['red', 'orange', 'yellow', 'green', 'unset'];

function stationFacts(reading: NowReading | undefined): [string, string][] {
  const station = (reading?.observed?.stations || [])[0];
  if (!station) {
    return [
      ['Station', NO_ROW],
      ['Distance', NOT_RECORDED],
      ['Observed at', NOT_RECORDED],
      ['Age at retrieval', NOT_RECORDED],
      ['Staleness', NOT_RECORDED],
    ];
  }
  return [
    ['Station', orNot(station.name || station.station_code)],
    ['Distance', station.distance_km === null || station.distance_km === undefined ? NOT_RECORDED : station.distance_km + ' km'],
    ['Observed at', station.observed_at_utc ? istStamp(station.observed_at_utc) : NOT_RECORDED],
    ['Age at retrieval', station.age_minutes === null || station.age_minutes === undefined ? NOT_RECORDED : station.age_minutes + ' minutes before retrieval'],
    ['Staleness', station.stale === true ? 'stale: the report is older than the layer\u2019s freshness window' : station.stale === false ? 'current' : 'staleness not recorded'],
  ];
}

export function Surface(): JSX.Element {
  const [place, setPlace] = useState<PlaceChoice | null>(null);
  const overview = useQuery({
    queryKey: ['overview'],
    queryFn: () => getJson<Envelope<OverviewData>>('/api/overview'),
    retry: false,
  });
  const now = useQuery({
    queryKey: ['now', place?.latitude, place?.longitude],
    queryFn: () =>
      getJson<Envelope<NowReading>>(withQuery('/api/now', { lat: place?.latitude, lon: place?.longitude })),
    enabled: place !== null,
    retry: false,
  });

  const national = overview.data?.data?.national;
  const radar = overview.data?.data?.radar;
  const tally = national?.tally || {};
  const strongest = worstColour(tally);
  const reading = now.data?.data;
  const hours = reading?.next_hours;
  const inForce = reading?.in_force;
  const unit = hours?.unit || {};

  return (
    <SurfaceShell
      title="Today"
      lead="The national district warning picture as this machine read it, and the composed right-now reading for one place: the station report, the published day and the model hours, kept apart."
      what="the national overview"
      envelope={overview.data}
      busy={overview.isPending}
      error={overview.error}
      onRetry={() => overview.refetch()}
    >
      <section className="module-section">
        <h2>The national picture</h2>
        <Facts
          testId="today-national"
          rows={[
            ['Districts in this read', count(national?.districts, 'district')],
            ['Source features without a district name', orNot(national?.skipped)],
            ['Bulletin date most rows carry', orNot(national?.bulletin_date)],
            ['Radar stations returned', count(radar?.stations, 'station')],
            ['Radar stations reporting a status', orNot(radar?.reported)],
          ]}
        />
        <p className="module-note">
          {strongest
            ? 'The tally this read returned contains ' + strongest.count + ' district-day(s) at ' + strongest.colour +
              ', the strongest colour the product itself printed for those days.'
            : 'The tally this read returned states no colour at all.'}
        </p>
        <DataTable
          testId="today-tally"
          caption="Colour tally exactly as the product returned it, one row per colour it printed."
          columns={['Colour', 'District-days counted']}
          rows={Array.from(new Set(TALLY_KEYS.concat(Object.keys(tally)))).map(key => [
            <ColourTag colour={key} key={key} text={key} />,
            orNot(tally[key]),
          ])}
        />
        <DataTable
          testId="today-bulletin-dates"
          caption="Bulletin dates as the returned rows state them; a date the source did not state is not shown as one."
          columns={['Bulletin date', 'Rows carrying it']}
          rows={Object.entries(national?.bulletin_dates || {}).map(([date, rows]) => [
            orNot(date, 'date not stated'),
            orNot(rows),
          ])}
        />
      </section>

      <section className="module-section">
        <h2>Right now where you are</h2>
        <p className="module-note">
          Naming a place resolves it against the place catalogue, then reads the composed now view for those coordinates.
        </p>
        <PlacePicker onPick={setPlace} hint="Type at least two characters; the catalogue returns places to choose from." />
        {!place ? (
          <p className="module-note">No point was requested, so no observation, warning day or model hour is shown here.</p>
        ) : now.isPending ? (
          <Reading what="the right-now reading" />
        ) : now.isError ? (
          <Failure error={now.error} what="right-now reading" onRetry={() => now.refetch()} />
        ) : (
          <>
            <Facts
              testId="today-place"
              rows={[['Place read', place.label ? place.label : 'label not recorded'], ['Coordinates', place.latitude + ', ' + place.longitude]]}
            />
            <h3>Observed</h3>
            <Facts rows={stationFacts(reading)} />
            <h3>In force</h3>
            {inForce && (inForce.district || inForce.status_line) ? (
              <>
                <Facts
                  rows={[
                    ['District', orNot(inForce.district) + (inForce.state ? ', ' + inForce.state : '')],
                    ['Day', orNot(inForce.day_label, NO_ROW)],
                    ['Issued', inForce.issued_at_utc ? istStamp(inForce.issued_at_utc) : NOT_RECORDED],
                    ['Quiet flag as published', inForce.quiet === undefined ? NOT_RECORDED : String(inForce.quiet)],
                  ]}
                />
                <p>
                  <ColourTag colour={inForce.colour} text={inForce.colour || 'colour not stated'} />{' '}
                  <span className="reading">{orNot(inForce.status_line, NO_ROW)}</span>
                </p>
              </>
            ) : (
              <p className="module-note">
                No district-day row was returned for this point. {NO_ROW}: a point outside every district polygon of the warning product carries no district guidance.
              </p>
            )}
            <h3>Next hours</h3>
            <p className="module-note">
              Model hours for the grid cell. An hour the product did not return is a gap in this table, never a zero.
            </p>
            <DataTable
              testId="today-hours"
              caption={'Next hours as returned' + (hours?.source_id ? ', source ' + hours.source_id : '')}
              columns={[
                'Hour (IST)',
                'temperature_2m (' + orNot(unit.temperature_2m, 'unit not stated') + ')',
                'precipitation_probability (' + orNot(unit.precipitation_probability, 'unit not stated') + ')',
                'precipitation (' + orNot(unit.precipitation, 'unit not stated') + ')',
                'wind_speed_10m (' + orNot(unit.wind_speed_10m, 'unit not stated') + ')',
              ]}
              rows={(hours?.rows || []).map(row => [
                row.at ? istStamp(row.at) : NOT_RECORDED,
                orNot(row.temperature_2m),
                orNot(row.precipitation_probability),
                orNot(row.precipitation),
                orNot(row.wind_speed_10m),
              ])}
            />
            {now.data ? <EvidenceFooter envelope={now.data} /> : null}
          </>
        )}
      </section>
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
