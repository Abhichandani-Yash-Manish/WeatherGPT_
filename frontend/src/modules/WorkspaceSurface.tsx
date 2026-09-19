/* The workspace: one place, read as a dashboard.

   It restores the place-centred desk the vanilla workspace had (web/home.js, removed in R6) — the picture at your
   place, the task tools that write a question, and "pick up where you left off" — and composes it with the reads
   this build already serves. Every section reads a governed route on its own and keeps its own source, instant and
   failure: /api/forecast for the model hour, the days and the next hours; /api/now for the station report and the
   district day in force; /api/warnings/place for the published district days; /api/warnings/national with the
   district geometry for the India map; /api/air-quality; /api/climate/index and /series for the district record;
   /api/briefs and /api/plans. The map, the climate record and the kept items read only when they come near the
   screen.

   Two rules from the original workspace hold. The builder writes the editable question box and never submits on its
   own ("the field builder writes the editable question box and never submits on its own"); asking is a separate,
   explicit button. And the right-now reading stays: station, published district line and model hours, kept apart.
   No value is computed: a day's warmest hour is the returned hour with the highest value, named with its instant. No
   condition icon is drawn, because no payload carries a condition code. */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { AnimatePresence, motion, type Variants } from 'motion/react';
import { getJson, withQuery } from '../api/client';
import type { Envelope, NowReading } from '../api/types';
import { ChartBlock } from '../charts/ChartBlock';
import { count, orNot } from '../lib/format';
import { istClock, istDay, istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import { DropletIcon, SendIcon, SkyGlyphIcon, SparkleIcon, ThermometerIcon, WindIcon, skyGlyph } from '../shell/icons';
import {
  ColourTag, DataTable, Facts, Failure, NO_ROW, NOT_RECORDED, PlacePicker, Reading, SurfaceShell, readWorkingPlace,
  rememberPlace, usePinnedPlaces, type PlaceChoice,
} from './Evidence';
import { IndiaWarningMap } from './IndiaWarningMap';
import { currentIndex, dayRows, valueAt, windowOf, type Series, type SeriesPoint } from './dashboard';
import './dashboard.css';

export const intents: string[] = (viewById('workspace')?.intents ?? []).concat([
  'Write a question for a place and a window, and read what is happening there right now.',
]);

/* now_view.py states `why` when a part could not be read; the shared NowReading type does not carry it yet. */
type ForceReading = NonNullable<NowReading['in_force']> & { why?: string };

type StationParameter = { field?: string; name?: string; value?: number | string | null; unit?: string | null };
type StationRow = {
  kind?: string; network?: string; name?: string; station_code?: string; distance_km?: number; age_minutes?: number | null;
  observed_at_utc?: string; stale?: boolean; source_id?: string; parameters?: StationParameter[];
};

type ForecastData = { parameters?: Record<string, Series>; grid?: { latitude?: number; longitude?: number } };
type PlaceWarningDay = { date_local?: string; colour?: string | null; hazards?: string[]; quiet?: boolean; source_text?: string; label?: string };
type PlaceWarnings = { district?: string; state?: string; issued_at_utc?: string; days?: PlaceWarningDay[] };
type AirData = { parameters?: Record<string, Series>; current?: Record<string, number | null>; domain?: string };
type ClimateIndex = { states?: { state?: string; districts?: { district?: string; first_year?: number; last_year?: number; years?: number }[] }[] };
type ClimateSeries = { district?: string; state?: string; points?: { year?: number; value?: string | number | null; unit?: string; series_id?: string; source_page?: string; source_row?: number }[] };
type BriefsView = { briefs?: { id?: string; title?: string; saved_at?: string }[] };
type PlansView = { plans?: { id?: string; title?: string; state?: string; state_words?: string; last_checked_at?: string }[] };

export type SurfaceProps = { onAsk?: (question: string) => void; query?: URLSearchParams };

type Ledger = { conversations?: { id?: string; opening_question?: string; updated?: string }[] };
type Transcript = { turns?: { role?: string; content?: string }[]; updated?: string };

/* The point a deep link names (#/workspace?lat=…&lon=…&label=…), or null when it names none. */
export function pointFromQuery(query?: URLSearchParams): PlaceChoice | null {
  const latitude = Number(query?.get('lat'));
  const longitude = Number(query?.get('lon'));
  if (!query?.get('lat') || !query?.get('lon') || !Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
  if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return null;
  return { label: query.get('label') || null, latitude, longitude };
}

/* The last stored exchange, read only when the column is on screen: the reader's own question and the text the
   conversation stored for it. Nothing is written here and nothing is asked. */
function LastExchange({ active }: { active: boolean }): JSX.Element | null {
  const ledger = useQuery({ queryKey: ['conversations'], enabled: active, retry: false, queryFn: () => getJson<Ledger>('/api/conversations') });
  const latest = ledger.data?.conversations?.[0];
  const transcript = useQuery({
    queryKey: ['conversation', latest?.id], enabled: active && Boolean(latest?.id), retry: false,
    queryFn: () => getJson<Transcript>('/api/conversations/' + encodeURIComponent(String(latest?.id))),
  });
  if (!active || ledger.isPending || ledger.isError || !latest) return null;
  const turns = transcript.data?.turns || [];
  const question = [...turns].reverse().find(turn => turn.role === 'user')?.content || latest.opening_question;
  const answer = [...turns].reverse().find(turn => turn.role !== 'user' && turn.content)?.content;
  return (
    <div className="dash-exchange" aria-label="Your most recent stored conversation">
      <motion.p className="dash-said dash-said-user" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22 }}>
        {orNot(question, 'question not recorded')}
      </motion.p>
      {answer ? (
        <motion.p className="dash-said" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22, delay: 0.08 }}>
          {answer.length > 280 ? answer.slice(0, 280).trimEnd() + '…' : answer}
        </motion.p>
      ) : null}
      <a className="dash-link" href={'#/assistant?conversation=' + encodeURIComponent(String(latest.id))}>
        Continue this conversation <span aria-hidden="true">→</span>
      </a>
    </div>
  );
}

/* A stale station is written as stale, and a station whose staleness the payload does not state says so. */
function staleness(station: StationRow): string {
  if (station.stale === true) return 'stale: the report is older than the layer’s freshness window';
  if (station.stale === false) return 'current';
  return 'staleness not recorded';
}

function stationName(station: StationRow): string {
  return orNot(station.name || station.station_code, 'station not named');
}

