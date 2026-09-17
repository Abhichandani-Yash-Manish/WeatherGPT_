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
import {
  ColourTag, DataTable, Failure, Facts, HAZARD_COLOURS, Limits, NO_ROW, NOT_RECORDED, Reading, Sources,
  SurfaceShell,
} from './Evidence';

export const intents: string[] = (viewById('map')?.intents ?? []).concat([
  'Which layers can this machine draw, and what does the served geometry state about them?',
]);

type LayerRow = { name?: string; file?: string; kind?: string; bytes?: number; budget_bytes?: number | null };
type LayersData = { build_id?: string; layers?: LayerRow[]; join_file?: string; attribution?: string;
  district_polygons?: number; skipped_without_a_name?: number };
type Position = number[];
type Geometry = { type?: string; coordinates?: unknown } | null | undefined;
type Feature = { type?: string; properties?: Record<string, unknown> | null; geometry?: Geometry };
type Collection = { type?: string; features?: Feature[] };
type ChosenPlace = { label: string; latitude: number; longitude: number };

/* The property names read from a feature's own properties; a layer that uses none of them is shown as
   "not recorded" rather than guessed at from a list this surface keeps. */
const NAME_KEYS = ['n', 'name', 'district', 'district_name', 'label', 'title'];
const STATE_KEYS = ['s', 'state', 'state_name', 'admin1', 'a'];
const WORDING_KEYS = ['hazards', 'hazard', 'wording', 'hazard_wording', 'status_line', 'source_text', 'headline'];
const COLOUR_KEYS = ['colour', 'color', 'hazard_colour', 'hazard_color', 'warning_colour', 'warning_color', 'fill'];

