/* Map: the layers the manifest says this machine can draw, and one of them drawn from the served
   FeatureCollection. The figure is a schematic fit of the returned coordinates: not a cartographic
   basemap, not a location map and not a warning service, and a feature is filled only with a colour
   its own properties stated. Absence is stated: no colour means an outline, a field the manifest did
   not state is "not recorded", and the table beside the figure is the accessible equivalent.

   The readout beside the figure states what is under the pointer or the keyboard cursor in words, from
   the feature's own properties only: the name, the colour as published and the hazard wording as
   published, or the absence of each. The drawn features act as one tab stop that the arrow keys, Home
   and End move, so the figure is not pointer-only. A place feature that states its own name and its own
   coordinates can be made the working place, and the surface reads /api/now for exactly those
   coordinates; nothing is ever inferred from a coordinate. */
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope, NowReading } from '../api/types';
import { count, orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import { Button } from '../ui/kit';
import {
  ColourTag, DataTable, Failure, Facts, HAZARD_COLOURS, Limits, NO_ROW, NOT_RECORDED, Reading, Sources,
  SurfaceShell,
} from './Evidence';

export const intents: string[] = (viewById('map')?.intents ?? []).concat([
  'Which layers can this machine draw, and what does the served geometry state about them?',
]);

type WarningDayPayload = { day?: number; label?: string | null; date_utc?: string | null; date_local?: string | null; colour?: string | null; hazards?: string[]; hazard_codes?: number[]; source_text?: string | null; quiet?: boolean | null; is_today?: boolean | null; is_past?: boolean | null };
type WarningRowPayload = { key?: string; district?: string | null; state?: string | null; bulletin_date?: string | null; bulletin_age_days?: number | null; days?: WarningDayPayload[] };
type WarningPayload = { districts?: WarningRowPayload[]; newest_bulletin_date_in_this_read?: string | null; bulletin_date?: string | null; tally?: Record<string, number> };

type LayerRow = { name?: string; file?: string; kind?: string; bytes?: number; budget_bytes?: number | null };
type LayersData = { build_id?: string; layers?: LayerRow[]; join_file?: string; attribution?: string;
  district_polygons?: number; skipped_without_a_name?: number };
import { areaPath, fitView, numberAt, pointAt, propertyText, type Collection, type Position } from './mapFigure';
import type { MapDay, MapWarningRow } from './DistrictRiskMap';
import { MapTip, type TipState } from './MapTip';
import { DistrictInspector } from './DistrictInspector';

type ChosenPlace = { label: string; latitude: number; longitude: number };

/* The property names read from a feature's own properties; a layer that uses none of them is shown as
   "not recorded" rather than guessed at from a list this surface keeps. */
const NAME_KEYS = ['n', 'name', 'district', 'district_name', 'label', 'title'];
const STATE_KEYS = ['s', 'state', 'state_name', 'admin1', 'a'];
const WORDING_KEYS = ['hazards', 'hazard', 'wording', 'hazard_wording', 'status_line', 'source_text', 'headline'];
const COLOUR_KEYS = ['colour', 'color', 'hazard_colour', 'hazard_color', 'warning_colour', 'warning_color', 'fill'];

type Shape = {
  key: number; d?: string; at?: Position; colour: string | null; describe: string;
  place: ChosenPlace | null;
  /* what the shape is, for the inspector and the hover tip */
  name: string | null; state: string | null; published: string | null; wording: string | null;
  drawnAs: string; joinKey: string | null; cx: number; cy: number;
};
type Plan = { viewBox: string; radius: number; shapes: Shape[]; rows: ReactNode[][]; drawn: number; coloured: number; centreX: number; centreY: number };

/* The join the districts layer needs: its own geometry states a key, a name and a state, and the warning
   product states the colour, the hazard wording and the edition for that key. Without this join a district
   layer can only ever be outlines, which is exactly what this surface used to draw for the one layer that
   carries the warning colours. */
type JoinOptions = { rows: MapWarningRow[]; dayIndex: number | null; colourOnly: boolean; join: boolean };

function dayForRow(row: MapWarningRow | null, dayIndex: number | null): MapDay | null {
  if (!row) return null;
  const days = row.days || [];
  if (dayIndex === null) return days.find(day => day.is_today === true) || null;
  return days.find(day => day.day === dayIndex) || null;
}

function joinedWording(day: MapDay | null, fallback: string | null): string | null {
  if (day) {
    if (day.source_text) return day.source_text;
    if (day.hazards && day.hazards.length) return day.hazards.join(', ');
    if (day.hazard_codes && day.hazard_codes.length) return 'hazard codes ' + day.hazard_codes.join(', ');
    if (day.quiet === true) return 'no hazard published in this product for this day';
  }
  return fallback;
}

/* The sentence the readout states for an area: its own name and state, the colour it published and the
   hazard wording it published, with the absence of either stated as absence. */
function areaDescription(name: string | null, state: string | null, published: string | null, wording: string | null, placeholder: boolean): string {
  const where = (name || 'name not stated in these properties') + (state ? ', ' + state : '');
  const colour = published || 'colour not supplied';
  const hazard = wording || 'no hazard wording published in these properties';
  const box = placeholder ? ' (the source supplies a bounding box for this feature, not a coastline)' : '';
  return where + ': ' + colour + ' \u00b7 ' + hazard + box;
}

/* The sentence the readout states for a point: its own name and its own geometry coordinates. A point
   that states no name is not offered as a working place, because a working place is never guessed from
   its coordinates. */
function placeDescription(name: string | null, state: string | null, latitude: number | null, longitude: number | null): string {
  const label = name ? (state ? name + ', ' + state : name) : 'place name not stated in these properties';
  const coordinates = latitude === null || longitude === null ? 'coordinates not stated in these properties' : latitude + ', ' + longitude;
  if (!name || latitude === null || longitude === null) {
    const missing = !name && (latitude === null || longitude === null) ? 'no name and no coordinates of its own'
      : !name ? 'no name of its own' : 'no coordinates of its own';
    return 'Point ' + label + ' \u00b7 ' + coordinates + ' \u00b7 this feature states ' + missing + ', so it cannot be made the working place';
  }
  return 'Place ' + label + ' \u00b7 ' + coordinates + ' \u00b7 select it to make it the working place';
}

function drawNote(drawable: boolean, ramp: string | null, published: string | null): string {
  if (!drawable) return 'not drawn: this surface draws the served polygons and points only';
  if (ramp) return 'filled with the stated ' + ramp;
  return published ? 'outline only: the stated colour \u201c' + published + '\u201d is not one of the hazard colours this workspace draws'
    : 'outline only: no colour stated in these properties';
}

function drawPlan(collection: Collection | undefined, options?: JoinOptions): Plan {
  const features = collection?.features || [];
  const join = options?.join ? options : null;
  const byKey = new Map<string, MapWarningRow>();
  (join?.rows || []).forEach(row => { if (row.key) byKey.set(row.key, row); });
  /* The projection now lives in mapFigure, shared with the Today dashboard's map, so one read has one fit. */
  const view = fitView(collection);
  const radius = Math.max(view.width, view.height) / 200;
  const shapes: Shape[] = [];
  const rows: ReactNode[][] = [];
  let drawn = 0; let coloured = 0;
  features.forEach((feature, index) => {
    const properties = feature?.properties || null;
    const name = propertyText(properties, NAME_KEYS);
    const state = propertyText(properties, STATE_KEYS);
    const ownWording = propertyText(properties, WORDING_KEYS);
    const ownColour = propertyText(properties, COLOUR_KEYS);
    const joinKey = propertyText(properties, ['k', 'key', 'id']);
    const row = join && joinKey ? byKey.get(joinKey) || null : null;
    const day = dayForRow(row, join ? join.dayIndex : null);
    const published = (day && day.colour ? String(day.colour) : null) || ownColour;
    const wording = joinedWording(day, ownWording);
    const stated = published ? published.trim().toLowerCase() : '';
    const ramp = published && HAZARD_COLOURS.includes(stated) ? stated : null;
    const placeholder = properties?.p === 1;
    const d = areaPath(feature?.geometry);
    const points = pointAt(feature?.geometry);
    const drawable = Boolean(d) || points.length > 0;
    if (drawable) {
      drawn += 1;
      if (ramp) coloured += 1;
      if (d) {
        shapes.push({
          key: index, d, colour: ramp, place: null,
          describe: areaDescription(name, state, published, wording, placeholder),
          name, state, published: published || null, wording: wording || null,
          drawnAs: drawNote(drawable, ramp, published), joinKey: joinKey || null,
          cx: centroidX(feature?.geometry), cy: centroidY(feature?.geometry),
        });
      }
      points.forEach((at, order) => {
        const latitude = numberAt(at, 1); const longitude = numberAt(at, 0);
        const location = latitude !== null && longitude !== null ? { latitude, longitude } : null;
        const stated = name && location ? (state ? name + ', ' + state : name) : null;
        shapes.push({
          key: index * 1000 + order, at, colour: ramp,
          place: stated && location ? { label: stated, ...location } : null,
          describe: placeDescription(name, state, latitude, longitude),
          name, state, published: published || null, wording: wording || null,
          drawnAs: drawNote(drawable, ramp, published), joinKey: joinKey || null,
          cx: at[0], cy: at[1],
        });
      });
    }
    rows.push([
      orNot(name, 'name not stated in these properties'), orNot(state),
      <ColourTag key="colour" colour={ramp || published} text={published || undefined} />,
      wording || 'no hazard wording published in these properties',
      drawNote(drawable, ramp, published) + (row ? ' · joined to the warning row for this key' : ''),
    ]);
  });
  return { viewBox: view.viewBox, radius, shapes, rows, drawn, coloured, centreX: view.centre.x, centreY: view.centre.y };
}

/* The centre of a feature's own coordinates: used to hold a zoomed selection still. */
function walkPositions(value: unknown, into: Position[]): void {
  if (Array.isArray(value) && typeof value[0] === 'number' && typeof value[1] === 'number') { into.push(value as Position); return; }
  if (Array.isArray(value)) value.forEach(entry => walkPositions(entry, into));
}

function boundsOf(geometry: { coordinates?: unknown } | null | undefined): { cx: number; cy: number } | null {
  if (!geometry) return null;
  const positions: Position[] = [];
  walkPositions(geometry.coordinates, positions);
  if (!positions.length) return null;
  let minX = Infinity; let maxX = -Infinity; let minY = Infinity; let maxY = -Infinity;
  positions.forEach(point => {
    const x = point[0]; const y = -point[1];
    minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
  });
  if (!Number.isFinite(minX)) return null;
  return { cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 };
}

function centroidX(geometry: { coordinates?: unknown } | null | undefined): number {
  const bounds = boundsOf(geometry);
  return bounds ? bounds.cx : 0;
}

function centroidY(geometry: { coordinates?: unknown } | null | undefined): number {
  const bounds = boundsOf(geometry);
  return bounds ? bounds.cy : 0;
}

/* The id a feature is selected by: its own join key when it states one, so the inspector can look up the
   warning row the feature belongs to, and its position in the draw pass otherwise. */
function shapeId(shape: { joinKey: string | null; key: number }): string {
  return shape.joinKey || String(shape.key);
}

function layerKey(layer: LayerRow): string {
  return orNot(layer.name, orNot(layer.file, 'unnamed layer'));
}

function figureCount(plan: Plan): string {
  if (!plan.drawn) return 'The read returned no feature with drawable coordinates, so no figure is drawn.';
  const outlines = plan.drawn - plan.coloured;
  if (!plan.coloured) return 'This figure drew ' + count(plan.drawn, 'feature') + ' from the chosen layer. No feature carried a colour, so every feature is drawn as an outline.';
  if (!outlines) return 'This figure drew ' + count(plan.drawn, 'feature') + ' from the chosen layer, and every one stated a hazard colour.';
  return 'This figure drew ' + count(plan.drawn, 'feature') + ' from the chosen layer: ' + count(plan.coloured, 'feature') +
    ' stated a hazard colour; ' + count(outlines, 'feature') + ' did not and ' + (outlines === 1 ? 'is' : 'are') + ' drawn as an outline.';
}

export function Surface(): JSX.Element {
  const [picked, setPicked] = useState('');
  const [cursor, setCursor] = useState(0);
  const [readout, setReadout] = useState('');
  const [zoom, setZoom] = useState(1);
  const [find, setFind] = useState('');
  const [place, setPlace] = useState<ChosenPlace | null>(null);
  const [colourOnly, setColourOnly] = useState(true);
  const [dayPick, setDayPick] = useState('today');
  const [selected, setSelected] = useState('');
  const [tip, setTip] = useState<TipState>(null);
  const shapeNodes = useRef<(SVGPathElement | SVGCircleElement | null)[]>([]);
  const layers = useQuery({ queryKey: ['map-layers'], queryFn: () => getJson<Envelope<LayersData>>('/api/map/layers'), retry: false });
  const listed = layers.data?.data?.layers || [];

  /* The layer the surface opens on. A district layer is the one that can carry the warning colours once it is
     joined to the warning product, so it is chosen ahead of the alphabetical first layer; every other layer
     stays one selection away. This is stated in the note under the selector, not left implicit. */
  const preferred = useMemo(() => {
    const districts = listed.find(row => /district/i.test(row.name || row.file || ''));
    return districts ? layerKey(districts) : listed.length ? layerKey(listed[0]) : '';
  }, [listed]);
  const chosen = listed.some(row => layerKey(row) === picked) ? picked : preferred;
  const districtLayer = /district/i.test(chosen || '');
  const layer = useQuery({ queryKey: ['map-layer', chosen], enabled: Boolean(chosen), retry: false,
    queryFn: () => getJson<Collection>('/api/map/static/' + encodeURIComponent(chosen)) });

  /* The warning rows the district layer is joined to. The key is the same one the Today surface uses, so the
     1.65 MB read is shared between the two surfaces rather than fetched twice. A layer whose geometry states
     its own colours needs no join, and no join is attempted for it. */
  const warnings = useQuery({
    queryKey: ['warnings-national'],
    queryFn: () => getJson<Envelope<WarningPayload>>('/api/warnings/national'),
    enabled: districtLayer,
    staleTime: 120_000,
  });
  const rows: MapWarningRow[] = useMemo(() => (warnings.data?.data?.districts || []).map(row => ({
    key: row.key, district: row.district, state: row.state,
    bulletin_date: row.bulletin_date, bulletin_age_days: row.bulletin_age_days,
    days: (row.days || []) as MapDay[],
  })), [warnings.data]);

  const dayIndex = dayPick === 'today' ? null : Number(dayPick);
  const join = Boolean(districtLayer && rows.length);
  const plan = useMemo(
    () => drawPlan(layer.data, { rows, dayIndex, colourOnly, join }),
    [layer.data, rows, dayIndex, colourOnly, join]);
  const manifest = layers.data?.data;

  /* The chosen place is exactly the point the chosen city feature states: the name from its properties and
     the coordinates from its geometry. The reading is GET /api/now for those coordinates. */
  const now = useQuery({
    queryKey: ['map-now', place?.latitude, place?.longitude],
    queryFn: () => getJson<Envelope<NowReading>>(withQuery('/api/now', { lat: place?.latitude, lon: place?.longitude })),
    enabled: place !== null,
    retry: false,
  });
  const reading = now.data?.data;
  const station = reading?.observed?.stations?.[0];
  const inForce = reading?.in_force;

  useEffect(() => {
    setCursor(0);
    setReadout('');
    shapeNodes.current = [];
  }, [chosen]);

  const cursorIndex = plan.shapes.length ? Math.min(cursor, plan.shapes.length - 1) : 0;

  /* What the tip states: the feature's own name and state, the colour its row published and the hazard wording
     as printed, with the edition it came from. Every field is what the read returned. */
  const tipFor = (shape: Shape, event: React.MouseEvent): TipState => ({
    x: event.clientX,
    y: event.clientY,
    name: shape.name || 'name not stated in these properties',
    state: shape.state,
    colour: shape.colour,
    colourText: shape.published || undefined,
    wording: shape.wording || 'no hazard wording published in these properties',
    meta: shape.drawnAs,
  });


  const moveCursor = (index: number) => {
    if (!plan.shapes.length) return;
    const next = Math.max(0, Math.min(plan.shapes.length - 1, index));
    setCursor(next);
    setReadout(plan.shapes[next].describe);
    shapeNodes.current[next]?.focus?.();
  };

  const choosePlace = (target: ChosenPlace) => {
    setPlace(target);
    setReadout('Working place set to ' + target.label + ' at the coordinates the vendored geometry carries (' + target.latitude + ', ' + target.longitude + ').');
  };

  const selectedShape = plan.shapes.find(shape => shapeId(shape) === selected) || null;

  const onShapeKey = (event: KeyboardEvent<SVGElement>, index: number) => {
    const key = event.key;
    if (key === 'ArrowRight' || key === 'ArrowDown') { event.preventDefault(); moveCursor(index + 1); return; }
    if (key === 'ArrowLeft' || key === 'ArrowUp') { event.preventDefault(); moveCursor(index - 1); return; }
    if (key === 'Home') { event.preventDefault(); moveCursor(0); return; }
    if (key === 'End') { event.preventDefault(); moveCursor(plan.shapes.length - 1); return; }
    const target = plan.shapes[index]?.place;
    if ((key === 'Enter' || key === ' ') && target) { event.preventDefault(); choosePlace(target); }
  };

  return (
    <SurfaceShell
      title="Map"
      lead="The published warning picture drawn for one layer, with the table beside it as the accessible equivalent. The figure is a schematic fit of the coordinates that read returned."
      what="the map layer manifest"
      envelope={layers.data}
      busy={layers.isPending}
      error={layers.error}
      onRetry={() => layers.refetch()}
      intents={intents}
    >
      <section className="module-section">
        <h2>The figure</h2>
        <p className="module-note">
          This is a schematic drawn from the served feature geometries: it is not a cartographic basemap, not a location map and not a warning service. The projection is a plain equirectangular fit of the coordinates this read returned, not a map projection.
        </p>
        {!listed.length ? <p className="module-note">This read returned no layer, so there is nothing to choose and nothing to draw.</p> : (
          <label className="module-field" htmlFor="map-layer">
            <span>Layer to draw</span>
            <select id="map-layer" value={chosen} onChange={event => setPicked(event.target.value)}>
              {listed.map(row => <option key={layerKey(row)} value={layerKey(row)}>{layerKey(row)}{row.kind ? ' · ' + row.kind : ''}</option>)}
            </select>
          </label>
        )}
        <p className="module-note" role="status" data-testid="map-count">
          {!chosen ? 'No layer is chosen, so no layer read was requested.'
            : layer.isPending ? 'Reading the chosen layer from the local store…'
              : layer.isError ? 'The chosen layer read failed; that failure is stated below.' : figureCount(plan)}
        </p>
        {!chosen ? null : layer.isError ? (
          <Failure error={layer.error} what="chosen map layer" onRetry={() => layer.refetch()} />
        ) : (
          <>
            <div className="flex flex-wrap items-start gap-4">
              {plan.drawn ? (
                <figure className="glass-soft m-0 flex min-w-0 flex-[1_1_28rem] flex-col p-3">
                  <svg data-testid="map-figure" role="group" viewBox={plan.viewBox} preserveAspectRatio="xMidYMid meet"
                    aria-label={'Schematic of the ' + chosen + ' layer: ' + count(plan.drawn, 'feature') + ' drawn from the served coordinates. Not a cartographic basemap.'}
                    className="h-auto w-full max-w-[46rem] dash-map-ink">
                    <g transform={zoom === 1 ? undefined : 'translate(' + plan.centreX + ' ' + plan.centreY + ') scale(' + zoom + ') translate(' + -plan.centreX + ' ' + -plan.centreY + ')'}>
                    {plan.shapes.map((shape, index) => shape.d ? (
                      <path
                        key={shape.key}
                        d={shape.d}
                        ref={node => { shapeNodes.current[index] = node; }}
                        className={(shape.colour ? 'district district-' + shape.colour : 'district') + (selected === shapeId(shape) ? ' district-selected' : '')}
                        data-colour={shape.colour || undefined}
                        tabIndex={index === cursorIndex ? 0 : -1}
                        role="img"
                        aria-label={shape.describe}
                        fill={shape.colour ? 'currentColor' : 'none'}
                        stroke="currentColor"
                        strokeWidth={0.5}
                        onMouseEnter={event => { setReadout(shape.describe); setTip(tipFor(shape, event)); }}
                        onMouseLeave={() => setTip(null)}
                        onFocus={() => { setCursor(index); setReadout(shape.describe); }}
                        onKeyDown={event => onShapeKey(event, index)}
                        onClick={() => setSelected(shapeId(shape))}
                      />
                    ) : shape.at ? (
                      <circle
                        key={shape.key}
                        cx={shape.at[0]}
                        cy={-shape.at[1]}
                        r={plan.radius}
                        ref={node => { shapeNodes.current[index] = node; }}
                        tabIndex={index === cursorIndex ? 0 : -1}
                        role={shape.place ? 'button' : 'img'}
                        aria-label={shape.describe}
                        fill={shape.colour ? 'currentColor' : 'none'}
                        stroke="currentColor"
                        strokeWidth={plan.radius / 3}
                        onMouseEnter={event => { setReadout(shape.describe); setTip(tipFor(shape, event)); }}
                        onMouseLeave={() => setTip(null)}
                        onFocus={() => { setCursor(index); setReadout(shape.describe); }}
                        onKeyDown={event => onShapeKey(event, index)}
                        onClick={() => {
                          setSelected(shapeId(shape));
                          if (shape.place) choosePlace(shape.place as ChosenPlace);
                        }}
                      />
                    ) : null)}
                  </g>
                  </svg>
                  {/* Controls sit outside the figure element: the figure's own circles are the drawn
                      features, and a control's icon must not be counted among them. */}
                  <div className="order-first mb-2 flex flex-wrap items-center gap-2">
                    <Button size="sm" aria-label="Zoom in" onClick={() => setZoom(2)}>+</Button>
                    <Button size="sm" aria-label="Zoom out" onClick={() => setZoom(1)}>-</Button>
                    <span className="pill pill-quiet">zoom {zoom}x</span>
                    {join ? (
                      <>
                        <label className="flex items-center gap-2 text-[12px] quiet" htmlFor="map-day">
                          Day to inspect
                          <select
                            id="map-day"
                            value={dayPick}
                            onChange={event => setDayPick(event.target.value)}
                            className="rounded-full border border-glass-line bg-glass-2 px-2 py-1 text-[12px] text-ink"
                          >
                            <option value="today">the day covering today</option>
                            {[1, 2, 3, 4, 5].map(day => <option key={day} value={day}>{'day ' + day}</option>)}
                          </select>
                        </label>
                        <label className="dash-toggle">
                          <input type="checkbox" checked={colourOnly} onChange={event => setColourOnly(event.target.checked)} />
                          <span>Colour only where published</span>
                        </label>
                      </>
                    ) : null}
                    <label className="ml-auto flex items-center gap-2 text-[12px] quiet" htmlFor="map-find">
                      Find a feature
                      <input
                        id="map-find"
                        type="search"
                        value={find}
                        placeholder="e.g. Patna"
                        className="rounded-full border border-glass-line bg-glass-2 px-2.5 py-1 text-[12px] text-ink"
                        onChange={event => {
                          const value = event.target.value;
                          setFind(value);
                          const needle = value.trim().toLowerCase();
                          if (needle.length < 2) return;
                          const index = plan.shapes.findIndex(shape => shape.describe.toLowerCase().includes(needle));
                          if (index >= 0) moveCursor(index);
                        }}
                      />
                    </label>
                  </div>
                  {/* The legend is built from what the draw pass actually drew, not from the ramp: a colour
                      with no feature is not shown, and the outline count is stated. */}
                  <ul className="mt-2 flex flex-wrap items-center gap-3" aria-label="Legend of the drawn features">
                    {HAZARD_COLOURS.map(colour => {
                      const shown = plan.shapes.filter(shape => shape.colour === colour).length;
                      if (!shown) return null;
                      return (
                        <li key={colour} className="flex items-center gap-2 text-[12px]">
                          <ColourTag colour={colour} text={colour} />
                          <span className="quiet evidence">{shown}</span>
                        </li>
                      );
                    })}
                    <li className="flex items-center gap-2 text-[12px]">
                      <ColourTag colour={null} text="outline only" />
                      <span className="quiet evidence">{plan.drawn - plan.coloured}</span>
                    </li>
                  </ul>
                  <figcaption className="module-note">
                    Drawn from the served coordinates of the {chosen} layer. A feature is filled only with a colour its own properties stated,
                    and only when that colour is in the product's hazard ramp ({HAZARD_COLOURS.join(', ')}); every other feature is an outline.
                  </figcaption>
                </figure>
              ) : null}
              <MapTip tip={tip} />
              <div className="dash-map-side min-w-0 flex-[1_1_20rem]">
                {join ? (
                  <DistrictInspector
                    rows={rows}
                    selectedKey={selected}
                    dayIndex={dayIndex}
                    statePick=""
                    onSelect={setSelected}
                    onState={() => undefined}
                    askHref={question => '#/assistant?ask=' + encodeURIComponent(question)}
                    warningsHref={district => district ? '#/warnings?district=' + encodeURIComponent(district) : '#/warnings'}
                  />
                ) : null}
                {/* A layer that carries no warning rows still gets a real panel: the selected feature's own
                    properties, the layer's own provenance, and a count of what was drawn. */}
                <section className="glass-soft inspector p-3" data-testid="map-inspector">
                  <div className="inspector-head">
                    <div className="min-w-0">
                      <p className="eyebrow m-0">Layer inspector</p>
                      <h3 className="inspector-title mt-1">{chosen || 'no layer chosen'}</h3>
                      <p className="module-note m-0">
                        {plan.drawn
                          ? count(plan.drawn, 'feature') + ' drawn: ' + count(plan.coloured, 'feature') + ' carried a published colour, '
                            + count(plan.drawn - plan.coloured, 'feature') + ' ' + (plan.drawn - plan.coloured === 1 ? 'is' : 'are') + ' an outline.'
                          : 'No feature with drawable coordinates came back for this layer.'}
                        {districtLayer
                          ? (rows.length
                              ? ' Filled from the warning rows this read returned, joined by district key.'
                              : warnings.isPending
                                ? ' Reading the warning rows this layer is joined to…'
                                : warnings.isError
                                  ? ' The warning rows read failed, so this layer is drawn as outlines.'
                                  : ' The warning read returned no row to join.')
                          : ' This layer states its own properties; it carries no warning rows, so the colour column is what its own fields say.'}
                      </p>
                    </div>
                  </div>
                  {selectedShape ? (
                    <dl className="module-facts glass-soft overflow-hidden" data-testid="map-feature-detail">
                      <div className="fact-row"><dt className="module-fact-label">Feature</dt><dd className="fact-value">{selectedShape.name || 'name not stated in these properties'}</dd></div>
                      <div className="fact-row"><dt className="module-fact-label">State</dt><dd className="fact-value">{selectedShape.state || 'state not stated in these properties'}</dd></div>
                      <div className="fact-row"><dt className="module-fact-label">Colour as published</dt><dd className="fact-value">
                        <ColourTag colour={selectedShape.colour} text={selectedShape.published || 'colour not stated'} />
                      </dd></div>
                      <div className="fact-row"><dt className="module-fact-label">Hazard wording</dt><dd className="fact-value">{selectedShape.wording || 'no hazard wording published in these properties'}</dd></div>
                      <div className="fact-row"><dt className="module-fact-label">Drawn as</dt><dd className="fact-value">{selectedShape.drawnAs}</dd></div>
                      <div className="fact-row"><dt className="module-fact-label">Join key</dt><dd className="fact-value evidence">{selectedShape.joinKey || 'no key stated in these properties'}</dd></div>
                    </dl>
                  ) : (
                    <p className="module-note m-0">
                      Select a feature on the figure, with the pointer or with the keyboard, to read its own
                      properties here. Nothing is guessed for a feature that states none of them.
                    </p>
                  )}
                  <p className="module-note m-0" data-testid="map-attribution">
                    {orNot(manifest?.attribution, 'Attribution not stated in this read')} Build {orNot(manifest?.build_id)}.
                  </p>
                </section>
              </div>
            </div>
            {/* The accessible equivalent stays on the page, collapsed: the table is the same read the figure draws. */}
            <details className="mt-2">
              <summary className="cursor-pointer text-[12px] quiet">
                The table behind the figure ({plan.drawn ? count(plan.drawn, 'row') : 'no rows'})
              </summary>
              <div className="mt-2">
                <DataTable testId="map-features"
                  caption="Every feature this read returned, as the layer states it: name, state, colour as published, hazard wording as published, and how the figure drew it."
                  columns={['Feature', 'State', 'Colour as published', 'Hazard wording as published', 'Drawn as']}
                  rows={plan.rows} />
              </div>
            </details>
            {plan.drawn ? (
              <>
                <p className="module-note" role="status" aria-live="polite" data-testid="map-readout">
                  {readout || 'Hover or focus a drawn feature to read out what the payload states about it.'}
                </p>
                <p className="module-note">
                  Keyboard: Tab reaches the figure, the arrow keys move between the drawn features of the chosen layer, Home and End jump to
                  the first and last, and Enter makes the focused place the working place when that feature states its own name and coordinates.
                </p>
              </>
            ) : null}
          </>
        )}
      </section>

      {/* The layer manifest, folded and below the figure. Measured 21 September 2026 on the captured first
          screen (light-map@1440): the surface opened on a table of file names, byte counts and byte budgets —
          a build manifest, read out to a reader who came to see which districts are under a warning. It is
          the read's own evidence and every row of it is still here, under the answer instead of in front of
          the question. */}
      <details className="module-meaning">
        <summary>The layers this machine can draw, and the files they came from</summary>
        <p className="module-note" data-testid="map-manifest">Build {orNot(manifest?.build_id)}, join file {orNot(manifest?.join_file)}; district polygons written {orNot(manifest?.district_polygons)}. Attribution as returned: {orNot(manifest?.attribution)}</p>
        <DataTable testId="map-layers"
          caption="One row per layer the manifest returned. A field the manifest did not state is shown as not recorded, never filled in from a list this surface keeps."
          columns={['Layer', 'Kind as stated', 'File', 'Bytes as returned', 'Budget bytes as returned']}
          rows={listed.map(row => [orNot(row.name, 'name not stated in this row'), orNot(row.kind), orNot(row.file), orNot(row.bytes), orNot(row.budget_bytes)])} />
      </details>

      {place ? (
        <section className="module-section">
          <h2>Right now at the place chosen on the map</h2>
          <p className="module-note">
            The working place was set from the name that feature states and the coordinates its vendored geometry carries; nothing was
            inferred from a coordinate. The reading below is GET /api/now for exactly that point.
          </p>
          <Facts testId="map-chosen-place" rows={[['Place read', place.label], ['Coordinates', place.latitude + ', ' + place.longitude]]} />
          {now.isPending ? (
            <Reading what="the right-now reading for the chosen place" />
          ) : now.isError ? (
            <Failure error={now.error} what="right-now reading for the chosen place" onRetry={() => now.refetch()} />
          ) : (
            <>
              <p className="reading" data-testid="map-now-summary">{orNot(reading?.summary, NO_ROW)}</p>
              <Facts testId="map-now-station" rows={[
                ['Point the route read', reading?.point ? reading.point.latitude + ', ' + reading.point.longitude : NOT_RECORDED],
                ['Freshest station', station ? orNot(station.name || station.station_code) : NO_ROW],
                ['Distance', typeof station?.distance_km === 'number' ? station.distance_km + ' km' : NOT_RECORDED],
                ['Observed at', station?.observed_at_utc ? istStamp(station.observed_at_utc) : NOT_RECORDED],
                ['Age at retrieval', typeof station?.age_minutes === 'number' ? station.age_minutes + ' minutes before retrieval' : NOT_RECORDED],
                ['Staleness', station?.stale === true ? 'stale: the report is older than the layer\u2019s freshness window'
                  : station?.stale === false ? 'current' : 'staleness not recorded'],
              ]} />
              {inForce && (inForce.district || inForce.status_line) ? (
                <p>
                  <ColourTag colour={inForce.colour} text={inForce.colour || 'colour not stated'} />{' '}
                  <span className="reading">{orNot(inForce.status_line, NO_ROW)}</span>
                </p>
              ) : (
                <p className="module-note">
                  No district-day row was returned for this point. {NO_ROW}: a point outside every district polygon of the warning product
                  carries no district guidance.
                </p>
              )}
              <Limits
                limitations={Array.from(new Set([...(reading?.limitations || []), ...(now.data?.limitations || [])]))}
                not_established={Array.from(new Set([...(reading?.not_established || []), ...(now.data?.not_established || [])]))}
              />
              <Sources sources={now.data?.sources} />
            </>
          )}
        </section>
      ) : null}
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