const RISE: Variants = {
  hidden: { opacity: 0, y: 14 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.36, ease: [0.22, 0.61, 0.36, 1], staggerChildren: 0.03 } },
};
const CELL: Variants = { hidden: { opacity: 0, y: 8 }, shown: { opacity: 1, y: 0, transition: { duration: 0.24 } } };

/* True once the element has come within 300px of the screen. Without IntersectionObserver the section offers a
   button instead, so a large read is never started behind the reader's back. */
function useNearScreen(): [(node: HTMLDivElement | null) => void, boolean, () => void] {
  const [node, setNode] = useState<HTMLDivElement | null>(null);
  const [near, setNear] = useState(false);
  useEffect(() => {
    if (near || !node || typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) setNear(true);
    }, { rootMargin: '300px' });
    observer.observe(node);
    return () => observer.disconnect();
  }, [near, node]);
  return [setNode, near, () => setNear(true)];
}

function Deferred({ near, start, what }: { near: boolean; start: () => void; what: string }): JSX.Element | null {
  if (near) return null;
  return (
    <p className="module-note">
      {what} is read when this section comes into view.{' '}
      <button type="button" className="btn btn-ghost" onClick={start}>Read it now</button>
    </p>
  );
}

function Section({ id, eyebrow, title, note, link, children, className }: {
  id: string; eyebrow: string; title: string; note?: ReactNode; link?: { view: string; label: string }; children: ReactNode; className?: string;
}): JSX.Element {
  return (
    <motion.section
      className={'dash-section' + (className ? ' ' + className : '')}
      aria-labelledby={id}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, amount: 0.08 }}
      variants={RISE}
    >
      <header className="dash-section-head">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2 id={id} className="dash-title">{title}</h2>
          {note ? <p className="module-note">{note}</p> : null}
        </div>
        {link ? <a className="dash-link" href={'#/' + link.view}>{link.label} <span aria-hidden="true">→</span></a> : null}
      </header>
      {children}
    </motion.section>
  );
}

/* A catalogue label ("Pune, Pune Division, State of Mahārāshtra") is shown whole, but headed by its first part. */
export function placeParts(place: PlaceChoice): { title: string; rest: string } {
  const label = orNot(place.label, place.latitude + ', ' + place.longitude);
  const [title, ...rest] = label.split(', ');
  return { title, rest: rest.join(', ') };
}

/* The name a question uses: the label's parts without repeats and without the "State of" prefix, as the vanilla desk wrote it. */
export function questionPlace(place: PlaceChoice): string {
  if (!place.label || !String(place.label).trim()) return place.latitude + ', ' + place.longitude;
  return Array.from(new Set(String(place.label).split(', ').map(part => part.replace(/^State of /, '').trim()).filter(Boolean))).join(', ');
}

function withUnit(point: SeriesPoint | null, unit?: string | null): string {
  if (!point) return 'no value returned';
  return point.v + (unit ? ' ' + unit : ' (unit not stated)');
}

/* ---- the hero: the model hour and what the station printed --------------------------------------------------- */

const HERO_METRICS: [string, string, (props: { size?: number }) => JSX.Element][] = [
  ['apparent_temperature', 'Feels like', ThermometerIcon],
  ['relative_humidity_2m', 'Humidity', DropletIcon],
  ['wind_speed_10m', 'Wind', WindIcon],
];

/* "read 4 min ago" from the source's own retrieval instant and this machine's clock. */
export function readAgo(retrieved: string | null | undefined, now: number): string {
  const at = Date.parse(String(retrieved || ''));
  if (!Number.isFinite(at)) return 'read time not recorded';
  const minutes = Math.max(0, Math.round((now - at) / 60000));
  if (minutes < 1) return 'read just now';
  if (minutes < 60) return 'read ' + minutes + ' min ago';
  return 'read ' + istStamp(retrieved);
}

function stationValue(station: StationRow | undefined, field: string): string | null {
  const entry = (station?.parameters || []).find(item => (item.field || item.name) === field);
  return entry && entry.value !== null && entry.value !== undefined && entry.value !== '' ? String(entry.value) + (entry.unit ? ' ' + entry.unit : '') : null;
}

const STATION_FIELDS: [string, string][] = [
  ['temp', 'temperature'], ['rh', 'humidity'], ['windsp', 'wind speed'], ['winddir', 'wind from'], ['visibility', 'visibility'],
];

function stationLine(station: StationRow): string {
  const parameters = station.parameters || [];
  const pick = (field: string) => parameters.find(entry => (entry.field || entry.name) === field);
  const values = STATION_FIELDS.flatMap(([field, label]) => {
    const entry = pick(field);
    if (!entry || entry.value === null || entry.value === undefined || entry.value === '') return [];
    return [label + ' ' + entry.value + (entry.unit ? ' ' + entry.unit : '')];
  });
  return values.length ? values.join(' · ') : 'no reported field in this row';
}

function stationSky(station: StationRow): string | null {
  const parameters = station.parameters || [];
  const text = parameters.find(entry => (entry.field || entry.name) === 'weather' && typeof entry.value === 'string')?.value
    || parameters.find(entry => (entry.field || entry.name) === 'nebulosity' && typeof entry.value === 'string')?.value;
  return typeof text === 'string' && text.trim() ? text.trim() : null;
}

