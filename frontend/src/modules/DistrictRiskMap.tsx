/* The dashboard's district map: the served district geometry joined to the national warning rows by the
   district key those two reads share.

   Three rules the figure keeps, all of them from the surface design (docs/97):

   1. A district is filled only with the colour its own returned row published for today, and only through
      the token layer's hazard colours. No row, no colour stated, or a colour outside the ramp leaves the
      path as an outline.
   2. The join is a join of two reads at two retrieval times, so the card that renders this states that, and
      a geometry with no matching row is reported as 'not in this read' rather than left ambiguous.
   3. The figure is one tab stop with a keyboard cursor and a live readout, and a real table elsewhere on the
      page carries the same facts for anyone who does not use the figure. No district is in the tab order.

   Zoom is three fixed levels applied as an SVG transform attribute (presentation attributes survive the
   strict CSP; React's style prop writes through the CSSOM and is used only for the measuring cursor). */
import { memo, useCallback, useEffect, useMemo, useState, type KeyboardEvent } from 'react';
import { count } from '../lib/format';
import { areaPath, fitView, propertyText, type Collection, type Position } from './mapFigure';
import { MapTip, type TipState } from './MapTip';

export type MapDay = {
  day?: number; label?: string | null; date_utc?: string | null; date_local?: string | null;
  colour?: string | null; hazards?: string[]; hazard_codes?: number[]; source_text?: string | null;
  quiet?: boolean | null; is_today?: boolean | null; is_past?: boolean | null;
};

export type MapWarningRow = {
  key?: string; district?: string | null; state?: string | null; bulletin_date?: string | null;
  bulletin_age_days?: number | null; days?: MapDay[];
};

type Props = {
  collection?: Collection;
  rows: MapWarningRow[];
  matchKeys?: Set<string> | null;
  colourOnly: boolean;
  dimQuiet: boolean;
  selectedKey?: string | null;
  onSelect?: (key: string) => void;
  /* which of the two reads produced the geometry, stated in the frame when the read failed */
  geometryState?: 'pending' | 'error' | 'ready';
  /* null inspects the day covering today; 1-5 inspects that published day instead. */
  dayIndex?: number | null;
};

export const HAZARD_RAMP = ['red', 'orange', 'yellow', 'green'];
const ZOOM_LEVELS = [1, 2, 4];

type Drawn = {
  key: string; d: string; cx: number; cy: number; name: string; state: string | null;
  colour: string | null; quiet: boolean; today: MapDay | null; row: MapWarningRow | null; matched: boolean;
};

function hazardWording(day: MapDay | null): string {
  if (!day) return 'no published day covering today in this read';
  if (day.source_text) return day.source_text;
  if (day.hazards && day.hazards.length) return day.hazards.join(', ');
  if (day.hazard_codes && day.hazard_codes.length) return 'hazard codes ' + day.hazard_codes.join(', ');
  return 'no hazard wording published';
}

function colourOf(day: MapDay | null, colourOnly: boolean): string | null {
  const stated = day && typeof day.colour === 'string' ? day.colour.trim().toLowerCase() : '';
  if (!colourOnly) return null;
  return HAZARD_RAMP.includes(stated) ? stated : null;
}

/* One path per feature, plus the centre its own coordinates state, so a zoom can hold the selection still. */
function buildPaths(collection: Collection | undefined, rows: MapWarningRow[], matchKeys: Set<string> | null, colourOnly: boolean, dayIndex: number | null): Drawn[] {
  const byKey = new Map<string, MapWarningRow>();
  rows.forEach(row => { if (row.key) byKey.set(row.key, row); });
  const drawn: Drawn[] = [];
  (collection?.features || []).forEach(feature => {
    const d = areaPath(feature?.geometry);
    if (!d) return;
    const key = propertyText(feature?.properties || null, ['k', 'key', 'id']) || ''; 
    const name = propertyText(feature?.properties || null, ['n', 'name', 'district']) || (key || 'name not stated in this read');
    const state = propertyText(feature?.properties || null, ['s', 'state']);
    const positions: Position[] = [];
    const walk = (value: unknown): void => {
      if (Array.isArray(value) && typeof value[0] === 'number' && typeof value[1] === 'number') { positions.push(value as Position); return; }
      if (Array.isArray(value)) value.forEach(walk);
    };
    walk(feature?.geometry?.coordinates);
    let minX = Infinity; let maxX = -Infinity; let minY = Infinity; let maxY = -Infinity;
    positions.forEach(point => {
      const x = point[0]; const y = -point[1];
      minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    });
    const row = byKey.get(key) || null;
    const today = dayIndex === null
      ? (row?.days || []).find(day => day.is_today === true) || null
      : (row?.days || []).find(day => day.day === dayIndex) || null;
    drawn.push({
      key, d, name, state: state || (row && row.state) || null,
      cx: Number.isFinite(minX) ? (minX + maxX) / 2 : 0, cy: Number.isFinite(minY) ? (minY + maxY) / 2 : 0,
      colour: colourOf(today, colourOnly), quiet: Boolean(today && today.quiet), today, row,
      matched: matchKeys ? matchKeys.has(key) : true,
    });
  });
  return drawn;
}

