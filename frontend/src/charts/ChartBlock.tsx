/* A returned series, drawn. The rules are the ones the vanilla chart renderer was checked against, ported
   rather than rewritten:

   1. only a value the engine returned is drawn — a missing point is a gap in the line, never a zero and never
      an interpolated segment;
   2. every drawn point is reachable by keyboard and names its exact source value and evidence id;
   3. the figure is accompanied by the same numbers as a table, so the picture is never the only copy;
   4. a series with nothing to draw says so instead of rendering an empty frame. */

import { useState } from 'react';
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

export function ChartBlock({ chart, title, unit }: { chart: Chart; title?: string; unit?: string }) {
  const [readout, setReadout] = useState('Select a point to inspect its exact source value. Missing intervals remain gaps.');
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
  const x = (value: number) => 62 + ((value - first) / Math.max(1, last - first)) * 550;
  const y = (value: number) => 215 - ((Number(value) - low) / (high - low)) * 180;

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
    <figure className="card px-3 py-3" data-testid="chart-block">
      <figcaption className="eyebrow">
        {heading}
        {measure ? <span className="quiet"> · {measure}</span> : null}
      </figcaption>
      {drawn.length ? (
        <svg viewBox="0 0 640 270" role="group" aria-label={heading + (measure ? ' in ' + measure : '')} className="mt-2 w-full">
          {[0, 0.5, 1].map(fraction => {
            const value = low + (high - low) * fraction;
            return (
              <g key={'grid-' + fraction}>
                <line x1={62} x2={612} y1={y(value)} y2={y(value)} className="chart-grid" />
                <text x={54} y={y(value) + 4} textAnchor="end" className="chart-axis">{value.toFixed(1)}</text>
              </g>
            );
          })}
          <text x={62} y={22} className="chart-axis">{measure}</text>
          <text x={62} y={245} className="chart-axis">{points[0].label || String(points[0].t || '')}</text>
          <text x={612} y={245} textAnchor="end" className="chart-axis">{points[points.length - 1].label || String(points[points.length - 1].t || '')}</text>
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
