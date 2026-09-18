/* Farm advisories: the publisher's crop-advisory directory this machine holds, and the published brief
   for the district a reader names. A listing is not proof of a current bulletin. The brief is quoted
   published text kept apart from the model forecast: not a field recommendation, not a crop diagnosis,
   no dose and no go/no-go decision, and 'not issued' is not 'no risk'. The brief route refuses to infer
   a district from a coordinate, and this surface refuses in the same words. */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot, shortHash } from '../lib/format';
import { istStamp, istWindow } from '../lib/time';
import { viewById } from '../shell/views';
import { DataTable, EvidenceFooter, Failure, Facts, Limits, NO_ROW, NOT_RECORDED, PlacePicker, Reading, Sources,
  SurfaceShell, type PlaceChoice } from './Evidence';

type Entry = { id?: string; label?: string };
type HoldingRow = { region?: string; state?: string | null; documents?: number; passages?: number;
  newest_issue_date?: string | null; oldest_issue_date?: string | null; age_days?: number | null; languages?: string[]; body?: string | null };
type HoldingState = { state?: string; regions?: number; documents?: number; passages?: number; newest_issue_date?: string | null };
/* The corpus read's document row, used only when this server build does not serve the holdings view. */
type CorpusDocument = { region?: string | null; state?: string | null; issue_date?: string | null; age_days?: number | null;
  passages?: number; family?: string; sha_prefix?: string };
type Point_ = { latitude?: number | null; longitude?: number | null };
type Window_ = { first_valid?: string | null; last_valid?: string | null };
type Passage = { source_id?: string; page?: number | string | null; issue_date?: string | null; section?: string | null; crop?: string | null; growth_stage?: string | null; quote?: string | null };
type Value = { parameter?: string; label?: string | null; first_value?: unknown; last_value?: unknown; unit?: string | null; samples?: number | null; series_start?: string | null; series_end?: string | null; source_id?: string | null };
type Brief = {
  status?: string; why?: string | null; query?: string | null; attempts?: string[]; crops_named_by_the_edition?: string[];
  request?: { crop?: string | null; growth_stage?: string | null; topic?: string | null; mode?: string | null; region?: string | null; state?: string | null; window?: Window_ | null; point?: Point_ | null };
  published_advice?: { family?: string | null; scope?: string | null; region?: string | null; passages?: Passage[]; matched?: number };
  forecast?: { status?: string; note?: string; values?: Value[] }; conditions_named_by_the_source?: string[];
  decision_support?: { what_the_source_conditions_are?: string[]; what_is_missing_for_a_decision?: string[]; statement?: string };
  not_established?: string[]; limitations?: string[]; sources?: string[]; brief_id?: string; forecast_status?: string | null; generated_at_utc?: string;
};

export const intents: string[] = (viewById('advisories')?.intents ?? []).concat([
  'Which districts does this machine hold a published advisory edition for?',
]);

const DAY_CHOICES = ['1', '2', '3', '5', '7'];
const MODE_CHOICES: [string, string][] = [['source_lookup', 'source lookup: the published text only'], ['decision_support', 'decision support: what a decision would still need']];
const REQUEST_FIELDS: [string, string][] = [['region', 'District or region (required)'], ['state', 'State as published'], ['crop', 'Crop'], ['stage', 'Growth stage'], ['topic', 'Topic']];
const REFUSAL = 'Name the district or region whose published advice should be read; the workspace will not guess one from a coordinate.';

