/* The India district warning map, restored from the vanilla map (web/map.js, removed in R6) and rebuilt for React.

   It joins two reads of the same basemap build: the district geometry (/api/map/static/districts, property `k`)
   and the national district warning table (/api/warnings/national, field `key`). The colour is applied at render
   time and never stored in the geometry. Three rules carry over from the vanilla map, and one is tightened:
   - a district is filled only with the colour its own published day stated; a district the warning table does not
     carry is drawn as unmapped and counted, never painted green;
   - the districts are one tab stop with a roving cursor (arrow keys, Home, End), and the readout says in words what
     the pointer or cursor is on;
   - zoom and pan move a transform, and "Find a district" frames the district it matches by name.
   Tightened: the vanilla map offered "day 1…5", but district rows carry different bulletin dates, so the same day
   number named different dates. This map selects a published date, and a district whose bulletin has no row for
   that date is stated as not covered for it. */
import { memo, useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { Failure, HAZARD_COLOURS, Reading } from './Evidence';

type WarningDay = {
  day?: number; date_local?: string; label?: string; colour?: string | null; hazards?: string[];
  source_text?: string; quiet?: boolean; is_today?: boolean;
};
export type WarningRow = {
  key?: string; district?: string; state?: string; bulletin_date?: string; issued_at_utc?: string; days?: WarningDay[];
};
type NationalData = { districts?: WarningRow[]; basemap_build?: string };
type Feature = { properties?: { k?: string; n?: string; s?: string; p?: number } | null; geometry?: { type?: string; coordinates?: unknown } | null };
type Collection = { features?: Feature[] };

const WINDOW = { west: 67.0, east: 98.5, south: 5.0, north: 38.5 };
const WIDTH = 900;
const HEIGHT = 820;
const project = (longitude: number, latitude: number): [number, number] => [
  ((longitude - WINDOW.west) / (WINDOW.east - WINDOW.west)) * WIDTH,
  ((WINDOW.north - latitude) / (WINDOW.north - WINDOW.south)) * HEIGHT,
];

type Shape = { key: string; name: string; state: string; d: string; bounds: [number, number, number, number] | null; placeholder: boolean };

function rings(geometry: Feature['geometry']): number[][][] {
  const coordinates = geometry?.coordinates;
  if (!Array.isArray(coordinates)) return [];
  if (geometry?.type === 'Polygon') return coordinates as number[][][];
  if (geometry?.type === 'MultiPolygon') return (coordinates as number[][][][]).flat();
  return [];
}

/* Any layer of the same basemap build, drawn as thin lines over the districts: the state borders the map already
   carried, and the river sub-basins and coastal zones the vanilla map offered as toggles. */
function linesOf(collection: Collection | undefined): string {
  const parts: string[] = [];
  (collection?.features || []).forEach(feature => rings(feature.geometry).forEach(ring => {
    ring.forEach((point, index) => {
      if (typeof point?.[0] !== 'number' || typeof point?.[1] !== 'number') return;
      const [x, y] = project(point[0], point[1]);
      parts.push((index === 0 ? 'M' : 'L') + x.toFixed(1) + ' ' + y.toFixed(1));
    });
    parts.push('Z');
  }));
  return parts.join('');
}

/* The place layer is points, not rings: each city is drawn where its own coordinates put it. */
function pointsOf(collection: Collection | undefined): { x: number; y: number; name: string }[] {
  return (collection?.features || []).flatMap(feature => {
    const coordinates = feature.geometry?.coordinates;
    if (feature.geometry?.type !== 'Point' || !Array.isArray(coordinates)) return [];
    const [longitude, latitude] = coordinates as number[];
    if (typeof longitude !== 'number' || typeof latitude !== 'number') return [];
    const [x, y] = project(longitude, latitude);
    return [{ x, y, name: feature.properties?.n || '' }];
  });
}

function shapesOf(collection: Collection | undefined): Shape[] {
  return (collection?.features || []).flatMap(feature => {
    const key = feature.properties?.k;
    if (!key) return [];
    let minX = Infinity; let minY = Infinity; let maxX = -Infinity; let maxY = -Infinity;
    const parts: string[] = [];
    rings(feature.geometry).forEach(ring => {
      ring.forEach((point, index) => {
        if (typeof point?.[0] !== 'number' || typeof point?.[1] !== 'number') return;
        const [x, y] = project(point[0], point[1]);
        minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
        parts.push((index === 0 ? 'M' : 'L') + x.toFixed(1) + ' ' + y.toFixed(1));
      });
      parts.push('Z');
    });
    if (parts.length < 2) return [];
    return [{
      key, name: feature.properties?.n || key, state: feature.properties?.s || '', d: parts.join(''),
      bounds: Number.isFinite(minX) ? [minX, minY, maxX, maxY] as [number, number, number, number] : null,
      placeholder: feature.properties?.p === 1,
    }];
  });
}

/** The published dates the table carries, oldest first. */
export function publishedDates(rows: WarningRow[]): string[] {
  const dates = new Set<string>();
  rows.forEach(row => (row.days || []).forEach(day => { if (day.date_local) dates.add(day.date_local); }));
  return Array.from(dates).sort();
}

/** The date a row's own bulletin marked as today, if any row did; otherwise the latest published date. */
export function defaultDate(rows: WarningRow[], dates: string[]): string {
  for (const row of rows) {
    const today = (row.days || []).find(day => day.is_today && day.date_local);
    if (today?.date_local) return today.date_local;
  }
  return dates[dates.length - 1] || '';
}

export type DistrictState = { tone: string; words: string; day: WarningDay | null; row: WarningRow | null };

/** What the map may say about one district on one date, from the table only. */
export function districtState(row: WarningRow | undefined, date: string): DistrictState {
  if (!row) return { tone: 'unmapped', words: 'not in the warning table', day: null, row: null };
  const day = (row.days || []).find(entry => entry.date_local === date) || null;
  if (!day) return { tone: 'uncovered', words: 'no published day for this date in its bulletin (' + orNot(row.bulletin_date) + ')', day: null, row };
  const colour = typeof day.colour === 'string' ? day.colour.toLowerCase() : '';
  const hazard = day.quiet === true ? 'no warning in this product' : day.source_text || (day.hazards || []).join(', ') || 'hazard wording not supplied';
  if (!HAZARD_COLOURS.includes(colour)) return { tone: 'unset', words: 'colour not supplied · ' + hazard, day, row };
  return { tone: colour, words: colour + ' · ' + hazard, day, row };
}

/* The layers a reader may draw over the districts, with the label the vanilla map used. */
const OVERLAYS: [string, string][] = [
  ['states', 'State borders'], ['basins', 'River sub-basins'], ['coast', 'Coastal zones'], ['cities', 'Cities'],
];

const LEGEND: [string, string][] = [
  ['red', 'Red'], ['orange', 'Orange'], ['yellow', 'Yellow'], ['green', 'Green'],
  ['unset', 'Colour not supplied'], ['uncovered', 'No day for this date'], ['unmapped', 'Not in the table'],
];

type CanvasProps = {
  shapes: Shape[]; tones: Record<string, string>; labels: Record<string, string>; cursor: number; found: string | null;
  highlight: string | null; marker: [number, number] | null; markerLabel: string; focusTone: string | null; statesPath: string;
  basinsPath: string; coastPath: string; cities: { x: number; y: number; name: string }[];
  onHover: (index: number) => void; onKey: (event: KeyboardEvent<SVGPathElement>, index: number) => void; onPick: (index: number) => void;
  transform: string; nodes: React.MutableRefObject<(SVGPathElement | null)[]>;
};

/* The 756 paths only re-render when the date, the cursor or the selection changes, never on a readout update. */
const Canvas = memo(function Canvas({ shapes, tones, labels, cursor, found, highlight, marker, markerLabel, focusTone, statesPath, basinsPath, coastPath, cities, onHover, onKey, onPick, transform, nodes }: CanvasProps) {
  return (
    <g transform={transform}>
      {shapes.map((shape, index) => (
        <path
          key={shape.key}
          d={shape.d}
          ref={node => { nodes.current[index] = node; }}
          className={'imap-district' + (shape.placeholder ? ' is-placeholder' : '') + (shape.key === found ? ' is-found' : '') + (shape.key === highlight ? ' is-home' : '') + (focusTone && tones[shape.key] !== focusTone ? ' is-dimmed' : '')}
          data-tone={tones[shape.key]}
          role="button"
          tabIndex={index === cursor ? 0 : -1}
          aria-label={labels[shape.key]}
          onPointerEnter={() => onHover(index)}
          onFocus={() => onHover(index)}
          onKeyDown={event => onKey(event, index)}
          onClick={() => onPick(index)}
        />
      ))}
      {basinsPath ? <path d={basinsPath} className="imap-basins" aria-hidden="true" /> : null}
      {coastPath ? <path d={coastPath} className="imap-coast" aria-hidden="true" /> : null}
      {statesPath ? <path d={statesPath} className="imap-states" aria-hidden="true" /> : null}
      {cities.length ? (
        <g className="imap-cities" aria-hidden="true">
          {cities.map(city => <circle key={city.name + city.x} cx={city.x.toFixed(1)} cy={city.y.toFixed(1)} r={2.4} />)}
        </g>
      ) : null}
      {marker ? (
        <g className="imap-marker" transform={'translate(' + marker[0].toFixed(1) + ' ' + marker[1].toFixed(1) + ')'} role="img" aria-label={markerLabel}>
          <circle r={9} className="imap-marker-halo" />
          <circle r={4} className="imap-marker-dot" />
        </g>
      ) : null}
    </g>
  );
});

export type IndiaWarningMapProps = {
  /** Reads start only when true, so a dashboard can defer the two large reads until the map is near the viewport. */
  active?: boolean;
  /** The working place, drawn as a marker at exactly its coordinates. */
  point?: { latitude: number; longitude: number; label?: string | null } | null;
  /** District and state as a right-now read named them; matched to a table row by exact name, never guessed. */
  home?: { district?: string | null; state?: string | null } | null;
  compact?: boolean;
  /** On the Map surface the district geometry read is the one the layer figure above already states, so its failure is
      referred to rather than announced twice. */
  geometryStatedAbove?: boolean;
};

export function IndiaWarningMap({ active = true, point = null, home = null, compact = false, geometryStatedAbove = false }: IndiaWarningMapProps): JSX.Element {
  const national = useQuery({
    queryKey: ['warnings-national'], enabled: active, retry: false, staleTime: 300_000,
    queryFn: () => getJson<Envelope<NationalData>>('/api/warnings/national'),
  });
  const geometry = useQuery({
    queryKey: ['map-layer', 'districts'], enabled: active, retry: false, staleTime: Infinity,
    queryFn: () => getJson<Collection>('/api/map/static/districts'),
  });
  /* The overlays the vanilla map carried as checkboxes. State borders are on by default; the others are read only
     once a reader turns them on, so nothing large is fetched for a map nobody asked to see in that much detail. */
  const [overlays, setOverlays] = useState<Record<string, boolean>>({ states: true, basins: false, coast: false, cities: false });
  const statesLayer = useQuery({
    queryKey: ['map-layer', 'states'], enabled: active && overlays.states, retry: false, staleTime: Infinity,
    queryFn: () => getJson<Collection>('/api/map/static/states'),
  });
  const basinsLayer = useQuery({
    queryKey: ['map-layer', 'basins'], enabled: active && overlays.basins, retry: false, staleTime: Infinity,
    queryFn: () => getJson<Collection>('/api/map/static/basins'),
  });
  const coastLayer = useQuery({
    queryKey: ['map-layer', 'coast-zones'], enabled: active && overlays.coast, retry: false, staleTime: Infinity,
    queryFn: () => getJson<Collection>('/api/map/static/coast-zones'),
  });
  const citiesLayer = useQuery({
    queryKey: ['map-layer', 'places'], enabled: active && overlays.cities, retry: false, staleTime: Infinity,
    queryFn: () => getJson<Collection>('/api/map/static/places'),
  });
  const basinsPath = useMemo(() => (overlays.basins ? linesOf(basinsLayer.data) : ''), [overlays.basins, basinsLayer.data]);
  const coastPath = useMemo(() => (overlays.coast ? linesOf(coastLayer.data) : ''), [overlays.coast, coastLayer.data]);
  const cities = useMemo(() => (overlays.cities ? pointsOf(citiesLayer.data) : []), [overlays.cities, citiesLayer.data]);
  const statesPath = useMemo(() => (overlays.states ? linesOf(statesLayer.data) : ''), [overlays.states, statesLayer.data]);
  const [focusTone, setFocusTone] = useState<string | null>(null);
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  const frameRef = useRef<HTMLDivElement | null>(null);
  const rows = useMemo(() => national.data?.data?.districts || [], [national.data]);
  const byKey = useMemo(() => new Map(rows.filter(row => row.key).map(row => [row.key as string, row])), [rows]);
  const shapes = useMemo(() => shapesOf(geometry.data), [geometry.data]);
  const dates = useMemo(() => publishedDates(rows), [rows]);
  const [picked, setPicked] = useState('');
  const date = dates.includes(picked) ? picked : defaultDate(rows, dates);
  const [cursor, setCursor] = useState(0);
  const [readout, setReadout] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [found, setFound] = useState<string | null>(null);
  const [find, setFind] = useState('');
  const [view, setView] = useState({ k: 1, x: 0, y: 0 });
  const nodes = useRef<(SVGPathElement | null)[]>([]);
  const drag = useRef<{ x: number; y: number; tx: number; ty: number; moved: boolean } | null>(null);
  const svg = useRef<SVGSVGElement | null>(null);

  const homeKey = useMemo(() => {
    if (!home?.district) return null;
    const district = home.district.trim().toLowerCase();
    const state = (home.state || '').trim().toLowerCase();
    const match = rows.find(row => (row.district || '').toLowerCase() === district && (!state || (row.state || '').toLowerCase() === state));
    return match?.key || null;
  }, [home, rows]);

  const states = useMemo(() => {
    const tones: Record<string, string> = {};
    const labels: Record<string, string> = {};
    const tally: Record<string, number> = {};
    shapes.forEach(shape => {
      const state = districtState(byKey.get(shape.key), date);
      tones[shape.key] = state.tone;
      tally[state.tone] = (tally[state.tone] || 0) + 1;
      labels[shape.key] = shape.name + (shape.state ? ', ' + shape.state : '') + ': ' + state.words +
        (shape.placeholder ? ' (the source supplies a bounding box for this district, not a coastline)' : '');
    });
    return { tones, labels, tally };
  }, [shapes, byKey, date]);

  useEffect(() => { setSelected(null); }, [date]);

  const describe = useCallback((index: number) => {
    const shape = shapes[index];
    if (shape) setReadout(states.labels[shape.key]);
  }, [shapes, states]);

  const frame = useCallback((shape: Shape | undefined) => {
    if (!shape?.bounds) return;
    const [minX, minY, maxX, maxY] = shape.bounds;
    const k = Math.max(1, Math.min(9, WIDTH / Math.max(30, maxX - minX, maxY - minY) / 1.6));
    setView({ k, x: WIDTH / 2 - ((minX + maxX) / 2) * k, y: HEIGHT / 2 - ((minY + maxY) / 2) * k });
  }, []);

  const pick = useCallback((index: number) => {
    if (drag.current?.moved) return;
    const shape = shapes[index];
    if (!shape) return;
    setCursor(index);
    setSelected(shape.key);
    setReadout(states.labels[shape.key]);
  }, [shapes, states]);

  const onKey = useCallback((event: KeyboardEvent<SVGPathElement>, index: number) => {
    const last = shapes.length - 1;
    const move = (next: number) => {
      event.preventDefault();
      const clamped = Math.max(0, Math.min(last, next));
      setCursor(clamped);
      nodes.current[clamped]?.focus();
    };
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') return move(index + 1);
    if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') return move(index - 1);
    if (event.key === 'Home') return move(0);
    if (event.key === 'End') return move(last);
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); pick(index); }
  }, [shapes.length, pick]);

  const zoom = (factor: number) => setView(current => {
    const k = Math.max(0.8, Math.min(12, current.k * factor));
    const ratio = k / current.k;
    return { k, x: WIDTH / 2 - (WIDTH / 2 - current.x) * ratio, y: HEIGHT / 2 - (HEIGHT / 2 - current.y) * ratio };
  });

  const onFind = (value: string) => {
    setFind(value);
    const needle = value.trim().toLowerCase();
    if (needle.length < 2) { setFound(null); return; }
    const index = shapes.findIndex(shape => shape.name.toLowerCase().includes(needle));
    if (index < 0) { setFound(null); setReadout('No district name in the geometry contains “' + value.trim() + '”.'); return; }
    setFound(shapes[index].key);
    setCursor(index);
    frame(shapes[index]);
    setReadout(states.labels[shapes[index].key]);
  };

  const onPointerDown = (event: PointerEvent<SVGSVGElement>) => {
    if (event.button !== 0) return;
    drag.current = { x: event.clientX, y: event.clientY, tx: view.x, ty: view.y, moved: false };
  };
  const onPointerMove = (event: PointerEvent<SVGSVGElement>) => {
    const target = event.target as Element;
    const box = frameRef.current?.getBoundingClientRect();
    const label = target?.getAttribute?.('aria-label');
    if (box && label && target.classList?.contains('imap-district')) setTip({ x: event.clientX - box.left, y: event.clientY - box.top, text: label });
    else setTip(null);
    const start = drag.current;
    if (!start) return;
    const dx = event.clientX - start.x; const dy = event.clientY - start.y;
    if (!start.moved && Math.hypot(dx, dy) < 4) return;
    if (!start.moved) { start.moved = true; svg.current?.setPointerCapture?.(event.pointerId); }
    const scale = WIDTH / (svg.current?.getBoundingClientRect().width || WIDTH);
    setView(current => ({ ...current, x: start.tx + dx * scale, y: start.ty + dy * scale }));
  };
  const onPointerUp = () => { window.setTimeout(() => { drag.current = null; }, 0); };

  /* Ctrl or Cmd with the wheel zooms the map; a plain wheel keeps scrolling the page. */
  useEffect(() => {
    const node = svg.current;
    if (!node) return;
    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      setView(current => {
        const k = Math.max(0.8, Math.min(12, current.k * (event.deltaY < 0 ? 1.15 : 1 / 1.15)));
        const rect = node.getBoundingClientRect();
        const cx = ((event.clientX - rect.left) / (rect.width || 1)) * WIDTH;
        const cy = ((event.clientY - rect.top) / (rect.height || 1)) * HEIGHT;
        const ratio = k / current.k;
        return { k, x: cx - (cx - current.x) * ratio, y: cy - (cy - current.y) * ratio };
      });
    };
    node.addEventListener('wheel', onWheel, { passive: false });
    return () => node.removeEventListener('wheel', onWheel);
  });

  const marker = point ? project(point.longitude, point.latitude) : null;
  const markerLabel = point ? 'Working place ' + orNot(point.label, 'label not recorded') + ' at ' + point.latitude + ', ' + point.longitude : '';
  const selectedState = selected ? districtState(byKey.get(selected), date) : null;
  const selectedShape = selected ? shapes.find(shape => shape.key === selected) : undefined;
  const transform = 'translate(' + view.x.toFixed(1) + ' ' + view.y.toFixed(1) + ') scale(' + view.k.toFixed(3) + ')';
  const cursorIndex = shapes.length ? Math.min(cursor, shapes.length - 1) : 0;
  const homeIndex = homeKey ? shapes.findIndex(shape => shape.key === homeKey) : -1;

  if (!active) return <p className="module-note">The map reads start when this section is near the screen.</p>;
  if (national.isPending || geometry.isPending) return <Reading what="the district warning table and the district geometry" />;
  if (national.isError) return <Failure error={national.error} what="national district warning table" onRetry={() => national.refetch()} />;
  if (geometry.isError && geometryStatedAbove) return <p className="module-note">The district geometry read failed, as the layer figure above states; this map is drawn once that read succeeds.</p>;
  if (geometry.isError) return <Failure error={geometry.error} what="district geometry" onRetry={() => geometry.refetch()} />;

  return (
    <div className={'imap' + (compact ? ' imap-compact' : '')} data-testid="india-warning-map">
      <div className="imap-toolbar">
        <label className="module-field imap-date">
          <span>Published date</span>
          <select value={date} onChange={event => setPicked(event.target.value)} disabled={!dates.length}>
            {dates.length ? dates.map(value => <option key={value} value={value}>{value}</option>) : <option value="">no published date</option>}
          </select>
        </label>
        <label className="module-field imap-find">
          <span>Find a district</span>
          <input type="search" value={find} placeholder="Type a district name" onChange={event => onFind(event.target.value)} />
        </label>
        <div className="imap-zoom" role="group" aria-label="Map view">
          <button type="button" className="btn" aria-label="Zoom out" onClick={() => zoom(1 / 1.35)}>−</button>
          <button type="button" className="btn" aria-label="Zoom in" onClick={() => zoom(1.35)}>+</button>
          {homeIndex >= 0 ? <button type="button" className="btn" onClick={() => { setCursor(homeIndex); frame(shapes[homeIndex]); describe(homeIndex); }}>My district</button> : null}
          <button type="button" className="btn btn-ghost" onClick={() => { setView({ k: 1, x: 0, y: 0 }); setFound(null); setFind(''); }}>Reset</button>
        </div>
        {/* The layer toggles the vanilla map carried. Each one reads its own layer of the same basemap build the first
            time it is turned on, and draws nothing at all when that read returns nothing. */}
        <fieldset className="imap-layers">
          <legend className="sr-only">Layers drawn over the districts</legend>
          {OVERLAYS.map(([key, label]) => (
            <label key={key} className="imap-layer">
              <input type="checkbox" checked={overlays[key]} onChange={event => setOverlays(current => ({ ...current, [key]: event.target.checked }))} />
              <span>{label}</span>
            </label>
          ))}
        </fieldset>
      </div>

      <div className="imap-body">
        <div className="imap-frame" ref={frameRef}>
          <svg
            ref={svg}
            viewBox={'0 0 ' + WIDTH + ' ' + HEIGHT}
            preserveAspectRatio="xMidYMid meet"
            role="group"
            aria-label={'India district warning map for ' + (date || 'no published date') + ': ' + count(shapes.length, 'district polygon') + '. Drag to pan; use the zoom buttons.'}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerLeave={() => { onPointerUp(); setTip(null); }}
          >
            <Canvas
              shapes={shapes} tones={states.tones} labels={states.labels} cursor={cursorIndex} found={found} highlight={homeKey}
              marker={marker} markerLabel={markerLabel} focusTone={focusTone} statesPath={statesPath}
              basinsPath={basinsPath} coastPath={coastPath} cities={cities}
              onHover={describe} onKey={onKey} onPick={pick} transform={transform} nodes={nodes}
            />
          </svg>
          {tip ? <div className="imap-tooltip" style={{ left: tip.x, top: tip.y }} aria-hidden="true">{tip.text}</div> : null}
        </div>

        <div className="imap-side">
          <ul className="imap-legend" aria-label={'District count by published state on ' + (date || 'no date')}>
            {LEGEND.map(([tone, label]) => (
              <li key={tone}>
                <button type="button" aria-pressed={focusTone === tone} onClick={() => setFocusTone(current => (current === tone ? null : tone))}
                  title={'Show only the districts drawn as ' + label.toLowerCase() + '; press again to show all'}>
                  <span className="imap-swatch" data-tone={tone} aria-hidden="true" />
                  <span>{label}</span>
                  <span className="evidence">{states.tally[tone] || 0}</span>
                </button>
              </li>
            ))}
          </ul>
          <p className="imap-readout" role="status" aria-live="polite" data-testid="imap-readout">
            {readout || 'Hover, tap or focus a district to read what its bulletin published for this date.'}
          </p>
          {selectedState?.row ? (
            <div className="imap-selected">
              <p className="eyebrow">Selected district</p>
              <p className="imap-selected-name">{orNot(selectedState.row.district)}{selectedState.row.state ? ', ' + selectedState.row.state : ''}</p>
              <p className="module-note">
                Bulletin {orNot(selectedState.row.bulletin_date)} · issued {selectedState.row.issued_at_utc ? istStamp(selectedState.row.issued_at_utc) : 'time not recorded'}
              </p>
              <ul className="imap-days">
                {(selectedState.row.days || []).map(day => {
                  const tone = districtState(selectedState.row as WarningRow, day.date_local || '').tone;
                  return (
                    <li key={(day.date_local || '') + day.day} className={day.date_local === date ? 'is-current' : undefined}>
                      <span className="imap-swatch" data-tone={tone} aria-hidden="true" />
                      <span className="evidence">{orNot(day.date_local)}</span>
                      <span>{orNot(day.colour, 'colour not supplied')}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : selectedShape ? (
            <p className="module-note">{selectedShape.name}: not in the warning table, so no published day is shown.</p>
          ) : null}
        </div>
      </div>

      <p className="module-note">
        {count(shapes.length, 'district polygon')} from basemap {orNot(national.data?.data?.basemap_build)} · {count(rows.length, 'warning row')} ·
        colours exactly as each district bulletin published them for the chosen date. A district the table does not carry is drawn
        neutral and counted, never painted green. Keyboard: Tab reaches the map, arrow keys move between districts, Home and End
        jump, Enter selects.
      </p>
    </div>
  );
}
