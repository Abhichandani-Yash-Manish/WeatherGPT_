/* What changed: the stored forecast retrievals for one point, read as two printed editions of the same
   valid hour, plus the published district product the change is about. A change between retrievals is
   vintage variance: not skill, not accuracy and not a correction. Where an entry states no delta the two
   printed values stand beside each other and nothing is computed here. The read's own interpretation is a
   Facts row below, and its own limitation and not-established lines are the standard "What this read
   returned" footer every surface carries — this surface does not scan the payload a second time for a
   field that merely sounds like a note; a generic key-name scan is not a decision about what matters. */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import {
  Awaiting, ColourTag, DataTable, EvidenceFooter, Failure, Facts, NO_ROW, NOT_RECORDED, PlacePicker, Reading,
  ReadingFor, SurfaceShell, readWorkingPlace, type PlaceChoice,
} from './Evidence';

export const intents: string[] = (viewById('changes')?.intents ?? []).concat([
  'What did the earlier and later printed editions say for this point?']);

type Point = { latitude?: number; longitude?: number };
type Retrieval = { retrieved_at_utc?: string | null; product?: string | null; request_date?: string | null; response_sha256_prefix?: string | null };
type Example = { valid_time_utc?: string | null; first_value?: number | null; last_value?: number | null; first_retrieved_utc?: string | null; last_retrieved_utc?: string | null };
type ChangeEntry = { unit?: string | null; valid_hours?: number | null; mean_abs_change?: number | null; max_abs_change?: number | null; example?: Example | null };
type ChangesData = { point?: Point | null; requested_point?: Point | null; retrievals?: Retrieval[]; retrieval_count?: number | null; parameters?: Record<string, ChangeEntry>; overlapping_valid_hours?: number | null; interpretation?: string | null; [key: string]: unknown };
type DayRow = { day?: number; day_label?: string | null; date_utc?: string | null; date_local?: string | null; colour?: string | null; hazards?: string[]; wording?: string | null; source_text?: string | null };
type PlaceData = { district?: string | null; state?: string | null; headline?: string | null; severity?: string | null; issued_at_utc?: string | null; days?: DayRow[]; [key: string]: unknown };

function valueText(value: unknown): string {
  return value === null || value === undefined || value === '' ? NOT_RECORDED : String(value);
}

function stampText(value?: string | null): string {
  return value ? istStamp(value) : NOT_RECORDED;
}

function deltaText(entry: ChangeEntry): string {
  const mean = entry.mean_abs_change === null || entry.mean_abs_change === undefined ? '' : 'mean absolute change as returned: ' + entry.mean_abs_change;
  const peak = entry.max_abs_change === null || entry.max_abs_change === undefined ? '' : 'largest absolute change as returned: ' + entry.max_abs_change;
  return [mean, peak].filter(Boolean).join('; ');
}

function dayName(day: DayRow): string {
  return orNot(day.day_label, day.day ? 'Day ' + day.day : NO_ROW);
}

function dayWording(day: DayRow): string {
  const wording = day.wording || day.source_text;
  return wording || (day.hazards?.length ? day.hazards.join(', ') : 'no hazard wording published for this district-day');
}

function PublishedDistrict({ view }: { view: Envelope<PlaceData> }): JSX.Element {
  const district = view.data;
  return (
    <>
      {district ? (
        <>
          <Facts testId="changes-district" rows={[
            ['District', orNot(district.district)], ['State', orNot(district.state)],
            ['Headline as published', orNot(district.headline)], ['Severity as returned', orNot(district.severity)],
            ['Issued', stampText(district.issued_at_utc)],
          ]} />
          <DataTable testId="changes-days"
            caption="The published days this district product returned, with the colour and hazard wording the product printed."
            columns={['Day', 'Date', 'Colour as published', 'Hazard wording as published']}
            rows={(district.days || []).map(day => [dayName(day), orNot(day.date_utc || day.date_local),
              <ColourTag key="colour" colour={day.colour} text={day.colour || undefined} />, dayWording(day)])} />
        </>
      ) : <p className="module-note">This read returned no district for the point, so no district-day row is shown here.</p>}
      <EvidenceFooter envelope={view} />
    </>
  );
}

