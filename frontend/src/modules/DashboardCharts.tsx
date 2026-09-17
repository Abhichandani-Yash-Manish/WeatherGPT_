/* Dashboard cards and chart primitives for the Today surface (docs/97).

   Every encoding here draws a value the read returned and nothing else: a bar is proportional to its own
   count, a bubble's area is proportional to its own count, a missing value is a gap, and each figure has a
   table alternative carrying the same numbers. Hazard colours come only from the token layer and only for a
   published colour; 'unset' is drawn as a hatched neutral so it never reads as the green of a quiet day. */
import type { ReactNode } from 'react';
import { count, orNot } from '../lib/format';

export const RAMP = ['red', 'orange', 'yellow', 'green'];
export const UNSET = 'unset';
export type Tally = Record<string, number>;

function tallyCount(tally: Tally, key: string): number | null {
  const value = tally[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function rampTotal(tally: Tally): number {
  return RAMP.reduce((sum, key) => sum + (tallyCount(tally, key) || 0), 0);
}

export function Card({ title, meta, children, testId, className }: {
  title: string; meta?: ReactNode; children: ReactNode; testId?: string; className?: string;
}) {
  return (
    <section className={'dash-card' + (className ? ' ' + className : '')} data-testid={testId}>
      <header className="dash-card-head">
        <h2>{title}</h2>
        {meta ? <p className="module-note">{meta}</p> : null}
      </header>
      {children}
    </section>
  );
}

/* A KPI card: label, hero numeral, unit, one caption line, one micro-visual. An absent value renders 'not
   recorded' in the numeral slot; it never renders 0 for a value the read did not state. */
export function Kpi({ label, value, unit, caption, children, testId }: {
  label: string; value: ReactNode; unit?: string; caption: ReactNode; children?: ReactNode; testId?: string;
}) {
  /* A numeral is set as a numeral; a word is set as a word. 'not recorded' at the numeral size burst out of
     the card, so the value slot measures its own content: digits and separators keep the display size, and
     anything else — 'not recorded', 'reading' — steps down and wraps on a balanced measure. */
  const text = typeof value === 'string' ? value.trim() : null;
  const numeral = text !== null && text.length > 0 && /^[\d.,\s%+-]+$/.test(text);
  const wordy = text !== null && !numeral;
  return (
    <article className="dash-kpi" data-testid={testId} data-value-kind={wordy ? 'word' : 'number'}>
      <p className="dash-kpi-label">{label}</p>
      <p className="dash-kpi-value">
        <span className={'dash-kpi-number' + (wordy ? ' dash-kpi-number-word' : '')}>{value}</span>
        {unit ? <span className="dash-kpi-unit">{unit}</span> : null}
      </p>
      <div className="dash-kpi-micro">{children}</div>
      <p className="dash-kpi-caption">{caption}</p>
    </article>
  );
}

export function notRecordedWhen(value: number | null | undefined): ReactNode {
  return typeof value === 'number' && Number.isFinite(value) ? value : 'not recorded';
}

/* The value slot for a read that has not answered yet. It is a state of the read, not a claim about the
   product: 'not recorded' would say the product stated nothing, which is a different sentence. */
export function readingWhen(value: number | null | undefined, reading: boolean): ReactNode {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  return reading ? 'reading…' : 'not recorded';
}

/* Editions this read returned, counted by their own printed date: one bar per date, the newest marked and
   the rows behind it split out. A read that stated no date draws nothing and says so. */
export function EditionHistogram({ dates, newest, oldestAge, behind }: {
  dates: Record<string, number>; newest?: string | null; oldestAge?: number | null; behind?: number | null;
}) {
  const rows = Object.entries(dates || {})
    .map(([date, value]) => ({ date, value: Number(value) }))
    .filter(row => Number.isFinite(row.value) && row.value > 0)
    .sort((left, right) => left.date.localeCompare(right.date));
  if (!rows.length) {
    return <p className="dash-gap">This read returned no printed bulletin date per row, so no edition profile is drawn.</p>;
  }
  const peak = rows.reduce((max, row) => Math.max(max, row.value), 0);
  const width = 300;
  const height = 86;
  const slot = width / rows.length;
  const newestTime = newest ? Date.parse(newest) : NaN;
  /* A printed edition more than a year behind the newest in the same read is drawn as stale: it is the
     reason this card exists, and one district sitting 1047 days back should not look like the other bars. */
  const ageDays = (date: string) => (Number.isNaN(newestTime) ? null : Math.round((newestTime - Date.parse(date)) / 86_400_000));
  return (
    <div className="dash-chart">
      <svg data-testid="today-edition-profile" className="dash-chart-svg" viewBox={'0 0 ' + width + ' ' + height} role="img"
        aria-label={'Districts per printed bulletin date: ' + rows.map(row => row.date + ' ' + row.value).join(', ')}>
        {rows.map((row, index) => {
          const barHeight = peak ? Math.max(3, (row.value / peak) * 54) : 0;
          const left = index * slot + slot * 0.15;
          const barWidth = Math.max(6, slot * 0.7);
          const isNewest = Boolean(newest) && row.date === newest;
          const age = ageDays(row.date);
          const isOld = !isNewest && age !== null && age > 365;
          return (
            <g key={row.date}>
              <rect
                className={'dash-edition-bar' + (isNewest ? ' dash-edition-newest' : '') + (isOld ? ' dash-edition-old' : '')}
                x={left} y={64 - barHeight} width={barWidth} height={barHeight}
                data-date={row.date} data-count={row.value} data-age-days={age === null ? undefined : age}
                data-newest={isNewest ? 'true' : undefined} data-stale={isOld ? 'true' : undefined}
              />
              <text className="dash-value" x={left + barWidth / 2} y={60 - barHeight}>{row.value}</text>
              {/* The year is part of the label: one district 1047 days behind prints a date three years back,
                  and a bare month-day would read as this year's edition. */}
              <text className="dash-axis" x={left + barWidth / 2} y="78" textAnchor="middle">{row.date.slice(2)}</text>
            </g>
          );
        })}
      </svg>
      <p className="module-note">
        One bar per printed bulletin date this read returned, each labelled with the count of district rows
        carrying it{newest ? '; the newest edition in this read is ' + newest : ''}.
        {typeof behind === 'number' ? ' Rows behind it: ' + behind + '.' : ''}
        {typeof oldestAge === 'number' ? ' The oldest is ' + oldestAge + ' days old at this read.' : ''}
        A date the read did not return is not drawn.
        {rows.some(row => { const age = ageDays(row.date); return row.date !== newest && age !== null && age > 365; })
          ? ' A bar marked as stale is more than a year behind the newest edition in this read.'
          : ''}
      </p>
    </div>
  );
}

/* KPI 1 micro-visual: a 100% stack of the published colour tally. Segment widths are proportional to their
   own counts; the unset share is a hatched neutral. */
export function ColourStrip({ tally }: { tally: Tally }) {
  const keys = RAMP.concat(UNSET).filter(key => (tallyCount(tally, key) || 0) > 0);
  if (!keys.length) return <p className="dash-gap">The read stated no colour tally, so no composition is drawn.</p>;
  return (
    <div className="dash-strip" role="img" aria-label={'Published colour tally: ' + keys.map(key => String(tally[key]) + ' ' + key).join(', ')}>
      {keys.map(key => (
        <span key={key} className={'dash-strip-part dash-strip-' + key} data-colour={key} style={{ flexGrow: tallyCount(tally, key) || 0 }} />
      ))}
    </div>
  );
}

/* KPI 2 micro-visual: one bar per published colour, each labelled with its own exact count. */
export function MiniBars({ tally }: { tally: Tally }) {
  const keys = RAMP.concat(UNSET).filter(key => (tallyCount(tally, key) || 0) > 0);
  if (!keys.length) return <p className="dash-gap">No published colour was counted in this read.</p>;
  const peak = Math.max.apply(null, keys.map(key => tallyCount(tally, key) || 0));
  return (
    <div className="dash-minibars" role="img" aria-label={'District-days by published colour: ' + keys.map(key => key + ' ' + String(tally[key])).join(', ')}>
      {keys.map(key => (
        <div className="dash-minibar" key={key}>
          <span className={'dash-minibar-bar dash-strip-' + key} data-colour={key} style={{ width: ((tallyCount(tally, key) || 0) / peak * 100) + '%' }} />
          <span className="dash-minibar-label quiet">{key + ' ' + String(tally[key])}</span>
        </div>
      ))}
    </div>
  );
}

/* KPI 4 micro-visual: a reporting ring. The arc length is reported/total, both of them stated numbers. */
export function ReportingRing({ reported, total }: { reported: number | null; total: number | null }) {
  if (!total) return <p className="dash-gap">The radar layer returned no station, so there is no ring to draw.</p>;
  const share = Math.max(0, Math.min(1, (reported || 0) / total));
  const length = 2 * Math.PI * 16;
  return (
    <svg className="dash-ring" viewBox="0 0 40 40" role="img" aria-label={String(reported || 0) + ' of ' + String(total) + ' stations report a status'}>
      <circle className="dash-ring-track" cx="20" cy="20" r="16" />
      <circle className="dash-ring-arc" cx="20" cy="20" r="16" strokeDasharray={String(length * share) + ' ' + String(length)} transform="rotate(-90 20 20)" />
    </svg>
  );
}

export type MatrixCell = { day: number; colour: string; count: number };

/* Published colour by published day.

   Geometry, stated so it can be checked: the colour names live in a fixed left gutter and no bubble may
   enter it (the plot starts clear of the labels), the row pitch is twice the largest possible radius plus a
   line of text, so a count printed above a bubble cannot touch the row above, and the radius never exceeds
   MAX_R so a large day cannot swallow its neighbours. A cell the rows did not return draws nothing at all:
   a gap in the grid, never a zero-sized bubble that would read as a measurement. */
const MAX_R = 13;
const GUTTER = 56;
const PLOT_LEFT = 70;
const PLOT_RIGHT = 604;
const TEXT_LINE = 16;

export function BubbleMatrix({ cells, days }: { cells: MatrixCell[]; days: { day: number; label: string | null }[] }) {
  const rows = RAMP.concat(UNSET);
  const peak = cells.reduce((max, cell) => Math.max(max, cell.count), 0);
  const byKey = new Map<string, number>();
  cells.forEach(cell => byKey.set(cell.day + '|' + cell.colour, cell.count));
  const rowPitch = 2 * MAX_R + TEXT_LINE + 12;
  const top = 30;
  const height = top + rows.length * rowPitch + 26;
  const width = 620;
  const step = days.length > 1 ? (PLOT_RIGHT - PLOT_LEFT) / (days.length - 1) : 0;
  const x = (index: number) => PLOT_LEFT + index * step;
  const y = (index: number) => top + index * rowPitch;
  const radius = (value: number) => (peak ? 3 + (MAX_R - 3) * Math.sqrt(value / peak) : 0);
  if (!days.length || !cells.length) return <p className="dash-gap">No district-day row stated a day and a colour, so no matrix is drawn.</p>;
  return (
    <div className="dash-chart">
      <svg data-testid="today-matrix" className="dash-chart-svg" viewBox={'0 0 ' + width + ' ' + height} role="img"
        aria-label={'Published colour by published day, bubble area proportional to the count of district-days: ' +
          cells.map(cell => 'day ' + cell.day + ' ' + cell.colour + ' ' + cell.count).join(', ')}>
        {/* Vertical guides, one per published day, drawn behind every row. */}
        {days.map((day, index) => (
          <line key={'guide-' + day.day} className="dash-gridline-vertical" x1={x(index)} y1={top - 12} x2={x(index)} y2={y(rows.length - 1) + 12} />
        ))}
        {rows.map((colour, index) => (
          <g key={colour}>
            <text className="dash-axis" x={GUTTER - 8} y={y(index) + 4} textAnchor="end">{colour}</text>
            <line className="dash-gridline" x1={PLOT_LEFT - 8} y1={y(index)} x2={PLOT_RIGHT + 8} y2={y(index)} />
            {days.map((day, dayIndex) => {
              const value = byKey.get(day.day + '|' + colour);
              if (value === undefined) return null; /* a gap, not a zero */
              const size = radius(value);
              const cx = x(dayIndex);
              const cy = y(index);
              return (
                <g key={colour + '-' + day.day} className="dash-bubble-cell">
                  <circle
                    className={'dash-bubble dash-strip-' + colour}
                    data-colour={colour}
                    data-count={value}
                    data-day={day.day}
                    cx={cx} cy={cy} r={size}
                  >
                    <title>{'day ' + day.day + ': ' + colour + ', ' + value + ' district-days'}</title>
                  </circle>
                  {/* The count is stated above the bubble in ink, never inside it: a number that has to be read
                      off a coloured shape is a number a reader can misread. */}
                  <text className="dash-value" x={cx} y={cy - size - 4}>{value}</text>
                </g>
              );
            })}
          </g>
        ))}
        {days.map((day, index) => (
          <g key={'label-' + day.day}>
            <text className="dash-axis" x={x(index)} y={height - 12} textAnchor="middle">day {day.day}</text>
            {day.label ? <text className="dash-axis dash-axis-quiet" x={x(index)} y={height - 1} textAnchor="middle">{day.label}</text> : null}
          </g>
        ))}
      </svg>
      <p className="module-note">Bubble area is proportional to the count of district-days in that cell, and the count is printed above each bubble. A cell with no returned rows is empty.</p>
    </div>
  );
}

/* Editions by printed bulletin date: one bar per date the read returned, each labelled with its own count.
   A date the read did not return is not drawn, and the caption says so. */
export function EditionBars({ editions }: { editions: { date: string; rows: number }[] }) {
  if (!editions.length) return <p className="dash-gap">No returned row stated a printed bulletin date.</p>;
  const peak = editions.reduce((max, edition) => Math.max(max, edition.rows), 0);
  const slot = 240 / editions.length;
  return (
    <div className="dash-chart">
      <svg data-testid="today-editions" className="dash-chart-svg" viewBox="0 0 300 140" role="img"
        aria-label={'Districts per printed bulletin date: ' + editions.map(edition => edition.date + ' ' + edition.rows).join(', ')}>
        {editions.map((edition, index) => {
          const height = peak ? (edition.rows / peak) * 96 : 0;
          const left = 30 + index * slot;
          return (
            <g key={edition.date}>
              <rect className="dash-bar" x={left} y={110 - height} width={Math.max(6, slot - 10)} height={height} />
              <text className="dash-value" x={left + Math.max(6, slot - 10) / 2} y={104 - height}>{edition.rows}</text>
              <text className="dash-axis" x={left + Math.max(6, slot - 10) / 2} y="126" textAnchor="middle">{edition.date.slice(5)}</text>
            </g>
          );
        })}
      </svg>
      <p className="module-note">One bar per printed bulletin date this read returned. A date with no rows is not drawn, so the axis is the read's own dates, not a calendar.</p>
    </div>
  );
}

/* Composition of the read: district-days by published colour, as a donut of exact counts. */
export function ColourDonut({ tally, total }: { tally: Tally; total: number }) {
  const keys = RAMP.concat(UNSET).filter(key => (tallyCount(tally, key) || 0) > 0);
  if (!keys.length || !total) return <p className="dash-gap">No published colour was counted, so no composition is drawn.</p>;
  const circumference = 2 * Math.PI * 34;
  let offset = 0;
  return (
    <div className="dash-donut-wrap">
      <svg data-testid="today-donut" className="dash-donut" viewBox="0 0 84 84" role="img"
        aria-label={'Composition of the read by published colour: ' + keys.map(key => key + ' ' + String(tally[key])).join(', ')}>
        {keys.map(key => {
          const value = tallyCount(tally, key) || 0;
          const length = (value / total) * circumference;
          const dash = String(length) + ' ' + String(circumference - length);
          const element = (
            <circle
              key={key}
              className={'dash-donut-slice dash-strip-' + key}
              data-colour={key}
              cx="42" cy="42" r="34"
              strokeDasharray={dash}
              strokeDashoffset={-offset}
              transform="rotate(-90 42 42)"
            />
          );
          offset += length;
          return element;
        })}
      </svg>
      <dl className="dash-legend">
        {keys.map(key => (
          <div className="dash-legend-row" key={key}>
            <dt><span className={'dash-swatch dash-strip-' + key} data-colour={key} />{key}</dt>
            <dd className="evidence">{orNot(tally[key])}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function captionCount(value: number | null | undefined, noun: string): string {
  return typeof value === 'number' && Number.isFinite(value) ? count(value, noun) : 'not recorded';
}

export function colourChip(colour: string | null | undefined): ReactNode {
  const stated = typeof colour === 'string' ? colour.trim().toLowerCase() : '';
  if (RAMP.includes(stated)) return <span className={'dash-swatch dash-strip-' + stated} data-colour={stated} />;
  return <span className="dash-swatch dash-swatch-empty" />;
}
