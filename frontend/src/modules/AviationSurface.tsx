/* Aviation: the airport reports this machine retrieved for the ICAO codes a reader names, read kind by
   kind. A METAR is an observation from that station and not a forecast; a TAF is a forecast and not an
   observation; neither is a flight-safety clearance, a runway state, a turbulence or icing determination
   or any operational advice. Every value here is a field this read returned, with its own unit, its own
   instant or window, its own age and the read's own freshness word beside it, and a station the read did
   not return is stated as missing rather than dropped. */
import { useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { elapsedWords, istStamp, istWindow } from '../lib/time';
import { viewById } from '../shell/views';
import { DataTable, Facts, Headline, NO_ROW, NOT_RECORDED, SurfaceShell } from './Evidence';

type RawFields = { name?: string | null; lat?: number | null; lon?: number | null; elev?: number | null; metarType?: string | null };
type Report = {
  station_id?: string; observed_at_utc?: string | null; age_seconds?: number | null; freshness?: string | null;
  raw_report?: string | null; temperature_c?: number | null; dewpoint_c?: number | null; wind_speed_kt?: number | null;
  wind_direction_native?: number | string | null; issued_at_raw?: string | null; valid_start_utc?: string | null;
  valid_end_utc?: string | null; active_by_time?: boolean; interpretation?: string | null;
  source_locator?: string | null; raw_fields?: RawFields;
};
type AviationData = { stations?: Report[]; kind?: string; missing?: string[] | null };

export const intents: string[] = (viewById('aviation')?.intents ?? []).concat([
  'What did the latest METAR for an airport report, and how old is it?',
  'Is the TAF for an airport an observation or a forecast?',
]);

const KINDS = ['metar', 'taf'];
/* The one paragraph this surface must say in its own voice, whichever kind answered. */
const REPORTS = 'A METAR is an observation from that station and not a forecast; a TAF is a forecast and not an observation. '
  + 'Neither is a flight-safety clearance, a runway state, a turbulence or icing determination or any other operational advice. '
  + 'A report older than the source\u2019s own validity is stale rather than current weather, and this surface prints the '
  + 'freshness, age and validity words the read returned beside each report instead of substituting its own.';

/* The decoded fields this record carries, with the unit this product states for them: a _c field reads in
   degrees Celsius and a _kt field in knots. A field whose unit the read does not state says so. */
const DECODED: [string, string, (report: Report) => unknown][] = [
  ['temperature_c', '\u00B0C', report => report.temperature_c],
  ['dewpoint_c', '\u00B0C', report => report.dewpoint_c],
  ['wind_speed_kt', 'kt', report => report.wind_speed_kt],
  ['wind_direction_native', 'unit not stated by this read', report => report.wind_direction_native],
];

function coordinates(report: Report): string {
  const raw = report.raw_fields || {};
  if (raw.lat === null || raw.lat === undefined || raw.lon === null || raw.lon === undefined) return NOT_RECORDED;
  return raw.lat + ', ' + raw.lon;
}

/* A stale report is drawn as stale; any other freshness word this read returned is set as the word it is,
   never restyled into current weather. */
function freshnessChip(word?: string | null): JSX.Element {
  const stated = typeof word === 'string' ? word.trim() : '';
  if (!stated) return <span className="chip is-unknown">freshness not recorded</span>;
  return <span className={stated === 'stale' ? 'chip is-stale' : 'chip is-unknown'}>{stated}</span>;
}

function ageText(report: Report): string {
  return report.age_seconds === null || report.age_seconds === undefined
    ? NOT_RECORDED
    : report.age_seconds + ' s as returned \u00B7 ' + elapsedWords(report.age_seconds);
}

/* The first-screen reading: the most recently returned station's own report, decoded into a sentence
   alongside the coded string — never instead of it, since the raw report stays verbatim in its own
   section below. A METAR reports what a station observed; a TAF states what it forecasts and when that
   forecast is valid. Neither becomes a clearance, a runway state or any other operational advice: it
   states only the fields the read itself decoded, in the read's own freshness or activity word. */
function decodeHeadline(kind: string, report: Report | undefined): { statement: string; source: string } {
  if (!report) return { statement: 'This read returned no station report to decode.', source: 'kind: ' + orNot(kind) };
  const id = orNot(report.station_id, 'station id not recorded');
  if (kind === 'taf') {
    const window = report.valid_start_utc && report.valid_end_utc ? istWindow(report.valid_start_utc, report.valid_end_utc) : NOT_RECORDED;
    const active = report.active_by_time === null || report.active_by_time === undefined ? NOT_RECORDED : String(report.active_by_time);
    return {
      statement: id + '’s TAF forecasts for ' + window + ': ' + orNot(report.interpretation, 'this read stated no interpretation for it') + '.',
      source: 'issued ' + orNot(report.issued_at_raw) + ' · active at retrieval by the read’s own test: ' + active,
    };
  }
  const parts: string[] = [];
  if (report.temperature_c !== null && report.temperature_c !== undefined) parts.push('temperature ' + report.temperature_c + '°C');
  if (report.dewpoint_c !== null && report.dewpoint_c !== undefined) parts.push('dewpoint ' + report.dewpoint_c + '°C');
  if (report.wind_speed_kt !== null && report.wind_speed_kt !== undefined) {
    const direction = report.wind_direction_native !== null && report.wind_direction_native !== undefined ? ' from ' + report.wind_direction_native : '';
    parts.push('wind ' + report.wind_speed_kt + ' kt' + direction);
  }
  const freshWord = typeof report.freshness === 'string' && report.freshness.trim() ? report.freshness.trim() : 'freshness not recorded';
  const instant = report.observed_at_utc ? istStamp(report.observed_at_utc) : NOT_RECORDED;
  return {
    statement: id + '’s most recent METAR (' + instant + ') reports ' + (parts.length ? parts.join(', ') : 'no decoded field') + '. This read’s own '
      + 'freshness word for it: ' + freshWord + '.',
    source: 'age ' + ageText(report) + ' · ' + (report.source_locator ? 'locator ' + report.source_locator : 'locator not recorded'),
  };
}

function StationReport({ report, kind, index }: { report: Report; kind: string; index: number }): JSX.Element {
  const raw = report.raw_fields || {};
  const instant = report.observed_at_utc ? istStamp(report.observed_at_utc) : NOT_RECORDED;
  /* The kind's own time basis: an observation is one instant, a forecast is a window it is valid for. */
  const kindRows: [string, ReactNode][] = kind === 'taf' ? [
    ['Issued as the source states it (issued_at_raw)', orNot(report.issued_at_raw)],
    ['Validity window as returned (IST)', report.valid_start_utc && report.valid_end_utc
      ? istWindow(report.valid_start_utc, report.valid_end_utc) : NOT_RECORDED],
    ['Active at retrieval by the read\u2019s own test (active_by_time)', report.active_by_time === null || report.active_by_time === undefined
      ? NOT_RECORDED : String(report.active_by_time)],
    ['Interpretation as this read states it', orNot(report.interpretation)],
  ] : [
    ['Observed at as returned (IST)', instant],
    ['Age at retrieval', ageText(report)],
    ['Freshness as this read states it', freshnessChip(report.freshness)],
  ];

  return (
    <article className="module-section">
      <h3>{orNot(report.station_id, 'station id not recorded')} &middot; {orNot(raw.name, 'station name not recorded')}</h3>
      <Facts testId={'aviation-station-' + index} rows={[
        ['Station identity as returned (ICAO)', orNot(report.station_id)],
        ['Report kind as this read states it', orNot(kind)],
        ['Source record type as returned (metarType)', orNot(raw.metarType, 'no source record type returned')],
        ['Coordinates as returned', coordinates(report)],
        ['Elevation as returned', orNot(raw.elev)],
        ['Source locator as returned', orNot(report.source_locator)],
        ...kindRows,
      ]} />
      <p className="module-note">
        Raw report as this read returned it (raw_report): <span className="evidence">{orNot(report.raw_report, 'raw report not returned')}</span>
      </p>
      {kind === 'taf' ? (
        <p className="module-note">
          This read returns no decoded values for a TAF beyond the window above: the source&rsquo;s change groups stay in the
          raw report, and a forecast is not an observation from the station.
        </p>
      ) : (
        <DataTable
          testId={'aviation-decoded-' + index}
          caption="Every decoded field this record returned, with the unit this product states for it and the report's own instant as the time basis."
          columns={['Decoded field as returned', 'Value as returned', 'Unit as this product states it', 'Time basis as returned']}
          rows={DECODED.map(([field, unit, read]) => [field, orNot(read(report)), unit, instant])}
        />
      )}
    </article>
  );
}

export function Surface(): JSX.Element {
  const [codes, setCodes] = useState('');
  const [kind, setKind] = useState('metar');
  const [asked, setAsked] = useState<{ codes: string; kind: string } | null>(null);
  const read = useQuery({
    queryKey: ['aviation', asked?.codes, asked?.kind],
    queryFn: () => getJson<Envelope<AviationData>>(withQuery('/api/aviation', { icao: asked?.codes, kind: asked?.kind })),
    enabled: asked !== null, retry: false,
  });

  const data = read.data?.data;
  const stations = data?.stations || [];
  const kindWord = orNot(data?.kind);
  const requested = (read.data?.coverage?.requested_stations as string[] | undefined) || [];
  const missing = Array.isArray(data?.missing) ? data?.missing : null;
  const stale = stations.filter(report => report.freshness === 'stale').length;

  return (
    <SurfaceShell
      title="Aviation"
      lead="Airport reports for the ICAO codes you name, read kind by kind: the station, the raw report as the source transmitted it, the decoded values with their own time basis, and the age of the report."
      what="the airport reports" envelope={asked ? read.data : undefined} busy={asked !== null && read.isPending}
      error={asked ? read.error : undefined} onRetry={() => read.refetch()} intents={intents}
    >
      <section className="module-section">
        <h2>What these reports are</h2>
        <p className="module-note" data-testid="aviation-standing">{REPORTS}</p>
        <div className="module-controls">
          <label className="module-field" htmlFor="aviation-icao">
            <span>ICAO codes to read, comma separated</span>
            <input id="aviation-icao" type="search" value={codes} placeholder="e.g. VOBL or VOBL,VAAH" onChange={event => setCodes(event.target.value)} />
          </label>
          <label className="module-field" htmlFor="aviation-kind">
            <span>Report kind to read</span>
            <select id="aviation-kind" value={kind} onChange={event => setKind(event.target.value)}>
              {KINDS.map(name => <option key={name} value={name}>{name}</option>)}
            </select>
          </label>
          <button type="button" className="btn" disabled={!codes.trim()} onClick={() => setAsked({ codes: codes.trim(), kind })}>
            Read these reports
          </button>
        </div>
        <p className="module-note">
          The route answers these two kinds and refuses a code that is not four letters; its own refusal sentence is shown
          here when it refuses, and a kind this route does not answer is never offered.
        </p>
      </section>

      {asked && !read.isPending && !read.isError ? (
        <section className="module-section">
          <h2>The reports this read returned</h2>
          <Facts testId="aviation-read" rows={[
            ['Report kind as this read states it', kindWord],
            ['Station reports returned', count(stations.length, 'station report')],
            ['Requested stations as this read states them', requested.length ? requested.join(', ') : NOT_RECORDED],
            ['Requested stations with no report', missing === null ? NOT_RECORDED
              : missing.length ? missing.join(', ') : 'every station this read was asked for answered'],
          ]} />
          {(() => {
            const headline = decodeHeadline(kindWord, stations[0]);
            return <Headline testId="aviation-headline" statement={headline.statement} source={headline.source} />;
          })()}
          <p className="module-note" role="status" aria-live="polite" data-testid="aviation-count">
            {count(stations.length, 'station report')} returned for {kindWord}; {stale
              ? count(stale, 'row') + ' carry the read\u2019s own stale word and must not be read as current weather'
              : 'no returned row carries a stale word'}.
          </p>
          {stations.length ? stations.map((report, index) => (
            <StationReport key={orNot(report.station_id, 'row') + '-' + index} report={report} kind={kindWord} index={index} />
          )) : (
            <p className="module-note">
              {NO_ROW}: this read returned no station report for the codes it was asked
              {missing && missing.length ? ' (no report came back for ' + missing.join(', ') + ')' : ''}. A missing report is
              not calm weather at that station.
            </p>
          )}
        </section>
      ) : null}
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