export function Surface(): JSX.Element {
  const [place, setPlace] = useState<PlaceChoice | null>(() => readWorkingPlace());
  const point = { lat: place?.latitude, lon: place?.longitude };
  const changes = useQuery({ queryKey: ['changes-point', point.lat, point.lon], enabled: place !== null, retry: false,
    queryFn: () => getJson<Envelope<ChangesData>>(withQuery('/api/forecast/changes', point)) });
  const published = useQuery({ queryKey: ['changes-district', point.lat, point.lon], enabled: place !== null, retry: false,
    queryFn: () => getJson<Envelope<PlaceData>>(withQuery('/api/warnings/place', point)) });
  const changeData = changes.data?.data;
  const parameters = Object.entries(changeData?.parameters || {});
  const answered = place !== null && !changes.isPending && !changes.isError;

  /* The control a reader used to ask for these reads, rendered in every state: the point survives a read in
     flight and survives a failed one, which is where a reader who named the wrong place needs it. */
  const ask = (
    <section className="module-section">
      <h2>The point</h2>
      {place ? <ReadingFor place={place} /> : null}
      <PlacePicker onPick={setPlace} hint="Name a place and choose a row; the stored retrievals are compared for those coordinates." />
      {!place ? (
        <Awaiting testId="changes-awaiting">
          Nothing has been read yet. Name a place below and this surface holds the stored retrievals for it side by side —
          what the earlier and the later edition printed for the same valid hour — with the published district product the
          change is about.
        </Awaiting>
      ) : null}
      {answered ? (
        <Facts testId="changes-point" rows={[
            ['Requested place', place.label ? place.label : 'label not recorded'],
            ['Requested coordinates', place.latitude + ', ' + place.longitude],
            ['Stored point the comparison used', changeData?.point ? orNot(changeData.point.latitude) + ', ' + orNot(changeData.point.longitude) : NOT_RECORDED],
            ['Stored retrievals for this point', valueText(changeData?.retrieval_count)],
            ['Valid hours retrieved more than once', valueText(changeData?.overlapping_valid_hours)],
            ['Interpretation as returned', orNot(changeData?.interpretation)],
          ]} />
      ) : null}
    </section>
  );

  return (
    <SurfaceShell
      title="What changed"
      lead="What the earlier and the later stored edition printed for the same valid hour, at one point, with the published district product the change is about."
      what="the changed-edition view"
      envelope={place ? changes.data : undefined}
      busy={place !== null && changes.isPending}
      error={place ? changes.error : undefined}
      onRetry={() => changes.refetch()}
      intents={intents}
      hold={ask}
    >
      {place ? (
        <>
          <section className="module-section">
            <h2>Changed parameters</h2>
            <p className="module-note">
              One row per parameter the store compared: what the earlier and the later retrieval printed for the same valid hour,
              the two vintages, and the delta only where this payload itself stated one. Where a row states no delta, its two
              printed values stand beside each other and nothing is computed here: the comparison is of two printed editions and
              is not a skill or accuracy claim.
            </p>
            <p className="module-note" role="status" data-testid="changes-count">
              {count(parameters.length, 'parameter')} with a comparison this read returned, across {count(changeData?.retrieval_count, 'stored retrieval')}.
            </p>
            <DataTable testId="changes-parameters"
              caption="The example the store attached to each parameter, with the two printed values, the two vintages and any delta the payload stated."
              columns={['Parameter', 'Example valid hour (IST)', 'Unit as returned', 'Earlier printed value', 'Earlier retrieval', 'Later printed value', 'Later retrieval', 'Delta as returned']}
              rows={parameters.map(([name, entry]) => {
                const example = entry.example || null;
                return [
                  name,
                  example ? (example.valid_time_utc ? istStamp(example.valid_time_utc) : NOT_RECORDED) : 'no example stated in this entry',
                  orNot(entry.unit),
                  example ? valueText(example.first_value) : 'no earlier edition stated in this entry',
                  example ? stampText(example.first_retrieved_utc) : NOT_RECORDED,
                  example ? valueText(example.last_value) : 'no later edition stated in this entry',
                  example ? stampText(example.last_retrieved_utc) : NOT_RECORDED,
                  deltaText(entry) || 'no delta stated by this entry; both printed values stand beside each other',
                ];
              })} />
          </section>

          <section className="module-section">
            <h2>Vintages this comparison used</h2>
            <p className="module-note">
              Retrieval time is not the upstream model issue time; the store's own limitation line says so under "What this read
              returned". This table lists the retrieval rows the payload returned, not necessarily every retrieval it counted.
            </p>
            <DataTable testId="changes-retrievals" caption="The stored retrievals this comparison used, as the store recorded them."
              columns={['Retrieved (IST)', 'Product as returned', 'Requested date', 'Response sha256 prefix']}
              rows={(changeData?.retrievals || []).map(row => [stampText(row.retrieved_at_utc), orNot(row.product), orNot(row.request_date), orNot(row.response_sha256_prefix)])} />
          </section>

          <section className="module-section">
            <h2>The published district product this change is about</h2>
            <p className="module-note">
              The district product published for this point, read on its own route. It is the product the stored change is about;
              it is not this surface's verdict on the change.
            </p>
            {published.isPending ? (
              <Reading what="the published district product" />
            ) : published.isError ? (
              <Failure error={published.error} what="published district product" onRetry={() => published.refetch()} />
            ) : published.data ? <PublishedDistrict view={published.data} /> : null}
          </section>
        </>
      ) : null}
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
