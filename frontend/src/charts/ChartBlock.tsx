/* A returned series, drawn. The rules are the ones the vanilla chart renderer was checked against, ported
   rather than rewritten:

   1. only a value the engine returned is drawn — a missing point is a gap in the line, never a zero and never
      an interpolated segment;
   2. every drawn point is reachable by keyboard and names its exact source value and evidence id;
   3. the figure is accompanied by the same numbers as a table, so the picture is never the only copy;
   4. a series with nothing to draw says so instead of rendering an empty frame. */

import { useId, useState } from 'react';
import type { Chart } from '../api/types';
import './charts.css';
import { orNot } from '../lib/format';

type Point = { t?: string; label?: string; value?: number | string | null; v?: number | string | null; evidence_id?: string; x?: number; year?: number };

function pointsOf(chart: Chart): Point[] {
  const raw = (chart.points || []) as unknown as Point[];
  return raw.map(point => ({
    ...point,
    value: point.value === undefined ? point.v ?? null : point.value,
    label: point.label ?? point.t ?? (point.year === undefined ? undefined : String(point.year)),
  }));
}

function axisOf(point: Point, index: number): number {
  if (typeof point.x === 'number') return point.x;
  const parsed = Date.parse(String(point.t ?? ''));
  if (Number.isFinite(parsed)) return parsed;
  if (typeof point.year === 'number') return point.year;
  return index;
}

/* The panel variant is the dashboard reference's chart container: a sentence-case title with a muted window beside it and a
   shorter plot. It draws the same points with the same rules. */
