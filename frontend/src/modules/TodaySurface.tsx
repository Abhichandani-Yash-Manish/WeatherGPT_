/* Today: the command dashboard. One national read as the dominant picture (the district warning product),
   four counted KPIs, two charts, the districts that published a hazard covering today, and the composition
   of the read — beside the right-now reading for a place the reader names.

   The design is docs/97. What it deliberately does not do, because the product refuses it everywhere else:
   no risk score, no confidence percentage, no severity ramp of this surface's own, and no value drawn for a
   row the read did not return. Hazard colours appear only where the product published one, and the map is a
   join of two reads (geometry and warning rows) whose join key and retrieval times the card states. */
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope, NowReading } from '../api/types';
import { count, orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import { VizFigure } from '../charts/VizFigure';
import { nowBandSpec } from '../charts/vizSpecs';
import {
  EvidenceFooter, ColourTag, DataTable, Facts, Failure, NO_ROW, NOT_RECORDED, PlacePicker, Reading,
  SurfaceShell, type PlaceChoice,
} from './Evidence';
import {
  BubbleMatrix, Card, ColourDonut, ColourStrip, EditionBars, EditionHistogram, Kpi, MiniBars, RAMP,
  ReportingRing, UNSET, notRecordedWhen, rampTotal, readingWhen, type MatrixCell, type Tally,
} from './DashboardCharts';
import { describeNational, useOverview } from '../home/overview';
import { DistrictRiskMap, type MapWarningRow } from './DistrictRiskMap';
import { DistrictInspector } from './DistrictInspector';
import type { Collection } from './mapFigure';

export const intents: string[] = (viewById('overview')?.intents ?? []).concat([
  'What is it like right now near a place I name?',
  'Which districts published a warning covering today, and in what colour?',
]);

const TALLY_KEYS = RAMP.concat(UNSET);
const SEVERITY: Record<string, number> = { red: 0, orange: 1, yellow: 2, green: 3, unset: 4 };
const LIST_SHOWN = 12;

type WarningDay = {
  day?: number; label?: string | null; date_utc?: string | null; date_local?: string | null;
  colour?: string | null; hazards?: string[]; hazard_codes?: number[]; source_text?: string | null;
  quiet?: boolean | null; is_today?: boolean | null; is_past?: boolean | null;
};

type WarningRow = MapWarningRow & { days?: WarningDay[] };

type WarningsData = {
  districts?: WarningRow[];
  tally?: Tally;
  skipped?: { obj_id?: string | number | null; reason?: string }[];
  newest_bulletin_date_in_this_read?: string | null;
  districts_behind_the_newest_edition?: number | null;
  oldest_bulletin_age_days?: number | null;
  oldest_edition_examples?: { district?: string | null; state?: string | null; bulletin_date?: string | null; bulletin_age_days?: number | null }[];
};

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

/* The day a row published for today, or the day the reader asked the map to inspect instead. */
function dayFor(row: WarningRow, dayIndex: number | null): WarningDay | null {
  const days = row.days || [];
  if (dayIndex === null) return days.find(day => day.is_today === true) || null;
  return days.find(day => day.day === dayIndex) || null;
}

function statedColour(day: WarningDay | null): string | null {
  const stated = day && typeof day.colour === 'string' ? day.colour.trim().toLowerCase() : '';
  return RAMP.includes(stated) ? stated : null;
}

function wordingOf(day: WarningDay | null): string {
  if (!day) return 'no published day in this read';
  if (day.source_text) return day.source_text;
  if (day.hazards && day.hazards.length) return day.hazards.join(', ');
  if (day.hazard_codes && day.hazard_codes.length) return 'hazard codes ' + day.hazard_codes.join(', ');
  return 'no hazard wording published';
}

export function Surface(): JSX.Element {
  const [place, setPlace] = useState<PlaceChoice | null>(null);
  const [needle, setNeedle] = useState('');
  const [statePick, setStatePick] = useState('');
  const [colourPick, setColourPick] = useState('');
  const [dayPick, setDayPick] = useState('today');
  const [colourOnly, setColourOnly] = useState(true);
  const [dimQuiet, setDimQuiet] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  /* One definition of the national read, in home/overview.ts, so this surface and the welcome cannot describe
     the same payload differently — and so the rules about what a count may say live in one place. */
  const overview = useOverview();
  const picture = describeNational(overview);
  const warnings = useQuery({
    /* The same read the Warnings surface asks for, under the same key: if both surfaces are ever mounted
       together they share one request and one cache entry instead of fetching the same URL twice. */
    queryKey: ['warnings-national'],
    queryFn: () => getJson<Envelope<WarningsData>>('/api/warnings/national'),
    enabled: Boolean(overview.data),
    retry: false,
  });
  /* The two dashboard reads wait for the overview read. The page is the overview first: if that read
     failed the surface states the failure and there is nothing to join to, so asking the store for 756
     warning rows and 1.5 MB of geometry would be work nobody can use. */
  const geometry = useQuery({
    queryKey: ['today-geometry'],
    queryFn: () => getJson<Collection>('/api/map/static/districts'),
    enabled: Boolean(overview.data),
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
  const rows = warnings.data?.data?.districts || [];
  const tally = (warnings.data?.data?.tally || national?.tally || {}) as Tally;
  const dayIndex = dayPick === 'today' ? null : Number(dayPick);

  const states = useMemo(() => {
    const seen = new Set<string>();
    rows.forEach(row => { if (row.state) seen.add(row.state); });
    return Array.from(seen).sort();
  }, [rows]);

  const dayAxis = useMemo(() => {
    const found: { day: number; label: string | null }[] = [];
    for (let day = 1; day <= 5; day += 1) {
      const row = rows.find(candidate => (candidate.days || []).some(entry => entry.day === day));
      const entry = row ? (row.days || []).find(candidate => candidate.day === day) || null : null;
      found.push({ day, label: entry ? (entry.label || entry.date_local || null) : null });
    }
    return found;
  }, [rows]);

  const matrix = useMemo(() => {
    const counts = new Map<string, number>();
    rows.forEach(row => {
      (row.days || []).forEach(day => {
        const colour = statedColour(day) || (day.quiet ? UNSET : null);
        if (!colour || typeof day.day !== 'number') return;
        const key = day.day + '|' + colour;
        counts.set(key, (counts.get(key) || 0) + 1);
      });
    });
    const cells: MatrixCell[] = [];
    counts.forEach((value, key) => {
      const parts = key.split('|');
      cells.push({ day: Number(parts[0]), colour: parts[1], count: value });
    });
    return cells;
  }, [rows]);

  const editions = useMemo(() => {
    const counts = new Map<string, number>();
    rows.forEach(row => { if (row.bulletin_date) counts.set(row.bulletin_date, (counts.get(row.bulletin_date) || 0) + 1); });
    return Array.from(counts.entries()).map(([date, value]) => ({ date, rows: value })).sort((a, b) => a.date.localeCompare(b.date));
  }, [rows]);

  const term = needle.trim().toLowerCase();
  const activeFilter = Boolean(term || statePick || colourPick || dayPick !== 'today');

  const matched = useMemo(() => rows.filter(row => {
    if (term && !String(row.district || '').toLowerCase().includes(term)) return false;
    if (statePick && row.state !== statePick) return false;
    if (colourPick) {
      const colour = statedColour(dayFor(row, dayIndex));
      if (colourPick === 'none' ? Boolean(colour) : colour !== colourPick) return false;
    }
    return true;
  }), [rows, term, statePick, colourPick, dayIndex]);

  const matchKeys = useMemo(
    () => (activeFilter ? new Set(matched.map(row => row.key).filter(Boolean) as string[]) : null),
    [activeFilter, matched]);

  /* The table behind the figure is built from the geometry the figure draws, joined to the warning rows:
     a district with no matching row belongs in the table as 'not in this read', because that is exactly
     what the figure shows for it. Building the table from the warning rows alone would hide the outlines. */
  const mapRows = useMemo(() => {
    const byKey = new Map<string, WarningRow>();
    rows.forEach(row => { if (row.key) byKey.set(row.key, row); });
    return (geometry.data?.features || []).map(feature => {
      const properties = (feature?.properties || {}) as Record<string, unknown>;
      const key = typeof properties.k === 'string' ? properties.k : '';
      const name = typeof properties.n === 'string' ? properties.n : key;
      const state = typeof properties.s === 'string' ? properties.s : null;
      const row = byKey.get(key) || null;
      return { key, name, state, row, day: row ? dayFor(row, dayIndex) : null };
    }).filter(entry => !matchKeys || matchKeys.has(entry.key));
  }, [rows, geometry.data, matchKeys, dayIndex]);

  const warnedToday = useMemo(() => rows
    .map(row => ({ row, day: dayFor(row, null) }))
    .filter(entry => Boolean(entry.day && !entry.day.quiet))
    .sort((a, b) => {
      const left = SEVERITY[(a.day && a.day.colour ? a.day.colour : '') || 'unset'];
      const right = SEVERITY[(b.day && b.day.colour ? b.day.colour : '') || 'unset'];
      const bySeverity = (left === undefined ? 9 : left) - (right === undefined ? 9 : right);
      if (bySeverity !== 0) return bySeverity;
      return String(a.row.district || '').localeCompare(String(b.row.district || ''));
    }), [rows]);

  const warnedMeta = warnedToday.length
    ? count(warnedToday.length, 'district') + ' in this read published a hazard for the district-day covering today, sorted by the colour the product printed.'
    : 'No district in this read published a hazard covering today. That is the product state, not an all-clear.';

  const dayDistrictDays = rampTotal(tally) + (tally[UNSET] || 0);
  /* Three facts, from whichever of the two reads stated them first. The overview read carries the same
     national fields and answers in milliseconds, while the row read is 1.65 MB: taking the row read alone
     made this card say 'not recorded' for a value the page already had. Nullish tests, not truthiness, so a
     count of 0 districts behind the newest edition stays 0. */
  const behind = warnings.data?.data?.districts_behind_the_newest_edition ?? national?.districts_behind_the_newest_edition ?? null;
  const newestEdition = warnings.data?.data?.newest_bulletin_date_in_this_read ?? national?.newest_bulletin_date_in_this_read ?? null;
  const oldestAge = warnings.data?.data?.oldest_bulletin_age_days ?? national?.oldest_bulletin_age_days ?? null;
  /* The profile of printed dates is the overview's own field; the row read's own dates are the fallback. */
  const editionDates = (national?.bulletin_dates as Record<string, number> | undefined)
    || (editions.length ? Object.fromEntries(editions.map(entry => [entry.date, entry.rows])) : {});
  const editionSource = national?.bulletin_dates ? 'the overview read' : editions.length ? 'the district rows this read returned' : null;
  /* 'Still reading' means the row read is actually in flight: a query the shell disabled (because the
     overview read failed) is pending with an idle fetch, and claiming it is being read would be untrue. */
  const stillReading = warnings.isPending && warnings.fetchStatus !== 'idle';
  const reading = now.data?.data;
  /* The three lanes the vanilla Today drew on one axis, from this same read: an observation is an
     instant, the published day is a district window, and the model hours are model output. */
  const band = useMemo(
    () => (reading
      ? nowBandSpec(reading as never, place?.label || null,
          'Three products on one axis, kept apart: an observation is an instant, the published day is a district ' +
          'window, and the model hours are model output.')
      : null),
    [reading, place],
  );
  const hours = reading?.next_hours;
  const inForce = reading?.in_force;
  const unit = hours?.unit || {};

  const geometryBusy = geometry.isPending;
  const geometryError = geometry.error;

  return (
    <SurfaceShell
      title="Today"
      lead="The national district warning picture as this machine read it: one command view of the districts, the colours the product itself printed and the edition each row came from, beside a right-now reading for one place."
      what="the national overview"
      envelope={overview.data}
      busy={overview.isPending}
      error={overview.error}
      onRetry={() => overview.refetch()}
    >
      <section className="dash-bar" data-testid="today-filters">
        <div className="dash-bar-fields">
          <label className="module-field" htmlFor="today-search">
            <span>Search district</span>
            <input id="today-search" type="search" value={needle} placeholder="e.g. Patna" onChange={event => setNeedle(event.target.value)} />
          </label>
          <label className="module-field" htmlFor="today-state">
            <span>State</span>
            <select id="today-state" value={statePick} onChange={event => setStatePick(event.target.value)}>
              <option value="">Every state in this read</option>
              {states.map(state => <option key={state} value={state}>{state}</option>)}
            </select>
          </label>
          <label className="module-field" htmlFor="today-colour">
            <span>Published colour</span>
            <select id="today-colour" value={colourPick} onChange={event => setColourPick(event.target.value)}>
              <option value="">Every published colour</option>
              {RAMP.map(colour => <option key={colour} value={colour}>{colour}</option>)}
              <option value="none">no colour stated</option>
            </select>
          </label>
          <label className="module-field" htmlFor="today-day">
            <span>Day to inspect</span>
            <select id="today-day" value={dayPick} onChange={event => setDayPick(event.target.value)}>
              <option value="today">the day covering today</option>
              {dayAxis.map(entry => (
                <option key={entry.day} value={String(entry.day)}>
                  {'day ' + entry.day + (entry.label ? ' · ' + entry.label : '')}
                </option>
              ))}
            </select>
          </label>
          <div className="dash-toggles">
            <label className="dash-toggle">
              <input type="checkbox" checked={colourOnly} onChange={event => setColourOnly(event.target.checked)} />
              <span>Colour only where published</span>
            </label>
            <label className="dash-toggle">
              <input type="checkbox" checked={dimQuiet} onChange={event => setDimQuiet(event.target.checked)} />
              <span>Dim districts with no published hazard</span>
            </label>
            {activeFilter ? (
              <button
                type="button"
                className="btn"
                onClick={() => { setNeedle(''); setStatePick(''); setColourPick(''); setDayPick('today'); }}
              >
                Reset the filters
              </button>
            ) : null}
          </div>
        </div>
        <p className="module-note" data-testid="today-filter-note">
          {activeFilter
            ? 'Filters are applied in this browser over the ' + count(rows.length, 'row') + ' this read returned: ' + count(matched.length, 'district') + ' match. The product is not asked again, and a filtered view is not a second read.'
            : 'Filters run in this browser over the ' + count(rows.length, 'row') + ' this read returned. The product is not asked again.'}
        </p>
      </section>

      <section className="dash-kpis" data-testid="today-national">
        <Kpi
          testId="today-kpi-districts"
          label="Districts in this read"
          value={notRecordedWhen(national?.districts)}
          unit={typeof national?.districts === 'number' ? 'districts' : undefined}
          caption={'Read from the national district warning product. Source features without a district name: ' + orNot(national?.skipped) + '.' +
            (picture.readAt ? ' Read ' + picture.readAt + '.' : ' The read time is not recorded in this payload.')}
        >
          <ColourStrip tally={tally} />
        </Kpi>
        <Kpi
          testId="today-kpi-district-days"
          label="District-days with a published colour"
          value={Object.keys(tally).length ? rampTotal(tally) : 'not recorded'}
          unit={Object.keys(tally).length ? 'district-days' : undefined}
          caption={'Counted from the tally the product returned, one day and colour per district. ' + (tally[UNSET] === undefined ? 'No unrecognised colour code was counted.' : 'Unrecognised colour codes counted separately: ' + tally[UNSET] + '.')}
        >
          <MiniBars tally={tally} />
        </Kpi>
        <Kpi
          testId="today-kpi-editions"
          label="Editions behind the newest in this read"
          value={readingWhen(behind, stillReading)}
          unit={typeof behind === 'number' ? 'districts' : undefined}
          caption={'Newest printed edition in this read: ' + orNot(newestEdition, NOT_RECORDED) + '. Oldest age among those behind it: ' + (typeof oldestAge === 'number' ? oldestAge + ' days before this read' : NOT_RECORDED) + '. Bulletin date most rows carry: ' + orNot(national?.bulletin_date, NOT_RECORDED) + (stillReading ? '. The district rows are still being read; these counts come from the overview read.' : editionSource ? '. Counted from ' + editionSource + '.' : '.')}
        >
          <EditionHistogram dates={editionDates} newest={newestEdition} oldestAge={oldestAge} behind={behind} />
        </Kpi>
        <Kpi
          testId="today-kpi-radar"
          label="Radar stations reporting a status"
          value={notRecordedWhen(radar?.reported)}
          unit={typeof radar?.stations === 'number' ? 'of ' + radar.stations + ' returned' : undefined}
          caption={'Radar stations returned: ' + count(radar?.stations, 'station') + '. A reporting station is a station that reported a status, not a healthy network.'}
        >
          <ReportingRing reported={radar?.reported ?? null} total={radar?.stations ?? null} />
        </Kpi>
      </section>

      <section className="dash-band">
        <Card
          testId="today-map-card"
          className="dash-card-map"
          title="Published warning colour by district"
          meta={'A join of two reads by district key: the served district geometry (' + count(geometry.data?.features?.length, 'district') + (geometryBusy ? ', reading…' : geometryError ? ', read failed' : '') + ') and the warning rows this read returned (' + count(rows.length, 'row') + '). A district with no matching row is drawn as an outline; absence of a row is not absence of a warning.'}
        >
          <div className="dash-map-layout">
            <div className="min-w-0">
              <DistrictRiskMap
                collection={geometry.data}
                rows={rows}
                matchKeys={matchKeys}
                colourOnly={colourOnly}
                dimQuiet={dimQuiet}
                selectedKey={selected}
                onSelect={setSelected}
                dayIndex={dayIndex}
                geometryState={geometryBusy ? 'pending' : geometryError ? 'error' : 'ready'}
              />
            </div>
            <div className="dash-map-side">
              <DistrictInspector
                rows={rows}
                selectedKey={selected}
                dayIndex={dayIndex}
                statePick={statePick}
                onSelect={setSelected}
                onState={value => { setStatePick(value); setSelected(null); }}
                askHref={question => '#/assistant?ask=' + encodeURIComponent(question)}
                warningsHref={district => district ? '#/warnings?district=' + encodeURIComponent(district) : '#/warnings'}
              />
            </div>
          </div>
          <ul className="dash-map-legend" aria-label="Published colour legend">
            {RAMP.map(colour => (
              <li key={colour}>
                <ColourTag colour={colour} text={colour} />
                <span className="quiet">{orNot(tally[colour], 'not counted in this read') + ' district-days'}</span>
              </li>
            ))}
            <li>
              <ColourTag colour={null} text="no colour stated" />
              <span className="quiet">{orNot(tally[UNSET], 'none') + ' district-days'}</span>
            </li>
          </ul>
          <DataTable
            testId="today-map-table"
            caption="The table behind the figure: one row per district this read returned, with the day it published and the colour and wording as published. The figure draws the same rows."
            columns={['District', 'State', 'Day', 'Date', 'Colour as published', 'Hazard wording as published']}
            rows={mapRows.slice(0, 40).map(entry => [
              orNot(entry.name),
              orNot(entry.state),
              entry.row ? orNot(entry.day && entry.day.day, NO_ROW) : NOT_RECORDED,
              orNot((entry.day && (entry.day.label || entry.day.date_local)) || (entry.row && entry.row.bulletin_date), NOT_RECORDED),
              entry.row
                ? <ColourTag key="colour" colour={statedColour(entry.day)} text={(entry.day && entry.day.colour) || 'no colour stated'} />
                : <span key="colour" className="quiet">not in this read</span>,
              entry.row ? wordingOf(entry.day) : 'this district has no warning row in this read',
            ])}
          />
        </Card>

        <div className="dash-column">
          <Card
            testId="today-matrix-card"
            title="Published colour by published day"
            meta="One bubble per cell the rows returned, area proportional to the count of district-days. A cell with no rows is empty, not zero."
          >
            <BubbleMatrix cells={matrix} days={dayAxis} />
            <DataTable
              testId="today-matrix-table"
              caption="The matrix as exact counts, one row per published colour."
              columns={['Colour', 'Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5']}
              rows={RAMP.concat(UNSET).map(colour => [
                <ColourTag key="colour" colour={colour === UNSET ? null : colour} text={colour} />,
                ...[1, 2, 3, 4, 5].map(day => {
                  const cell = matrix.find(entry => entry.day === day && entry.colour === colour);
                  return cell ? String(cell.count) : NOT_RECORDED;
                }),
              ])}
            />
          </Card>
          <Card
            testId="today-editions-card"
            title="Editions by printed bulletin date"
            meta="How many districts in this read carry each printed bulletin date. The axis is the read's own dates."
          >
            <EditionBars editions={editions} />
            <DataTable
              testId="today-bulletin-dates"
              caption="Bulletin dates as the returned rows state them; a date the source did not state is not shown as one."
              columns={['Bulletin date', 'Rows carrying it']}
              rows={editions.map(edition => [orNot(edition.date, 'date not stated'), String(edition.rows)])}
            />
          </Card>
        </div>
      </section>

      <section className="dash-band">
        <Card
          testId="today-warned"
          title="Districts with a published hazard covering today"
          meta={warnedMeta}
        >
          {warnings.error ? (
            <p className="module-note" data-testid="today-warned-error">
              The warning read failed, so this list is empty because the rows were not read — not because nothing was published.
            </p>
          ) : null}
          {!warnings.error && !warnedToday.length ? (
            <p className="module-note">
              {rows.length ? 'No district-day covering today is non-quiet in this read. The product may still publish hazards on other days; the day selector above shows them.' : 'This read returned no district rows, so nothing can be listed.'}
            </p>
          ) : null}
          {warnedToday.length ? (
            <ul className="dash-list">
              {(showAll ? warnedToday : warnedToday.slice(0, LIST_SHOWN)).map(entry => (
                <li key={entry.row.key || String(entry.row.district)}>
                  <button
                    type="button"
                    className={'dash-list-row' + (selected && selected === entry.row.key ? ' dash-list-row-active' : '')}
                    onClick={() => setSelected(entry.row.key || null)}
                  >
                    <ColourTag colour={statedColour(entry.day)} text={(entry.day && entry.day.colour) || 'colour not stated'} />
                    <span className="dash-list-name">{orNot(entry.row.district)}{entry.row.state ? ', ' + entry.row.state : ''}</span>
                    <span className="dash-list-wording quiet">{wordingOf(entry.day)}</span>
                    <span className="dash-list-meta evidence">
                      {(entry.day && (entry.day.label || entry.day.date_local) ? (entry.day.label || entry.day.date_local) : 'date not stated') + (entry.row.bulletin_date ? ' · edition ' + entry.row.bulletin_date : '')}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {warnedToday.length > LIST_SHOWN ? (
            <button type="button" className="btn" onClick={() => setShowAll(value => !value)}>
              {showAll ? 'Show the first ' + LIST_SHOWN : 'Show all ' + warnedToday.length}
            </button>
          ) : null}
        </Card>

        <Card
          testId="today-composition"
          title="How this read is composed"
          meta="Share of district-days by the colour the product printed. A composition of published values, not a risk score, a probability or a confidence."
        >
          <ColourDonut tally={tally} total={dayDistrictDays} />
          <Facts
            testId="today-composition-facts"
            rows={[
              ['Newest printed edition in this read', orNot(newestEdition, NOT_RECORDED)],
              ['Districts behind that edition', notRecordedWhen(behind)],
              ['Oldest age among them', typeof oldestAge === 'number' ? oldestAge + ' days before this read' : NOT_RECORDED],
              ['District-days with an unrecognised colour code', orNot(tally[UNSET], 'none')],
            ]}
          />
          <DataTable
            testId="today-tally"
            caption="Colour tally exactly as the product returned it, one row per colour it printed."
            columns={['Colour', 'District-days counted']}
            rows={Array.from(new Set(TALLY_KEYS.concat(Object.keys(tally)))).map(key => [
              <ColourTag colour={key} key={key} text={key} />,
              orNot(tally[key]),
            ])}
          />
          <p className="module-note">
            These are counts of what the source published, read at the instant stated above. They are not a forecast, not a probability, not a skill or risk score, and not an all-clear: a quiet district-day is the product's own state, not a statement that nothing will happen.
          </p>
        </Card>
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
            {band ? <VizFigure kind="nowBand" spec={band} /> : null}
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
