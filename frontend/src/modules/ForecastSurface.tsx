/* Forecast: the model series for one point, each parameter as its own table, and the changed-edition
   view of stored retrievals for the same point. Two routes, one product family: a model forecast is
   not an observation, and a change between two retrievals is not skill. */
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import { ChartBlock } from '../charts/ChartBlock';
import { VizFigure } from '../charts/VizFigure';
import { meteogramSpec } from '../charts/vizSpecs';
import { DataTable, EvidenceFooter, Failure, Facts, NO_ROW, NOT_RECORDED, PlacePicker, Reading, SurfaceShell, type PlaceChoice } from './Evidence';

type Point = { unit?: string | null; points?: { t?: string | null; v?: number | null }[] };

type ForecastData = {
  requested?: { label?: string | null; latitude?: number; longitude?: number };
  parameters?: Record<string, Point>;
  days?: number;
  source_family?: string;
  time_basis?: string;
};

type ChangeEntry = {
  unit?: string | null;
  valid_hours?: number;
  mean_abs_change?: number;
  max_abs_change?: number;
  example?: { valid_time_utc?: string; first_value?: number; last_value?: number };
};

type ChangesData = {
  retrievals?: { retrieved_at_utc?: string; product?: string; request_date?: string; response_sha256_prefix?: string }[];
  retrieval_count?: number;
  parameters?: Record<string, ChangeEntry>;
  overlapping_valid_hours?: number;
  interpretation?: string;
};

export const intents: string[] = (viewById('forecast')?.intents ?? []).concat([
  'What changed between the stored retrievals of this point?',
]);

const DAY_CHOICES = ['1', '2', '3', '5', '7'];

