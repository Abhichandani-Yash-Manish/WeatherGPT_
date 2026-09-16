/* Warnings: the national district warning product as it was returned, one row per district-day.
   The colour is drawn only where the payload stated one, and the product's own wording stays beside
   it. A quiet day is a quiet day in this product: never an all-clear. The name filter runs in this
   browser over the rows this read returned, and the surface says so. */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import { ColourTag, DataTable, NO_ROW, NOT_RECORDED, SurfaceShell } from './Evidence';

type WarningDay = {
  day?: number;
  day_label?: string | null;
  label?: string | null;
  date?: string | null;
  date_local?: string | null;
  date_utc?: string | null;
  colour?: string | null;
  colour_code?: number | null;
  hazards?: string[];
  hazard_codes?: number[];
  wording?: string | null;
  source_text?: string | null;
  quiet?: boolean;
};

type DistrictRow = {
  key?: string;
  district?: string | null;
  state?: string | null;
  bulletin_date?: string | null;
  issued_at_utc?: string | null;
  updated_at?: string | null;
  days?: WarningDay[];
};

type WarningsData = {
  districts?: DistrictRow[];
  tally?: Record<string, number>;
  skipped?: { obj_id?: string | number | null; reason?: string }[];
};

export const intents: string[] = (viewById('warnings')?.intents ?? []).concat([
  'Which district-days does the national product publish, and in what colour?',
]);

const DAY_ROWS_SHOWN = 150;
const DISTRICT_ROWS_SHOWN = 60;

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

export function Surface(): JSX.Element {
  const [needle, setNeedle] = useState('');
  const warnings = useQuery({
    queryKey: ['warnings-national'],
    queryFn: () => getJson<Envelope<WarningsData>>('/api/warnings/national'),
    retry: false,
  });

  const districts = warnings.data?.data?.districts || [];
  const term = needle.trim().toLowerCase();
  const matched = term ? districts.filter(row => String(row.district || '').toLowerCase().includes(term)) : districts;
  const rows = matched.flatMap(row => (row.days || []).map(day => ({ row, day })));
  const shown = rows.slice(0, DAY_ROWS_SHOWN);
  const skipped = warnings.data?.data?.skipped || [];

  return (
    <SurfaceShell
      title="Warnings"
      lead="The national district warning product as this machine read it: one row per district-day, the colour the product printed for that day, and the hazard wording it published."
      what="the national district warning product"
      envelope={warnings.data}
      busy={warnings.isPending}
      error={warnings.error}
      onRetry={() => warnings.refetch()}
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
        <p className="module-note" role="status" data-testid="warnings-count">
          Showing {count(shown.length, 'district-day row')} of {count(rows.length, 'district-day row')} matching this
          filter{rows.length > shown.length ? ', listing the first ' + DAY_ROWS_SHOWN + '.' : '.'}
        </p>
      </section>

      <section className="module-section">
        <h2>District-days</h2>
        <p className="module-note">
          A colour chip is drawn only where the product stated a colour for that district-day; an unstated colour is
          set as a word, never as a colour of this surface's choosing.
        </p>
        <DataTable
          testId="warnings-table"
          caption="One row per district-day, exactly as returned."
          columns={['District', 'State', 'Day', 'Date', 'Colour as published', 'Hazard wording as published']}
          rows={shown.map(({ row, day }) => [
            orNot(row.district),
            orNot(row.state),
            dayName(day),
            dayDate(day),
            <ColourTag key="colour" colour={day.colour} text={day.colour || undefined} />,
            dayWording(day),
          ])}
        />
        <DataTable
          testId="warnings-bulletins"
          caption="Bulletin identity per district row this read returned."
          columns={['District', 'Bulletin date', 'Issued', 'Updated']}
          rows={matched.slice(0, DISTRICT_ROWS_SHOWN).map(row => [
            orNot(row.district),
            orNot(row.bulletin_date),
            row.issued_at_utc ? istStamp(row.issued_at_utc) : NOT_RECORDED,
            row.updated_at ? istStamp(row.updated_at) : NOT_RECORDED,
          ])}
        />
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
