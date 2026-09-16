/* Climate records: the stored district rainfall record this machine holds, read through the two routes
   that carry it — the index that says what the collection covers, and the series for one district the
   reader chooses from that index. The series is the source's own published annual total, year by year:
   a year the record does not hold is a row that says so and a gap in the drawing, never a zero, and no
   value is interpolated across it. Nothing here is a projection, an attribution or a forecast, and no
   colour, score or derived number is drawn. */
import { useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { ChartBlock } from '../charts/ChartBlock';
import { count, orNot } from '../lib/format';
import { viewById } from '../shell/views';
import { DataTable, EvidenceFooter, Failure, Facts, NO_ROW, NOT_RECORDED, Reading, SurfaceShell } from './Evidence';

type IndexGroup = { state?: string; districts?: { district?: string; years?: number | null; first_year?: number | null; last_year?: number | null }[] };
type IndexData = { states?: IndexGroup[]; districts?: number };
type SeriesPoint = { year?: number; value?: number | string | null; unit?: string | null; series_id?: string;
  source_page?: string | number | null; source_row?: number | null; source_file?: string | null;
  asset_sha256_prefix?: string | null; quality_flags?: string | null; label?: string | null };
type SeriesData = { district?: string; state?: string | null; parameter?: string; series_id?: string;
  points?: SeriesPoint[]; first_year?: number | null; last_year?: number | null };

export const intents: string[] = (viewById('climate')?.intents ?? []).concat([
  'Which years of the stored rainfall record does a district hold, and which years are missing?',
  'Is the stored record a climate projection or a forecast?',
]);

/* The one paragraph this surface must say in its own voice, whichever read answered. */
const STORED_RECORD = 'This is a stored historical record as this machine holds it: the published district rainfall tables, '
  + 'transcribed and read back row by row from the local database. It is not an observation from a station here, not a '
  + 'model output and not a forecast. The years returned are the years the source published; a year inside the record\u2019s '
  + 'own span that carries no row is a gap in the table and in the drawing, never a zero, and no value is interpolated '
  + 'across a missing year. A trend drawn across these years is not a climate projection, not an attribution and not a '
  + 'forecast.';

type Choice = { key: string; label: string; district: string; state: string };

function numeric(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  const text = typeof value === 'string' ? value.trim() : '';
  return text !== '' && Number.isFinite(Number(text)) ? Number(text) : null;
}

/* What a returned cell actually states: an absent or empty value stays absent, so nothing can read it as zero. */
function statedValue(value: unknown): number | string | null {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  return text === '' ? null : (value as number | string);
}

/* Only the districts the index returned can be chosen, and each carries the index's own year figures. */
function choicesOf(data?: IndexData): Choice[] {
  const choices: Choice[] = [];
  (data?.states || []).forEach(group => {
    const state = String(group.state || '').trim();
    (group.districts || []).forEach(row => {
      const district = String(row.district || '').trim();
      if (!district) return;
      const years = numeric(row.years);
      const first = numeric(row.first_year);
      const last = numeric(row.last_year);
      choices.push({
        key: state + '|' + district, district, state,
        label: district + (state ? ' (' + state + ')' : '') + ' · '
          + (years === null ? 'year count not stated by the index' : count(years, 'year') + ' as the index counted them') + ' · '
          + (first !== null && last !== null ? first + ' to ' + last : 'first and last year not stated'),
      });
    });
  });
  return choices;
}

type YearRow = { year: number; point?: SeriesPoint };

/* Every year the record's own span covers, in order: a year with no returned row keeps its place and states
   that no row came back, so the table never closes a gap silently and never draws the gap as zero. A read
   that states no usable span is not spanned here, and says so rather than pretending to cover years. */
function yearRows(data?: SeriesData): { rows: YearRow[]; spanned: boolean } {
  const points = (data?.points || []).filter(point => typeof point.year === 'number');
  const first = numeric(data?.first_year);
  const last = numeric(data?.last_year);
  if (first === null || last === null || last < first || last - first > 400) {
    return { rows: points.map(point => ({ year: point.year as number, point })), spanned: false };
  }
  const byYear = new Map(points.map(point => [point.year as number, point]));
  const rows: YearRow[] = [];
  for (let year = first; year <= last; year += 1) rows.push({ year, point: byYear.get(year) });
  return { rows, spanned: true };
}

export function Surface(): JSX.Element {
  const [picked, setPicked] = useState('');
  const index = useQuery({
    queryKey: ['climate-index'],
    queryFn: () => getJson<Envelope<IndexData>>('/api/climate/index'),
    retry: false,
  });
  const indexData = index.data?.data;
  const choices = choicesOf(indexData);
  const active = choices.find(choice => choice.key === picked) || null;
  const series = useQuery({
    queryKey: ['climate-series', active?.state, active?.district],
    queryFn: () => getJson<Envelope<SeriesData>>(withQuery('/api/climate/series', { district: active?.district, state: active?.state })),
    enabled: active !== null, retry: false,
  });

  const seriesData = series.data?.data;
  const points = seriesData?.points || [];
  const { rows, spanned } = yearRows(seriesData);
  const unit = String(points.map(point => point.unit).find(entry => typeof entry === 'string' && entry.trim() !== '') || '');
  const firstYear = numeric(seriesData?.first_year);
  const lastYear = numeric(seriesData?.last_year);
  const hashes = Array.from(new Set(points.map(point => String(point.asset_sha256_prefix || '').trim()).filter(Boolean)));
  const hashText = hashes.length === 1 ? hashes[0]
    : hashes.length ? 'the returned rows carry different prefixes' : 'hash prefix not returned with these rows';
  const spanSentence = spanned
    ? 'This record\u2019s own span is ' + orNot(firstYear) + ' to ' + orNot(lastYear) + ', and every year in it has a row below.'
    : 'This read stated no usable first and last year, so the table below lists only the rows it returned.';

  function valueCell(point?: SeriesPoint): ReactNode {
    if (!point) return <span className="module-gap">{NO_ROW} for this year</span>;
    const value = statedValue(point.value);
    return value === null ? <span className="module-gap">{NOT_RECORDED} in this row</span> : String(value);
  }

  return (
    <SurfaceShell
      title="Climate records"
      lead="The stored district rainfall record as this machine holds it: the index says what the collection covers, and the series shows the published annual totals for one district you choose, year by year."
      what="climate record index" envelope={index.data} busy={index.isPending} error={index.error} onRetry={() => index.refetch()}
    >
      <section className="module-section">
        <h2>What this record is</h2>
        <p className="module-note" data-testid="climate-standing">{STORED_RECORD}</p>
      </section>

      <section className="module-section">
        <h2>What the record holds</h2>
        <p className="module-note">One index row for every district this collection carries, with the years the index counted for it. The picker below offers these districts and nothing else.</p>
        <Facts testId="climate-index" rows={[
          ['States in this record', count(numeric(index.data?.coverage?.states), 'state')],
          ['Districts in this record', count(numeric(index.data?.coverage?.districts), 'district')],
          ['Districts this index listed', count(numeric(indexData?.districts), 'district')],
          ['Districts the picker offers', count(choices.length, 'district')],
        ]} />
        <DataTable
          testId="climate-index-table"
          caption="Every district row this index returned, with the years it counted and the span it states."
          columns={['State as the record spells it', 'District as the record spells it', 'Years the index counted', 'First year as returned', 'Last year as returned']}
          rows={(indexData?.states || []).flatMap(group => (group.districts || []).map(row =>
            [orNot(group.state), orNot(row.district), orNot(row.years), orNot(row.first_year), orNot(row.last_year)]))}
        />
      </section>

      <section className="module-section">
        <h2>The stored series for one district</h2>
        <label className="module-field" htmlFor="climate-district-select">
          <span>District to read the rainfall series for</span>
          <select id="climate-district-select" value={picked} onChange={event => setPicked(event.target.value)}>
            <option value="">No district chosen</option>
            {choices.map(choice => <option key={choice.key} value={choice.key}>{choice.label}</option>)}
          </select>
        </label>
        <p className="module-note">Only the rainfall parameter is offered, because the index this surface reads names no other parameter.</p>
        {!active ? (
          <p className="module-note">No district was chosen, so no series was read.</p>
        ) : series.isPending ? (
          <Reading what="the stored rainfall series" />
        ) : series.isError ? (
          <Failure error={series.error} what="stored rainfall series" onRetry={() => series.refetch()} />
        ) : (
          <>
            <Facts testId="climate-series" rows={[
              ['District as this read echoed it', orNot(seriesData?.district)],
              ['State as this read echoed it', orNot(seriesData?.state)],
              ['Parameter', orNot(seriesData?.parameter)],
              ['Series identifier', orNot(seriesData?.series_id)],
              ['Unit as the rows state it', unit || 'unit not stated by this read'],
              ['Time basis', 'Calendar year of the published table; each value is that year\u2019s published annual total as transcribed, not an instant.'],
              ['Hash prefix on the returned rows', <span className="evidence" key="hash">{hashText}</span>],
            ]} />
            <p className="module-note" role="status" aria-live="polite" data-testid="climate-series-count">
              {count(points.length, 'year row')} returned for this district. {spanSentence} A year with no returned row says so
              rather than showing a zero, and no value is interpolated across it.
            </p>
            {series.data?.status && series.data.status !== 'ok' ? (
              <p className="module-note">This read answered with its own status word &lsquo;{String(series.data.status)}&rsquo;; the absence below is stated rather than filled.</p>
            ) : null}
            <ChartBlock
              chart={{
                title: 'Annual rainfall as this record holds it', unit, axis_label: 'Year',
                points: rows.map(row => ({ year: row.year, x: row.year, label: String(row.year), value: statedValue(row.point?.value) })),
              }}
            />
            <p className="module-note">This route attaches no evidence id to a point, so the drawing names none; each point&rsquo;s source page, source row and file are in the table below.</p>
            <DataTable
              testId="climate-years"
              caption={(spanned ? 'Every year of the span this read stated' : 'Every year row this read returned')
                + ', with the value and source cell the record holds — unit ' + (unit || 'not stated by this read')}
              columns={['Year', 'Annual total (' + (unit || 'unit not stated') + ')', 'Source page as returned', 'Source row as returned', 'Quality flags as returned']}
              rows={rows.map(row => [
                String(row.year),
                valueCell(row.point),
                row.point ? orNot(row.point.source_page) : NO_ROW,
                row.point ? orNot(row.point.source_row) : NO_ROW,
                row.point ? orNot(row.point.quality_flags, 'no flag on this row') : NO_ROW,
              ])}
            />
            {series.data ? <EvidenceFooter envelope={series.data} /> : null}
          </>
        )}
      </section>
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