function numberAt(point: unknown, index: number): number | null {
  const value = Array.isArray(point) ? point[index] : undefined;
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function collectPositions(value: unknown, out: Position[]): void {
  if (!Array.isArray(value)) return;
  if (typeof value[0] === 'number' && typeof value[1] === 'number') { out.push(value as Position); return; }
  value.forEach(item => collectPositions(item, out));
}

/* A ring is drawn as a closed path and a multipolygon's rings are joined into one path per feature. */
function ringPath(ring: unknown): string {
  const steps: string[] = [];
  (Array.isArray(ring) ? ring : []).forEach(point => {
    const x = numberAt(point, 0); const y = numberAt(point, 1);
    if (x !== null && y !== null) steps.push((steps.length ? 'L' : 'M') + x + ' ' + -y);
  });
  return steps.length > 2 ? steps.join(' ') + ' Z' : '';
}

function areaPath(geometry: Geometry): string {
  const { type, coordinates } = geometry || {};
  if (!Array.isArray(coordinates)) return '';
  if (type === 'Polygon') return coordinates.map(ringPath).filter(Boolean).join(' ');
  if (type === 'MultiPolygon') return coordinates.map(p => (Array.isArray(p) ? p.map(ringPath).filter(Boolean).join(' ') : '')).filter(Boolean).join(' ');
  return '';
}

function pointAt(geometry: Geometry): Position[] {
  if (geometry?.type !== 'Point' && geometry?.type !== 'MultiPoint') return [];
  const out: Position[] = [];
  collectPositions(geometry?.coordinates, out);
  return out;
}

function propertyText(properties: Record<string, unknown> | null | undefined, keys: string[]): string | null {
  if (!properties) return null;
  for (const key of keys) {
    const value = properties[key];
    if (typeof value === 'string' && value.trim()) return value.trim();
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
    const words = Array.isArray(value) ? value.filter(item => typeof item === 'string' && item.trim()) as string[] : [];
    if (words.length) return words.join(', ');
  }
  return null;
}

type Shape = { key: number; d?: string; at?: Position; colour: string | null; describe: string; place: ChosenPlace | null };
type Plan = { viewBox: string; radius: number; shapes: Shape[]; rows: ReactNode[][]; drawn: number; coloured: number };

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

function drawPlan(collection: Collection | undefined): Plan {
  const features = collection?.features || [];
  const everything: Position[] = [];
  features.forEach(feature => { if (feature?.geometry) collectPositions(feature.geometry.coordinates, everything); });
  let west = Infinity; let east = -Infinity; let south = Infinity; let north = -Infinity;
  everything.forEach(point => {
    const x = numberAt(point, 0); const y = numberAt(point, 1);
    if (x === null || y === null) return;
    west = Math.min(west, x); east = Math.max(east, x);
    south = Math.min(south, y); north = Math.max(north, y);
  });
  const box = Number.isFinite(west) && Number.isFinite(north)
    ? { minX: west, minY: -north, width: east - west || 1, height: north - south || 1 }
    : { minX: -1, minY: -1, width: 2, height: 2 };
  const radius = Math.max(box.width, box.height) / 200;
  const shapes: Shape[] = [];
  const rows: ReactNode[][] = [];
  let drawn = 0; let coloured = 0;
  features.forEach((feature, index) => {
    const properties = feature?.properties || null;
    const name = propertyText(properties, NAME_KEYS);
    const state = propertyText(properties, STATE_KEYS);
    const wording = propertyText(properties, WORDING_KEYS);
    const published = propertyText(properties, COLOUR_KEYS);
    const ramp = published && HAZARD_COLOURS.includes(published.toLowerCase()) ? published.toLowerCase() : null;
    const placeholder = properties?.p === 1;
    const d = areaPath(feature?.geometry);
    const points = pointAt(feature?.geometry);
    const drawable = Boolean(d) || points.length > 0;
    if (drawable) {
      drawn += 1;
      if (ramp) coloured += 1;
      if (d) shapes.push({ key: index, d, colour: ramp, place: null, describe: areaDescription(name, state, published, wording, placeholder) });
      points.forEach((at, order) => {
        const latitude = numberAt(at, 1); const longitude = numberAt(at, 0);
        const location = latitude !== null && longitude !== null ? { latitude, longitude } : null;
        const stated = name && location ? (state ? name + ', ' + state : name) : null;
        shapes.push({
          key: index * 1000 + order, at, colour: ramp,
          place: stated && location ? { label: stated, ...location } : null,
          describe: placeDescription(name, state, latitude, longitude),
        });
      });
    }
    rows.push([
      orNot(name, 'name not stated in these properties'), orNot(state),
      <ColourTag key="colour" colour={ramp || published} text={published || undefined} />,
      wording || 'no hazard wording published in these properties', drawNote(drawable, ramp, published),
    ]);
  });
  return { viewBox: [box.minX, box.minY, box.width, box.height].join(' '), radius, shapes, rows, drawn, coloured };
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
  const [place, setPlace] = useState<ChosenPlace | null>(null);
  const shapeNodes = useRef<(SVGPathElement | SVGCircleElement | null)[]>([]);
  const layers = useQuery({ queryKey: ['map-layers'], queryFn: () => getJson<Envelope<LayersData>>('/api/map/layers'), retry: false });
  const listed = layers.data?.data?.layers || [];
  const chosen = listed.some(row => layerKey(row) === picked) ? picked : listed.length ? layerKey(listed[0]) : '';
  const layer = useQuery({ queryKey: ['map-layer', chosen], enabled: Boolean(chosen), retry: false,
    queryFn: () => getJson<Collection>('/api/map/static/' + encodeURIComponent(chosen)) });
  const plan = useMemo(() => drawPlan(layer.data), [layer.data]);
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
      lead="The layers this machine can draw, and one of them drawn from the served feature geometry. The figure is a schematic fit of the coordinates that read returned; the table beside it is the accessible equivalent."
      what="the map layer manifest"
      envelope={layers.data}
      busy={layers.isPending}
      error={layers.error}
      onRetry={() => layers.refetch()}
    >
      <section className="module-section">
        <h2>The layers this machine can draw</h2>
        <p className="module-note" data-testid="map-manifest">Build {orNot(manifest?.build_id)}, join file {orNot(manifest?.join_file)}; district polygons written {orNot(manifest?.district_polygons)}. Attribution as returned: {orNot(manifest?.attribution)}</p>
        <DataTable testId="map-layers"
          caption="One row per layer the manifest returned. A field the manifest did not state is shown as not recorded, never filled in from a list this surface keeps."
          columns={['Layer', 'Kind as stated', 'File', 'Bytes as returned', 'Budget bytes as returned']}
          rows={listed.map(row => [orNot(row.name, 'name not stated in this row'), orNot(row.kind), orNot(row.file), orNot(row.bytes), orNot(row.budget_bytes)])} />
      </section>

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
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-4)', alignItems: 'flex-start' }}>
              {plan.drawn ? (
                <figure style={{ flex: '1 1 24rem', minWidth: 0 }}>
                  <svg data-testid="map-figure" role="group" viewBox={plan.viewBox} preserveAspectRatio="xMidYMid meet"
                    aria-label={'Schematic of the ' + chosen + ' layer: ' + count(plan.drawn, 'feature') + ' drawn from the served coordinates. Not a cartographic basemap.'}
                    style={{ width: '100%', height: 'auto', maxWidth: '36rem' }}>
                    {plan.shapes.map((shape, index) => shape.d ? (
                      <path
                        key={shape.key}
                        d={shape.d}
                        ref={node => { shapeNodes.current[index] = node; }}
                        tabIndex={index === cursorIndex ? 0 : -1}
                        role="img"
                        aria-label={shape.describe}
                        className={shape.colour ? 'chip-colour' : undefined}
                        data-colour={shape.colour || undefined}
                        fill={shape.colour ? 'currentColor' : 'none'}
                        stroke="currentColor"
                        strokeWidth={0.5}
                        onMouseEnter={() => setReadout(shape.describe)}
                        onFocus={() => { setCursor(index); setReadout(shape.describe); }}
                        onKeyDown={event => onShapeKey(event, index)}
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
                        className={shape.colour ? 'chip-colour' : undefined}
                        data-colour={shape.colour || undefined}
                        fill={shape.colour ? 'currentColor' : 'none'}
                        stroke="currentColor"
                        strokeWidth={plan.radius / 3}
                        onMouseEnter={() => setReadout(shape.describe)}
                        onFocus={() => { setCursor(index); setReadout(shape.describe); }}
                        onKeyDown={event => onShapeKey(event, index)}
                        onClick={shape.place ? () => choosePlace(shape.place as ChosenPlace) : undefined}
                      />
                    ) : null)}
                  </svg>
                  <figcaption className="module-note">
                    Drawn from the served coordinates of the {chosen} layer. A feature is filled only with a colour its own properties stated,
                    and only when that colour is in the product's hazard ramp ({HAZARD_COLOURS.join(', ')}); every other feature is an outline.
                  </figcaption>
                </figure>
              ) : null}
              <div style={{ flex: '1 1 24rem', minWidth: 0 }}>
                <DataTable testId="map-features"
                  caption="Every feature this read returned, as the layer states it: name, state, colour as published, hazard wording as published, and how the figure drew it."
                  columns={['Feature', 'State', 'Colour as published', 'Hazard wording as published', 'Drawn as']}
                  rows={plan.rows} />
              </div>
            </div>
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
