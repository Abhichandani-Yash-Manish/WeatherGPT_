/* The spectrum: a continuous palette, not four rooms with doors between them.
   ============================================================================
   tokens.css still holds four complete palettes, keyed by `[data-hour]`, and it is right to: they are the
   hand-tuned, AA-measured anchors this file blends between, and they remain the correct page for a reader
   with JavaScript off or for a route this file does not reach (the place page has its own frame). What this
   file adds is what a static attribute cannot: the page a reader is actually looking at drifts continuously
   with the sun's own position, so 11:58 and 12:02 differ by two minutes of light rather than by nothing at
   all, and a long afternoon is not one frozen slide.

   Two different questions get two different answers here, because they carry two different risks:

   1. INK AGAINST GROUND — paper, mist, the surfaces glass sits on, the accent that has to read against both.
      A text colour that is halfway between "near-white on near-black" and "near-black on near-white" is a
      grey ink on a grey ground: contrast collapses to about 1:1 at the midpoint of any naive blend across
      that divide. So this group changes REGIME (which of the two ink families is in force) at exactly two
      altitudes — the same −6° and +8° fieldPaint.ts already uses to decide dawn and dusk — and blends
      CONTINUOUSLY on either side of each, connecting smoothly into the palette it is leaving and switching
      cleanly into the one it is entering. The switch itself is not softened, because softening it is exactly
      what would put a reader's eyes on a grey page for the two or three minutes either side of it.

   2. THE ATMOSPHERE — the sky gradient, the two drifting auras, the vignette, where the light stands across
      the halo. Nothing here is read as text and nothing here is compared against ink, so nothing here needs
      a regime: it drifts on a full 24-hour cycle, keyed to the sun's own hour angle rather than to altitude,
      which is what lets a long, high, bright afternoon keep moving instead of sitting on one frozen value
      the way the old four-band page did.

   Nothing published — none of the four hazard colours a bulletin can print — is touched by any of this: this
   module never reads or writes --g-red, --g-orange, --g-yellow or --g-green, and Claim.tsx's --g-lit is set
   inline on the one element that carries a source, which this module's root-level custom properties cannot
   reach or override. */

import { HORIZON, NIGHT_BELOW, type SolarPosition } from './fieldPaint';

type RGBA = { r: number; g: number; b: number; a: number };

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

/** A cubic ease between two edges, 0 before the first and 1 after the second — the same curve CSS's own
    `ease` approximates, used here because a linear blend arrives and leaves at a visible constant rate,
    which reads as mechanical against a sky that never moves at a constant rate. */
function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = clamp01((x - edge0) / (edge1 - edge0));
  return t * t * (3 - 2 * t);
}

function parseHex(hex: string): RGBA {
  const h = hex.replace('#', '');
  return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16), a: 1 };
}

function parseRgba(value: string): RGBA {
  const m = /rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)/.exec(value);
  if (!m) throw new Error('spectrum.ts: not an rgb()/rgba() colour: ' + value);
  return { r: Number(m[1]), g: Number(m[2]), b: Number(m[3]), a: m[4] === undefined ? 1 : Number(m[4]) };
}

const mix = (a: number, b: number, t: number) => a + (b - a) * t;

function mixRgba(from: RGBA, to: RGBA, t: number): RGBA {
  return { r: mix(from.r, to.r, t), g: mix(from.g, to.g, t), b: mix(from.b, to.b, t), a: mix(from.a, to.a, t) };
}

const byteHex = (v: number) => Math.round(clamp01(v / 255) * 255).toString(16).padStart(2, '0');
const toHex = (c: RGBA) => '#' + byteHex(c.r) + byteHex(c.g) + byteHex(c.b);
const round3 = (n: number) => Math.round(n * 1000) / 1000;
const toRgba = (c: RGBA) => 'rgba(' + Math.round(c.r) + ', ' + Math.round(c.g) + ', ' + Math.round(c.b) + ', ' + round3(c.a) + ')';

const mixHexValue = (a: string, b: string, t: number) => toHex(mixRgba(parseHex(a), parseHex(b), t));
const mixRgbaValue = (a: string, b: string, t: number) => toRgba(mixRgba(parseRgba(a), parseRgba(b), t));

/* ---- the ink-and-ground family, the four hand-tuned anchors verbatim from tokens.css --------------- */

type CriticalPalette = {
  voidHex: string; bg: string; raise: string; raise2: string; line: string; lineSoft: string;
  paper: string; mist: string; mist2: string;
  accent: string; accent2: string; accentWash: string; mark2: string;
  glass: string; glass2: string; scrim: string;
  railStop1: string; railStop2: string;
  grainA: number;
};

