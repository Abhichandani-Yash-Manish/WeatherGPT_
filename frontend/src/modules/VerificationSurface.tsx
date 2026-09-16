/* Forecast verification: one bounded comparison this machine holds — archived model runs at fixed
   lead-time offsets matched hour by hour against the reference the read names, over one completed
   window and one point. The reference is reanalysis, a modelled analysis, not a station observation.
   The statistics describe this sample for this model, variable and window: this surface computes no
   metric, averages nothing, ranks nothing, and a lead the read did not measure stays unmeasured. */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { viewById } from '../shell/views';
import { DataTable, Facts, NO_ROW, NOT_RECORDED, PlacePicker, SurfaceShell, type PlaceChoice } from './Evidence';

type Coords = { latitude?: number | null; longitude?: number | null };
type LeadRow = {
  lead_days?: number | null;
  forecast_hours?: number | null;
  unmatched_hours?: number | null;
  n?: number | null;
  status?: string | null;
  bias?: string | null;
  mae?: string | null;
  rmse?: string | null;
  correlation?: string | null;
  correlation_note?: string | null;
  reason?: string | null;
};
type VerificationData = {
  method?: Record<string, string> | null;
  minimum_sample_hours?: number | null;
  forecast?: { source_id?: string | null; model?: string | null; grid?: Coords | null } | null;
  reference?: { source_id?: string | null; grid?: Coords | null } | null;
  variables?: Record<string, LeadRow[]> | null;
  units?: Record<string, string | null> | null;
  limits?: string[] | null;
  window?: { start?: string | null; end?: string | null } | null;
};

export const intents: string[] = (viewById('verification')?.intents ?? []).concat([
  'What was compared, over which window and sample, and from which sources?',
  'Which metrics did this read state, and which leads did it leave unmeasured?',
]);

const NO_MEASURE = 'this read did not answer for this lead';
const PROTOTYPE_NOT_SKILL =
  'This is a prototype comparison over the window and sample this read states: it is not validated forecast skill, not a '
  + 'nationwide accuracy claim and not an operational clearance. A metric this payload does not state is not computed here, '
  + 'and the sample sizes are the read\u2019s own counts.';
const WHAT_WAS_COMPARED =
  'The forecast side is the archived model runs at the fixed lead-time offsets the read names; each pair matches one of those '
  + 'hours against the reference the read names at the same valid hour. A pair counts only where both sides carry a value, and '
  + 'a lead with fewer matched hours than the stated minimum is reported as unmeasured, never given a number.';

function pair(point?: Coords | null): string {
  if (!point || point.latitude === null || point.latitude === undefined) return NOT_RECORDED;
  if (point.longitude === null || point.longitude === undefined) return NOT_RECORDED;
  return point.latitude + ', ' + point.longitude;
}

function metric(row: LeadRow, key: 'bias' | 'mae' | 'rmse' | 'correlation'): string {
  if (row.status !== 'measured') return NO_MEASURE;
  const value = row[key];
  if (value === null || value === undefined) {
    return key === 'correlation' ? orNot(row.correlation_note, NOT_RECORDED) : NOT_RECORDED;
  }
  return String(value);
}

