/* The field.
   ============================================================================
   The background the user kept: an aurora of the hour, quantised through an ordered dither so it carries a
   fine grain instead of a smooth ramp, and faded out by the middle of the page so the conversation owns the
   lower half. It is drawn small — a few hundred cells wide — and scaled up with image-rendering: pixelated,
   which is what gives the grain its even, printed quality rather than a blurry gradient.

   The dither is not decoration for its own sake: a large dark gradient bands badly on a projector, and an
   ordered dither is the oldest correct fix for that. It also happens to look like the thing the user chose.

   Nothing here is a weather statement. The hour sets the palette; that is all. */

export type Hour = 'daybreak' | 'noon' | 'golden' | 'night';

/* Each hour is a stack of stops down the field, plus two wide blooms that give it an aurora's drift.
   Read off the capture the user chose: a violet-mauve body over a blue-grey base, going black at the foot. */
import { phaseOf, solarPosition } from '../flagship/solar';

const FIELDS: Record<Hour, { stops: [number, string][]; blooms: [number, number, number, string][] }> = {
  night: {
    stops: [[0, '#080b14'], [0.30, '#151a2c'], [0.52, '#2a3350'], [0.68, '#3b3f5c'], [0.82, '#22263a'], [1, '#0a0c12']],
    blooms: [[0.68, 0.34, 0.62, 'rgba(120, 136, 190, 0.26)'], [0.26, 0.52, 0.54, 'rgba(78, 92, 150, 0.2)']],
  },
  daybreak: {
    stops: [[0, '#2f4a7a'], [0.26, '#6d7fae'], [0.46, '#b18c9c'], [0.62, '#e8b48a'], [0.78, '#dcc3a2'], [0.92, '#c9b295'], [1, '#b3a088']],
    blooms: [[0.30, 0.40, 0.60, 'rgba(248, 200, 150, 0.34)'], [0.74, 0.28, 0.52, 'rgba(140, 158, 214, 0.24)']],
  },
  /* Midday is the bright one: a saturated azure at the top falling to a warm sand at the foot, the way the
     chosen capture reads. The dark hours keep their own body; the day does not borrow it. */
  noon: {
    stops: [[0, '#4d8ada'], [0.30, '#79aae6'], [0.52, '#a8c9ec'], [0.68, '#d5e2ef'], [0.80, '#e6dac2'], [0.92, '#d2c0a0'], [1, '#bfae93']],
    blooms: [[0.66, 0.26, 0.62, 'rgba(255, 240, 210, 0.34)'], [0.22, 0.44, 0.52, 'rgba(120, 168, 232, 0.26)']],
  },
  golden: {
    stops: [[0, '#2a2350'], [0.26, '#5b3f6e'], [0.46, '#9a5f77'], [0.60, '#c8836a'], [0.72, '#e0a06f'], [0.86, '#6b5a6e'], [1, '#241f30']],
    blooms: [[0.64, 0.34, 0.62, 'rgba(232, 150, 96, 0.34)'], [0.26, 0.30, 0.52, 'rgba(140, 108, 178, 0.26)']],
  },
};

/* An 8 × 8 ordered (Bayer) matrix, normalised to 0..1. The classic recursive construction. */
const BAYER = (() => {
  const n = 8;
  const m: number[][] = [[0]];
  for (let size = 1; size < n; size *= 2) {
    const next: number[][] = [];
    for (let y = 0; y < size * 2; y += 1) {
      next[y] = [];
      for (let x = 0; x < size * 2; x += 1) {
        const q = m[y % size][x % size] * 4;
        next[y][x] = q + (y < size ? (x < size ? 0 : 2) : (x < size ? 3 : 1));
      }
    }
    m.length = 0;
    next.forEach(row => m.push(row));
  }
  const max = n * n;
  return m.map(row => row.map(v => v / max));
})();

