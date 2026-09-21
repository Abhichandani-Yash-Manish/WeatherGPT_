/* Forecast verification: one bounded comparison this machine holds — archived model runs at fixed
   lead-time offsets matched hour by hour against the reference the read names, over one completed
   window and one point. The reference is reanalysis, a modelled analysis, not a station observation.
   The statistics describe this sample for this model, variable and window: this surface computes no
   metric, averages nothing, ranks nothing, and a lead the read did not measure stays unmeasured.

   Who this surface is for, and what it is for: a reader who is about to trust a forecast and wants to
   know how the archived runs for THIS point actually did, against the reference, over a window that has
   closed. Measured on 21 September 2026 in this build: the first screen was a title, three "Ask instead"
   chips and a card headed "What this comparison is" spending three paragraphs on what the surface does
   not claim — the first screen of forecast verification contained no verification. It contains one now,
   and the window fields arrive filled, because a surface whose first act is to ask a reader to invent two
   dates has not been finished. The dates are where the read's own refusal sentence says they have to be:
   "ERA5 hourly is published with about a five-day delay; choose an earlier window". */
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

/* Where the two window fields start: seven completed days ending six days ago, in the same basis the
   route measures the window in (UTC). Six is not a preference and not a computed reading — it is where
   the read's own refusal sentence puts the earliest window it will answer, "ERA5 hourly is published with
   about a five-day delay; choose an earlier window", with a day of margin. Both fields are visible and
   editable, and the window the read actually used is printed back beside the one that was asked for, so a
   default request can never be mistaken for a value the read returned. */
function completedWindow(days: number, now: Date = new Date()): { start: string; end: string } {
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - 6));
  const start = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate() - (days - 1)));
  const iso = (date: Date) => date.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end) };
}

/* The first-screen reading: the shortest measured lead's mean absolute error, in the read's own unit and
   the read's own words for what "mae" means. This is the trust-building line this surface has always
   buried in a table: it states what the sample measured, never forecast skill, never a confidence and
   never a ranking of one model against another. A window with no measured lead states that plainly
   instead of leaving a reader to find it by scanning every row for "unmeasured". */
function metricHeadline(variables: [string, LeadRow[]][], data?: VerificationData): { statement: string; source: string } {
  const sourceLine = 'forecast ' + orNot(data?.forecast?.source_id) + ' vs reference ' + orNot(data?.reference?.source_id)
    + ' · mae: ' + orNot(data?.method?.mae, 'definition not stated');
  for (const [name, rows] of variables) {
    const measured = rows
      .filter(row => row.status === 'measured' && row.mae !== null && row.mae !== undefined)
      .sort((a, b) => (a.lead_days ?? Infinity) - (b.lead_days ?? Infinity))[0];
    if (!measured) continue;
    const unit = data?.units?.[name];
    return {
      statement: 'At a ' + orNot(measured.lead_days) + '-day lead, this read’s ' + name + ' forecast differed from the reference by a '
        + 'mean absolute error of ' + measured.mae + (unit ? ' ' + unit : '') + ' over ' + count(measured.n, 'matched hour') + '.',
      source: sourceLine,
    };
  }
  return {
    statement: variables.length
      ? 'This read measured no lead with a stated mean absolute error for this window: every lead below is unmeasured, or measured with no mae value.'
      : 'This read returned no measured comparison for this point and window.',
    source: sourceLine,
  };
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
  const [place, setPlace] = useState<PlaceChoice | null>(() => readWorkingPlace());
  const [window, setWindow] = useState(() => completedWindow(7));
  const [start, setStart] = useState(window.start);
  const [end, setEnd] = useState(window.end);
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
  const returned = data?.window;
  const windowText = returned?.start && returned?.end ? returned.start + ' to ' + returned.end : NOT_RECORDED;
  const answered = ready && !read.isPending && !read.isError;
  const headline = answered ? metricHeadline(variables, data) : null;

  /* The controls a reader used to ask for this read. They are rendered in every state — while the
     read is in flight and after it has failed — so the place a reader just chose, and the window or the
     code they typed beside it, cannot disappear from under them at the moment they act. */
  const ask = (
    <section className="module-section">
      <h2>The point and the window</h2>
      {place ? <ReadingFor place={place} /> : null}
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
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => { const next = completedWindow(7); setWindow(next); setStart(next.start); setEnd(next.end); }}
        >
          The recent completed week
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => { const next = completedWindow(31); setWindow(next); setStart(next.start); setEnd(next.end); }}
        >
          The recent completed month
        </button>
      </div>
      {!ready ? (
        <Awaiting testId="verification-awaiting">
          Nothing has been read yet. Name a place below and this surface measures the archived model runs for it against
          the reference. The window starts on {window.start} to {window.end}
          {' '}— the most recent completed week the reference has published — and both dates can be moved.
        </Awaiting>
      ) : null}
      {/* The control block survives a read in flight, so the facts below it are drawn only once this read has
          answered: a field printed while the read is working would be an absence this surface has not
          established. */}
      {ready && !read.isPending && !read.isError ? (
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
      ) : null}
    </section>
  );

  return (
    <SurfaceShell
      title="Forecast verification"
      lead="How the archived model runs for one point actually did against the reference, over a window that has closed."
      what="the verification read"
      envelope={ready ? read.data : undefined}
      busy={ready && read.isPending}
      error={ready ? read.error : undefined}
      onRetry={() => read.refetch()}
      intents={intents}
      reading={headline ? { testId: 'verification-headline', statement: headline.statement, source: headline.source } : undefined}
      hold={ask}
    >
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

      {/* Under the evidence, folded: the three paragraphs that used to be the first screen of this surface,
          unchanged in wording and now where they define the numbers above them. */}
      <Meaning
        testId="verification-meaning"
        summary="What this comparison is, what was compared, and what it does not claim"
        lines={[
          { text: PROTOTYPE_NOT_SKILL, testId: 'verification-not-skill' },
          { text: WHAT_WAS_COMPARED, testId: 'verification-what-was-compared' },
        ]}
      />
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
