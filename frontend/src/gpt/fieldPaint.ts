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
const FIELDS: Record<Hour, { stops: [number, string][]; blooms: [number, number, number, string][] }> = {
  night: {
    stops: [[0, '#0c0f1a'], [0.30, '#231f33'], [0.50, '#56496a'], [0.64, '#786a86'], [0.78, '#4d566e'], [1, '#0b0d10']],
    blooms: [[0.68, 0.36, 0.62, 'rgba(150,130,168,0.34)'], [0.26, 0.54, 0.54, 'rgba(96,112,160,0.24)']],
  },
  daybreak: {
    stops: [[0, '#121a30'], [0.28, '#3d4068'], [0.48, '#836d80'], [0.62, '#ad8272'], [0.78, '#6a6c85'], [1, '#0b0d10']],
    blooms: [[0.30, 0.44, 0.60, 'rgba(226,168,126,0.30)'], [0.74, 0.30, 0.52, 'rgba(126,146,206,0.22)']],
  },
  noon: {
    stops: [[0, '#0d1528'], [0.30, '#1f3560'], [0.50, '#3f5d92'], [0.64, '#6480a8'], [0.78, '#4c5a78'], [1, '#0b0d10']],
    blooms: [[0.62, 0.28, 0.60, 'rgba(130,168,224,0.30)'], [0.20, 0.50, 0.50, 'rgba(80,114,182,0.20)']],
  },
  golden: {
    stops: [[0, '#111530'], [0.28, '#3f2e52'], [0.48, '#7e4e62'], [0.62, '#ab7460'], [0.78, '#5e5670'], [1, '#0b0d10']],
    blooms: [[0.66, 0.38, 0.62, 'rgba(216,132,92,0.32)'], [0.28, 0.32, 0.50, 'rgba(126,96,168,0.22)']],
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
  /* A local solar hour is enough here: the field only has to know morning from afternoon from night, and a
     full solar position would be precision nobody can see in a background. */
  const utcHours = at.getUTCHours() + at.getUTCMinutes() / 60;
  const solar = (utcHours + longitude / 15 + 24) % 24;
  void latitude;
  if (solar >= 5 && solar < 9) return 'daybreak';
  if (solar >= 9 && solar < 16) return 'noon';
  if (solar >= 16 && solar < 19.5) return 'golden';
  return 'night';
}
