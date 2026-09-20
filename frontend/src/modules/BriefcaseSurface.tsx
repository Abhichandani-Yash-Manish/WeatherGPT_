/* The briefcase: the briefs this workspace composed from its own sources and kept on this machine.
   /api/briefs is not envelope-shaped — it states a version, a delivery state and a note, and attaches no
   coverage, limitation or source row — so the footer prints the sections it does not have as the absence they
   are. The server composes a brief when asked; nothing here is delivered or published. */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, getJson, postJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { downloadFile } from '../chat/actions';
import { count, orNot } from '../lib/format';
import { istStamp, istWindow } from '../lib/time';
import { viewById } from '../shell/views';
import { DataTable, Facts, Failure, NOT_RECORDED, PinPlaceButton, PlacePicker, Reading, SurfaceShell, failureSentence, type PlaceChoice } from './Evidence';

export const intents: string[] = (viewById('briefcase')?.intents ?? []).concat([
  'Which briefs are kept on this machine, and what does each one rest on?',
  'Compose an alert brief for a place I name, and keep it in the briefcase.',
  'What does a kept brief say is not established, and what does it export as?',
]);

type BriefEvidence = { sources?: string[]; not_established?: string[]; why?: string | null; notes?: string[] };
type BriefEntry = {
  id?: string; saved_at?: string; kind?: string; title?: string; status?: string; delivery?: string;
  place?: { district?: string | null; state?: string | null; label?: string | null; latitude?: number | null; longitude?: number | null };
  window?: { label?: unknown; day?: number | null; starts_utc?: string | null; ends_utc?: string | null };
  content_sha256?: string; sources?: string[]; evidence?: BriefEvidence;
};
type BriefsView = { schema_version?: string; delivery?: string; note?: string; briefs?: BriefEntry[] };
type OpenedView = { schema_version?: string; delivery?: string; entry?: BriefEntry; markdown?: string };
type KeepView = { detail?: string; saved?: boolean; entry?: BriefEntry };
type DeletedView = { deleted?: string; detail?: string };

/* /api/briefing/latest is a file-series read, not a service: it states whether a briefing exists in
   this machine's series directory, the run it holds and the limits written with it. */
type BriefingRun = {
  generated_at_utc?: string | null; briefing_id?: string | null; place_count?: number | null; day_number?: number | null;
  forecast_days?: number | null; sources?: string[]; change?: string | null; latency_seconds?: number | null;
  interval_seconds?: number | null; record_path?: string | null; markdown_path?: string | null; runner_note?: string | null;
};
type BriefingSeriesRow = { run?: number | null; generated_at_utc?: string | null; place_count?: number | null; latency_seconds?: number | null; change?: string | null };
type BriefingView = {
  schema_version?: string; present?: boolean; directory?: string | null; note?: string | null; detail?: string | null;
  run?: BriefingRun | null; briefing?: { not_established?: string[] } | null; markdown?: string | null; series?: BriefingSeriesRow[];
};

/* The export file name is derived from the entry the same way the store route derives it: a slug of the
   title and the first eight characters of the identifier. Nothing is invented, and the browser writes the
   file, so an export is a file the reader keeps on this machine. */
