/* The workspace: the guided task builder and the right-now reading for the point it names.
   The builder writes a question into an editable box and sends nothing — the recorded vanilla check
   ("the field builder writes the editable question box and never submits on its own") holds this line.
   The reading is GET /api/now for the chosen point: observed, in force and next hours, kept apart. */
import { useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope, NowReading } from '../api/types';
import { orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import { ColourTag, DataTable, Facts, Failure, NO_ROW, NOT_RECORDED, PlacePicker, Reading, SurfaceShell, type PlaceChoice } from './Evidence';

export const intents: string[] = (viewById('workspace')?.intents ?? []).concat([
  'Write a question for a place and a window, and read what is happening there right now.',
]);

/* now_view.py states `why` when a part could not be read; the shared NowReading type does not carry it yet. */
type ForceReading = NonNullable<NowReading['in_force']> & { why?: string };

type StationRow = {
  kind?: string; network?: string; name?: string; station_code?: string; distance_km?: number; age_minutes?: number | null;
  observed_at_utc?: string; stale?: boolean; source_id?: string;
};

/* A stale station is written as stale, and a station whose staleness the payload does not state says so. */
function staleness(station: StationRow): string {
  if (station.stale === true) return 'stale: the report is older than the layer’s freshness window';
  if (station.stale === false) return 'current';
  return 'staleness not recorded';
}

function stationName(station: StationRow): string {
  return orNot(station.name || station.station_code, 'station not named');
}

export function Surface(): JSX.Element {
  const [point, setPoint] = useState<PlaceChoice | null>(null);
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [draft, setDraft] = useState('');
  const [written, setWritten] = useState<string | null>(null);
  const [missing, setMissing] = useState('');
  const box = useRef<HTMLTextAreaElement | null>(null);
  const now = useQuery({
    queryKey: ['workspace-now', point?.latitude, point?.longitude],
    queryFn: () => getJson<Envelope<NowReading>>(withQuery('/api/now', { lat: point?.latitude, lon: point?.longitude })),
    enabled: point !== null,
    retry: false,
  });

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
    const question = 'What is the forecast for ' + where + (start && end ? ' from ' + start + ' to ' + end + ' IST' : '') + '?';
    setMissing('');
    setWritten(question);
    setDraft(question);
    box.current?.focus();
  };

  const reading = now.data?.data;
  const stations: StationRow[] = reading?.observed?.stations || [];
  const inForce: ForceReading | undefined = reading?.in_force;
  const hours = reading?.next_hours;
  const unit = hours?.unit || {};

  /* The right-now read starts only once a point is chosen, so the shell's own pending and error path would hide
     the builder; that read's Reading and Failure are rendered in its own section instead, with the same retry. */
  return (
    <SurfaceShell
      title="Workspace"
      lead="The guided task builder: name a place, give a window, and write the question into an editable box — nothing is sent from here. The same point is read right now: the station report, the published district product line and the model hours, kept apart."
      what="right-now reading"
      envelope={now.data}
      busy={false}
      error={undefined}
      onRetry={() => { void now.refetch(); }}
    >
      <section className="module-section">
        <h2>Build a question</h2>
        <p className="module-note">
          This builder writes the question box and nothing else. It sends nothing: writing a question makes no request, and no
          value is filled in for you. A coordinate is not turned into a district here — the engine resolves names, and a
          district is never inferred from a coordinate. This surface never submits the question: it stays editable in the box for you.
        </p>
        <PlacePicker onPick={setPoint} hint="Type at least two characters; the catalogue returns places to choose from. Choosing one reads its right-now point and writes nothing." />
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
        <label className="module-field" htmlFor="question">
          <span>Your question</span>
          <textarea id="question" rows={3} ref={box} value={draft} onChange={event => setDraft(event.target.value)} />
        </label>
        <p className="module-note" role="status" aria-live="polite" data-testid="workspace-written">
          {missing
            || (written
              ? 'Wrote this into the editable question box above: “' + written + '”. The box stays editable — change it there before the question is asked anywhere. Nothing was sent.'
              : 'Nothing has been written yet. The box is empty and editable; the builder writes only the values you enter.')}
        </p>
      </section>

      <section className="module-section">
        <h2>Right now where you are</h2>
        <p className="module-note">
          Naming a place reads GET /api/now for that point and nothing else: the station report, the published district product
          line and the model hours are kept apart, each with its own status, instant and limits.
        </p>
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
          <>
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
          </>
        ) : null}
      </section>
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
