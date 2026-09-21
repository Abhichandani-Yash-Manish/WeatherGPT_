/* Warnings: the national district warning product as it was returned, one row per district-day.
   The colour is drawn only where the payload stated one, and the product's own wording stays beside
   it. A quiet day is a quiet day in this product: never an all-clear. A chosen district-day opens its
   own detail read from the rows this surface already holds. The CAP relay is the other source in this
   area and is kept in its own block: CAP reference resolution alone never authorises dissemination.
   A brief for one point is composed only when the reader asks, and says which point it was resolved
   for. */
import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot, shortHash } from '../lib/format';
import { istStamp, istWindow } from '../lib/time';
import { viewById } from '../shell/views';
import { VizFigure } from '../charts/VizFigure';
import { warningMatrixSpec } from '../charts/vizSpecs';
import {
  ColourTag, DataTable, Failure, Facts, HAZARD_COLOURS, Limits, NO_ROW, NOT_RECORDED, PlacePicker, Reading,
  SurfaceShell, type PlaceChoice,
} from './Evidence';

/* A tally slot is a number the read returned, or nothing. It is never defaulted to zero here: a colour the
   product did not print for any day is absent from the tally, and the reading says what was published
   rather than printing four zeroes as if the day had been measured quiet in each of them. */
function numeric(value: unknown): number {
  const number = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(number) ? number : 0;
}

type WarningDay = {
  day?: number;
  day_label?: string | null;
  label?: string | null;
  date?: string | null;
  date_local?: string | null;
  date_utc?: string | null;
  starts_utc?: string | null;
  ends_utc?: string | null;
  colour?: string | null;
  colour_code?: number | null;
  hazards?: string[];
  hazard_codes?: number[];
  wording?: string | null;
  source_text?: string | null;
  quiet?: boolean;
  is_past?: boolean | null;
};

type DistrictRow = {
  key?: string;
  district?: string | null;
  state?: string | null;
  bulletin_date?: string | null;
  issued_at_utc?: string | null;
  /* Measured from the printed bulletin date to the read instant. A district whose edition is older
     than the read is stated as older: on 17 September 2026 one district in the national read still
     carried bulletin days dated November 2023. */
  bulletin_age_days?: number | null;
  /* Whether this district's edition lags the newest edition this read returned, and by how many
     days. An edition two days old can be the current product for today, so the surface states the
     relative fact rather than calling a current edition stale. */
  bulletin_behind_the_newest_read_days?: number | null;
  bulletin_is_older_than_this_read?: boolean | null;
  updated_at?: string | null;
  days?: WarningDay[];
};

type WarningsData = {
  districts?: DistrictRow[];
  tally?: Record<string, number>;
  skipped?: { obj_id?: string | number | null; reason?: string }[];
  newest_bulletin_date_in_this_read?: string | null;
  districts_behind_the_newest_edition?: number;
  oldest_bulletin_age_days?: number | null;
  oldest_edition_examples?: { district?: string | null; state?: string | null; bulletin_date?: string | null; bulletin_age_days?: number | null; days_behind_the_newest_edition?: number | null }[];
};

type CapRecord = {
  identifier?: string | null;
  sender?: string | null;
  sent?: string | null;
  status?: string | null;
  msg_type?: string | null;
  event?: string | null;
  severity?: string | null;
  certainty?: string | null;
  urgency?: string | null;
  onset?: string | null;
  expires?: string | null;
};

type CapData = {
  messages?: number | null;
  eligible_by_lifecycle?: number | null;
  latest_sent?: string | null;
  delivery?: string | null;
  records?: CapRecord[];
};

type BriefData = {
  status?: string;
  why?: string;
  place?: { district?: string | null; state?: string | null };
  day?: {
    day?: number | null;
    label?: string | null;
    date_local?: string | null;
    starts_utc?: string | null;
    ends_utc?: string | null;
  };
  status_line?: string | null;
  day_status?: {
    colour?: string | null;
    colour_code?: number | null;
    hazards?: string[];
    quiet?: boolean;
    official_wording?: string | null;
    wording_note?: string | null;
  };
  issuer?: {
    source_id?: string;
    product?: string;
    layer?: string;
    issued_at_utc?: string | null;
    retrieved_at_utc?: string | null;
    source_locator?: string | null;
    day_boundary_basis?: string | null;
  };
  relay?: {
    source_id?: string;
    messages?: number | null;
    eligible_by_lifecycle?: number | null;
    latest_sent?: string | null;
    note?: string;
  };
  what_would_change_this?: string[];
  how_to_check_again?: string[];
  not_established?: string[];
  brief_id?: string;
};