export function ChartBlock({ chart, title, unit, variant, subtitle, tone }: { chart: Chart; title?: string; unit?: string; variant?: 'panel'; subtitle?: string; tone?: 'rain' }) {
  const panel = variant === 'panel';
  const H = panel ? 262 : 300;
  /* The drawing box is wider for a full-width figure. A 640-unit box stretched to about 1100px scaled its points,
     strokes and axis text by 1.7, which is why the card charts read as oversized; a wider box draws the same figure
     close to its intended size. The panel variant keeps the reference dashboard's box. */
  const W = panel ? 640 : 980;
  const RIGHT = W - 28;
  const [readout, setReadout] = useState('Select a point to inspect its exact source value. Missing intervals remain gaps.');
  const gradient = 'chart-fill-' + useId().replace(/:/g, '');
  const points = pointsOf(chart);
  const drawn = points.filter(point => point.value !== null && point.value !== undefined && Number.isFinite(Number(point.value)));
  const heading = title || chart.title || 'Retrieved series';
  const measure = unit || chart.unit || '';
  const axisLabel = String(chart.axis_label || 'Point');

  if (!points.length) {
    return (
      <figure className="card px-3 py-3" data-testid="chart-empty">
        <figcaption className="eyebrow">{heading}</figcaption>
        <p className="mt-1 text-sm text-ink-soft">The engine returned this series with no points at all. Nothing is drawn: an empty frame would read as a measurement of zero.</p>
      </figure>
    );
  }

  const xs = points.map(axisOf);
  const first = Math.min(...xs);
  const last = Math.max(...xs);
  let low = drawn.length ? Math.min(...drawn.map(point => Number(point.value))) : 0;
  let high = drawn.length ? Math.max(...drawn.map(point => Number(point.value))) : 1;
  // A rainfall axis starts at zero, and a flat series must not divide by zero.
  if (measure === 'mm') low = Math.min(0, low);
  if (high === low) {
    low -= 1;
    high += 1;
  }
  const x = (value: number) => 62 + ((value - first) / Math.max(1, last - first)) * (RIGHT - 62);
  const y = (value: number) => H - 55 - ((Number(value) - low) / (high - low)) * (H - 90);

  const segments: string[][] = [];
  let current: string[] = [];
  points.forEach((point, index) => {
    if (point.value === null || point.value === undefined || !Number.isFinite(Number(point.value))) {
      if (current.length > 1) segments.push(current);
      current = [];
      return;
    }
    current.push(x(axisOf(point, index)).toFixed(1) + ',' + y(Number(point.value)).toFixed(1));
  });
  if (current.length > 1) segments.push(current);

  return (
    <figure className={panel ? 'chart-panel' + (tone === 'rain' ? ' chart-rain' : '') : 'card px-3 py-3'} data-testid="chart-block">
      <figcaption className={panel ? 'chart-panel-title' : 'eyebrow'}>
        {heading}
        {panel && subtitle ? <span className="chart-panel-sub"> ({subtitle})</span> : null}
        {!panel && measure ? <span className="quiet"> · {measure}</span> : null}
      </figcaption>
      {drawn.length ? (
        <svg viewBox={'0 0 ' + W + ' ' + H} role="group" aria-label={heading + (measure ? ' in ' + measure : '')} className="mt-2 w-full">
          {[0, 0.5, 1].map(fraction => {
            const value = low + (high - low) * fraction;
            return (
              <g key={'grid-' + fraction}>
                <line x1={62} x2={RIGHT} y1={y(value)} y2={y(value)} className="chart-grid" />
                <text x={54} y={y(value) + 4} textAnchor="end" className="chart-axis">{value.toFixed(1)}</text>
              </g>
            );
          })}
          <text x={62} y={22} className="chart-axis">{measure}</text>
          <text x={62} y={H - 25} className="chart-axis">{points[0].label || String(points[0].t || '')}</text>
          <text x={RIGHT} y={H - 25} textAnchor="end" className="chart-axis">{points[points.length - 1].label || String(points[points.length - 1].t || '')}</text>
          <defs>
            <linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" className="chart-fill-top" />
              <stop offset="100%" className="chart-fill-bottom" />
            </linearGradient>
          </defs>
          {/* The area sits only under a returned segment and closes to the axis at that segment's own ends, so a gap in
              the series stays an empty gap in the fill as well. */}
          {segments.map(segment => {
            const firstX = segment[0].split(',')[0];
            const lastX = segment[segment.length - 1].split(',')[0];
            return <polygon key={'area-' + segment[0]} points={firstX + ',' + (H - 55) + ' ' + segment.join(' ') + ' ' + lastX + ',' + (H - 55)} fill={'url(#' + gradient + ')'} className="chart-area" aria-hidden="true" />;
          })}
          {segments.map(segment => (
            <polyline key={segment[0]} points={segment.join(' ')} fill="none" className="chart-series" />
          ))}
          {points.map((point, index) => {
            if (point.value === null || point.value === undefined || !Number.isFinite(Number(point.value))) return null;
            const label = point.label || String(point.t || '');
            const text = label + ': ' + String(point.value) + (measure ? ' ' + measure : '') + (point.evidence_id ? ' · ' + point.evidence_id : ' · no evidence id');
            return (
              <circle
                key={label + index}
                cx={x(axisOf(point, index))}
                cy={y(Number(point.value))}
                r={4.5}
                tabIndex={0}
                role="button"
                aria-label={text}
                className="chart-point"
                onFocus={() => setReadout(text)}
                onMouseEnter={() => setReadout(text)}
                onClick={() => setReadout(text)}
                onKeyDown={event => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    setReadout(text);
                  }
                }}
              />
            );
          })}
        </svg>
      ) : (
        <p className="mt-2 text-sm text-ink-soft">
          Every point in this series is missing, so nothing is drawn. A line or a zero here would be a
          measurement the engine did not return.
        </p>
      )}
      <p className="mt-1 text-xs text-ink-soft" aria-live="polite">{readout}</p>
      <details className="mt-2">
        <summary className="cursor-pointer text-xs font-semibold text-ink-soft">View exact values and evidence IDs</summary>
        <table className="mt-2 w-full text-left text-xs">
          <caption className="sr-only">{heading} as a table, with the evidence id of every point</caption>
          <thead>
            <tr>
              <th scope="col" className="quiet">{axisLabel}</th>
              <th scope="col" className="quiet">Value{measure ? ' (' + measure + ')' : ''}</th>
              <th scope="col" className="quiet">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {points.map((point, index) => (
              <tr key={'row-' + index}>
                <td>{orNot(point.label ?? point.t ?? point.year, 'point not stated')}</td>
                <td className="evidence">{point.value === null || point.value === undefined ? 'Missing' : String(point.value)}</td>
                <td className="evidence">{orNot(point.evidence_id, 'no evidence id')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
