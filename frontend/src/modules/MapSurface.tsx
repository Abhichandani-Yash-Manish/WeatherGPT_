/* Map: the layers the manifest says this machine can draw, and one of them drawn from the served
   FeatureCollection. The figure is a schematic fit of the returned coordinates: not a cartographic
   basemap, not a location map and not a warning service, and a feature is filled only with a colour
   its own properties stated. Absence is stated: no colour means an outline, a field the manifest did
   not state is "not recorded", and the table beside the figure is the accessible equivalent. */
import { useMemo, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { viewById } from '../shell/views';
import { ColourTag, DataTable, Failure, HAZARD_COLOURS, SurfaceShell } from './Evidence';

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

type Shape = { key: number; d?: string; at?: Position; colour: string | null };
type Plan = { viewBox: string; radius: number; shapes: Shape[]; rows: ReactNode[][]; drawn: number; coloured: number };

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
    const d = areaPath(feature?.geometry);
    const points = pointAt(feature?.geometry);
    const drawable = Boolean(d) || points.length > 0;
    if (drawable) {
      drawn += 1;
      if (ramp) coloured += 1;
      if (d) shapes.push({ key: index, d, colour: ramp });
      points.forEach((at, order) => shapes.push({ key: index * 1000 + order, at, colour: ramp }));
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
  const layers = useQuery({ queryKey: ['map-layers'], queryFn: () => getJson<Envelope<LayersData>>('/api/map/layers'), retry: false });
  const listed = layers.data?.data?.layers || [];
  const chosen = listed.some(row => layerKey(row) === picked) ? picked : listed.length ? layerKey(listed[0]) : '';
  const layer = useQuery({ queryKey: ['map-layer', chosen], enabled: Boolean(chosen), retry: false,
    queryFn: () => getJson<Collection>('/api/map/static/' + encodeURIComponent(chosen)) });
  const plan = useMemo(() => drawPlan(layer.data), [layer.data]);
  const manifest = layers.data?.data;

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
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-4)', alignItems: 'flex-start' }}>
            {plan.drawn ? (
              <figure style={{ flex: '1 1 24rem', minWidth: 0 }}>
                <svg data-testid="map-figure" role="img" viewBox={plan.viewBox} preserveAspectRatio="xMidYMid meet"
                  aria-label={'Schematic of the ' + chosen + ' layer: ' + count(plan.drawn, 'feature') + ' drawn from the served coordinates. Not a cartographic basemap.'}
                  style={{ width: '100%', height: 'auto', maxWidth: '36rem' }}>
                  {plan.shapes.map(shape => shape.d ? (
                    <path key={shape.key} d={shape.d} className={shape.colour ? 'chip-colour' : undefined} data-colour={shape.colour || undefined}
                      fill={shape.colour ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={0.5} />
                  ) : shape.at ? (
                    <circle key={shape.key} cx={shape.at[0]} cy={-shape.at[1]} r={plan.radius} className={shape.colour ? 'chip-colour' : undefined}
                      data-colour={shape.colour || undefined} fill={shape.colour ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={plan.radius / 3} />
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
        )}
      </section>
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