const NIGHT_C: CriticalPalette = {
  voidHex: '#05080f', bg: '#0a0f1a', raise: '#111828', raise2: '#172032', line: '#222d40', lineSoft: '#18212f',
  paper: '#edf1f7', mist: '#9eabc0', mist2: '#737f97',
  accent: '#a8c7fa', accent2: '#7ea6e8', accentWash: 'rgba(168, 199, 250, 0.10)', mark2: '#3f5d8f',
  glass: 'rgba(14, 20, 33, 0.82)', glass2: 'rgba(15, 22, 36, 0.60)', scrim: 'rgba(4, 7, 13, 0.62)',
  railStop1: 'rgba(8, 12, 20, 0.86)', railStop2: 'rgba(5, 8, 15, 0.92)', grainA: 0.032,
};

const DAYBREAK_C: CriticalPalette = {
  voidHex: '#f0e9e1', bg: '#fdfaf6', raise: '#ffffff', raise2: '#f8f2ea', line: '#e2d7c9', lineSoft: '#ede5da',
  paper: '#241c14', mist: '#574d40', mist2: '#6d6254',
  accent: '#2f5fc0', accent2: '#244da3', accentWash: 'rgba(47, 95, 192, 0.10)', mark2: '#1c3f86',
  glass: 'rgba(255, 252, 247, 0.86)', glass2: 'rgba(255, 253, 250, 0.72)', scrim: 'rgba(24, 30, 45, 0.40)',
  railStop1: 'rgba(246, 238, 229, 0.86)', railStop2: 'rgba(240, 231, 220, 0.92)', grainA: 0.022,
};

const NOON_C: CriticalPalette = {
  voidHex: '#e9eef6', bg: '#f2f6fb', raise: '#ffffff', raise2: '#eef4fa', line: '#d3dce9', lineSoft: '#e3e9f2',
  paper: '#121a27', mist: '#465166', mist2: '#5b6679',
  accent: '#1f5ccc', accent2: '#1849a8', accentWash: 'rgba(31, 92, 204, 0.10)', mark2: '#15409b',
  glass: 'rgba(255, 255, 255, 0.86)', glass2: 'rgba(255, 255, 255, 0.72)', scrim: 'rgba(24, 30, 45, 0.40)',
  railStop1: 'rgba(238, 244, 251, 0.86)', railStop2: 'rgba(231, 239, 249, 0.92)', grainA: 0.022,
};

const GOLDEN_C: CriticalPalette = {
  voidHex: '#0a0711', bg: '#14101c', raise: '#1e1729', raise2: '#251d33', line: '#372b45', lineSoft: '#271f35',
  paper: '#f3edf5', mist: '#ad9fb7', mist2: '#857793',
  accent: '#c3aae8', accent2: '#a98fd4', accentWash: 'rgba(195, 170, 232, 0.12)', mark2: '#6b4a8f',
  glass: 'rgba(26, 20, 36, 0.82)', glass2: 'rgba(28, 21, 39, 0.60)', scrim: 'rgba(8, 5, 14, 0.62)',
  railStop1: 'rgba(16, 11, 23, 0.86)', railStop2: 'rgba(10, 7, 17, 0.92)', grainA: 0.032,
};

function mixCritical(a: CriticalPalette, b: CriticalPalette, t: number): CriticalPalette {
  return {
    voidHex: mixHexValue(a.voidHex, b.voidHex, t),
    bg: mixHexValue(a.bg, b.bg, t),
    raise: mixHexValue(a.raise, b.raise, t),
    raise2: mixHexValue(a.raise2, b.raise2, t),
    line: mixHexValue(a.line, b.line, t),
    lineSoft: mixHexValue(a.lineSoft, b.lineSoft, t),
    paper: mixHexValue(a.paper, b.paper, t),
    mist: mixHexValue(a.mist, b.mist, t),
    mist2: mixHexValue(a.mist2, b.mist2, t),
    accent: mixHexValue(a.accent, b.accent, t),
    accent2: mixHexValue(a.accent2, b.accent2, t),
    accentWash: mixRgbaValue(a.accentWash, b.accentWash, t),
    mark2: mixHexValue(a.mark2, b.mark2, t),
    glass: mixRgbaValue(a.glass, b.glass, t),
    glass2: mixRgbaValue(a.glass2, b.glass2, t),
    scrim: mixRgbaValue(a.scrim, b.scrim, t),
    railStop1: mixRgbaValue(a.railStop1, b.railStop1, t),
    railStop2: mixRgbaValue(a.railStop2, b.railStop2, t),
    grainA: mix(a.grainA, b.grainA, t),
  };
}

/** Which ink-and-ground family is in force, and how far this instant sits from the boundary it just crossed
    or is about to. Below −6° it is always NIGHT_C; at or above +8° it is always NOON_C — a reader looking at
    the page at 11am and again at 2pm sees the identical plateau either way, which is correct: nothing about
    the ink needs to move while the sun is simply high. Between the two, which of the twilight palettes is in
    play depends on whether the sun is climbing or falling, read straight off the sign of the hour angle
    rather than by sampling a second instant the way the discrete `hourOf` has to. */