export function Surface(): JSX.Element {
  const [place, setPlace] = useState<PlaceChoice | null>(null);
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const ready = place !== null && start !== '' && end !== '';
  const read = useQuery({
    queryKey: ['verification', place?.latitude, place?.longitude, start, end],
    queryFn: () =>
      getJson<Envelope<VerificationData>>(
        withQuery('/api/verification', { lat: place?.latitude, lon: place?.longitude, start, end }),
      ),
    enabled: ready,
    retry: false,
  });

  const data = read.data?.data;
  const variables = Object.entries(data?.variables || {});
  const leads = variables.flatMap(([, rows]) => rows);
  const window = data?.window;
  const windowText = window?.start && window?.end ? window.start + ' to ' + window.end : NOT_RECORDED;

  return (
    <SurfaceShell
      title="Forecast verification"
      lead="One bounded comparison this machine holds: archived model runs at the lead times the read names, matched hour by hour against the reference it names, over one completed window and one point."
      what="the verification read"
      envelope={ready ? read.data : undefined}
      busy={ready && read.isPending}
      error={ready ? read.error : undefined}
      onRetry={() => read.refetch()}
    >
      <section className="module-section">
        <h2>What this comparison is</h2>
        <p className="module-note" data-testid="verification-not-skill">{PROTOTYPE_NOT_SKILL}</p>
        <p className="module-note" data-testid="verification-what-was-compared">{WHAT_WAS_COMPARED}</p>
      </section>

      <section className="module-section">
        <h2>The point and the window</h2>
        <PlacePicker onPick={setPlace} hint="Name a place and choose a row; the comparison is then read for those coordinates." />
        <div className="module-controls">
          <label className="module-field" htmlFor="verification-start">
            <span>Window start (completed date)</span>
            <input id="verification-start" type="date" value={start} onChange={event => setStart(event.target.value)} />
          </label>
          <label className="module-field" htmlFor="verification-end">
            <span>Window end (completed date)</span>
            <input id="verification-end" type="date" value={end} onChange={event => setEnd(event.target.value)} />
          </label>
        </div>
        {!ready ? (
          <p className="module-note">
            {place
              ? 'Give both completed dates to read the comparison for this point; the read is not requested before then.'
              : 'No point was named, so no verification read was requested.'}
          </p>
        ) : (
          <>
            <Facts
              testId="verification-window"
              rows={[
                ['Point named', place.label ? place.label : 'label not recorded'],
                ['Requested coordinates', place.latitude + ', ' + place.longitude],
                ['Window requested', start + ' to ' + end],
                ['Window as the reading returned it', windowText],
                ['Model as returned', orNot(data?.forecast?.model)],
                ['Forecast side as returned', orNot(data?.forecast?.source_id)],
                ['Reference side as returned', orNot(data?.reference?.source_id)],
                ['Forecast cell as returned', pair(data?.forecast?.grid)],
                ['Reference cell as returned', pair(data?.reference?.grid)],
                ['Minimum matched hours for a measured lead', orNot(data?.minimum_sample_hours)],
              ]}
            />
            <p className="module-note">
              The reference side is the reanalysis the read names, and its own limits state what that reference is; this
              surface does not call it an observation and does not turn a modelled analysis into one.
            </p>
          </>
        )}
      </section>

      {ready && !read.isPending && !read.isError ? (
        <section className="module-section">
          <h2>The measured comparison</h2>
          <p className="module-note" role="status" aria-live="polite" data-testid="verification-count">
            {count(leads.length, 'lead row')} returned across {count(variables.length, 'parameter')}. Each row carries the
            read&rsquo;s own matched-hour count (n), forecast-hour count and unmatched-hour count; a lead the read did not
            measure is printed as unmeasured and no metric is computed here.
          </p>
          <p className="module-note">
            This payload returns the matched, forecast and unmatched counts per lead, not the individual paired hours; a
            pair-level list is not part of this view.
          </p>
          <DataTable
            testId="verification-method"
            caption="What each metric name means, in the read's own words."
            columns={['Metric as returned', 'Definition as returned']}
            rows={Object.entries(data?.method || {}).map(([name, definition]) => [name, orNot(definition)])}
          />
          {variables.length ? (
            variables.map(([name, rows]) => (
              <div key={name}>
                <h3>
                  {name} ({orNot(data?.units?.[name], 'unit not stated')})
                </h3>
                <DataTable
                  testId={'verification-' + name}
                  caption={'Every lead this read measured or left unmeasured for ' + name + ', with the counts and notes it returned.'}
                  columns={['Lead (days)', 'Status as returned', 'Matched hours (n)', 'Forecast hours in this lead', 'Unmatched hours', 'Bias', 'MAE', 'RMSE', 'Correlation', 'Note as returned']}
                  rows={rows.map(row => [
                    orNot(row.lead_days),
                    orNot(row.status, 'status not stated'),
                    orNot(row.n),
                    orNot(row.forecast_hours),
                    orNot(row.unmatched_hours),
                    metric(row, 'bias'),
                    metric(row, 'mae'),
                    metric(row, 'rmse'),
                    metric(row, 'correlation'),
                    orNot(row.reason || row.correlation_note, 'no note returned'),
                  ])}
                />
              </div>
            ))
          ) : (
            <p className="module-note">{NO_ROW}: this read returned no measured comparison for this point and window.</p>
          )}
        </section>
      ) : null}
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