export const intents: string[] = (viewById('warnings')?.intents ?? []).concat([
  'Which district-days does the national product publish, and in what colour?',
  'Write the alert brief for the point I name.',
]);

const DAY_ROWS_SHOWN = 150;
/* The matrix draws this many districts at once; the table below carries every row. */
const MATRIX_ROWS_SHOWN = 60;
const DISTRICT_ROWS_SHOWN = 60;
const PUBLISHED_DAYS = ['1', '2', '3', '4', '5'];
/* The product's own day contract, stated in words rather than re-derived here. */
const DAY_BOUNDARY_BASIS =
  'Day 1 is the bulletin date and each following day is the next IST calendar day. The published date and the ' +
  'validity window of each day come from the bulletin date by that contract; they are not re-derived in this browser.';
const CAP_SEPARATION = 'The CAP relay is reported on its own and is never merged with the district guidance above.';
const CAP_RULE = 'CAP reference resolution alone never authorises dissemination.';
const CAP_READ_NOTE = 'This assessment is read only when asked; nothing is polled in the background.';

function dayName(day: WarningDay): string {
  return orNot(day.day_label || day.label, day.day ? 'Day ' + day.day : NO_ROW);
}

function dayDate(day: WarningDay): string {
  return orNot(day.date || day.date_local || day.date_utc);
}

function dayWording(day: WarningDay): string {
  const wording = day.wording || day.source_text;
  if (wording) return wording;
  const codes = day.hazards?.length ? day.hazards.join(', ') : day.hazard_codes?.length ? 'codes ' + day.hazard_codes.join(', ') : '';
  return codes || 'no hazard wording published for this district-day';
}

function dayWindow(day: WarningDay): string {
  return day.starts_utc && day.ends_utc ? istWindow(day.starts_utc, day.ends_utc) : NOT_RECORDED;
}

/* The state the read stated for a district-day, in its own column: a day whose published window has
   closed is not a quiet day, an explicitly quiet day is not an unknown one, and a day whose quiet flag
   the read did not return is never passed off as quiet. */
function dayState(day: WarningDay): string {
  if (day.is_past === true) return 'past as returned: the window this product published for this day has closed';
  if (day.quiet === true) return 'quiet as returned: no warning in this product for this district-day';
  if (day.quiet === false) return 'not quiet as returned: this district-day is not a quiet day in this product';
  return 'the quiet flag was not returned: this district-day is not stated as quiet';
}

function briefReason(data: BriefData): string {
  return orNot(data.why || data.status_line, 'no brief was composed and the payload stated no reason');
}

/* The district a deep link names, or an empty filter when the link names none. */
function districtFromHash(): string {
  const hash = typeof window === 'undefined' ? '' : window.location.hash;
  const start = hash.indexOf('?');
  if (start === -1) return '';
  return new URLSearchParams(hash.slice(start + 1)).get('district') || '';
}