export function exportFileName(entry: BriefEntry): string {
  const slug = String(entry.title || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'brief';
  return slug + '-' + String(entry.id || '').slice(0, 8) + '.md';
}

const placesInWords = (value?: number | null): string => (typeof value === 'number' ? value + ' place(s)' : NOT_RECORDED);
const secondsInWords = (value?: number | null): string => (typeof value === 'number' ? value + ' s' : NOT_RECORDED);

function listEnvelope(view: BriefsView): Envelope<BriefsView> {
  return { schema_version: orNot(view.schema_version), data: view };
}

function placeLine(entry: BriefEntry): string {
  const place = entry.place || {};
  const name = orNot(place.label || place.district, 'place not recorded');
  return place.state && place.state !== place.district && place.state !== place.label ? name + ', ' + place.state : name;
}

/* A window is read as the entry states it; an advisory entry's own first_valid/last_valid instants are formatted as returned. */
function windowLine(entry: BriefEntry): string {
  const window = entry.window || {};
  if (typeof window.label === 'string' && window.label.trim()) {
    return window.day === null || window.day === undefined ? window.label : window.label + ' · day ' + window.day;
  }
  if (window.starts_utc || window.ends_utc) return istWindow(window.starts_utc, window.ends_utc);
  const label = (window.label || {}) as { first_valid?: string; last_valid?: string };
  return label.first_valid || label.last_valid ? istWindow(label.first_valid, label.last_valid) : NOT_RECORDED;
}

const sourceIds = (entry: BriefEntry): string[] => (entry.sources?.length ? entry.sources : entry.evidence?.sources || []);
const StatedList = ({ lines, what }: { lines?: string[]; what: string }): JSX.Element =>
  lines?.length ? <ul>{lines.map((line, index) => <li key={index}>{line}</li>)}</ul>
                 : <p className="module-note">This entry carries no {what} line.</p>;

export function Surface(): JSX.Element {
  const client = useQueryClient();
  const [point, setPoint] = useState<PlaceChoice | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<BriefEntry | null>(null);
  const [removed, setRemoved] = useState<{ id?: string; title: string; detail: string } | null>(null);
  const kept = useQuery({ queryKey: ['briefcase'], queryFn: () => getJson<BriefsView>('/api/briefs'), retry: false });
  const opened = useQuery({ queryKey: ['briefcase-entry', openId], enabled: openId !== null, retry: false,
                            queryFn: () => getJson<OpenedView>(withQuery('/api/briefs/get', { id: openId })) });
  const keep = useMutation({
    mutationFn: () => postJson<KeepView>('/api/briefs/save', { kind: 'alert_brief', lat: point?.latitude, lon: point?.longitude }),
    retry: false, onSuccess: () => { void client.invalidateQueries({ queryKey: ['briefcase'] }); },
  });
  const remove = useMutation({
    mutationFn: (entry: BriefEntry) => postJson<DeletedView>('/api/briefs/delete', { id: entry.id }),
    retry: false,
    onSuccess: (result, entry) => {
      setRemoved({ id: result.deleted || entry.id, title: entry.title || entry.id || 'the kept brief', detail: orNot(result.detail, 'this read returned no detail line') });
      setConfirming(null);
      if (openId && openId === entry.id) setOpenId(null);
      void client.invalidateQueries({ queryKey: ['briefcase'] });
    },
  });
  /* An export reads the file route for one entry and hands the browser the Markdown file it returned.
     The read goes through the API client like every other read, and nothing is delivered, pushed or
     published by it: the file stays wherever the reader saves it. */
  const exportBrief = useMutation({
    mutationFn: async (item: BriefEntry) => {
      const markdown = await api<string>(withQuery('/api/briefs/export', { id: item.id }));
      const name = exportFileName(item);
      downloadFile(name, markdown, 'text/markdown');
      return { name: name, title: item.title || item.id || 'the kept brief' };
    },
    retry: false,
  });
  const briefing = useQuery({ queryKey: ['briefing-latest'], queryFn: () => getJson<BriefingView>('/api/briefing/latest'), retry: false });
  const view = kept.data;
  const entries = view?.briefs || [];
  const entry = opened.data?.entry;

  return (
    <SurfaceShell
      title="Briefcase"
      lead="Briefs this workspace composed from its own sources and kept on this machine. A brief is asked for and composed by the server — this page cannot post one. Nothing here is delivered or published, and the briefcase is not a warning service."
      what="kept-brief list"
      envelope={view ? listEnvelope(view) : undefined}
      busy={kept.isPending}
      error={kept.error}
      onRetry={() => { void kept.refetch(); }}
      intents={intents}
    >
      <section className="module-section">
        <h2>Kept briefs</h2>
        <p className="module-note" role="status" aria-live="polite" data-testid="briefcase-count">
          {view?.briefs ? count(entries.length, 'kept brief') + ' in this read' : 'This read returned no briefs list'} ·
          delivery as returned: <span className="evidence">{orNot(view?.delivery)}</span>
        </p>
        <p className="module-note" data-testid="briefcase-delivery-note">
          This read's own delivery sentence: {orNot(view?.note, 'this read returned no delivery note')}
        </p>
        <p className="module-note">
          Kept briefs are composed from their sources and held on this machine only; an export is a file you keep, not a delivery.
          Deleting removes the entry from this machine's local store. The briefcase is not a warning service and is not an all-clear.
        </p>
        <DataTable
          testId="briefcase-table"
          caption="Every kept brief this read returned, one row per entry."
          columns={['Brief', 'Kind', 'Place', 'Window', 'Saved', 'Sources named', 'Status', 'Controls']}
          rows={entries.map(item => [
            orNot(item.title, item.id || NOT_RECORDED), orNot(item.kind),
            placeLine(item), windowLine(item),
            item.saved_at ? istStamp(item.saved_at) : NOT_RECORDED,
            sourceIds(item).length ? sourceIds(item).join(', ') : 'none named in this entry',
            orNot(item.status, 'status not recorded'),
            <span key="controls">
              <button type="button" className="btn btn-ghost" aria-label={'Open ' + (item.title || item.id)} onClick={() => setOpenId(item.id || null)}>Open</button>{' '}
              <button type="button" className="btn btn-ghost" aria-label={'Export ' + (item.title || item.id)} onClick={() => { exportBrief.reset(); exportBrief.mutate(item); }}>Export</button>{' '}
              <button type="button" className="btn btn-ghost btn-danger" aria-label={'Delete ' + (item.title || item.id)} onClick={() => { remove.reset(); setRemoved(null); setConfirming(item); }}>Delete</button>
            </span>,
          ])}
        />
        <p className="module-note" data-testid="briefcase-export-note">
          Download reads GET /api/briefs/export?id=&lt;entry&gt; and hands the browser the Markdown file the store composed for that
          entry. An export is a file you keep on this machine; nothing is delivered, pushed or published by it.
        </p>
        {exportBrief.isPending ? <Reading what="the export file" /> : null}
        {exportBrief.data ? (
          <p className="module-note" role="status" data-testid="briefcase-export">
            Exported “{exportBrief.data.title}” as {exportBrief.data.name} — a Markdown file you keep on this machine. Nothing was
            delivered, pushed or published.
          </p>
        ) : null}
        {exportBrief.isError ? (
          <div role="alert">
            <p className="reading">{failureSentence(exportBrief.error)}</p>
            <p className="module-note">This export was not written: the read failed, and no file was handed to the browser.</p>
            <button type="button" className="btn" onClick={() => { if (exportBrief.variables) exportBrief.mutate(exportBrief.variables); }}>Retry this export</button>
          </div>
        ) : null}
        {confirming ? (
          <div className="module-section" data-testid="briefcase-confirm">
            <h3>Remove “{orNot(confirming.title, confirming.id || NOT_RECORDED)}” from this machine's local store?</h3>
            <p className="module-note">
              This asks the workspace to delete the kept entry from the briefcase. An exported file stays where you saved it, and
              nothing was delivered or published from the entry either way.
            </p>
            <div className="module-controls">
              <button type="button" className="btn btn-danger" disabled={remove.isPending} onClick={() => remove.mutate(confirming)}>Yes, remove it from the local store</button>
              <button type="button" className="btn btn-ghost" onClick={() => setConfirming(null)}>Keep it</button>
            </div>
            {remove.isError ? (
              <div role="alert">
                <p className="reading">{failureSentence(remove.error)}</p>
                <button type="button" className="btn" onClick={() => remove.mutate(confirming)}>Retry this removal</button>
              </div>
            ) : null}
          </div>
        ) : null}
        {removed ? (
          <p className="module-note" role="status" data-testid="briefcase-removed">
            Removed “{removed.title}” (entry {orNot(removed.id, 'identifier not recorded')}): {removed.detail}
          </p>
        ) : null}
      </section>

      {openId ? (
        <section className="module-section" data-testid="briefcase-entry">
          <h2>Opened brief</h2>
          {opened.isPending ? <Reading what="kept brief" /> : null}
          {opened.isError ? <Failure error={opened.error} what="kept brief" onRetry={() => { void opened.refetch(); }} /> : null}
          {entry ? (
            <>
              <h3>{orNot(entry.title, entry.id || NOT_RECORDED)}</h3>
              <Facts testId="briefcase-entry-facts" rows={[
                ['Status as stored', orNot(entry.status, 'status not recorded in this entry')], ['Saved', entry.saved_at ? istStamp(entry.saved_at) : NOT_RECORDED],
                ['Entry id', orNot(entry.id, 'identifier not recorded')], ['Kind', orNot(entry.kind)],
                ['Place', placeLine(entry)], ['Window', windowLine(entry)],
                ['Coordinates in the entry', typeof entry.place?.latitude === 'number' && typeof entry.place?.longitude === 'number'
                  ? entry.place.latitude + ', ' + entry.place.longitude : 'coordinates not recorded in this entry'],
                ['Content hash', entry.content_sha256 ? 'sha256 ' + entry.content_sha256.slice(0, 16) : NOT_RECORDED],
              ]} />
              <h3>Source identifiers this entry names</h3>
              <DataTable testId="briefcase-entry-sources"
                caption="The identifiers stored with the entry. The entry keeps identifiers, not registry rows, so product, retrieval instant and hash are stated as not recorded here."
                columns={['Source', 'Product', 'Retrieved', 'sha256 prefix']}
                rows={sourceIds(entry).map(id => [id, NOT_RECORDED, NOT_RECORDED, NOT_RECORDED])} />
              <h3>Not established, notes and reason this entry carries</h3>
              <StatedList lines={entry.evidence?.not_established} what="not-established" />
              {entry.evidence?.why ? <p className="module-note">Why it is stored as it is: {entry.evidence.why}</p> : null}
              <StatedList lines={entry.evidence?.notes} what="note" />
              <h3>The brief as written</h3>
              <p className="module-note">The export route returns this same Markdown as a file you keep; nothing was delivered or published from it.</p>
              <pre data-testid="briefcase-markdown">{orNot(opened.data?.markdown, 'this read returned no Markdown for the entry')}</pre>
            </>
          ) : <p className="module-note">This read answered without an entry for that identifier.</p>}
        </section>
      ) : null}

      <section className="module-section">
        <h2>Compose an alert brief for a point</h2>
        <p className="module-note">
          The workspace composes the brief from the official district warning product and the CAP relay, keeps the entry it returns and
          names the day it used. The client asks for a brief; it cannot post one. A brief is composed for a point, so this control is
          offered only once a place row states coordinates. No day is sent: the first published day is composed.
        </p>
        <PlacePicker onPick={chosen => { keep.reset(); setPoint(chosen); }}
                     hint="Type at least two characters; only a row that states coordinates can be read as a point." />
        {point ? (
          <>
            <Facts testId="briefcase-point" id="briefcase-point-facts" rows={[['Point resolved', orNot(point.label, 'label not recorded')], ['Coordinates', point.latitude + ', ' + point.longitude]]} />
            <div className="module-controls">
              <button type="button" className="btn" disabled={keep.isPending} onClick={() => keep.mutate()}>Compose and keep an alert brief for this point</button>
              <PinPlaceButton place={point} describedBy="briefcase-point-facts" />
            </div>
            {keep.data ? (
              <p className="module-note" role="status" data-testid="briefcase-kept">
                {orNot(keep.data.detail, 'This read returned no detail line for the keep.')} Kept as “
                {orNot(keep.data.entry?.title, 'title not recorded')}”, entry {orNot(keep.data.entry?.id, 'identifier not recorded')},
                saved {keep.data.entry?.saved_at ? istStamp(keep.data.entry.saved_at) : NOT_RECORDED}, status as stored: {orNot(keep.data.entry?.status, 'status not recorded')}.
              </p>
            ) : null}
            {keep.isError ? (
              <div role="alert">
                <p className="reading">{failureSentence(keep.error)}</p>
                <button type="button" className="btn" onClick={() => keep.mutate()}>Retry this request</button>
              </div>
            ) : null}
          </>
        ) : (
          <p className="module-note">No point is resolved yet, so no compose control is offered: a brief is composed for a point, and the route refuses a request without lat and lon.</p>
        )}
      </section>

      {/* The briefing series is a local file series, not a service. The surface reads the newest run the
          workspace series directory holds and states the run, the limits written with it and what it
          does not establish; with no run written yet it says so rather than omitting the section. */}
      <section className="module-section" data-testid="briefing-latest">
        <h2>Latest briefing on this machine</h2>
        <p className="module-note">
          A briefing is a foreground run of this local prototype: it reads the connected products for named places and writes a
          Markdown file and a series record into this machine's briefings directory. It is not a warning, not an all-clear and not
          advice, and the workspace schedules, delivers and pushes nothing.
        </p>
        {briefing.isPending ? <Reading what="the briefing series" /> : null}
        {briefing.isError ? <Failure error={briefing.error} what="briefing series" onRetry={() => { void briefing.refetch(); }} /> : null}
        {briefing.data ? (
          <>
            <p className="module-envelope evidence" data-testid="briefing-status">
              {orNot(briefing.data.schema_version)} · present: {briefing.data.present ? 'yes' : 'no'} · series directory:{' '}
              {orNot(briefing.data.directory, 'directory not recorded')}
            </p>
            {briefing.data.note ? <p className="module-note">This read's own note: {briefing.data.note}</p> : null}
            {briefing.data.present ? (
              <>
                <Facts
                  testId="briefing-run"
                  rows={[
                    ['Run instant', briefing.data.run?.generated_at_utc ? istStamp(briefing.data.run.generated_at_utc) : NOT_RECORDED],
                    ['Briefing identity', briefing.data.run?.briefing_id ? 'sha256 ' + briefing.data.run.briefing_id.slice(0, 16) : NOT_RECORDED],
                    ['Places read', placesInWords(briefing.data.run?.place_count)],
                    ['Official day', briefing.data.run?.day_number === null || briefing.data.run?.day_number === undefined
                      ? NOT_RECORDED : 'day ' + briefing.data.run.day_number + ' of the published product'],
                    ['Forecast days retrieved', briefing.data.run?.forecast_days === null || briefing.data.run?.forecast_days === undefined
                      ? NOT_RECORDED : String(briefing.data.run.forecast_days)],
                    ['Sources named', briefing.data.run?.sources?.length ? briefing.data.run.sources.join(', ') : 'none named in this record'],
                    ['Change since the previous run', orNot(briefing.data.run?.change, 'not recorded')],
                    ['Interval', typeof briefing.data.run?.interval_seconds === 'number'
                      ? briefing.data.run.interval_seconds + ' s between runs in that invocation' : 'a single run'],
                    ['Latency', secondsInWords(briefing.data.run?.latency_seconds)],
                    ['Written to', [briefing.data.run?.record_path, briefing.data.run?.markdown_path].filter(Boolean).join(' · ') || NOT_RECORDED],
                  ]}
                />
                <h3>Runs in this series</h3>
                <DataTable
                  testId="briefing-series"
                  caption="Every run this series index recorded, as the read returned it."
                  columns={['Run', 'Generated', 'Places', 'Latency', 'Change']}
                  rows={(briefing.data.series || []).map(row => [
                    row.run === null || row.run === undefined ? NOT_RECORDED : 'run ' + row.run,
                    row.generated_at_utc ? istStamp(row.generated_at_utc) : NOT_RECORDED,
                    placesInWords(row.place_count),
                    secondsInWords(row.latency_seconds),
                    orNot(row.change, 'not recorded'),
                  ])}
                />
                <h3>The briefing as written</h3>
                {typeof briefing.data.markdown === 'string' && briefing.data.markdown.trim() ? (
                  <pre data-testid="briefing-markdown">{briefing.data.markdown}</pre>
                ) : (
                  <p className="module-note">This read returned no Markdown for the briefing.</p>
                )}
                <h3>What this briefing says is not established</h3>
                {briefing.data.briefing?.not_established?.length ? (
                  <ul>{briefing.data.briefing.not_established.map((line, index) => <li key={index}>{line}</li>)}</ul>
                ) : (
                  <p className="module-note">This record carried no not-established line.</p>
                )}
              </>
            ) : (
              <p className="module-note" role="status" data-testid="briefing-absent">
                This machine holds no briefing yet. Nothing has been scheduled or delivered.{' '}
                {orNot(briefing.data.detail, 'This read returned no detail line for the missing briefing.')}
              </p>
            )}
          </>
        ) : null}
      </section>
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