export function Surface(): JSX.Element {
  const [place, setPlace] = useState<PlaceChoice | null>(null);
  const [days, setDays] = useState('3');
  const point = { lat: place?.latitude, lon: place?.longitude };

  const forecast = useQuery({
    queryKey: ['forecast', point.lat, point.lon, days],
    queryFn: () => getJson<Envelope<ForecastData>>(withQuery('/api/forecast', { ...point, days })),
    enabled: place !== null,
    retry: false,
  });
  const changes = useQuery({
    queryKey: ['forecast-changes', point.lat, point.lon],
    queryFn: () => getJson<Envelope<ChangesData>>(withQuery('/api/forecast/changes', point)),
    enabled: place !== null,
    retry: false,
  });

  const data = forecast.data?.data;

  /* The meteogram spec is built from the same returned series the parameter tables read, so the figure and
     the tables can never disagree about a value. */
  const meteogram = useMemo(() => meteogramSpec(data?.parameters || {}), [data]);
  const parameters = Object.entries(data?.parameters || {});
  const changeData = changes.data?.data;

  return (
    <SurfaceShell
      title="Forecast"
      lead="Model output for one grid cell, one table per parameter, with the unit the product stated and the instant each value is valid for. Model hours are not observations."
      what="the point forecast"
      envelope={place ? forecast.data : undefined}
      busy={place !== null && forecast.isPending}
      error={place ? forecast.error : undefined}
      onRetry={() => forecast.refetch()}
    >
      <section className="module-section">
        <h2>The point</h2>
        <div className="module-controls">
          <label className="module-field" htmlFor="forecast-days">
            <span>Days requested</span>
            <select id="forecast-days" value={days} onChange={event => setDays(event.target.value)}>
              {DAY_CHOICES.map(value => (
                <option key={value} value={value}>
                  {value} day{value === '1' ? '' : 's'}
                </option>
              ))}
            </select>
          </label>
        </div>
        <PlacePicker onPick={setPlace} hint="Name a place and choose a row; the forecast is read for those coordinates." />
        {!place ? (
          <p className="module-note">No point was named, so no forecast series was requested.</p>
        ) : (
          <Facts
            testId="forecast-requested"
            rows={[
              ['Requested place', place.label ? place.label : 'label not recorded'],
              ['Requested coordinates', place.latitude + ', ' + place.longitude],
              ['Label as the reading returned it', orNot(data?.requested?.label)],
              ['Coordinates as the reading returned them', data?.requested?.latitude === undefined || data?.requested?.longitude === undefined
                ? NOT_RECORDED
                : data.requested.latitude + ', ' + data.requested.longitude],
              ['Days requested', orNot(data?.days, days)],
              ['Time basis', orNot(data?.time_basis)],
            ]}
          />
        )}
      </section>

      {place && !forecast.isPending && !forecast.isError && meteogram ? (
  <section className="module-section">
          <h2>Meteogram</h2>
          <p className="module-note">
            Temperature, precipitation and wind on one time axis, drawn by the chart engine this build serves. A gap
            is a source gap: nothing is interpolated, and a zero bar is a returned zero. Night hours are shaded by the
            IST clock.
          </p>
          <VizFigure kind="meteogram" spec={meteogram} />
        </section>

      ) : null}

      {place && !forecast.isPending && !forecast.isError ? (
        <section className="module-section">
          <h2>Parameter series</h2>
          <p className="module-note">
            One table per parameter, exactly the points the product returned. A point the product did not return is a gap and
            is never drawn as a zero; a value returned as null is shown as that null, not substituted.
          </p>
          {parameters.length ? (
            parameters.map(([name, series]) => {
              const points = series.points || [];
              const gaps = points.filter(entry => entry.v === null || entry.v === undefined).length;
              return (
                <div key={name}>
                  <h3>
                    {name} ({orNot(series.unit, 'unit not stated')})
                  </h3>
                  <p className="module-note" data-testid={'forecast-gaps-' + name}>
                    {count(points.length, 'point')} returned, {gaps ? count(gaps, 'point') + ' holding no value' : 'every returned point holds a value'}.
                    A missing point is a gap, never a zero.
                  </p>
                  {/* The same points the table holds, drawn: a point with no value breaks the line instead
                      of being drawn at zero. */}
                  <ChartBlock chart={{ title: name, unit: series.unit || '', axis_label: 'Valid at', points }} />
                  <DataTable
                    caption={'Every point the product returned for ' + name + '.'}
                    columns={['Valid at (IST)', 'Value as returned']}
                    rows={points.map(entry => [
                      entry.t ? istStamp(entry.t) : NOT_RECORDED,
                      entry.v === null || entry.v === undefined ? <span className="module-gap">no value returned for this point</span> : String(entry.v),
                    ])}
                  />
                </div>
              );
            })
          ) : (
            <p className="module-note">{NO_ROW}: this read returned no parameter series for the point.</p>
          )}
        </section>
      ) : null}

      {place ? (
        <section className="module-section">
          <h2>What changed between stored retrievals</h2>
          <p className="module-note">
            The same valid hour as two or more stored retrievals hold it: vintage variance, not skill and not a correction.
          </p>
          {changes.isPending ? (
            <Reading what="the changed-edition view" />
          ) : changes.isError ? (
            <Failure error={changes.error} what="changed-edition view" onRetry={() => changes.refetch()} />
          ) : (
            <>
              <Facts
                testId="forecast-changes"
                rows={[
                  ['Stored retrievals for this point', orNot(changeData?.retrieval_count)],
                  ['Valid hours retrieved more than once', orNot(changeData?.overlapping_valid_hours)],
                  ['Interpretation as returned', orNot(changeData?.interpretation)],
                ]}
              />
              <DataTable
                caption="The retrievals this comparison used, as the store recorded them."
                columns={['Retrieved', 'Product', 'Requested date', 'Response sha256 prefix']}
                rows={(changeData?.retrievals || []).map(row => [
                  row.retrieved_at_utc ? istStamp(row.retrieved_at_utc) : NOT_RECORDED,
                  orNot(row.product),
                  orNot(row.request_date),
                  orNot(row.response_sha256_prefix),
                ])}
              />
              <DataTable
                caption="Per parameter, the change between the first and the last retrieval of the same valid hour."
                columns={['Parameter', 'Unit', 'Valid hours', 'Mean absolute change', 'Largest absolute change']}
                rows={Object.entries(changeData?.parameters || {}).map(([name, entry]) => [
                  name,
                  orNot(entry.unit),
                  orNot(entry.valid_hours),
                  orNot(entry.mean_abs_change),
                  orNot(entry.max_abs_change),
                ])}
              />
              {changes.data ? <EvidenceFooter envelope={changes.data} /> : null}
            </>
          )}
        </section>
      ) : null}
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