export function Surface(): JSX.Element {
  /* A deep link from the Today inspector carries the district it was inspecting: #/warnings?district=Patna.
     The filter is initialised from it, and the same link opening a second time updates it rather than leaving
     the reader on the previous district. Nothing else about the surface changes. */
  const [needle, setNeedle] = useState(() => districtFromHash());
  useEffect(() => {
    const onHash = () => setNeedle(districtFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  const [chosen, setChosen] = useState<{ row: DistrictRow; day: WarningDay } | null>(null);
  const [place, setPlace] = useState<PlaceChoice | null>(null);
  const [day, setDay] = useState('');
  const [asked, setAsked] = useState<{ place: PlaceChoice; day: string } | null>(null);
  const [capAsked, setCapAsked] = useState(false);

  const warnings = useQuery({
    queryKey: ['warnings-national'],
    queryFn: () => getJson<Envelope<WarningsData>>('/api/warnings/national'),
    retry: false,
  });
  /* The CAP relay is the other source in this area. It is read on request rather than merged into the
     district rows, and it answers inside its own block below. */
  const cap = useQuery({
    queryKey: ['warnings-cap'],
    queryFn: () => getJson<Envelope<CapData>>('/api/warnings/cap'),
    enabled: capAsked,
    retry: false,
  });
  /* The brief is composed for one point and one published day, and only after the reader asks for it. */
  const brief = useQuery({
    queryKey: ['warnings-alert-brief', asked?.place.latitude, asked?.place.longitude, asked?.day],
    queryFn: () => getJson<Envelope<BriefData>>(withQuery('/api/warnings/alert-brief', {
      lat: asked?.place.latitude, lon: asked?.place.longitude, day: asked?.day,
    })),
    enabled: asked !== null,
    retry: false,
  });

  const data = warnings.data?.data;
  const districts = data?.districts || [];
  const source = warnings.data?.sources?.[0];
  const term = needle.trim().toLowerCase();
  const matched = term ? districts.filter(row => String(row.district || '').toLowerCase().includes(term)) : districts;
  const rows = matched.flatMap(row => (row.days || []).map(day => ({ row, day })));
  const shown = rows.slice(0, DAY_ROWS_SHOWN);

  /* The scan view of the same rows: the district x day matrix the served chart engine draws, filtered by the same
     search, with a cell opening that district-day below. */
  const matrix = useMemo(
    () => warningMatrixSpec(matched as never, MATRIX_ROWS_SHOWN, row => {
      const full = (row as DistrictRow).days || [];
      if (full.length) setChosen({ row: row as DistrictRow, day: full[0] });
    }),
    [matched],
  );
  const skipped = data?.skipped || [];
  const behindNewest = data?.districts_behind_the_newest_edition || 0;

  const capData = cap.data?.data;
  const briefData = brief.data?.data;
  const briefPlace = briefData?.place || {};
  const briefDay = briefData?.day || {};
  const dayStatus = briefData?.day_status || {};
  const issuer = briefData?.issuer || {};
  const relay = briefData?.relay || {};

  /* The first-screen reading: what the national product actually published in this read, in the product's
     own four colour words, so a reader knows before they filter whether today is a quiet national day or a
     red one. Measured 21 September 2026 on the captured first screen (light-warnings@1440): the surface
     opened on a filter box and a sentence about how many rows were being listed. A colour here is a count
     of rows that printed that colour — never a verdict, never a severity this surface chose, and never an
     alert; a colour the product did not print for any day is not shown as a zero, it is absent from the
     sentence. */
  const tally = warnings.data?.data?.tally || {};
  const printed = HAZARD_COLOURS.filter(colour => numeric(tally[colour]) > 0);
  const nationalReading = warnings.isSuccess ? {
    statement: districts.length
      ? 'This read returned ' + count(districts.length, 'district') + ' and ' + count(rows.length, 'district-day row') + '. '
        + (printed.length
          ? 'The colours the product itself printed are ' + printed.map(colour => colour + ' on ' + count(numeric(tally[colour]), 'day')).join(', ') + '.'
          : 'The product printed no hazard colour for any district-day in this read.')
      : 'This read returned no district row at all: that is an empty read, not a quiet day.',
    source: 'view ' + orNot(warnings.data?.view) + ' · status ' + orNot(warnings.data?.status)
      + ' · read ' + (warnings.data?.generated_at_utc ? istStamp(warnings.data.generated_at_utc) : NOT_RECORDED)
      + ' · source ' + orNot(source?.source_id),
  } : null;

  return (
    <SurfaceShell
      title="Warnings"
      lead="The national district warning product as this machine read it: one row per district-day, the colour the product printed for that day, and the hazard wording it published."
      what="the national district warning product"
      envelope={warnings.data}
      busy={warnings.isPending}
      error={warnings.error}
      onRetry={() => warnings.refetch()}
      intents={intents}
      reading={nationalReading ? { testId: 'warnings-headline', statement: nationalReading.statement, source: nationalReading.source } : undefined}
    >
      <section className="module-section">
        <h2>Filter</h2>
        <div className="module-controls">
          <label className="module-field" htmlFor="warnings-filter">
            <span>District name contains</span>
            <input
              id="warnings-filter"
              type="search"
              value={needle}
              placeholder="e.g. Patna"
              onChange={event => setNeedle(event.target.value)}
            />
          </label>
        </div>
        <p className="module-note">
          This filter runs in this browser over the {count(districts.length, 'district row')} this read returned. The
          product is not asked again, so a district this read did not return cannot appear here.
        </p>
        {/* A filter that is not set cannot be described as if it were: the earlier wording said the rows
            shown were "matching this filter" whether or not one had been entered. */}
        <p className="module-note" role="status" data-testid="warnings-count">
          {needle.trim()
            ? 'Showing ' + shown.length + ' of ' + count(rows.length, 'district-day row') + ' matching this filter'
              + (rows.length > shown.length ? ', listing the first ' + DAY_ROWS_SHOWN + '.' : '.')
            : rows.length > shown.length
              ? 'Showing the first ' + DAY_ROWS_SHOWN + ' of ' + count(rows.length, 'district-day row') + ' this read returned.'
              : 'Showing all ' + count(rows.length, 'district-day row') + ' this read returned.'}
        </p>
      </section>

      {matrix ? (
        <section className="module-section" data-testid="warnings-matrix-section">
          <h2>District × day matrix</h2>
          <p className="module-note">
            The published product as a grid, drawn by the chart engine this build serves. A cell shows the colour
            the source printed for that district-day; focus one to read its hazard wording, and choose one to open
            that district below. A colour is what the product printed, never a verdict of this surface.
          </p>
          <VizFigure kind="warningMatrix" spec={matrix} />
        </section>
      ) : null}

      <section className="module-section">
        <h2>District-days</h2>
        <p className="module-note">
          A colour chip is drawn only where the product stated a colour for that district-day; an unstated colour is
          set as a word, never as a colour of this surface's choosing. The state column keeps the distinctions the read
          returned: a past day, a quiet day, a day the product published a hazard for, and a day whose quiet flag was
          not returned are four different states.
        </p>
        <p className="module-note">
          Choosing a district-day opens its own detail below: the hazard wording the product published, the validity
          window of each day, and the bulletin and source it came from.
        </p>
        {/* Currency is measured from each printed bulletin date, and stated relative to the newest
            edition this read returned: an edition two days old can still be the current official
            product for today, so no district is called stale for being recent (measured 17 September
            2026: 755 of 756 districts carried the 15 September edition and one carried November 2023). */}
        <p className="module-note" data-testid="warnings-bulletin-age">
          {behindNewest
            ? count(behindNewest, 'district') + ' in this read carry an edition older than the newest edition of this read'
              + (data?.newest_bulletin_date_in_this_read ? ' (' + data.newest_bulletin_date_in_this_read + ')' : '')
              + (data?.oldest_bulletin_age_days ? ', the oldest ' + data.oldest_bulletin_age_days + ' days before this read' : '')
              + '. An older edition is still the official product for the days it covers; it is simply behind what this read held.'
            : data?.newest_bulletin_date_in_this_read
              ? 'Every district in this read carries the newest edition this read held (' + data.newest_bulletin_date_in_this_read + ').'
              : 'The returned rows state no bulletin date, so currency is not established here.'}
        </p>
        <DataTable
          testId="warnings-table"
          caption="One row per district-day, exactly as returned."
          columns={['District', 'State', 'Day', 'Date', 'Colour as published', 'Hazard wording as published', 'Day state as returned']}
          rows={shown.map(({ row, day }) => [
            <button type="button" className="btn btn-ghost" key="district" onClick={() => setChosen({ row, day })}>
              {orNot(row.district)}
            </button>,
            orNot(row.state),
            dayName(day),
            dayDate(day),
            <ColourTag key="colour" colour={day.colour} text={day.colour || undefined} />,
            dayWording(day),
            dayState(day),
          ])}
        />
        <DataTable
          testId="warnings-bulletins"
          caption="Bulletin identity per district row this read returned."
          columns={['District', 'Bulletin date', 'Bulletin age at this read', 'Issued', 'Updated']}
          rows={matched.slice(0, DISTRICT_ROWS_SHOWN).map(row => [
            orNot(row.district),
            /* A printed date must not break across lines: measured 17 September 2026, '2026-09-11'
               wrapped as '2026-' / '09-11' inside the date column at 1440x900. */
            <span className="whitespace-nowrap" key="date">{orNot(row.bulletin_date)}</span>,
            row.bulletin_age_days === null || row.bulletin_age_days === undefined
              ? NOT_RECORDED
              : String(row.bulletin_age_days) + (row.bulletin_age_days === 1 ? ' day' : ' days')
                + (row.bulletin_is_older_than_this_read
                  ? ' \u00b7 ' + String(row.bulletin_behind_the_newest_read_days) + ' days behind the newest edition in this read'
                  : ''),
            row.issued_at_utc ? istStamp(row.issued_at_utc) : NOT_RECORDED,
            row.updated_at ? istStamp(row.updated_at) : NOT_RECORDED,
          ])}
        />
      </section>

      {chosen ? (
        <section className="module-section" data-testid="warnings-district">
          <h2>
            District detail · {orNot(chosen.row.district)}
            {chosen.row.state ? ', ' + chosen.row.state : ''}
          </h2>
          <p className="module-note">
            Opened from {dayName(chosen.day)} · {dayDate(chosen.day)}. This detail reads the rows this surface already
            holds; the product is not asked again for it.
          </p>
          <Facts
            testId="warnings-district-bulletin"
            rows={[
              ['District', orNot(chosen.row.district)],
              ['State', orNot(chosen.row.state)],
              ['Bulletin date', orNot(chosen.row.bulletin_date)],
              ['Bulletin issued', chosen.row.issued_at_utc ? istStamp(chosen.row.issued_at_utc) : NOT_RECORDED],
              ['Bulletin updated', chosen.row.updated_at ? istStamp(chosen.row.updated_at) : NOT_RECORDED],
              ['Source id', orNot(source?.source_id)],
              ['Source product', orNot(source?.product)],
              ['Source layer', orNot(source?.layer)],
              ['Day boundary basis', DAY_BOUNDARY_BASIS],
            ]}
          />
          <DataTable
            testId="warnings-district-days"
            caption="Every published day this district row returned, with its own validity window and hazard wording."
            columns={['Day', 'Date', 'Colour as published', 'Validity window as returned', 'Hazard wording as published', 'Day state as returned']}
            rows={(chosen.row.days || []).map(dayRow => [
              dayName(dayRow),
              dayDate(dayRow),
              <ColourTag key="colour" colour={dayRow.colour} text={dayRow.colour || undefined} />,
              dayWindow(dayRow),
              dayWording(dayRow),
              dayState(dayRow),
            ])}
          />
          <div className="module-controls">
            <button type="button" className="btn btn-ghost" onClick={() => setChosen(null)}>
              Close this district detail
            </button>
          </div>
        </section>
      ) : null}

      <section className="module-section">
        <h2>Write the alert brief</h2>
        <p className="module-note">
          A brief is composed for one point and one published day from the official district warning product, with the
          CAP relay reported separately. It is read only when asked, and it is not a warning anyone else receives.
        </p>
        <PlacePicker onPick={setPlace} hint="Name a place and choose a row; the brief is composed for those coordinates." />
        <div className="module-controls">
          <label className="module-field" htmlFor="warnings-brief-day">
            <span>Published day to compose</span>
            <select id="warnings-brief-day" value={day} onChange={event => setDay(event.target.value)}>
              <option value="">First published day</option>
              {PUBLISHED_DAYS.map(value => (
                <option key={value} value={value}>Day {value}</option>
              ))}
            </select>
          </label>
          <button type="button" className="btn" disabled={!place} onClick={() => place && setAsked({ place, day })}>
            Write the alert brief
          </button>
        </div>
        {!place ? (
          <p className="module-note">
            No point was named, so no brief has been asked for. A brief is composed for one point, and the workspace
            will not guess which.
          </p>
        ) : null}
        {asked ? (
          <div data-testid="warnings-brief">
            <h3>Alert brief as composed</h3>
            {brief.isPending ? <Reading what="the composed alert brief" /> : null}
            {brief.isError ? (
              <Failure error={brief.error} what="composed alert brief" onRetry={() => { void brief.refetch(); }} />
            ) : null}
            {briefData ? (
              <>
                <p className="module-note" data-testid="warnings-brief-point">
                  Composed for the point that was resolved to {orNot(briefPlace.district, 'no district of this product')}
                  {briefPlace.state ? ', ' + briefPlace.state : ''}. It is not a warning anyone else receives.
                </p>
                <p className="module-note" data-testid="warnings-brief-status">
                  {briefData.status === 'ok'
                    ? orNot(briefData.status_line, 'no status line was returned')
                    : briefReason(briefData)}
                </p>
                <Facts
                  testId="warnings-brief-facts"
                  rows={[
                    ['Status as returned', orNot(brief.data?.status)],
                    ['Point the brief names', orNot(briefPlace.district, 'no district of this product') + (briefPlace.state ? ', ' + briefPlace.state : '')],
                    ['Day', orNot(briefDay.label) + (briefDay.day ? ' · day ' + briefDay.day + ' of the published product' : '')],
                    ['Validity window', briefDay.starts_utc && briefDay.ends_utc ? istWindow(briefDay.starts_utc, briefDay.ends_utc) : NOT_RECORDED],
                    ['Colour as published', <ColourTag key="colour" colour={dayStatus.colour} text={dayStatus.colour || undefined} />],
                    ['Hazards as published', dayStatus.hazards?.length ? dayStatus.hazards.join(', ') : 'none listed'],
                    ['Official wording', orNot(dayStatus.official_wording || dayStatus.wording_note, 'no free-text wording and no note was returned')],
                    ['Issuer', orNot(issuer.source_id) + ' · ' + orNot(issuer.product)],
                    ['Issued at', issuer.issued_at_utc ? istStamp(issuer.issued_at_utc) : NOT_RECORDED],
                    ['Retrieved at', issuer.retrieved_at_utc ? istStamp(issuer.retrieved_at_utc) : NOT_RECORDED],
                    ['Source locator', orNot(issuer.source_locator)],
                    ['CAP relay, reported separately', orNot(relay.source_id) + ' · ' + (typeof relay.messages === 'number' ? relay.messages + ' message(s)' : NOT_RECORDED) + ' · ' + orNot(relay.note, 'no note returned')],
                    ['Brief identity', shortHash(briefData.brief_id) + ' (sha256 prefix of the content hash)'],
                  ]}
                />
                {(briefData.what_would_change_this || []).length ? (
                  <>
                    <h3>What would change this brief</h3>
                    <ul className="module-note">
                      {(briefData.what_would_change_this || []).map((line, index) => (
                        <li key={index}>{line}</li>
                      ))}
                    </ul>
                  </>
                ) : null}
                <Limits limitations={brief.data?.limitations} not_established={briefData.not_established} />
              </>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="module-section" data-testid="warnings-cap">
        <h2>CAP relay assessment</h2>
        <p className="module-note">{CAP_SEPARATION}</p>
        <p className="module-note">
          {CAP_RULE} This block reports a source assessment, not an alert and not a warning for a place.
        </p>
        <div className="module-controls">
          <button
            type="button"
            className="btn"
            onClick={() => { if (capAsked) { void cap.refetch(); } else { setCapAsked(true); } }}
          >
            {capAsked ? 'Read the CAP relay assessment again' : 'Read the CAP relay assessment'}
          </button>
        </div>
        {capAsked ? (
          <>
            {cap.isPending ? <Reading what="the CAP relay assessment" /> : null}
            {cap.isError ? (
              <Failure error={cap.error} what="CAP relay assessment" onRetry={() => { void cap.refetch(); }} />
            ) : null}
            {capData ? (
              <>
                <Facts
                  testId="warnings-cap-facts"
                  rows={[
                    ['Messages retrieved', orNot(capData.messages, 'count not recorded')],
                    ['Passing the time, status and reference checks', orNot(capData.eligible_by_lifecycle, 'count not recorded')],
                    ['Newest sent', capData.latest_sent ? istStamp(capData.latest_sent) : NOT_RECORDED],
                    ['Delivery as returned', orNot(capData.delivery)],
                  ]}
                />
                <p className="module-note">
                  An eligible set is not an all-clear: a reachable relay is not evidence that nothing is in force.
                </p>
                {capData.records?.length ? (
                  <DataTable
                    testId="warnings-cap-records"
                    caption="Every retrieved CAP message this read returned, as the relay stated it."
                    columns={['Sent', 'Event', 'Severity', 'Status', 'Expires']}
                    rows={capData.records.map(record => [
                      record.sent ? istStamp(record.sent) : NOT_RECORDED,
                      orNot(record.event),
                      orNot(record.severity),
                      orNot(record.status),
                      record.expires ? istStamp(record.expires) : NOT_RECORDED,
                    ])}
                  />
                ) : (
                  <p className="module-note">{NO_ROW} for the retrieved CAP messages: this read returned none.</p>
                )}
                <Limits limitations={cap.data?.limitations} not_established={cap.data?.not_established} />
              </>
            ) : null}
          </>
        ) : (
          <p className="module-note">{CAP_READ_NOTE}</p>
        )}
      </section>

      <section className="module-section">
        <h2>Features this read could not key</h2>
        <p className="module-note">
          {skipped.length
            ? count(skipped.length, 'source feature') + ' returned without a district name, so no district row could be keyed for them. They are listed rather than dropped silently.'
            : 'Every source feature this read returned carried a district name.'}
        </p>
        <DataTable
          testId="warnings-skipped"
          caption="Source features that were skipped, with the reason this read recorded."
          columns={['Source object id', 'Reason']}
          rows={skipped.map(item => [orNot(item.obj_id, 'object id not recorded'), orNot(item.reason)])}
        />
      </section>
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
