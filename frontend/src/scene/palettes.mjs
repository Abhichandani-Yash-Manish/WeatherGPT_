/* The sky palettes.
   ============================================================================
   Four phases. Three of them are the user's own specification (19 September): calibrated so they do not band
   on a projector and so a frosted-glass panel stays legible over them. Golden Hour is derived in the same
   spirit, because the spec gave three and a day has four moments worth drawing.

   Every other colour in a scene is mixed from these three stops, which is what makes a phase change re-tint
   the whole illustration at once instead of swapping assets: the far range, the mid silhouette, the landmark
   and the ground are the horizon colour walked toward the ink by a fixed amount, so aerial perspective comes
   out of the palette rather than being hand-picked per scene. */

export const PHASES = ['daybreak', 'noon', 'golden', 'night'];

export const PALETTES = {
  daybreak: {
    label: 'Daybreak',
    zenith: '#A1C4FD',
    mid: '#C2E9FB',
    horizon: '#FFD194',
    ink: '#1E293B',
    glass: 'rgba(255,255,255,0.40)',
    glassLine: 'rgba(255,255,255,0.55)',
    text: '#1E293B',
    sun: '#FFF3D6',
    sunGlow: 'rgba(255,209,148,0.75)',
    sunAt: [0.22, 0.70],
    blur: 12,
  },
  noon: {
    label: 'High Noon',
    zenith: '#0052D4',
    mid: '#4364F6',
    horizon: '#6FB1FC',
    ink: '#0B1B3A',
    glass: 'rgba(255,255,255,0.20)',
    glassLine: 'rgba(255,255,255,0.35)',
    text: '#F8FAFC',
    sun: '#FFFFFF',
    sunGlow: 'rgba(255,255,255,0.55)',
    sunAt: [0.78, 0.18],
    blur: 16,
  },
  /* Derived, not supplied: the same method as the three above — a saturated zenith, a warm mid, a luminous
     horizon, and an ink dark enough that the landmark reads as a silhouette rather than as a brown shape. */
  golden: {
    label: 'Golden Hour',
    zenith: '#2B3A67',
    mid: '#E96443',
    horizon: '#FFC371',
    ink: '#241429',
    glass: 'rgba(255,255,255,0.28)',
    glassLine: 'rgba(255,255,255,0.40)',
    text: '#1B1020',
    sun: '#FFF0C9',
    sunGlow: 'rgba(255,150,80,0.70)',
    sunAt: [0.72, 0.78],
    blur: 14,
  },
  night: {
    label: 'Deep Night',
    zenith: '#090A0F',
    mid: '#151928',
    horizon: '#242C45',
    ink: '#05070C',
    glass: 'rgba(0,0,0,0.40)',
    glassLine: 'rgba(255,255,255,0.10)',
    text: '#F8FAFC',
    sun: '#E8EEFF',
    sunGlow: 'rgba(180,200,255,0.30)',
    sunAt: [0.24, 0.20],
    blur: 14,
  },
};

/** #rrggbb -> [r,g,b] */
export function rgb(hex) {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

/** Walk one colour toward another. amount 0 = a, 1 = b. */
export function mix(a, b, amount) {
  const x = rgb(a);
  const y = rgb(b);
  const out = x.map((value, index) => Math.round(value + (y[index] - value) * amount));
  return '#' + out.map(value => value.toString(16).padStart(2, '0')).join('');
}

/** How far each plane walks from the horizon toward the ink.
    Aerial perspective: the far range is nearly the sky, the landmark is nearly the ink. The curve is looser
    at night, because against a near-black sky a silhouette that walks the full distance disappears — the
    shapes have to stay lighter than the ink to read at all. */
const DEPTH = {
  daybreak: [0.10, 0.26, 0.60, 0.74],
  noon: [0.12, 0.30, 0.64, 0.78],
  golden: [0.12, 0.30, 0.66, 0.80],
  night: [0.10, 0.22, 0.46, 0.58],
};

export function planes(palette, phase = 'noon') {
  const [far, mid, near, ground] = DEPTH[phase] || DEPTH.noon;
  return {
    far: mix(palette.horizon, palette.ink, far),
    mid: mix(palette.horizon, palette.ink, mid),
    near: mix(palette.horizon, palette.ink, near),
    ground: mix(palette.horizon, palette.ink, ground),
    groundFar: mix(palette.horizon, palette.ink, mid + 0.06),
  };
}
