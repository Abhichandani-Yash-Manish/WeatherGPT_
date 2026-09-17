/* Ensemble spread: the member-summary series one ensemble model returned for one grid cell, exactly as
   the product view passed them through. An ensemble member is one model run; the spread is a property of
   those runs at that cell and instant, and it is not a probability of the outcome at your place, not a
   confidence in the answer and not a skill score. The member count is the read's own count, never a
   completeness percentage computed here, and a member the payload did not return is absent. */
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import { VizFigure } from '../charts/VizFigure';
import { ensembleFanSpec } from '../charts/vizSpecs';
import { DataTable, Facts, NO_ROW, NOT_RECORDED, PlacePicker, SurfaceShell, type PlaceChoice } from './Evidence';

type Point = { t?: string | null; v?: number | string | null; start?: string | null; end?: string | null };
type Series = { unit?: string | null; aggregation?: string | null; model?: string | null; quality_flags?: string[]; points?: Point[] };
type Coords = { latitude?: number | null; longitude?: number | null };
type EnsembleData = {
  parameters?: Record<string, Series>;
  days?: number;
  model?: string | null;
  member_total?: Record<string, number> | null;
  statistics?: Record<string, string> | null;
  grid?: Coords | null;
  requested?: Coords | null;
  time_basis?: string | null;
};

export const intents: string[] = (viewById('ensemble')?.intents ?? []).concat([
  'How many ensemble members did this read return for each parameter?',
  'What spread does the ensemble state for this cell and instant?',
]);

const DAY_CHOICES = ['1', '2', '3', '5', '7'];
const NO_VALUE = 'no value returned for this point';
const MEMBER_IS_ONE_RUN =
  'An ensemble member is one model run. The spread is a property of those runs at this cell and instant: it is not a '
  + 'probability of the outcome at your place, not a confidence in the answer and not a skill score.';
const RETURNED_MEMBERS =
  'Every value on this surface is modelled ensemble output for a grid cell of the model the read names, not an observation '
  + 'and not a station measurement. A member this payload did not return is absent: the count of returned members is the '
  + 'read\u2019s own count, and no completeness percentage is computed here.';

function pair(point?: Coords | null): string {
  if (!point || point.latitude === null || point.latitude === undefined) return NOT_RECORDED;
  if (point.longitude === null || point.longitude === undefined) return NOT_RECORDED;
  return point.latitude + ', ' + point.longitude;
}

/* The payload's own variable name for a series: the member-total key that prefixes it, else the series
   name itself, so an unmatched series is never relabelled with a name the read did not return. */
function variableFor(parameter: string, totals?: Record<string, number> | null): string {
  return Object.keys(totals || {}).find(name => parameter.startsWith(name + '_')) || parameter;
}