function criticalAt(altitude: number, ascending: boolean): CriticalPalette {
  if (altitude >= HORIZON) return NOON_C;
  if (altitude < NIGHT_BELOW) return NIGHT_C;
  const t = smoothstep(NIGHT_BELOW, HORIZON, altitude);
  /* Ascending: t=0 at −6° is DAYBREAK_C outright — the one deliberate snap, at the instant night's own ink
     would otherwise have to share a page with a paper-white ground. From there it blends up to NOON_C by
     +8°, matching the flat plateau it walks into without a seam.
     Descending: the mirror snap sits at +8°, where NOON_C's dark ink flips to GOLDEN_C's light one, and from
     there it blends the rest of the way down into NIGHT_C by −6° — no seam there either, because golden and
     night are already the same ink family and share nothing to be careful about. */
  return ascending ? mixCritical(DAYBREAK_C, NOON_C, t) : mixCritical(GOLDEN_C, NIGHT_C, 1 - t);
}

/* ---- the atmosphere, on its own 24-hour clock -------------------------------------------------------- */

type DecorativePalette = {
  sky1: string; sky2: string; aura1: string; aura2: string; haloX: number; vignette: string;
  /* The three washes that end the monotony task 3 named by name: the rail, the bar and a reader's own
     bubble each read their colour from a different part of the SAME hour rather than from one grey repeated
     three times. All three are low-alpha atmosphere, layered under a component's existing fill, never text —
     so, like sky/aura/vignette, they carry no contrast obligation and are free to be genuinely decorative. */
  railTint: string; barTint: string; bubbleTint: string;
};

const NIGHT_D: DecorativePalette = {
  sky1: '#0a1124', sky2: '#070b15', aura1: 'rgba(120, 148, 210, 0.11)', aura2: 'rgba(96, 116, 176, 0.08)',
  haloX: 32, vignette: 'rgba(3, 6, 12, 0.46)',
  railTint: 'rgba(168, 199, 250, 0.05)', barTint: 'rgba(150, 176, 230, 0.06)', bubbleTint: 'rgba(180, 168, 220, 0.07)',
};
const DAYBREAK_D: DecorativePalette = {
  sky1: '#f6dcc0', sky2: '#fcf1e6', aura1: 'rgba(240, 166, 102, 0.36)', aura2: 'rgba(184, 166, 226, 0.22)',
  haloX: 22, vignette: 'rgba(146, 126, 104, 0.14)',
  railTint: 'rgba(47, 95, 192, 0.045)', barTint: 'rgba(224, 158, 96, 0.05)', bubbleTint: 'rgba(150, 120, 190, 0.05)',
};
const NOON_D: DecorativePalette = {
  sky1: '#c4d9f5', sky2: '#e4eefb', aura1: 'rgba(124, 170, 238, 0.34)', aura2: 'rgba(150, 186, 240, 0.22)',
  haloX: 64, vignette: 'rgba(94, 118, 158, 0.11)',
  railTint: 'rgba(31, 92, 204, 0.04)', barTint: 'rgba(120, 170, 230, 0.05)', bubbleTint: 'rgba(90, 130, 200, 0.05)',
};
const GOLDEN_D: DecorativePalette = {
  sky1: '#2a1f38', sky2: '#140f1c', aura1: 'rgba(226, 138, 86, 0.22)', aura2: 'rgba(150, 110, 200, 0.16)',
  haloX: 78, vignette: 'rgba(8, 5, 14, 0.48)',
  railTint: 'rgba(195, 170, 232, 0.05)', barTint: 'rgba(226, 148, 96, 0.06)', bubbleTint: 'rgba(170, 130, 190, 0.06)',
};

function mixDecorative(a: DecorativePalette, b: DecorativePalette, t: number): DecorativePalette {
  return {
    sky1: mixHexValue(a.sky1, b.sky1, t),
    sky2: mixHexValue(a.sky2, b.sky2, t),
    aura1: mixRgbaValue(a.aura1, b.aura1, t),
    aura2: mixRgbaValue(a.aura2, b.aura2, t),
    haloX: mix(a.haloX, b.haloX, t),
    vignette: mixRgbaValue(a.vignette, b.vignette, t),
    railTint: mixRgbaValue(a.railTint, b.railTint, t),
    barTint: mixRgbaValue(a.barTint, b.barTint, t),
    bubbleTint: mixRgbaValue(a.bubbleTint, b.bubbleTint, t),
  };
}

