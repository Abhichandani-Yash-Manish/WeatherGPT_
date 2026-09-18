/* The geometry primitives the map figures share: reading coordinates out of a served FeatureCollection,
   turning rings into SVG paths, and fitting one equirectangular box around everything the read returned.

   Extracted from MapSurface when the Today dashboard needed the same figure with a different colour rule,
   so the projection and the point reading exist once. Nothing here draws or colours anything: a surface
   decides what a feature is filled with, and this module only reports what the geometry states. */

export type Position = number[];
export type Geometry = { type?: string; coordinates?: unknown } | null | undefined;
export type Feature = { type?: string; properties?: Record<string, unknown> | null; geometry?: Geometry };
export type Collection = { type?: string; features?: Feature[] };

export function numberAt(point: unknown, index: number): number | null {
  const value = Array.isArray(point) ? point[index] : undefined;
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/* Every position in a nested coordinate array, whatever the geometry type nests. */
export function collectPositions(value: unknown, out: Position[] = []): Position[] {
  if (!Array.isArray(value)) return out;
  if (typeof value[0] === 'number' && typeof value[1] === 'number') { out.push(value as Position); return out; }
  value.forEach(item => collectPositions(item, out));
  return out;
}

/* A ring is drawn as a closed path and a multipolygon's rings are joined into one path per feature. */
export function ringPath(ring: unknown): string {
  const steps: string[] = [];
  (Array.isArray(ring) ? ring : []).forEach(point => {
    const x = numberAt(point, 0); const y = numberAt(point, 1);
    if (x !== null && y !== null) steps.push((steps.length ? 'L' : 'M') + x + ' ' + -y);
  });
  return steps.length > 2 ? steps.join(' ') + ' Z' : '';
}

export function areaPath(geometry: Geometry): string {
  const { type, coordinates } = geometry || {};
  if (!Array.isArray(coordinates)) return '';
  if (type === 'Polygon') return coordinates.map(ringPath).filter(Boolean).join(' ');
  if (type === 'MultiPolygon') return coordinates.map(p => (Array.isArray(p) ? p.map(ringPath).filter(Boolean).join(' ') : '')).filter(Boolean).join(' ');
  return '';
}

export function pointAt(geometry: Geometry): Position[] {
  if (geometry?.type !== 'Point' && geometry?.type !== 'MultiPoint') return [];
  return collectPositions(geometry?.coordinates, []);
}

/* The first stated value among the keys a surface reads; an absent field is null, never a guess. */
export function propertyText(properties: Record<string, unknown> | null | undefined, keys: string[]): string | null {
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

export type FittedView = {
  viewBox: string;
  width: number;
  height: number;
  minX: number;
  minY: number;
  /* the coordinate the map centre names, for zoom transforms and labels */
  centre: { x: number; y: number };
};

/* One equirectangular fit of every position the features carry. A read with no finite coordinate fits a
   unit box, so the frame still exists and the surface states that nothing was drawable. */
export function fitView(collection: Collection | undefined, padding = 0.02): FittedView {
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
  const finite = Number.isFinite(west) && Number.isFinite(north);
  const box = finite
    ? { minX: west, minY: -north, width: east - west || 1, height: north - south || 1 }
    : { minX: -1, minY: -1, width: 2, height: 2 };
  const pad = Math.max(box.width, box.height) * padding;
  const padded = { minX: box.minX - pad, minY: box.minY - pad, width: box.width + pad * 2, height: box.height + pad * 2 };
  return {
    viewBox: [padded.minX, padded.minY, padded.width, padded.height].join(' '),
    width: padded.width,
    height: padded.height,
    minX: padded.minX,
    minY: padded.minY,
    centre: { x: padded.minX + padded.width / 2, y: padded.minY + padded.height / 2 },
  };
}