export function Surface(): JSX.Element {
  const [place, setPlace] = useState<PlaceChoice | null>(null);
  const [days, setDays] = useState('3');
  const read = useQuery({
    queryKey: ['ensemble', place?.latitude, place?.longitude, days],
    queryFn: () =>
      getJson<Envelope<EnsembleData>>(withQuery('/api/ensemble', { lat: place?.latitude, lon: place?.longitude, days })),
    enabled: place !== null,
    retry: false,
  });

  const data = read.data?.data;
  const totals = data?.member_total;
  const parameters = Object.entries(data?.parameters || {});
  const groups: [string, [string, Series][]][] = [];
  parameters.forEach(([name, series]) => {
    const variable = variableFor(name, totals);
    const group = groups.find(([key]) => key === variable);
    if (group) group[1].push([name, series]);
    else groups.push([variable, [[name, series]]]);
  });
  const spread = parameters.filter(([name]) => name.endsWith('_spread'));
  /* The distribution figure: the shaded band is p10 to p90, the heavy line the median and the thin whiskers
     min to max, all as the read returned them. Spread is a property of the returned runs, not a probability, a
     confidence or a skill score. */
  const families = groups.map(([name]) => name);
  const chosen = variableFor(String(families[0] || ''), totals);
  const fan = useMemo(
    () => (chosen ? ensembleFanSpec(data?.parameters || {}, chosen, data?.model || null, totals?.[chosen], data?.statistics) : null),
    [data, chosen, totals],
  );

  return (
    <SurfaceShell
      title="Ensemble spread"
      lead="The member-summary series one ensemble model returned for one grid cell: the spread it states, the members it returned and every point as the read returned it. Modelled output, not an observation."
      what="the ensemble spread read"
      envelope={place ? read.data : undefined}
      busy={place !== null && read.isPending}
      error={place ? read.error : undefined}
      onRetry={() => read.refetch()}
    >
      <section className="module-section">
        <h2>What a member and a spread are here</h2>
        <p className="module-note" data-testid="ensemble-meaning">{MEMBER_IS_ONE_RUN}</p>
        <p className="module-note" data-testid="ensemble-members-stated">{RETURNED_MEMBERS}</p>
      </section>

      <section className="module-section">
        <h2>The point this read used</h2>
        <PlacePicker onPick={setPlace} hint="Name a place and choose a row; the ensemble is then read for those coordinates." />
        <div className="module-controls">
          <label className="module-field" htmlFor="ensemble-days">
            <span>Days requested</span>
            <select id="ensemble-days" value={days} onChange={event => setDays(event.target.value)}>
              {DAY_CHOICES.map(value => (
                <option key={value} value={value}>
                  {value} day{value === '1' ? '' : 's'}
                </option>
              ))}
            </select>
          </label>
        </div>
        {!place ? (
          <p className="module-note">No point was named, so no ensemble read was requested.</p>
        ) : (
          <>
            <Facts
              testId="ensemble-point"
              rows={[
                ['Requested place', place.label ? place.label : 'label not recorded'],
                ['Requested coordinates', place.latitude + ', ' + place.longitude],
                ['Coordinates as the reading returned them', pair(data?.requested)],
                ['Cell identity as returned', pair(data?.grid)],
                ['Model as returned', orNot(data?.model)],
                ['Time basis', orNot(data?.time_basis)],
                ['Days requested', orNot(data?.days, days)],
              ]}
            />
            {Object.keys(totals || {}).length ? (
              <DataTable
                testId="ensemble-member-total"
                caption="The member count per named variable, exactly as this read returned it; no percentage of a member set is computed here."
                columns={['Variable as returned', 'Members this read returned']}
                rows={Object.keys(totals || {}).map(variable => [variable, orNot(totals?.[variable])])}
              />
            ) : (
              <p className="module-note">
                The count of returned members is {NOT_RECORDED} in this read: the payload carried no member-total field for any
                variable. An absent count is not a zero.
              </p>
            )}
          </>
        )}
      </section>

      {place && !read.isPending && !read.isError && fan ? (
        <section className="module-section" data-testid="ensemble-fan-section">
          <h2>Member distribution</h2>
          <p className="module-note">
            The members this read returned, drawn as a distribution by the chart engine this build serves: the shaded
            band is p10 to p90, the heavy line the median and the thin whiskers min to max. Spread is a property of
            those runs, not a probability, a confidence or a skill score.
          </p>
          <VizFigure kind="ensembleFan" spec={fan} />
        </section>
      ) : null}

      {place && !read.isPending && !read.isError ? (
        <section className="module-section">
          <h2>The series this read returned</h2>
          <p className="module-note" role="status" aria-live="polite" data-testid="ensemble-count">
            {count(parameters.length, 'series', 'series')} returned across {count(groups.length, 'variable name')}. The member counts the
            read stated appear above; a member it did not return is absent and no completeness percentage is computed here.
          </p>
          <p className="module-note">
            Every point appears exactly as the read returned it. An instant the payload did not carry is a gap in these tables
            and is never a zero; values are model output for the grid cell, not measurements at your place.
          </p>
          <DataTable
            testId="ensemble-statistics"
            caption="What each statistic name means, in the read's own words."
            columns={['Statistic as returned', 'Definition as returned']}
            rows={Object.entries(data?.statistics || {}).map(([name, definition]) => [name, orNot(definition)])}
          />
          <h3>The spread as this read stated it</h3>
          <DataTable
            testId="ensemble-spread"
            caption="One row per spread point this read returned, with the unit and the member count for its variable."
            columns={['Spread series as returned', 'Valid at (IST)', 'Spread value as returned', 'Unit as returned', 'Members returned for its variable']}
            rows={spread.flatMap(([name, series]) =>
              (series.points || []).map(point => [
                name,
                point.t ? istStamp(point.t) : NOT_RECORDED,
                point.v === null || point.v === undefined ? <span className="module-gap">{NO_VALUE}</span> : String(point.v),
                orNot(series.unit, 'unit not stated'),
                orNot(totals?.[variableFor(name, totals)]),
              ]),
            )}
          />
          {spread.length ? null : (
            <p className="module-note">This read returned no spread series, so no spread is stated here. {NO_ROW}.</p>
          )}
          {groups.map(([variable, rows]) => {
            const members = totals?.[variable];
            return (
              <div key={variable}>
                <h3>
                  {variable} ·{' '}
                  {members === null || members === undefined
                    ? 'members returned: ' + NOT_RECORDED
                    : count(members, 'returned member')}
                </h3>
                <DataTable
                  testId={'ensemble-series-' + variable}
                  caption={'Every series point this read returned under ' + variable + '.'}
                  columns={['Series as returned', 'Valid at (IST)', 'Value as returned', 'Unit as returned', 'Aggregation as returned', 'Interval start (IST)', 'Interval end (IST)', 'Quality flags as returned']}
                  rows={rows.flatMap(([name, series]) =>
                    (series.points || []).map(point => [
                      name,
                      point.t ? istStamp(point.t) : NOT_RECORDED,
                      point.v === null || point.v === undefined ? <span className="module-gap">{NO_VALUE}</span> : String(point.v),
                      orNot(series.unit, 'unit not stated'),
                      orNot(series.aggregation, 'aggregation not stated'),
                      point.start ? istStamp(point.start) : NOT_RECORDED,
                      point.end ? istStamp(point.end) : NOT_RECORDED,
                      orNot((series.quality_flags || []).join(', '), 'no flag returned'),
                    ]),
                  )}
                />
              </div>
            );
          })}
          {groups.length ? null : (
            <p className="module-note">{NO_ROW}: this read returned no ensemble series for the point.</p>
          )}
        </section>
      ) : null}
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