function rgbOf(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function rampAt(stops: [number, string][], t: number): [number, number, number] {
  let lower = stops[0];
  let upper = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i += 1) {
    if (t >= stops[i][0] && t <= stops[i + 1][0]) {
      lower = stops[i];
      upper = stops[i + 1];
      break;
    }
  }
  const span = upper[0] - lower[0] || 1;
  const k = Math.min(1, Math.max(0, (t - lower[0]) / span));
  const a = rgbOf(lower[1]);
  const b = rgbOf(upper[1]);
  return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
}

export type FieldOptions = {
  hour: Hour;
  /** Cells across. The capture that set this design measured well at ~620. */
  cells?: number;
  /** Quantisation steps per channel. Seven reads as grain; sixteen reads as a smooth ramp. */
  levels?: number;
  /** How much of the dither to apply. 1 is a hard posterise; 0.55 keeps the ramp and adds the grain. */
  amplitude?: number;
  /** Drift, 0..1, for the blooms. One slow pass makes the aurora breathe without ever looping visibly. */
  drift?: number;
};

/** Paint one frame of the field into a canvas. The canvas is small; CSS scales it up. */
export function paintField(canvas: HTMLCanvasElement, options: FieldOptions): void {
  const { hour, cells = 620, levels = 10, amplitude = 0.42, drift = 0 } = options;
  const spec = FIELDS[hour] || FIELDS.night;
  const w = cells;
  const h = Math.round(cells * 0.56);
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
  const ctx = canvas.getContext('2d', { alpha: false });
  if (!ctx) return;
  const image = ctx.createImageData(w, h);
  const data = image.data;
  const step = 255 / (levels - 1);
  const wobble = Math.sin(drift * Math.PI * 2);

  for (let y = 0; y < h; y += 1) {
    const t = y / (h - 1);
    const base = rampAt(spec.stops, t);
    for (let x = 0; x < w; x += 1) {
      let r = base[0];
      let g = base[1];
      let b = base[2];

      /* The blooms: wide, soft, and slowly displaced, which is the whole of the motion. */
      for (const [bx, by, radius, colour] of spec.blooms) {
        const dx = (x / w - (bx + wobble * 0.03)) / radius;
        const dy = (y / h - by) / (radius * 0.72);
        const d = dx * dx + dy * dy;
        if (d >= 1) continue;
        const falloff = (1 - d) * (1 - d);
        const parts = colour.match(/[\d.]+/g);
        if (!parts) continue;
        const alpha = Number(parts[3] ?? 1) * falloff;
        r += (Number(parts[0]) - r) * alpha;
        g += (Number(parts[1]) - g) * alpha;
        b += (Number(parts[2]) - b) * alpha;
      }

      /* The ordered dither: nudge by the cell's threshold, then snap to the level grid. */
      const threshold = (BAYER[y & 7][x & 7] - 0.5) * step * amplitude;
      const index = (y * w + x) * 4;
      data[index] = Math.max(0, Math.min(255, Math.round((r + threshold) / step) * step));
      data[index + 1] = Math.max(0, Math.min(255, Math.round((g + threshold) / step) * step));
      data[index + 2] = Math.max(0, Math.min(255, Math.round((b + threshold) / step) * step));
      data[index + 3] = 255;
    }
  }
  ctx.putImageData(image, 0, 0);
}

/** Which field the hour gets. Astronomy decides, never a reading. */
export function hourOf(at: Date, latitude = 23.0, longitude = 82.5): Hour {
  /* The phase comes from the sun itself now — altitude and azimuth from the reader's own place and hour, the
     equation of time included — rather than from a bucket on the clock. A place at 8°N and a place at 34°N no
     longer light identically, and the palettes are the four phases of the sky (docs/110, "the sky is the
     interface"). The Hour names are kept because four palettes already carry them. */
  const phase = phaseOf(solarPosition(latitude, longitude, at));
  return phase === 'night' ? 'night' : phase === 'dawn' ? 'daybreak' : phase === 'day' ? 'noon' : 'golden';
}