/** 0 at solar midnight, 0.5 at solar noon, 1 at the next solar midnight — always true by the definition of
    the hour angle, whatever the latitude or the season, which is exactly why the atmosphere is keyed to this
    rather than to the wall clock. The quarter-points either side of noon stand in for dawn and dusk: an
    approximation (real sunrise is not always six solar hours from noon), and an acceptable one, because
    nothing this clock drives is ever asked to carry contrast — it is sky, haze and the drift of a halo. */
function dayClockOf(hourAngle: number): number {
  return (((hourAngle + 180) % 360) + 360) % 360 / 360;
}

const DECO_ANCHORS: [number, DecorativePalette][] = [
  [0, NIGHT_D], [0.25, DAYBREAK_D], [0.5, NOON_D], [0.75, GOLDEN_D], [1, NIGHT_D],
];

function decorativeAt(hourAngle: number): DecorativePalette {
  const clock = dayClockOf(hourAngle);
  for (let i = 0; i < DECO_ANCHORS.length - 1; i++) {
    const [from, fromPalette] = DECO_ANCHORS[i];
    const [to, toPalette] = DECO_ANCHORS[i + 1];
    if (clock >= from && clock <= to) return mixDecorative(fromPalette, toPalette, smoothstep(from, to, clock));
  }
  /* Unreachable — dayClockOf always returns a value in [0, 1] and the anchors span exactly that — but a
     function with a documented return type does not get to return undefined if the loop's own logic ever
     drifts, so night is the floor rather than a crash. */
  return NIGHT_D;
}

/* ---- the twenty-seven custom properties this module owns ---------------------------------------------- */

const SPECTRUM_PROPERTIES = [
  '--g-void', '--g-bg', '--g-raise', '--g-raise-2', '--g-line', '--g-line-soft',
  '--g-paper', '--g-mist', '--g-mist-2',
  '--g-accent', '--g-accent-2', '--g-accent-wash', '--g-mark-2',
  '--g-glass', '--g-glass-2', '--g-scrim', '--g-rail-bg', '--g-grain-a',
  '--g-sky-1', '--g-sky-2', '--g-aura-1', '--g-aura-2', '--g-halo-x', '--g-vignette',
  '--g-rail-tint', '--g-bar-tint', '--g-bubble-tint',
] as const;

export type SpectrumProperty = (typeof SPECTRUM_PROPERTIES)[number];
export type Spectrum = Record<SpectrumProperty, string>;

/** The continuous palette at one solar position. Every value here is a plain colour or gradient string,
    ready for `style.setProperty` — never a class, never an attribute, because an inline style is the one
    layer of the cascade that reliably outranks the four `[data-hour]` blocks in tokens.css without having to
    delete or rewrite them. Those blocks stay exactly as measured: they are what a reader with JavaScript off
    sees, and what this function's own two regime snaps agree with at every boundary. */
export function spectrumAt(position: SolarPosition): Spectrum {
  const c = criticalAt(position.altitude, position.hourAngle < 0);
  const d = decorativeAt(position.hourAngle);
  return {
    '--g-void': c.voidHex, '--g-bg': c.bg, '--g-raise': c.raise, '--g-raise-2': c.raise2,
    '--g-line': c.line, '--g-line-soft': c.lineSoft,
    '--g-paper': c.paper, '--g-mist': c.mist, '--g-mist-2': c.mist2,
    '--g-accent': c.accent, '--g-accent-2': c.accent2, '--g-accent-wash': c.accentWash, '--g-mark-2': c.mark2,
    '--g-glass': c.glass, '--g-glass-2': c.glass2, '--g-scrim': c.scrim,
    '--g-rail-bg': 'linear-gradient(180deg, ' + c.railStop1 + ', ' + c.railStop2 + ')',
    '--g-grain-a': String(round3(c.grainA)),
    '--g-sky-1': d.sky1, '--g-sky-2': d.sky2, '--g-aura-1': d.aura1, '--g-aura-2': d.aura2,
    '--g-halo-x': round3(d.haloX).toFixed(1) + '%', '--g-vignette': d.vignette,
    '--g-rail-tint': d.railTint, '--g-bar-tint': d.barTint, '--g-bubble-tint': d.bubbleTint,
  };
}

/** Paints the continuous spectrum onto an element — the document element in practice, so every hour block in
    every one of this product's stylesheets inherits it the way `[data-hour]` already does. */
export function applySpectrum(el: HTMLElement, spectrum: Spectrum): void {
  SPECTRUM_PROPERTIES.forEach(name => el.style.setProperty(name, spectrum[name]));
}

/** Undoes exactly what applySpectrum set, so an element that stops painting the spectrum (Field unmounting)
    falls back to whatever `[data-hour]` or the base `:root` was already declaring, rather than freezing on
    the last instant it painted. */
export function clearSpectrum(el: HTMLElement): void {
  SPECTRUM_PROPERTIES.forEach(name => el.style.removeProperty(name));
}