function Hero({ place, forecast, now, onPlace, now_ms }: {
  place: PlaceChoice | null;
  forecast: UseQueryResult<Envelope<ForecastData>>;
  now: UseQueryResult<Envelope<NowReading>>;
  onPlace: (place: PlaceChoice) => void;
  now_ms: number;
}): JSX.Element {
  const pins = usePinnedPlaces();
  const parameters = forecast.data?.data?.parameters || {};
  const temperature = parameters.temperature_2m;
  const index = currentIndex(temperature?.points, now_ms);
  const hour = valueAt(temperature, index);
  const reading = now.data?.data;
  const station = (reading?.observed?.stations as StationRow[] | undefined)?.[0];
  const source = forecast.data?.sources?.[0];
  const sky = station ? stationSky(station) : null;
  const glyph = skyGlyph(sky);
  const extra = (name: string, label: string) => {
    const point = valueAt(parameters[name], index);
    return point ? <span className="dash-fine-metric">{label} {point.v} {orNot(parameters[name]?.unit, '')}</span> : null;
  };

  return (
    <section className="dash-hero" aria-labelledby="dash-place" data-ground="housing">
      <div className="dash-hero-head">
        <div className="dash-hero-title">
          <p className="dash-hero-label">Right now</p>
          <h2 id="dash-place" className="dash-place">{place ? placeParts(place).title : 'Choose your place'}</h2>
        </div>
        <div className="dash-hero-actions">
          {place ? (
            <details className="dash-hero-more">
              <summary>Model output · more readings and source</summary>
              <p className="dash-hero-fine">
                Model output for the grid cell, not an observation.
                <span className="dash-fine-metric">{(placeParts(place).rest ? placeParts(place).rest + ' · ' : '') + place.latitude + ', ' + place.longitude}</span>
                {hour ? <span className="dash-fine-metric">{'valid ' + istStamp(hour.t)}</span> : null}
                {extra('precipitation_probability', 'Rain chance')}
                {extra('wind_gusts_10m', 'Gusts')}
                {extra('visibility', 'Visibility')}
                {stationValue(station, 'mslp') ? <span className="dash-fine-metric">Pressure {stationValue(station, 'mslp')} (station, no unit)</span> : null}
                {source ? <span className="dash-fine-metric">{orNot(source.source_id) + ' · ' + orNot(source.product) + ' · read ' + (source.retrieved_at_utc ? istStamp(source.retrieved_at_utc) : NOT_RECORDED)}</span> : null}
              </p>
            </details>
          ) : null}
          <details className={'dash-change' + (place ? '' : ' dash-change-inline')} open={!place}>
            <summary>{place ? 'Change place' : 'Choose a place'}</summary>
            <div className="dash-change-body">
              <PlacePicker onPick={onPlace} clearOnPick hint="Type at least two characters; the catalogue returns places to choose from. Choosing one reads its right-now point and writes nothing." />
            </div>
          </details>
        </div>
      </div>

      {!place ? (
        <div className="dash-empty">
          <p className="dash-lead">
            Name a place, or search one in the bar above, to read its model hour, the station report nearest to it, the district day
            in force, the next days and its record — each with its own source and read time.
          </p>
          {pins.length ? (
            <div className="dash-pins" role="group" aria-label="Your pinned places">
              {pins.map(pin => (
                <button key={pin.label} type="button" className="chip dash-chip" onClick={() => onPlace(pin)}>
                  {pin.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={place.latitude + ',' + place.longitude}
            className="dash-reading"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.22 }}
          >
            {forecast.isPending ? (
              <Reading what="the model hour for this place" />
            ) : forecast.isError ? (
              <Failure error={forecast.error} what="point forecast" onRetry={() => forecast.refetch()} />
            ) : (
              <div className="dash-hero-row">
                <div className="dash-temp-block">
                  <div className="dash-temp" data-testid="dash-temperature">
                    <span className="dash-numeral">{hour ? hour.v : '—'}</span>
                    <span className="dash-unit">{hour ? orNot(temperature?.unit, 'unit not stated') : 'no value returned'}</span>
                  </div>
                  <p className="dash-temp-label">{hour ? 'Model hour · ' + istClock(hour.t) + ' IST' : 'No temperature returned for this hour'}</p>
                </div>
                <div className="dash-cond">
                  {glyph ? <span className="dash-cond-glyph" aria-hidden="true"><SkyGlyphIcon glyph={glyph} size={40} /></span> : null}
                  <span className="dash-cond-text">
                    <span className="dash-cond-printed" title={sky || undefined}>{sky || (now.isPending ? 'Reading the station sky…' : 'No sky printed nearby')}</span>
                    {sky && station ? <span className="dash-cond-by">{'as ' + stationName(station) + ' printed it'}</span> : null}
                  </span>
                </div>
                <dl className="dash-metrics">
                  {HERO_METRICS.map(([name, label, MetricIcon]) => {
                    const point = valueAt(parameters[name], index);
                    return (
                      <div key={name} className="dash-metric">
                        <dt><span className="dash-metric-badge" aria-hidden="true"><MetricIcon size={13} /></span>{label}</dt>
                        <dd className="evidence">{point ? <>{point.v}<span className="dash-metric-unit"> {orNot(parameters[name]?.unit, '')}</span></> : <span className="dash-gap">not returned</span>}</dd>
                      </div>
                    );
                  })}
                </dl>
                <div className="dash-updated">
                  <span className="dash-metric-label">Updated</span>
                  <span>{readAgo(source?.retrieved_at_utc, now_ms)}</span>
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      )}
    </section>
  );
}

/* The station report and the district day, as two panels under the charts. */
function StatusPanels({ now }: { now: UseQueryResult<Envelope<NowReading>> }): JSX.Element {
  const reading = now.data?.data;
  const station = (reading?.observed?.stations as StationRow[] | undefined)?.[0];
  const inForce: ForceReading | undefined = reading?.in_force;
  return (
    <div className="dash-status">
      <section className="dash-panel dash-observed" aria-labelledby="dash-observed-title">
        <h2 id="dash-observed-title" className="dash-panel-title">Observed nearby</h2>
        {now.isPending ? (
          <p className="dash-foot-text">Reading the nearest station report…</p>
        ) : now.isError ? (
          <p className="dash-foot-text">The right-now read failed; the failure and its retry are in the evidence below.</p>
        ) : station ? (
          <>
            <p className="dash-foot-strong">
              {'At ' + stationName(station) + (station.station_code && station.name ? ' (' + station.station_code + ')' : '') +
                (typeof station.distance_km === 'number' ? ', ' + station.distance_km + ' km away' : '')}
            </p>
            <p className="dash-foot-text">{stationLine(station)}</p>
            <p className="dash-foot-meta">
              {(station.observed_at_utc ? 'reported ' + istStamp(station.observed_at_utc) : 'report time not recorded') +
                ' · ' + staleness(station) + ' · units as the station layer printed them'}
            </p>
          </>
        ) : (
          <p className="dash-foot-text">No station row came back within the search radius for this point.</p>
        )}
      </section>
      <section className="dash-panel dash-inforce" aria-labelledby="dash-inforce-title">
        <h2 id="dash-inforce-title" className="dash-panel-title">District day in force</h2>
        {now.isPending ? (
          <p className="dash-foot-text">Reading the district product…</p>
        ) : inForce?.status_line ? (
          <>
            <p className="dash-foot-strong">
              <ColourTag colour={inForce.colour} text={inForce.colour || 'colour not stated'} />{' '}
              {orNot(inForce.district) + (inForce.state ? ', ' + inForce.state : '')}
            </p>
            <p className="dash-foot-text">{'IMD district product: ' + inForce.status_line}</p>
            <p className="dash-foot-meta">{inForce.issued_at_utc ? 'issued ' + istStamp(inForce.issued_at_utc) : 'issue time not recorded'}</p>
          </>
        ) : (
          <p className="dash-foot-text">No published district-day row came back for this point.</p>
        )}
      </section>
    </div>
  );
}

/* ---- the days and the hours ---------------------------------------------------------------------------------- */

function Outlook({ forecast, warnings, now_ms }: {
  forecast: UseQueryResult<Envelope<ForecastData>>;
  warnings: UseQueryResult<Envelope<PlaceWarnings>>;
  now_ms: number;
}): JSX.Element {
  const [day, setDay] = useState('');
  const strip = useRef<HTMLDivElement | null>(null);
  const parameters = forecast.data?.data?.parameters || {};
  const temperature = parameters.temperature_2m;
  const rain = parameters.precipitation_probability;
  const rows = dayRows(temperature, rain);
  const published = warnings.data?.data?.days || [];
  const chosen = rows.some(row => row.date === day) ? day : '';
  const chosenLabel = chosen ? istDay(Date.parse(chosen + 'T12:00:00+05:30')) : '';
  const chart = (name: string, title: string, tone?: 'rain') => {
    const series = parameters[name];
    const points = windowOf(series, now_ms, chosen || undefined).map(point => ({
      t: point.t || undefined, v: point.v ?? null, label: point.t ? istDay(point.t) + ' ' + istClock(point.t) : undefined,
      evidence_id: point.source_locator,
    }));
    return (
      <ChartBlock variant="panel" tone={tone} title={title} subtitle={chosen ? chosenLabel : 'next 24h'} unit={series?.unit || ''}
        chart={{ title, unit: series?.unit || '', axis_label: 'Valid at (IST)', points } as never} />
    );
  };

  return (
    <div className="dash-forecast">
      <div className="dash-block-head">
        <h2 className="dash-block-title">Forecast</h2>
        <span className="dash-block-sub">{rows.length ? rows.length + '-day forecast · IST dates · warmest | coolest hour (' + orNot(temperature?.unit, 'unit not stated') + ')' : 'model hours for the grid cell'}</span>
        <a className="dash-link" href="#/forecast">Every parameter <span aria-hidden="true">→</span></a>
      </div>
      {forecast.isPending ? (
        <Reading what="the forecast days" />
      ) : forecast.isError ? (
        <p className="module-note">The forecast read failed; its failure and retry are stated in the reading above.</p>
      ) : !rows.length ? (
        <p className="module-note">{NO_ROW}: this read returned no temperature series to lay out by day.</p>
      ) : (
        <>
          <div className="dash-daystrip">
            <motion.div ref={strip} className="dash-days" role="group" aria-label="Choose a day for the hourly charts" variants={RISE} initial="hidden" animate="shown">
              {rows.map(row => {
                const warning = published.find(entry => entry.date_local === row.date);
                const label = istDay(Date.parse(row.date + 'T12:00:00+05:30'));
                return (
                  <motion.button key={row.date} type="button" variants={CELL} className="dash-day"
                    aria-pressed={chosen === row.date} onClick={() => setDay(chosen === row.date ? '' : row.date)}
                    aria-label={label + ': warmest returned hour ' + withUnit(row.warmest, temperature?.unit) + ', coolest ' + withUnit(row.coolest, temperature?.unit) +
                      ', highest hourly rain chance ' + withUnit(row.wettest, rain?.unit) + ', ' + count(row.hours, 'hour') + ' returned' +
                      (warning?.colour ? ', district day published ' + warning.colour : '')}>
                    <span className="dash-day-name">{label}</span>
                    <span className="dash-day-rain" aria-hidden="true" style={{ ['--rain' as string]: String(row.wettest ? Math.max(0, Math.min(100, Number(row.wettest.v))) / 100 : 0) }}>
                      <DropletIcon size={28} strokeWidth={1.5} />
                      <DropletIcon size={28} strokeWidth={1.5} fill="currentColor" className="dash-day-rain-fill" />
                    </span>
                    <span className="dash-day-temps evidence">
                      <span className="dash-hi">{row.warmest ? row.warmest.v : '—'}</span>
                      <span className="dash-sep" aria-hidden="true">|</span>
                      <span className="dash-lo">{row.coolest ? row.coolest.v : '—'}</span>
                    </span>
                    <span className="dash-day-meta evidence">{row.wettest ? row.wettest.v + orNot(rain?.unit, '') : '—'}</span>
                    {warning?.colour ? <span className="dash-day-flag" data-colour={warning.colour.toLowerCase()} aria-hidden="true" /> : null}
                  </motion.button>
                );
              })}
            </motion.div>
            <button type="button" className="dash-daystrip-more" aria-label="Scroll the forecast days" onClick={() => strip.current?.scrollBy({ left: 280, behavior: 'smooth' })}>
              <span aria-hidden="true">›</span>
            </button>
          </div>
          <p className="dash-daystrip-note" title="Hours the product returned, not a published daily figure. Choose a day for its hours; choose it again for the next 24 hours.">
            Warmest | coolest returned hour ({orNot(temperature?.unit, 'unit not stated')}) · droplet: highest hourly rain chance · dot: published district colour{warnings.isError ? ' (district day read failed)' : ''} · choose a day for its hours
          </p>
          <div className="dash-charts">
            {chart('temperature_2m', 'Hourly Temperature Trend')}
            {chart('precipitation_probability', 'Hourly Precipitation Probability', 'rain')}
          </div>
        </>
      )}
    </div>
  );
}

/* ---- air quality, the map, the record ------------------------------------------------------------------------ */

const AIR: [string, string][] = [
  ['us_aqi', 'US AQI'], ['european_aqi', 'European AQI'], ['pm2_5', 'PM2.5'], ['pm10', 'PM10'], ['ozone', 'Ozone'], ['nitrogen_dioxide', 'NO₂'],
];

function Air({ air }: { air: UseQueryResult<Envelope<AirData>> }): JSX.Element {
  if (air.isPending) return <Reading what="the modelled air quality" />;
  if (air.isError) return <Failure error={air.error} what="air-quality" onRetry={() => air.refetch()} />;
  const data = air.data?.data;
  const current = data?.current || {};
  return (
    <>
      <dl className="dash-air">
        {AIR.map(([name, label]) => (
          <div key={name} className="dash-air-cell">
            <dt>{label}</dt>
            <dd className="evidence">
              {typeof current[name] === 'number' ? current[name] : <span className="dash-gap">not returned</span>}
              <span className="dash-metric-unit"> {orNot(data?.parameters?.[name]?.unit, '')}</span>
            </dd>
          </div>
        ))}
      </dl>
      <p className="module-note">
        Current values as {orNot(data?.parameters?.pm2_5?.model, 'the model')} returned them for its grid ({orNot(data?.domain)}). Modelled
        concentrations and the source’s own indices: not a ground monitor and not a health assessment.
      </p>
    </>
  );
}

function Climate({ inForce, active, waiting }: { inForce?: ForceReading; active: boolean; waiting: boolean }): JSX.Element {
  const district = inForce?.district || '';
  const state = inForce?.state || '';
  const index = useQuery({
    queryKey: ['climate-index'], enabled: active && Boolean(district), retry: false, staleTime: 300_000,
    queryFn: () => getJson<Envelope<ClimateIndex>>('/api/climate/index'),
  });
  const match = (() => {
    const entry = (index.data?.data?.states || []).find(row => (row.state || '').toLowerCase() === state.toLowerCase());
    const found = entry?.districts?.find(row => (row.district || '').toLowerCase() === district.toLowerCase());
    return entry && found ? { state: entry.state as string, district: found.district as string, first: found.first_year, last: found.last_year } : null;
  })();
  const series = useQuery({
    queryKey: ['climate-series', match?.state, match?.district], enabled: active && match !== null, retry: false,
    queryFn: () => getJson<Envelope<ClimateSeries>>(withQuery('/api/climate/series', { state: match?.state, district: match?.district })),
  });

  if (!district && waiting) return <p className="module-note">The district record follows the district the right-now read names; that read is still working.</p>;
  if (!district) return <p className="module-note">The right-now read named no district for this point, so no district record is read.</p>;
  if (!active) return <></>;
  if (index.isPending) return <Reading what="the district record index" />;
  if (index.isError) return <Failure error={index.error} what="climate record index" onRetry={() => index.refetch()} />;
  if (!match) {
    return (
      <p className="module-note">
        The stored district record has no district named exactly {district}{state ? ', ' + state : ''}. A near-match is not substituted:
        open Climate records to choose a district from the index.
      </p>
    );
  }
  if (series.isPending) return <Reading what="the district rainfall series" />;
  if (series.isError) return <Failure error={series.error} what="district rainfall series" onRetry={() => series.refetch()} />;
  const points = (series.data?.data?.points || []).map(point => ({
    year: point.year, v: point.value === null || point.value === undefined || point.value === '' ? null : Number(point.value),
    label: point.year === undefined ? undefined : String(point.year),
    evidence_id: [point.series_id, point.source_page ? 'p' + point.source_page : '', point.source_row ? 'row ' + point.source_row : ''].filter(Boolean).join(' · '),
  }));
  const unit = series.data?.data?.points?.[0]?.unit || '';
  return (
    <>
      <ChartBlock title={'Annual rainfall, ' + match.district + ', ' + match.state} unit={unit}
        chart={{ title: 'Annual rainfall', unit, axis_label: 'Year', points } as never} />
      <p className="module-note">
        {count(points.length, 'year')} of the published district table ({orNot(match.first)}–{orNot(match.last)}), transcribed row by row. A
        year the table does not carry is a gap, never a zero; this is a historical record, not a projection.
      </p>
    </>
  );
}

/* ---- tools that write a question (restored from the vanilla workspace desk) ---------------------------------- */

type Tool = { id: string; group: string; title: string; detail: string; output: string; question?: (place: string) => string; view?: string };

/* The defaults a tool writes (tomorrow, morning, cotton, VOBL, 1981–2010) are the vanilla desk's own defaults; the box
   stays editable and the status line says they are there to be changed. */
export const TOOLS: Tool[] = [
  { id: 'now', group: 'Daily weather', title: 'Understand right now', detail: 'Nearby station reports, the published warning day and the next model hours.', output: 'Current-condition reading', question: p => 'What is it like right now in ' + p + '?' },
  { id: 'forecast', group: 'Daily weather', title: 'Plan a weather window', detail: 'Rain, temperature, humidity and wind for a place and part of the day.', output: 'Forecast with exact hours', question: p => 'What is the weather forecast for ' + p + ' tomorrow morning?' },
  { id: 'air-quality', group: 'Daily weather', title: 'Read modelled air quality', detail: 'CAMS pollutant concentrations and the source’s own indices. Model output, not a ground monitor or health assessment.', output: 'Hourly air-quality evidence', question: p => 'Show PM2.5 and US AQI for ' + p + ' tomorrow.' },
  { id: 'compare', group: 'Models & history', title: 'Compare forecast models', detail: 'Put GFS and the best-match product side by side. Their model lineage can overlap.', output: 'Source comparison', question: p => 'Compare the GFS and best-match forecast for rain in ' + p + ' tomorrow morning.' },
  { id: 'ensemble', group: 'Models & history', title: 'Explore ensemble spread', detail: 'Read the range and spread of model members. Spread is not confidence or forecast skill.', output: 'Member statistics', question: p => 'Show the ensemble spread for temperature in ' + p + ' tomorrow.' },
  { id: 'verification', group: 'Models & history', title: 'Check a model’s recent errors', detail: 'Match archived model runs to ERA5 reanalysis by lead time. A measurement against reanalysis, not a skill score.', output: 'Error table by lead time', view: 'verification' },
  { id: 'warning', group: 'Warnings & plans', title: 'Read the warning brief', detail: 'The district day, published hazards, issue time and what the product does not establish.', output: 'Brief to save or export', view: 'warnings' },
  { id: 'watch', group: 'Warnings & plans', title: 'Watch a plan', detail: 'Describe an activity and when it happens. Check official district guidance while the workspace runs.', output: 'Plan and local inbox', question: p => 'Notify me about official weather warning changes for my outdoor event in ' + p + ' tomorrow morning.' },
  { id: 'farm', group: 'Published advice', title: 'Read a crop advisory', detail: 'Find published passages for your district and crop, with their issue date and original PDF.', output: 'Cited advisory passages', question: p => 'What does the district agromet advisory for ' + p + ' say for cotton?' },
  { id: 'bulletin', group: 'Published advice', title: 'Search published bulletins', detail: 'Read the indexed national weather bulletin by topic. Published wording stays reference material.', output: 'Passages and source pages', question: () => 'What does the latest all India weather bulletin say about heavy rainfall?' },
  { id: 'history', group: 'Models & history', title: 'Explore rainfall history', detail: 'Read the published district series and its descriptive trend, within the available years.', output: 'Chart and source records', question: p => 'Show the annual rainfall trend for ' + p + ' district from 1981 to 2010.' },
  { id: 'reanalysis', group: 'Models & history', title: 'Look back at a weather week', detail: 'Ask for daily modelled reanalysis for a chosen past date. This is not a station record.', output: 'Historical daily series', question: p => 'Show daily ERA5 temperature and rainfall for ' + p + ' from 2025-07-01 to 2025-07-07.' },
  { id: 'aviation', group: 'Specialist weather', title: 'Read an airport report', detail: 'METAR observations or a TAF forecast for the airport code you choose.', output: 'Station report and explanation', question: () => 'Show the latest METAR for VOBL and explain it.' },
  { id: 'marine', group: 'Specialist weather', title: 'Explore waves offshore', detail: 'Modelled wave height, direction and period, with the answering cell and distance.', output: 'Wave forecast', question: p => 'What are the wave conditions off ' + p + ' tomorrow?' },
  { id: 'river', group: 'Specialist weather', title: 'Explore river discharge', detail: 'Modelled discharge near a point. No observed water level, danger level or flood extent.', output: 'Discharge forecast', question: p => 'Show the modelled river discharge near ' + p + ' tomorrow.' },
  { id: 'briefing', group: 'Warnings & plans', title: 'Keep a place briefing', detail: 'Keep a dated reading of warnings and forecast context in the briefcase.', output: 'Dated local briefing', view: 'briefcase' },
];

const GROUP_NAMES = ['All tools', ...Array.from(new Set(TOOLS.map(tool => tool.group)))];

function Tools({ place, onWrite }: { place: PlaceChoice | null; onWrite: (question: string, tool: Tool) => void }): JSX.Element {
  const [group, setGroup] = useState('All tools');
  const [term, setTerm] = useState('');
  const needle = term.trim().toLowerCase();
  const found = TOOLS.filter(tool => (group === 'All tools' || tool.group === group) &&
    [tool.title, tool.detail, tool.output].join(' ').toLowerCase().includes(needle));
  return (
    <>
      <div className="dash-tool-controls">
        <div className="dash-filters" role="group" aria-label="Filter tools">
          {GROUP_NAMES.map(name => (
            <button key={name} type="button" className="chip" aria-pressed={group === name} onClick={() => setGroup(name)}>{name}</button>
          ))}
        </div>
        <label className="module-field dash-tool-search">
          <span>Find a tool</span>
          <input type="search" value={term} placeholder="rain, bulletin, airport…" onChange={event => setTerm(event.target.value)} />
        </label>
      </div>
      <ul className="dash-tools">
        {found.map(tool => (
          <motion.li key={tool.id} className="dash-tool" layout="position" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <p className="dash-tool-group">{tool.group}</p>
            <h3 className="dash-tool-title">{tool.title}</h3>
            <p className="dash-tool-detail">{tool.detail}</p>
            <div className="dash-tool-foot">
              <span className="dash-tool-output">{tool.output}</span>
              {tool.view ? (
                <a className="btn" href={'#/' + tool.view}>Open <span aria-hidden="true">→</span></a>
              ) : (
                <button type="button" className="btn" aria-label={'Write the question: ' + tool.title}
                  onClick={() => onWrite(tool.question!(place ? questionPlace(place) : 'your place'), tool)}>
                  Write question
                </button>
              )}
            </div>
          </motion.li>
        ))}
      </ul>
      <p className="module-note" aria-live="polite">
        {found.length ? count(found.length, 'tool') + ' · a tool writes the question box beside the reading and sends nothing.' : 'No tools match. Try “rain”, “bulletin” or “airport”.'}
      </p>
    </>
  );
}

function Kept({ active }: { active: boolean }): JSX.Element {
  const briefs = useQuery({ queryKey: ['briefcase'], enabled: active, retry: false, queryFn: () => getJson<BriefsView>('/api/briefs') });
  const plans = useQuery({ queryKey: ['plans'], enabled: active, retry: false, queryFn: () => getJson<PlansView>('/api/plans') });
  if (!active) return <></>;
  const openPlans = () => (document.querySelector('[data-testid="plans-open"]') as HTMLButtonElement | null)?.click();
  return (
    <div className="dash-kept">
      <div className="dash-kept-col">
        <h3 className="dash-kept-title">Saved briefs</h3>
        {briefs.isPending ? <Reading what="the briefcase" /> : briefs.isError ? <Failure error={briefs.error} what="briefcase" onRetry={() => briefs.refetch()} /> : (
          (briefs.data?.briefs || []).length ? (
            <ul className="dash-kept-list">
              {(briefs.data?.briefs || []).slice(0, 3).map(entry => (
                <li key={entry.id || entry.title}><span>{orNot(entry.title, 'Saved brief')}</span><span className="dash-foot-meta">saved {entry.saved_at ? istStamp(entry.saved_at) : NOT_RECORDED}</span></li>
              ))}
            </ul>
          ) : <p className="module-note">No brief is kept yet. A warning brief or a place briefing can be saved, reopened and exported from the briefcase.</p>
        )}
        <a className="dash-link" href="#/briefcase">Open the briefcase <span aria-hidden="true">→</span></a>
      </div>
      <div className="dash-kept-col">
        <h3 className="dash-kept-title">Plans and inbox</h3>
        {plans.isPending ? <Reading what="the plans" /> : plans.isError ? <Failure error={plans.error} what="plans" onRetry={() => plans.refetch()} /> : (
          (plans.data?.plans || []).length ? (
            <ul className="dash-kept-list">
              {(plans.data?.plans || []).slice(0, 3).map(entry => (
                <li key={entry.id || entry.title}><span>{orNot(entry.title, 'Plan')}</span><span className="dash-foot-meta">{orNot(entry.state_words || entry.state, 'state not recorded')} · checked {entry.last_checked_at ? istStamp(entry.last_checked_at) : 'not yet'}</span></li>
              ))}
            </ul>
          ) : <p className="module-note">No plan is saved. “Watch a plan” writes a question that describes one.</p>
        )}
        <button type="button" className="dash-link dash-link-button" onClick={openPlans}>Open plans and inbox <span aria-hidden="true">→</span></button>
      </div>
    </div>
  );
}

/* ---- the surface --------------------------------------------------------------------------------------------- */

export function Surface({ onAsk, query }: SurfaceProps = {}): JSX.Element {
  /* The place a link names, or the one this browser last resolved. The vanilla workspace opened on the working place;
     the port opened empty unless a link carried one, so a reader who had just read a place had to name it again. */
  const [point, setPoint] = useState<PlaceChoice | null>(() => pointFromQuery(query) || readWorkingPlace());
  const linked = query?.toString() || '';
  useEffect(() => {
    const named = pointFromQuery(query);
    if (named) {
      setPoint(named);
      rememberPlace(named);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linked]);
  const [askRef, askNear] = useNearScreen();
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [draft, setDraft] = useState('');
  const [written, setWritten] = useState<string | null>(null);
  const [missing, setMissing] = useState('');
  const box = useRef<HTMLTextAreaElement | null>(null);
  const [nowMs] = useState(() => Date.now());
  const [mapRef, mapNear, startMap] = useNearScreen();
  const [climateRef, climateNear, startClimate] = useNearScreen();
  const [keptRef, keptNear, startKept] = useNearScreen();
  const coordinates = { lat: point?.latitude, lon: point?.longitude };

  const now = useQuery({
    queryKey: ['workspace-now', point?.latitude, point?.longitude],
    queryFn: () => getJson<Envelope<NowReading>>(withQuery('/api/now', coordinates)),
    enabled: point !== null,
    retry: false,
  });
  const forecast = useQuery({
    queryKey: ['workspace-forecast', point?.latitude, point?.longitude],
    queryFn: () => getJson<Envelope<ForecastData>>(withQuery('/api/forecast', { ...coordinates, days: 7 })),
    enabled: point !== null,
    retry: false,
  });
  const warnings = useQuery({
    queryKey: ['workspace-warnings', point?.latitude, point?.longitude],
    queryFn: () => getJson<Envelope<PlaceWarnings>>(withQuery('/api/warnings/place', coordinates)),
    enabled: point !== null,
    retry: false,
  });
  const air = useQuery({
    queryKey: ['workspace-air', point?.latitude, point?.longitude],
    queryFn: () => getJson<Envelope<AirData>>(withQuery('/api/air-quality', coordinates)),
    enabled: point !== null,
    retry: false,
  });

  const writeQuestion = (question: string) => {
    setMissing('');
    setWritten(question);
    setDraft(question);
    box.current?.focus();
  };

  /* The builder's whole job: compose the sentence from the values the reader gave, write it into the box,
     then put the cursor there. It never asks the workspace and never submits the question. */
  const write = () => {
    const label = point?.label && String(point.label).trim() ? String(point.label).trim() : '';
    const where = label || (point ? point.latitude + ', ' + point.longitude : '');
    if (!where) {
      setWritten(null);
      setMissing('Name a place first: the builder writes the values you give it and will not guess one. Nothing was written and nothing was sent.');
      return;
    }
    writeQuestion('What is the forecast for ' + where + (start && end ? ' from ' + start + ' to ' + end + ' IST' : '') + '?');
  };

  const reading = now.data?.data;
  const stations: StationRow[] = (reading?.observed?.stations as StationRow[] | undefined) || [];
  const inForce: ForceReading | undefined = reading?.in_force;
  const hours = reading?.next_hours;
  const unit = hours?.unit || {};
  const placeName = point ? questionPlace(point) : '';
  const suggestions = point ? [
    'What is it like right now in ' + placeName + '?',
    'Will it rain in ' + placeName + ' tomorrow morning?',
    'Is any warning in force for ' + placeName + ' today?',
    'Show the hourly forecast for ' + placeName + ' tomorrow.',
  ] : [];

  const mapSection = (
    <Section id="dash-map" eyebrow="India" title="District warnings across India" link={{ view: 'warnings', label: 'Every district day' }}
      note="The colour each district bulletin published for the chosen date, drawn on the district geometry of the same basemap build.">
      <div ref={mapRef}>
        <Deferred near={mapNear} start={startMap} what="The national warning table and the district geometry" />
        {mapNear ? <IndiaWarningMap point={point} home={inForce ? { district: inForce.district, state: inForce.state } : null} compact /> : null}
      </div>
    </Section>
  );

  /* The right-now read starts only once a point is chosen, so the shell's own pending and error path would hide
     the builder; that read's Reading and Failure are rendered in its own section instead, with the same retry. */
  return (
    <SurfaceShell
      title="Dashboard"
      lead="Your place, read as one picture: the model hour and the nearest station, the district day in force, the next days and hours, the India warning map, air quality and the district record. Every value keeps its own source and read time; nothing is sent from here until you ask."
      what="right-now reading"
      envelope={now.data}
      busy={false}
      error={undefined}
      onRetry={() => { void now.refetch(); }}
      className="module-dashboard"
    >
      <div className="dash">
        <Hero place={point} forecast={forecast} now={now} onPlace={place => { rememberPlace(place); setPoint(place); }} now_ms={nowMs} />

        <aside className="dash-aside" aria-labelledby="dash-ask-title">
          <div className="dash-ask" ref={askRef}>
            <h2 id="dash-ask-title" className="dash-ask-title">AI Assistant</h2>
            <LastExchange active={askNear} />
            {suggestions.length ? (
              <div className="dash-suggestions" role="group" aria-label="Questions to write for this place">
                <p className="dash-suggestions-label">{'Suggested for ' + placeParts(point!).title + ':'}</p>
                {suggestions.map(question => (
                  <button key={question} type="button" className="dash-suggestion" onClick={() => writeQuestion(question)}>
                    “{question}”
                  </button>
                ))}
              </div>
            ) : null}
            <div className="dash-ask-spacer" aria-hidden="true"><SparkleIcon size={22} /></div>
            <div className="dash-question-pill">
              <span className="dash-pill-badge" aria-hidden="true">W</span>
              <label className="dash-question" htmlFor="question">
                <span className="sr-only">Your question</span>
                <textarea id="question" rows={1} ref={box} value={draft} placeholder={point ? 'Ask about ' + placeParts(point).title + '…' : 'Ask about weather…'} onChange={event => setDraft(event.target.value)} />
              </label>
              {onAsk ? (
                <button type="button" className="dash-send" aria-label="Ask this in the conversation" disabled={!draft.trim()} onClick={() => onAsk(draft.trim())}>
                  <SendIcon size={15} />
                </button>
              ) : (
                <a className="dash-send" href="#/assistant" aria-label="Open the conversation"><SendIcon size={15} /></a>
              )}
            </div>
            <p className="module-note" role="status" aria-live="polite" data-testid="workspace-written">
              {missing
                || (written
                  ? 'Wrote this into the editable question box above: “' + written + '”. The box stays editable — change it there before the question is asked anywhere. Nothing was sent.'
                  : 'Nothing has been written yet. The box is empty and editable; the builder writes only the values you enter.')}
            </p>
            <details className="dash-builder">
              <summary>Time window, and how this box works</summary>
              <div className="module-controls">
                <label className="module-field" htmlFor="workspace-start">
                  <span>From (IST)</span>
                  <input id="workspace-start" type="time" value={start} onChange={event => setStart(event.target.value)} />
                </label>
                <label className="module-field" htmlFor="workspace-end">
                  <span>Until (IST)</span>
                  <input id="workspace-end" type="time" value={end} onChange={event => setEnd(event.target.value)} />
                </label>
                <button type="button" className="btn" onClick={write}>Write this into the question</button>
              </div>
              <p className="module-note dash-ask-rules">
                This builder writes the question box and nothing else. It sends nothing: writing a question makes no request, and no
                value is filled in for you. A coordinate is not turned into a district here — the engine resolves names, and a
                district is never inferred from a coordinate. This surface never submits the question: it stays editable in the box for you.
              </p>
            </details>
          </div>
        </aside>

        {point ? (
          <>
            <Outlook forecast={forecast} warnings={warnings} now_ms={nowMs} />
            <StatusPanels now={now} />

            {mapSection}

            <Section id="dash-air" eyebrow="Air" title="Modelled air quality" link={{ view: 'air-quality', label: 'Hourly air quality' }}>
              <Air air={air} />
            </Section>

            <Section id="dash-climate" eyebrow="Record" title="The district rainfall record" link={{ view: 'climate', label: 'Climate records' }}>
              <div ref={climateRef}>
                <Climate inForce={inForce} active={climateNear} waiting={now.isPending} />
                {inForce?.district ? <Deferred near={climateNear} start={startClimate} what="The district record" /> : null}
              </div>
            </Section>
          </>
        ) : null}


        {!point ? mapSection : null}

        <Section id="dash-tools" eyebrow="Tools" title="What do you want to do?" note="Each tool writes a question into the box beside the reading, or opens the surface that answers it.">
          <Tools place={point} onWrite={question => writeQuestion(question)} />
        </Section>

        <Section id="dash-kept" eyebrow="Kept" title="Pick up where you left off">
          <div ref={keptRef}>
            <Kept active={keptNear} />
            <Deferred near={keptNear} start={startKept} what="The briefcase and the plans" />
          </div>
        </Section>

        <Section id="dash-evidence" eyebrow="Evidence" title="Right now where you are"
          note="Naming a place reads GET /api/now for that point and nothing else: the station report, the published district product line and the model hours are kept apart, each with its own status, instant and limits.">
          {!point ? (
            <p className="module-note">
              No point has been chosen, so no right-now reading was requested: no limitation line, source row or not-established
              line is shown for a read that did not happen.
            </p>
          ) : now.isPending ? (
            <Reading what="right-now reading" />
          ) : now.isError ? (
            <Failure error={now.error} what="right-now reading" onRetry={() => { void now.refetch(); }} />
          ) : reading ? (
            <div className="dash-evidence">
              <Facts testId="workspace-point" rows={[
                ['Point the read returned', reading.point && reading.point.latitude !== undefined
                  ? reading.point.latitude + ', ' + reading.point.longitude : 'coordinates not recorded in this read'],
                ['Label as returned', orNot(reading.point?.label, 'label not recorded in this read')],
                ['Place you picked', orNot(point.label, 'label not recorded')],
              ]} />
              <h3>Observed</h3>
              <DataTable testId="workspace-stations"
                caption="Station rows this read returned, each with its own distance, instant and age; a station is not a district average."
                columns={['Station', 'Network', 'Distance', 'Observed at', 'Age at retrieval', 'Staleness']}
                rows={stations.map(station => [
                  stationName(station) + (station.station_code && station.name ? ' · ' + station.station_code : ''),
                  orNot(station.network || station.kind),
                  station.distance_km === null || station.distance_km === undefined ? NOT_RECORDED : station.distance_km + ' km',
                  station.observed_at_utc ? istStamp(station.observed_at_utc) : NOT_RECORDED,
                  station.age_minutes === null || station.age_minutes === undefined ? NOT_RECORDED : station.age_minutes + ' minutes before retrieval',
                  staleness(station),
                ])} />
              <h3>In force</h3>
              {inForce && inForce.status_line ? (
                <>
                  <Facts rows={[
                    ['District', orNot(inForce.district) + (inForce.state ? ', ' + inForce.state : '')],
                    ['Day', orNot(inForce.day_label, NO_ROW)],
                    ['Issued', inForce.issued_at_utc ? istStamp(inForce.issued_at_utc) : NOT_RECORDED],
                    ['Quiet flag as published', inForce.quiet === undefined ? NOT_RECORDED : String(inForce.quiet)],
                  ]} />
                  <p>
                    <ColourTag colour={inForce.colour} text={inForce.colour || 'colour not stated'} />{' '}
                    <span className="reading">{inForce.status_line}</span>
                  </p>
                </>
              ) : (
                <p className="module-note">
                  No published district-day row came back for this point: {orNot(inForce?.why, NO_ROW)}. A point outside every
                  district polygon of the warning product carries no district guidance.
                </p>
              )}
              <h3>Next hours</h3>
              <p className="module-note">
                Model hours for the grid cell, not observations. An hour the product did not return is a gap in this table, never a zero.
              </p>
              <DataTable testId="workspace-hours"
                caption={'Next hours as returned' + (hours?.source_id ? ', source ' + hours.source_id : '') + (hours?.model ? ' · ' + hours.model : '')}
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
                ])} />
            </div>
          ) : null}
        </Section>
      </div>
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