const Paths = memo(function Paths({ paths, selected, cursor, onHover, onPick, onTip }: {
  paths: Drawn[]; selected: string | null; cursor: number;
  onHover: (index: number) => void; onPick: (index: number) => void;
  onTip: (index: number, event: React.MouseEvent) => void;
}) {
  return (
    <>{paths.map((path, index) => {
      const classes = ['district'];
      if (path.colour) classes.push('district-' + path.colour);
      if (!path.colour && path.row && !path.quiet) classes.push('district-stated-not-on-ramp');
      if (!path.matched) classes.push('district-muted');
      else if (path.quiet) classes.push('district-quiet');
      if (path.key && path.key === selected) classes.push('district-selected');
      if (index === cursor) classes.push('district-cursor');
      return (
        <path
          key={path.key || String(index)}
          d={path.d}
          className={classes.join(' ')}
          data-colour={path.colour || undefined}
          data-key={path.key || undefined}
          onMouseEnter={event => { onHover(index); onTip(index, event); }}
          onFocus={() => onHover(index)}
          onClick={() => onPick(index)}
        />
      );
    })}</>
  );
});

export function DistrictRiskMap({ collection, rows, matchKeys = null, colourOnly, dimQuiet, selectedKey = null, onSelect, geometryState = 'ready', dayIndex = null }: Props): JSX.Element {
  const [cursor, setCursor] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [tip, setTip] = useState<TipState>(null);
  const view = useMemo(() => fitView(collection), [collection]);
  const paths = useMemo(
    () => buildPaths(collection, rows, matchKeys, colourOnly, dayIndex),
    [collection, rows, matchKeys, colourOnly, dayIndex]);

  const selectedIndex = useMemo(() => paths.findIndex(path => path.key && path.key === selectedKey), [paths, selectedKey]);
  const active = paths[cursor] || null;
  const matched = paths.filter(path => path.matched).length;
  const coloured = paths.filter(path => path.matched && path.colour).length;

  useEffect(() => { setCursor(0); }, [collection, matchKeys]);
  useEffect(() => { setZoom(1); }, [collection]);

  const move = useCallback((index: number) => {
    if (!paths.length) return;
    setCursor(Math.max(0, Math.min(paths.length - 1, index)));
  }, [paths]);

  const pick = useCallback((index: number) => {
    const path = paths[index];
    if (!path) return;
    setCursor(index);
    setZoom(level => (level === 1 ? 2 : level));
    if (onSelect) onSelect(path.key);
  }, [paths, onSelect]);

  const onHover = useCallback((index: number) => { setCursor(index); }, []);

  /* The tip states what the feature's own row said, in the words the readout uses. It is positioned from the
     pointer event that entered the feature, so hovering 756 districts costs one update per district entered
     and none per pixel moved. */
  const onTip = useCallback((index: number, event: React.MouseEvent) => {
    const path = paths[index];
    if (!path) return;
    const day = path.today;
    const stated = day && typeof day.colour === 'string' ? day.colour.trim().toLowerCase() : '';
    const when = day
      ? (day.label || (day.day !== undefined ? 'day ' + day.day : 'day not stated'))
      : 'no published day in this read';
    setTip({
      x: event.clientX,
      y: event.clientY,
      name: path.name,
      state: path.state,
      colour: HAZARD_RAMP.includes(stated) ? stated : null,
      colourText: day && day.colour ? String(day.colour) : undefined,
      wording: hazardWording(day),
      meta: when + (path.row && path.row.bulletin_date ? ' · edition ' + path.row.bulletin_date : ' · no edition row'),
    });
  }, [paths]);

  const onKeyDown = (event: KeyboardEvent<SVGSVGElement>) => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') { event.preventDefault(); move(cursor + 1); return; }
    if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') { event.preventDefault(); move(cursor - 1); return; }
    if (event.key === 'Home') { event.preventDefault(); move(0); return; }
    if (event.key === 'End') { event.preventDefault(); move(paths.length - 1); return; }
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); pick(cursor); return; }
    if (event.key === 'Escape') { event.preventDefault(); setZoom(1); if (onSelect) onSelect(''); }
  };

  const focus = selectedIndex >= 0 ? paths[selectedIndex] : (active || null);
  const centreX = focus ? focus.cx : view.centre.x;
  const centreY = focus ? focus.cy : view.centre.y;
  const transform = zoom === 1 ? undefined : 'translate(' + centreX + ' ' + centreY + ') scale(' + zoom + ') translate(' + -centreX + ' ' + -centreY + ')';

  const summary = paths.length
    ? 'Schematic of the served district geometry: ' + count(paths.length, 'district') + ' drawn, ' + coloured +
      ' filled with the colour its own returned row published for today, ' + matched + ' matching the current filters.'
    : 'No district geometry was returned by this read, so no figure is drawn.';

  const readout = !paths.length
    ? 'Nothing is drawn, so there is nothing to inspect. The geometry read returned no drawable feature.'
    : !active
      ? 'Move the pointer over the figure, or focus it and use the arrow keys, to inspect a district.'
      : active.name + (active.state ? ', ' + active.state : '') +
        ' — published ' + (dayIndex === null ? 'day covering today' : 'day ' + dayIndex) + ': ' +
          (active.today ? (active.today.label || ('day ' + String(active.today.day))) : 'none in this read') +
        ' · colour as published: ' + (active.today && active.today.colour ? active.today.colour : 'none stated') +
        ' · ' + hazardWording(active.today) +
        (active.row && active.row.bulletin_date ? ' · edition ' + active.row.bulletin_date : '') +
        (active.row ? '' : ' · this district has no warning row in this read, so no colour is drawn') + '.';

  return (
    <div className="dash-map">
      <div className="dash-map-controls">
        <button type="button" className="btn" aria-label="Zoom in" onClick={() => setZoom(level => ZOOM_LEVELS[Math.min(ZOOM_LEVELS.length - 1, ZOOM_LEVELS.indexOf(level) + 1)] || level)}>+</button>
        <button type="button" className="btn" aria-label="Zoom out" onClick={() => setZoom(level => ZOOM_LEVELS[Math.max(0, ZOOM_LEVELS.indexOf(level) - 1)] || level)}>−</button>
        <button type="button" className="btn" aria-label="Reset the map zoom" onClick={() => setZoom(1)}>Reset</button>
        <span className="dash-map-zoom quiet">{'zoom ' + zoom + '×'}</span>
      </div>
      {geometryState === 'pending' ? (
        <div className="dash-map-frame dash-map-skeleton" data-testid="risk-map-pending"><span className="quiet">Reading the district geometry…</span></div>
      ) : geometryState === 'error' ? (
        <div className="dash-map-frame" data-testid="risk-map-error"><span className="quiet">The district geometry read failed, so no figure is drawn. The counts on this page come from the warning read and stand on their own.</span></div>
      ) : (
        <figure className="dash-map-figure">
          <svg
            data-testid="risk-map"
            className="dash-map-svg"
            viewBox={view.viewBox}
            preserveAspectRatio="xMidYMid meet"
            role="img"
            aria-label={summary}
            aria-describedby="risk-map-readout"
            tabIndex={0}
            onKeyDown={onKeyDown}
            onMouseLeave={() => setTip(null)}
          >
            <g transform={transform}>
              <Paths paths={paths} selected={selectedKey} cursor={cursor} onHover={onHover} onPick={pick} onTip={onTip} />
            </g>
          </svg>
          <figcaption className="dash-map-caption">
            A schematic fit of the served district coordinates: not a cartographic basemap and not a warning
            service. Filled only where the district's own returned row published a colour for today.
          </figcaption>
        </figure>
      )}
      <MapTip tip={tip} />
      <p className="module-note dash-map-readout" id="risk-map-readout" role="status" data-testid="risk-map-readout">{readout}</p>
      {dimQuiet ? <p className="module-note">Districts whose published day is quiet are dimmed; their colour is still the colour the product printed.</p> : null}
    </div>
  );
}