export function Surface(): JSX.Element {
  const [chosen, setChosen] = useState('');
  const [needle, setNeedle] = useState('');
  const [form, setForm] = useState<Record<string, string>>({ mode: 'source_lookup', day: '1' });
  const [asked, setAsked] = useState<Record<string, string> | null>(null);
  const [refused, setRefused] = useState(false);
  const [point, setPoint] = useState<PlaceChoice | null>(null);
  const [holdingNeedle, setHoldingNeedle] = useState('');
  const [holdingState, setHoldingState] = useState('');

  const states = useQuery({
    queryKey: ['advisory-states'],
    queryFn: () => getJson<Envelope<{ states?: Entry[] }>>('/api/advisories/states'),
    retry: false,
  });
  const stateRows = states.data?.data?.states || [];
  /* What this machine holds, from the corpus index. The surface used to open on the publisher's
     directory alone, so a reader could see 36 listed states and no advisory text at all. */
  const holdings = useQuery({
    queryKey: ['advisory-holdings'],
    queryFn: () => getJson<Envelope<{ regions?: HoldingRow[]; states?: HoldingState[]; counts?: Record<string, number> }>>(
      withQuery('/api/advisories/holdings', { family: 'district_agromet', limit: 1000 })),
    retry: false, staleTime: 120_000,
  });
  /* A workspace started before the holdings view existed answers 404 for it, and the surface must not be blank
     for that: the corpus read it already serves carries the same editions. The fallback is used only when the
     dedicated read fails, and the panel says which read produced the rows. */
  const corpusFallback = useQuery({
    queryKey: ['advisory-holdings-fallback'],
    queryFn: () => getJson<Envelope<{ documents?: CorpusDocument[]; counts?: Record<string, number> }>>(
      withQuery('/api/corpus', { family: 'district_agromet', documents_listed: 200 })),
    enabled: holdings.isError, retry: false, staleTime: 60_000,
  });
  const holdingsStatus = holdings.isError ? (holdings.error as { status?: number } | null)?.status : undefined;
  /* The first directory row the payload returned selects the state; a row with no id selects none. */
  const activeState = chosen || stateRows[0]?.id || '';
  const districts = useQuery({
    queryKey: ['advisory-districts', activeState],
    queryFn: () => getJson<Envelope<{ state?: string; districts?: Entry[] }>>(withQuery('/api/advisories/districts', { state: activeState })),
    enabled: activeState !== '', retry: false,
  });
  /* The brief is read only for a district the reader named: a coordinate is never turned into one. */
  const brief = useQuery({
    queryKey: ['advisory-brief', asked],
    queryFn: () => getJson<Brief>(withQuery('/api/advisories/brief', { ...(asked || {}) })),
    enabled: asked !== null, retry: false,
  });

  const districtRows = districts.data?.data?.districts || [];
  /* The state name the payload printed for the selected row; the payload's own id stands in when it printed none. */
  const activeLabel = stateRows.find(entry => entry.id === activeState)?.label || activeState;
  /* Rows from the holdings view, or derived from the corpus documents when only that read answered. */
  const fallbackDocuments = (corpusFallback.data?.data?.documents || []).filter(row => Boolean(row.region));
  const fallbackRows: HoldingRow[] = fallbackDocuments.map(row => ({
    region: row.region || undefined, state: row.state ?? null, documents: 1, passages: row.passages,
    newest_issue_date: row.issue_date ?? null, age_days: row.age_days ?? null,
  }));
  const holdingRows = holdings.data?.data?.regions || fallbackRows;
  const holdingStates = holdings.data?.data?.states?.length
    ? holdings.data!.data!.states!
    : Array.from(fallbackRows.reduce((buckets, row) => {
        const name = row.state || 'state not stated in the held editions';
        const bucket = buckets.get(name) || { state: name, regions: 0, documents: 0, passages: 0, newest_issue_date: null as string | null };
        bucket.regions = (bucket.regions || 0) + 1;
        bucket.documents = (bucket.documents || 0) + (row.documents || 0);
        bucket.passages = (bucket.passages || 0) + (row.passages || 0);
        if (row.newest_issue_date && (!bucket.newest_issue_date || row.newest_issue_date > bucket.newest_issue_date)) bucket.newest_issue_date = row.newest_issue_date;
        buckets.set(name, bucket);
        return buckets;
      }, new Map<string, HoldingState>()).values());
  const holdingCounts = holdings.data?.data?.counts || {
    regions: holdingRows.length,
    documents: holdingRows.reduce((sum, row) => sum + (row.documents || 0), 0),
    passages: holdingRows.reduce((sum, row) => sum + (row.passages || 0), 0),
    states_named: new Set(holdingRows.map(row => row.state).filter(Boolean)).size,
    regions_without_a_printed_issue_date: holdingRows.filter(row => !row.newest_issue_date).length,
  };
  const holdingsFromFallback = holdings.isError && fallbackRows.length > 0;
  const heldTerm = holdingNeedle.trim().toLowerCase();
  const heldRegions = holdingRows.filter(entry => (
    (!holdingState || String(entry.state || '') === holdingState)
    && (!heldTerm || (String(entry.region || '') + ' ' + String(entry.state || '')).toLowerCase().includes(heldTerm))));

  const term = needle.trim().toLowerCase();
  const matched = term ? districtRows.filter(row => String(row.label || row.id || '').toLowerCase().includes(term)) : districtRows;
  const path = brief.data;
  const forecast = path?.forecast;
  const window_ = path?.request?.window;

  function ask() {
    if (!(form.region || '').trim()) { setRefused(true); setAsked(null); return; }
    setRefused(false);
    setAsked({ ...form, ...(point ? { lat: String(point.latitude), lon: String(point.longitude) } : {}) });
  }

  return (
    <SurfaceShell
      title="Farm advisories"
      lead="The publisher's district crop-advisory directory this machine read, and the published brief for one district you name, with the model forecast kept apart as context."
      what="the advisory directory" envelope={states.data} busy={states.isPending} error={states.error}
      onRetry={() => states.refetch()}
    >
      <section className="module-section">
        <h2>The published directory</h2>
        <p className="module-note">
          Directory rows as the publisher returned them. A listing is not proof that a bulletin was issued for that state or district, and a row the payload did not return cannot be shown here.
        </p>
        <DataTable testId="advisories-states" caption="Every state row this read returned, with the payload's own identifier."
          columns={['State as published', 'Source identifier']} rows={stateRows.map(entry => [orNot(entry.label), orNot(entry.id)])} />
        <div className="module-controls">
          <label className="module-field" htmlFor="advisory-state-select">
            <span>State to read districts for</span>
            <select id="advisory-state-select" value={activeState} onChange={event => setChosen(event.target.value)}>
              {stateRows.map((entry, index) => (
                <option key={entry.id || 'row-' + index} value={entry.id || ''}>
                  {orNot(entry.label, orNot(entry.id, 'row ' + (index + 1) + ' without a stated name'))}
                </option>
              ))}
            </select>
          </label>
          <label className="module-field" htmlFor="advisory-filter">
            <span>District name contains</span>
            <input id="advisory-filter" type="search" value={needle} placeholder="e.g. Ahmedabad" onChange={event => setNeedle(event.target.value)} />
          </label>
        </div>
        <p className="module-note">
          This filter runs in this browser over the {count(districtRows.length, 'district row')} this read returned for {orNot(activeLabel, 'no state read yet')}:
          the publisher is not asked again, so a district this read did not return cannot appear here.
        </p>
        <p className="module-note" role="status" data-testid="advisories-count">
          Showing {count(matched.length, 'district row')} of {count(districtRows.length, 'district row')} read for this state.
        </p>
        {districts.isPending && activeState ? (
          <Reading what="the district directory" />
        ) : districts.isError ? (
          <Failure error={districts.error} what="district directory" onRetry={() => districts.refetch()} />
        ) : (
          <>
            <DataTable testId="advisories-districts" caption="The district rows this read returned that match the filter above; the filter never asks the publisher again."
              columns={['District as published', 'Source identifier', 'State read']}
              rows={matched.map(entry => [orNot(entry.label), orNot(entry.id), orNot(districts.data?.data?.state, activeState)])} />
            {districts.data ? <EvidenceFooter envelope={districts.data} /> : null}
          </>
        )}
      </section>

      <section className="module-section">
        <h2>What this machine holds</h2>
        <p className="module-note">
          The advisory editions this machine has ingested, one row per published region, with the edition&rsquo;s
          own printed issue date, the age the corpus measured against that edition&rsquo;s retrieval instant, and
          the number of indexed passages behind it. This is an inventory, not a coverage claim: a region the
          publisher lists and this machine does not hold does not appear here, and a region whose edition states
          no printed date shows that as unknown.
        </p>
        <div className="module-controls">
          <label className="module-field" htmlFor="advisory-holding-filter">
            <span>Region or state contains</span>
            <input id="advisory-holding-filter" type="search" value={holdingNeedle} placeholder="e.g. Ahmedabad or Gujarat"
              onChange={event => setHoldingNeedle(event.target.value)} />
          </label>
          <label className="module-field" htmlFor="advisory-holding-state">
            <span>State held</span>
            <select id="advisory-holding-state" value={holdingState} onChange={event => setHoldingState(event.target.value)}>
              <option value="">Every state this machine holds editions for</option>
              {holdingStates.map(entry => (
                <option key={entry.state} value={entry.state}>{orNot(entry.state)} ({entry.regions})</option>
              ))}
            </select>
          </label>
        </div>
        {holdings.isPending ? (
          <Reading what="the advisory holdings" />
        ) : holdings.isError && !holdingsFromFallback ? (
          <Failure error={holdings.error} what="advisory holdings" onRetry={() => { holdings.refetch(); corpusFallback.refetch(); }} />
        ) : corpusFallback.isPending && holdings.isError ? (
          <Reading what="the advisory holdings from the corpus index" />
        ) : (
          <>
            <Facts testId="advisories-holdings-counts" rows={[
              ['Regions held', orNot(holdingCounts.regions)],
              ['Documents held', orNot(holdingCounts.documents)],
              ['Indexed passages', orNot(holdingCounts.passages)],
              ['States named by the editions', orNot(holdingCounts.states_named)],
              ['Regions whose edition states no printed date', orNot(holdingCounts.regions_without_a_printed_issue_date)],
            ]} />
            {holdingsFromFallback ? (
              <p className="module-note" data-testid="advisories-holdings-source">
                These rows come from the corpus index read (<span className="evidence">/api/corpus</span>) because this
                workspace build did not answer the holdings view
                {holdingsStatus === 404 ? ' (it answered 404, so it was started before that view existed)' : ''}.
                Restart the local workspace to serve <span className="evidence">/api/advisories/holdings</span>; the
                editions listed here are the same ones either way.
              </p>
            ) : null}
            <p className="module-note" role="status" data-testid="advisories-holdings-status">
              Showing {count(heldRegions.length, 'region')} of {count(holdingRows.length, 'region')} held here
              {holdingState ? ' in ' + holdingState : ''}. Reading a region&rsquo;s advice quotes its published text below.
            </p>
            <DataTable testId="advisories-holdings"
              caption="The advisory editions this machine holds for the filter above, newest printed edition first. A row is an ingested edition, not proof of a current issue."
              columns={['Region', 'State as published', 'Newest printed issue', 'Age at its retrieval', 'Documents', 'Passages', '']}
              rows={heldRegions.slice(0, 60).map(entry => [
                orNot(entry.region),
                orNot(entry.state, 'state not stated in the held edition'),
                orNot(entry.newest_issue_date, NOT_RECORDED),
                typeof entry.age_days === 'number' ? entry.age_days + ' days' : NOT_RECORDED,
                orNot(entry.documents),
                orNot(entry.passages),
                <button key="read" type="button" className="btn" data-testid={'advisory-read-' + entry.region}
                  onClick={() => {
                    /* A holding row names the region the publisher's edition carries, so the brief is asked for
                       exactly that region in source-lookup mode: the published text, not a decision. */
                    const next = { ...form, region: String(entry.region || ''), state: String(entry.state || ''), mode: 'source_lookup' };
                    setForm(next);
                    setRefused(false);
                    setAsked({ ...next, ...(point ? { lat: String(point.latitude), lon: String(point.longitude) } : {}) });
                    setChosen(stateRows.find(row => row.label === entry.state)?.id || '');
                  }}>
                  Read its advice
                </button>,
              ])} />
            {heldRegions.length > 60 ? (
              <p className="module-note">Showing the first 60 of {count(heldRegions.length, 'region')} that match; narrow the filter to reach the rest.</p>
            ) : null}
            {holdings.data ? <EvidenceFooter envelope={holdings.data} /> : null}
          </>
        )}
      </section>

      <section className="module-section">
        <h2>The published brief for one district</h2>
        <p className="module-note" data-testid="advisories-standing">
          This is the publisher&rsquo;s advisory text for a named district, quoted as printed. It is not a field recommendation and it is not a crop diagnosis: no pesticide dosage and no irrigation decision is made here. A district whose advice was not published is &lsquo;not issued&rsquo; rather than &lsquo;no risk&rsquo;.
        </p>
        <p className="module-note">
          {REFUSAL} So name the district: this surface does not read a coordinate as one, and it asks rather than guessing.
        </p>
        <div className="module-controls">
          {REQUEST_FIELDS.map(([name, label]) => (
            <label className="module-field" key={name} htmlFor={'advisory-' + name}>
              <span>{label}</span>
              <input id={'advisory-' + name} type="text" value={form[name] || ''} onChange={event => setForm({ ...form, [name]: event.target.value })} />
            </label>
          ))}
          <label className="module-field" htmlFor="advisory-mode">
            <span>Mode</span>
            <select id="advisory-mode" value={form.mode} onChange={event => setForm({ ...form, mode: event.target.value })}>
              {MODE_CHOICES.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
            </select>
          </label>
          <label className="module-field" htmlFor="advisory-day">
            <span>Forecast days for the context</span>
            <select id="advisory-day" value={form.day} onChange={event => setForm({ ...form, day: event.target.value })}>
              {DAY_CHOICES.map(value => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <button type="button" className="btn" onClick={ask}>Read the published brief</button>
        </div>
        <PlacePicker onPick={setPoint} hint="Optional: name a place for the forecast context. The point never selects a district — the district is the one you name above." />
        {refused ? <p className="module-failure" role="alert" data-testid="advisories-refusal">{REFUSAL} No brief was read and no district was assumed.</p> : null}

        {asked === null ? (
          <p className="module-note" data-testid="advisories-brief-idle">No district has been named yet, so no brief was composed and no advice is shown.</p>
        ) : brief.isPending ? (
          <Reading what="the published brief" />
        ) : brief.isError ? (
          <Failure error={brief.error} what="published brief" onRetry={() => brief.refetch()} />
        ) : path ? (
          <>
            <Facts testId="advisories-brief-identity" rows={[
              ['Status as returned', orNot(path.status) + ' · forecast context ' + orNot(path.forecast_status || forecast?.status)],
              ['Edition read', path.published_advice ? orNot(path.published_advice.family) + ' (' + orNot(path.published_advice.scope) +
                ') for ' + orNot(path.published_advice.region) : NOT_RECORDED],
              ['Passages quoted', path.published_advice ? orNot(path.published_advice.matched) : NOT_RECORDED],
              ['Request as the brief understood it', [orNot(path.request?.region, asked.region), orNot(path.request?.crop),
                orNot(path.request?.growth_stage), orNot(path.request?.topic), orNot(path.request?.mode)].join(' · ')],
              ['Forecast window', istWindow(window_?.first_valid, window_?.last_valid)],
              ['Point used for context', path.request?.point ? String(path.request.point.latitude) + ', ' + String(path.request.point.longitude)
                : 'no point was given, so no forecast context was retrieved'],
              ['Brief identity / composed at', (path.brief_id ? 'sha256 ' + shortHash(path.brief_id, 16) : NOT_RECORDED) + ' · ' +
                (path.generated_at_utc ? istStamp(path.generated_at_utc) : NOT_RECORDED)],
            ]} />
            {path.status === 'ok' ? null : (
              <p className="module-note" data-testid="advisories-brief-not-available">
                {orNot(path.why, 'the payload stated no reason for a missing brief')} Query: {orNot(path.query, NO_ROW)}.
                Editions searched: {(path.attempts || []).join(', ') || NO_ROW}. Crops the edition names: {(path.crops_named_by_the_edition || []).join(', ') || NOT_RECORDED}.
              </p>
            )}
            <h3>Published advice, quoted</h3>
            <DataTable testId="advisories-passages" caption="Each passage with its source, its printed issue date and its physical page, quoted as published."
              columns={['Source, page and printed issue', 'Crop / stage as the passage names them', 'Quote as printed']}
              rows={(path.published_advice?.passages || []).map(passage => [orNot(passage.source_id) + ' · page ' + orNot(passage.page) +
                ' · printed ' + orNot(passage.issue_date) + (passage.section ? ' · ' + passage.section : ''),
                orNot(passage.crop) + ' / ' + orNot(passage.growth_stage), passage.quote || 'the passage returned no quote'])} />
            <h3>Conditions the source itself names</h3>
            {(path.conditions_named_by_the_source || []).length ? (
              <div className="module-limits">
                <ul>{(path.conditions_named_by_the_source || []).map((condition, index) => <li key={index}>{condition}</li>)}</ul>
              </div>
            ) : <p className="module-note">This brief returned no condition line, so no condition is attributed to the source.</p>}
            <h3>Forecast context</h3>
            <p className="module-note">{orNot(forecast?.note, 'the brief returned no forecast note')} Status as returned: {orNot(forecast?.status)}.</p>
            <DataTable testId="advisories-forecast" caption="Model values as the brief returned them: the first and last value of each retrieved series, with the sample count."
              columns={['Parameter', 'First value', 'Last value', 'Samples', 'Unit', 'Series starts', 'Series ends', 'Source']}
              rows={(forecast?.values || []).map(value => [orNot(value.label || value.parameter), orNot(value.first_value), orNot(value.last_value),
                orNot(value.samples), orNot(value.unit, 'unit not stated'), value.series_start ? istStamp(value.series_start) : NOT_RECORDED,
                value.series_end ? istStamp(value.series_end) : NOT_RECORDED, orNot(value.source_id)])} />
            {path.decision_support ? (
              <div className="module-limits">
                <h3>Decision support as the payload stated it</h3>
                <p className="module-note">{orNot(path.decision_support.statement, NO_ROW)}</p>
                <p className="module-fact-label">Conditions the source names</p>
                <ul>{(path.decision_support.what_the_source_conditions_are || []).map((line, index) => <li key={index}>{line}</li>)}</ul>
                <p className="module-fact-label">What a decision would still need</p>
                <ul>{(path.decision_support.what_is_missing_for_a_decision || []).map((line, index) => <li key={index}>{line}</li>)}</ul>
              </div>
            ) : null}
            <Limits limitations={path.limitations} not_established={path.not_established} />
            <Sources sources={(path.sources || []).map(source_id => ({ source_id }))} />
          </>
        ) : null}
      </section>
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
