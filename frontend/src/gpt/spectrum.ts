/* The spectrum: a continuous palette, not four rooms with doors between them.
   ============================================================================
   tokens.css still holds four complete palettes, keyed by `:root[data-hour]`, and it is right to: they are the
   hand-tuned, AA-measured anchors this file blends between, and they remain the correct page for a reader
   with JavaScript off or for a route this file does not reach (the place page has its own frame). What this
   file adds is what a static attribute cannot: the page a reader is actually looking at drifts continuously
   with the sun's own position, so 11:58 and 12:02 differ by two minutes of light rather than by nothing at
   all.

   THREE QUESTIONS, THREE ANSWERS — because they carry three different risks.

   1. INK AGAINST GROUND. A text colour halfway between "near-white on near-black" and "near-black on
      near-white" is a grey ink on a grey ground. So this group changes REGIME at exactly two altitudes — the
      same −6° and +8° fieldPaint.ts uses to decide dawn and dusk — and blends continuously on either side of
      each. The switch is a clean flip rather than a smear, which is the point.

   2. THE GROUND ITSELF. This group used to drift on the hour angle while the ink flipped on altitude, and the
      two clocks disagreed for up to an hour and a half at a time: at 18:00 IST on 21 June at Nagpur the sky
      was already GOLDEN_D's violet while the ink was still NOON_C's near-black, a measured 1.001:1. The
      disagreement is not a tuning error and cannot be tuned away — with a near-black paper (L 0.012) and a
      near-white one (L 0.85) there is no ground luminance at which BOTH clear 4.5:1 (the crossover sits at
      3.84:1), so a ground that drifts across that band is unreadable whichever ink is in force. The ground is
      therefore bimodal by construction: it shares the ink's two altitudes, it flips with it, and inside each
      regime it still drifts — the day from a high-sun blue toward a low-sun warm, the night from a deep sky
      toward first light. Nothing about the ground's structure changed: the same five layers, the same
      gradient, the same auras, grain, vignette and one mark.

   3. THE ATMOSPHERE. The auras, where the light stands across the halo, how much of a printed condition the
      ground takes, and how strong the watermark is, are not read as text and are not compared against ink, so
      they keep the 24-hour clock keyed to the sun's own hour angle.

   AND THE MATERIALS. A fourth group: the rail, the top bar, the reader's own bubble and the machine's own pane
   each take their own film out of the same hour, so a reader can see four different materials lit by one sun
   rather than one grey repeated four times. Each is a translucent film over the ground, which is what makes it
   glass rather than paint: the sky reads through all four and the film only says how much of the hour's light
   that material catches, at what temperature. The rail is the shade (deepest, densest, coolest); the bar is
   the light (the thinnest film, and the one that is least the ground's own colour); the bubble is the warmth;
   the pane is the instrument's own surface. They are keyed to the SAME two altitudes as the ink, so each
   material's identity survives the regime flip rather than being re-chosen by it.

   Nothing published — none of the four hazard colours a bulletin can print — is touched by any of this: this
   module never reads or writes --g-red, --g-orange, --g-yellow or --g-green, and Claim.tsx's --g-lit is set
   inline on the one element that carries a source, which this module's root-level custom properties cannot
   reach or override. materials.test.ts holds that to the computed values rather than to the names.

   4. THE SCHEME. Everything above describes what a reader gets when the browser has stated no colour-scheme
      preference of its own: the family (light ink, dark ink) is chosen by the sun's altitude, exactly as
      before. A reader who has told their OS or browser they want dark, or light, has made a stronger and more
      durable statement than the sun's position at this one instant — a farmer checking an advisory at noon in
      dark mode does not want the page to go white on them — so that choice picks the FAMILY outright and the
      sun is left to do only what it has always done inside a family: drift. `criticalAt`/`skyAt` above are
      therefore untouched — they are exactly the 'system' path, byte-for-byte what this module has always
      computed — and a forced scheme instead walks a second, independent set of anchors keyed to `dayClockOf`
      (the same 0-at-midnight, 0.5-at-noon clock the atmosphere already uses), rather than to altitude: a
      forced palette has no regime to flip between, so it has nothing for an altitude threshold to decide.
      Two of the four anchors each forced family needs already existed — NIGHT_C/NIGHT_SKY for the dark family,
      GOLDEN_C/DUSK_SKY for its evening, DAYBREAK_C/DAWN_SKY for the light family's morning, NOON_C/DAY_HIGH_SKY
      for its midday — and this section adds the two each was missing: a dark morning and a dark high sun
      (DARK_DAWN_C, DARK_NOON_C), and a light night and a light dusk (LIGHT_NIGHT_C, LIGHT_DUSK_C). Each is
      hand-tuned in the same register as the four it joins — the same near-black-or-near-white ink, the same
      five-to-eight-percent line opacity, the same low-chroma void — so a forced family reads as one more hour
      of the same product rather than a fifth, unrelated palette. */

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

/* ---- perceptual arithmetic, so a drift does not pass through the neutral it would have to cross --------
   Mixing two colours in sRGB is a straight line through the RGB cube, and a straight line between a warm
   cream and a blue runs through grey. That is not a taste problem, it is a measurement one: the dawn sky
   (#f6dcc0, chroma 0.047) and the noon sky (#c4d9f5, chroma 0.045) sit on opposite sides of the neutral
   axis, and every sRGB blend between them lands near chroma 0.005 halfway. Two consequences, both measured
   before this was written: the page went grey in the middle of a sunrise, and a material whose chroma was
   close to the ground's stopped being a different material at exactly that instant (rail vs ground came
   within 0.0001 of each other in OKLab chroma at Nagpur on 21 June).

   So the atmosphere and the materials drift in OKLab's own polar form — lightness, chroma and hue angle,
   with the hue taking the short way round — and the hue sweep keeps its chroma instead of losing it, which
   is also what a real sunrise does: a dawn sky goes cream, then rose, then lavender, then blue, and it is
   never grey on the way.

   This is the one place in this file that has to be more than arithmetic between two hex strings, and it is
   the arithmetic the test in materials.test.ts re-implements from scratch (the test carries no dependency on
   this module beyond spectrumAt itself, and no colour library either). */

type Lab = { L: number; a: number; b: number };

const toLinear = (v: number) => { const x = v / 255; return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
const fromLinear = (v: number) => { const x = v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(Math.max(0, v), 1 / 2.4) - 0.055; return Math.min(255, Math.max(0, x * 255)); };

function okLabOf(hex: string): Lab {
  const c = parseHex(hex);
  const r = toLinear(c.r), g = toLinear(c.g), b = toLinear(c.b);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return {
    L: 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
    a: 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
    b: 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
  };
}

function rgbOfOkLab(L: number, a: number, b: number): string {
  const l = L + 0.3963377774 * a + 0.2158037573 * b;
  const m = L - 0.1055613458 * a - 0.0638541728 * b;
  const s = L - 0.0894841775 * a - 1.2914855480 * b;
  const l3 = l * l * l, m3 = m * m * m, s3 = s * s * s;
  return toHex({
    r: fromLinear(4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3),
    g: fromLinear(-1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3),
    b: fromLinear(-0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3),
    a: 1,
  });
}

/** Whether sRGB can show this colour at all. Every other function here clamps silently, which is right for a
    gradient stop and wrong for a target: a target that had to be clamped is a material that will not look
    like the material it was asked for. */
function inGamut(L: number, a: number, b: number): boolean {
  const l = L + 0.3963377774 * a + 0.2158037573 * b;
  const m = L - 0.1055613458 * a - 0.0638541728 * b;
  const s = L - 0.0894841775 * a - 1.2914855480 * b;
  const l3 = l * l * l, m3 = m * m * m, s3 = s * s * s;
  const channels = [
    4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3,
    -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3,
    -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3,
  ];
  return channels.every(v => v >= -0.001 && v <= 1.001);
}

/** The most chroma a screen can show at this lightness and hue. Below about L 0.2 it is the constraint that
    actually binds: a dark blue-violet cannot hold a saturated colour, and a material defined without asking
    came out at 0.9 alpha — a film so dense it had stopped being glass — while still landing short of the
    colour asked for. Bisection, eight steps, once a minute. */
function maxChromaAt(L: number, h: number): number {
  const rad = h * Math.PI / 180;
  let low = 0, high = 0.20;
  for (let i = 0; i < 14; i++) {
    const mid = (low + high) / 2;
    if (inGamut(L, mid * Math.cos(rad), mid * Math.sin(rad))) low = mid; else high = mid;
  }
  return low;
}

/** One colour moved by a lightness, a chroma and a hue offset — how a material is defined against the ground
    it sits on rather than against an absolute value of its own. */

const hueOf = (lab: Lab) => { const h = Math.atan2(lab.b, lab.a) * 180 / Math.PI; return h < 0 ? h + 360 : h; };

/** A colour at a lightness, a chroma and a hue — clamped into what sRGB can actually show, because a chroma
    that a screen cannot draw is not a colour and asking for one silently darkens the hue instead. */
function chromaTo(L: number, C: number, h: number, maxC = 0.16): string {
  const clamped = Math.min(Math.max(C, 0), maxC);
  return rgbOfOkLab(L, clamped * Math.cos(h * Math.PI / 180), clamped * Math.sin(h * Math.PI / 180));
}

/** Lightness and chroma straight, hue the short way round — a drift that keeps its colour. */
function polarMix(from: string, to: string, t: number): string {
  const A = okLabOf(from), B = okLabOf(to);
  const ca = Math.hypot(A.a, A.b), cb = Math.hypot(B.a, B.b);
  const ha = hueOf(A), hb = hueOf(B);
  let delta = ((hb - ha) % 360 + 540) % 360 - 180;
  return chromaTo(mix(A.L, B.L, t), mix(ca, cb, t), ha + delta * t);
}

/** One colour moved by a lightness, a chroma and a hue offset — how a material is defined against the ground
    it sits on rather than against an absolute value of its own. */
function shifted(hex: string, dL: number, dC: number, dH: number): { hex: string; C: number; h: number } {
  const lab = okLabOf(hex);
  const C = Math.max(0, Math.hypot(lab.a, lab.b) + dC);
  const h = hueOf(lab) + dH;
  return { hex: chromaTo(lab.L + dL, C, h), C, h: ((h % 360) + 360) % 360 };
}

/** The film that puts `target` over `ground`: the inverse of the ordinary over() composite, which is what a
    translucent surface can actually be. Alpha is chosen by search rather than fixed, because a target that is
    darker than the ground needs a denser film than one that is lighter, and a fixed alpha would silently
    clamp the film into a different colour than the one asked for. */
function filmOver(target: string, ground: string, preferred: number): string {
  const t = parseHex(target), g = parseHex(ground);
  const candidates = [preferred, preferred * 0.8, preferred * 1.25, preferred * 0.6, preferred * 1.6, preferred * 0.45, 0.75, 0.35];
  let best: RGBA | null = null, bestError = Infinity;
  for (const raw of candidates) {
    const a = Math.min(0.9, Math.max(0.08, raw));
    const film = { r: (t.r - g.r * (1 - a)) / a, g: (t.g - g.g * (1 - a)) / a, b: (t.b - g.b * (1 - a)) / a, a };
    const clipped = { r: Math.min(255, Math.max(0, film.r)), g: Math.min(255, Math.max(0, film.g)), b: Math.min(255, Math.max(0, film.b)), a };
    const error = Math.abs(film.r - clipped.r) + Math.abs(film.g - clipped.g) + Math.abs(film.b - clipped.b);
    if (error < bestError) { bestError = error; best = clipped; }
    if (error < 0.5) break;
  }
  const f = best as RGBA;
  return toRgba({ r: f.r, g: f.g, b: f.b, a: round3(f.a) });
}
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

/* ---- the ground: the sky, on the ink's own two altitudes ---------------------------------------------
   Four sky anchors rather than one 24-hour drift, because the ground has to change regime exactly when the
   ink does (see the header). Inside a regime it still moves: the light family drifts from a warm low sun to a
   cool high one, and the dark family from the deep sky of the night toward first light. Both ends of each
   drift are on the same side of the readable line, which is what makes the drift safe to have. */

type Sky = { sky1: string; sky2: string; vignette: string };

/* Below the horizon and well before first light: the deepest sky of the night. */
/* ---- the sky, in a matte mineral register, with somewhere to stand -----------------------------------
   The second half of this was the bigger mistake, and it took a screenshot to see it. Taking the chroma
   out of four sugared pastels was right. Leaving them all at 92-96% lightness was not: a ground that pale
   is a ground nothing can float ABOVE. Every white card, every frosted pane, every lifted rail had at most
   four points of lightness to work with, so the whole page flattened into one bright wash and read as
   unfinished rather than as calm. Desaturating it only changed the flavour of the flatness.

   Each sky drops five to eight points and takes a clear TEMPERATURE instead of a hue: dawn is warm because
   the light at dawn is warm, noon is cool and bright, dusk is dimmed and faintly warm the way a room is
   before the lamps go on, and the night is cool ash. That is what gives a white card somewhere to be.
   ---- and the original note, which still stands -----------------------------------------------------------
   The four light skies used to be sugared almonds: periwinkle #dde3f3, PINK #f4dce8, peach #f6dcc0 and
   baby blue #c4d9f5. Individually defensible as "soft"; together they are the palette of a children's
   weather app, and this one is presented to a meteorological department.

   Every one of them has had most of its chroma taken out and what is left pushed toward a mineral - ash,
   oat, stone, graphite. The HUES are kept, because they are the ones the sun actually makes: morning is
   still warmer than noon and dusk is still cooler than morning. What is gone is the saturation that made
   them sweet. A sky at 4% chroma still reads unmistakably as morning beside a noon at 3%; it just stops
   looking like an illustration of morning.

   The dark skies were already in this register and are barely touched - dusk lost the purple that was
   the one sugared note left after dark. */
const NIGHT_SKY_DEEP: Sky = { sky1: '#080f21', sky2: '#060a16', vignette: 'rgba(2, 4, 10, 0.52)' };
/* The sun at −6°, arriving or leaving. NIGHT_D's own values, unchanged. */
const NIGHT_SKY: Sky = { sky1: '#0a1124', sky2: '#070b15', vignette: 'rgba(3, 6, 12, 0.46)' };
/* First light: DAYBREAK_D's own values, unchanged — the warm cream the old dawn anchor held. */
const DAWN_SKY: Sky = { sky1: '#ddd2c2', sky2: '#efe9df', vignette: 'rgba(122, 106, 86, 0.17)' };
/* The high-sun sky: NOON_D's own values, unchanged. */
const DAY_HIGH_SKY: Sky = { sky1: '#c3cdd6', sky2: '#e4e9ee', vignette: 'rgba(84, 99, 118, 0.14)' };
/* The light's own two ends, and both of them blue. The day's change is clarity rather than hue: a dull,
   wide morning or evening (chroma 0.017) clearing to a saturated noon (0.045). The warmth of a low sun is
   not here — it is in the auras and the vignette below, which the hour angle drives, and in the twilight
   palettes. That separation is deliberate and measured: an sRGB blend from a warm sky to a blue one passes
   through grey, and a grey sky is a sky whose own chroma has vanished, which is what let a material and its
   ground collapse onto the same colour at midday (docs/134). */
const DAY_LOW_SKY: Sky = { sky1: '#dbe4f0', sky2: '#eef3fa', vignette: 'rgba(104, 120, 148, 0.12)' };
/* Dusk: GOLDEN_D's own values, unchanged — the violet the sun leaves behind. */
const DUSK_SKY: Sky = { sky1: '#241e2b', sky2: '#131117', vignette: 'rgba(8, 6, 11, 0.48)' };

function mixSky(a: Sky, b: Sky, t: number): Sky {
  return {
    /* The two stops drift in OKLab's polar form so the sky keeps its chroma the whole way: an sRGB line from
       the dawn's cream to the day's blue would spend the middle of every sunrise at chroma 0.005, and a
       neutral sky is a sky that erases the difference between the surfaces standing on it. */
    sky1: polarMix(a.sky1, b.sky1, t),
    sky2: polarMix(a.sky2, b.sky2, t),
    vignette: mixRgbaValue(a.vignette, b.vignette, t),
  };
}

/** The light family, drifting from a warm low sun to a cool high one. The altitude decides and the hour angle
    keeps the middle hours of a long afternoon moving: at 45° the altitude alone would have settled on one
    value from eleven until four, so the drift is damped rather than stopped as the light swings west. Both
    ends of it are light pages, so the ink never has to follow. */
function daySky(altitude: number, hourAngle: number): Sky {
  const high = smoothstep(HORIZON, 55, altitude);
  const swung = 0.55 + 0.45 * (1 - Math.min(1, Math.abs(hourAngle) / 95));
  return mixSky(DAY_LOW_SKY, DAY_HIGH_SKY, clamp01(high * swung));
}

/** The dark family, drifting from the deep sky of the night toward first light as the sun comes back up to
    −6°. Symmetric about midnight, because the same sky is above a reader at both ends of the night. */
function nightSky(altitude: number): Sky {
  return mixSky(NIGHT_SKY_DEEP, NIGHT_SKY, smoothstep(-32, NIGHT_BELOW, altitude));
}


function skyAt(altitude: number, hourAngle: number, ascending: boolean): Sky {
  if (altitude >= HORIZON) return daySky(altitude, hourAngle);
  if (altitude < NIGHT_BELOW) return nightSky(altitude);
  const w = smoothstep(NIGHT_BELOW, HORIZON, altitude);
  /* Ascending, the twilight runs from first light into the day family's own value at this altitude — the very
     value the plateau above +8° holds, so there is no step at the top of the ramp.
     Descending, it runs from the dusk sky into the night family's, which is what the plateau below −6° holds.
     What is left is two flips, at −6° climbing and at +8° falling, and the ink flips at both of them too. */
  return ascending ? mixSky(DAWN_SKY, daySky(altitude, hourAngle), w) : mixSky(DUSK_SKY, nightSky(altitude), 1 - w);
}

/* ---- the material family: four films over that ground, on the same two altitudes ---------------------- */

type Materials = {
  /* The rail is the shade: denser than the others and the deepest thing on the page. The bar is the light:
     the thinnest film, and the least the ground's own colour. The bubble is the reader's own words and the
     warmest surface in the product. The pane is the machine's own glass — the instrument's surface rather
     than the reader's. */
  rail: string; bar: string; bubble: string; pane: string;
  /* The two icon inks: the surrounding quiet ink with the material's own temperature in it, so a glyph in the
     rail and a glyph in the bar are not the same grey. Kept near their base ink, because an icon still has to
     be found — materials.test.ts checks them against the fill they are drawn on at the non-text floor. */
  railIcon: string; barIcon: string;
};

/* ---- the rules the four materials follow -----------------------------------------------------------
   Each material is defined against the ground it is drawn on rather than by an absolute colour of its own: a
   lightness offset, a chroma offset, and a hue. That is what makes the separation structural instead of
   incidental — two films picked by hand at four hours drifted past each other between the anchors (the rail
   and the bar came within 0.0005 of each other in OKLab chroma at Kanyakumari on 21 June, and the rail and
   the ground within 0.0001 at Nagpur), because a hand-picked film and a moving sky are two clocks.

   The hues are placed in the arc the ground's own hue never enters. Through a day the sky's hue runs from the
   dawn's cream (69°) down through red and violet to the night's blue-violet (265°) and the dusk's (304°); it
   never enters the range between 70° and 250°. So the rail sits at 235° and the bar at 205° — cool, the two
   materials that are not the reader's — and the reader's own bubble sits at 95°, which is the only warm hue
   inside that arc: a gold rather than an amber, because an amber is a hue the sky passes through on the way
   to dawn, and two colours with the same hue are not two materials. It is the one place in this palette where
   the design gives something up to the measurement, and it is recorded as such. */
type MaterialRule = {
  /** How far above or below the ground's own lightness this material sits. */
  dL: number;
  /** What share of the ground's chroma it keeps, and how much is added. */
  ck: number; dc: number;
  /** Its hue in OKLab degrees, the accent's own hue for the instrument's surface, or 'shade' for the ground's
      own hue turned 30° cool. The shade is the only material defined by rotation rather than by an absolute
      hue, and it is the one that needs it: on the dark hours the ground's own hue swings 39° between the
      night's blue-violet and the dusk's violet, and a rail holding one fixed hue would be sixty degrees away
      from the sky at one end of that swing and twenty-five at the other — which is a film at 0.9 alpha, a pane
      that has stopped being glass. Turned 30° from wherever the sky is, the same separation holds at both ends
      and the film stays thin enough to read the sky through. */
  h: number | 'accent' | 'shade';
  /** The alpha the film is solved at, before the gamut search moves it. */
  a: number;
};
type MaterialRules = { rail: MaterialRule; bar: MaterialRule; bubble: MaterialRule; pane: MaterialRule };

/* Widened from the first cut of this palette (rail dc 0.018, bar dc 0, bubble dc 0.038): materials.test.ts's
   own header records the worst measured gap at 0.0128 chroma against a 0.010 floor — passing, but by less than
   a third of the floor itself, which is what "the four materials read as one wash" measures as. The bar was
   the thinnest offender: ck 0.30 and no chroma of its own at all, so it carried almost none of the ground's
   own colour and none it was given. Raising rail and bubble's dc and giving the bar some of its own moves the
   worst pair further from the floor without moving any hue, so the family the rail/bar/bubble/pane read as
   together is unchanged — they are simply no longer whispering it. */
/* REFINED FROST. On the light hours every material now sits ABOVE the ground rather than below it, and
   that single sign change is most of what was wrong with this page.

   The rail used to be 4.8% DARKER than the field it sits beside (dL -0.048) and carried all of the
   ground's chroma. On a pale lilac field that produces a flat, muted blue slab which reads as a
   different application bolted to the left-hand edge - the gradient does not pass through it, and the
   sun's work on the field is invisible on the one surface a reader looks at most. It is white glass now:
   lifted well above the ground, holding only a third of its chroma, thin enough that the field's colour
   still moves underneath it through the day.

   The pane - the composer, the cards - is lifted and thickened for the opposite reason. It was 0.20
   alpha, which is not a surface, it is a tint; the primary control on the page had no more presence than
   the air around it. At 0.46 it is a white card the field shows through rather than a suggestion of one.

   The reader's own bubble takes the accent's hue instead of a fixed yellow-green, so the one thing on the
   page that is the reader's is coloured by the product's accent rather than by an unrelated third hue. */
const LIGHT_RULES: MaterialRules = {
  rail: { dL: 0.044, ck: 0.58, dc: 0.016, h: 232, a: 0.68 },
  /* The top bar sits CLOSE to the ground rather than above it, and is the one material that does.
     Lifting it was the obvious move and it does not work: to reach +0.11 lightness through a 40% film
     the film itself has to be lighter than white, so it clamps - and a clamped film stops responding to
     its own hue and chroma entirely. Three separate edits to this rule moved the measured distance by
     exactly nothing before that was understood. A thin strip holding one line of text does not need to
     be a raised surface; it needs an edge, which it has. */
  /* Separated from the rail by VALUE, in the rail's own hue family, rather than by being a different
     colour. Pushing them apart on the colour wheel is the easy way to satisfy a distinctness check and
     the wrong way to satisfy an eye: a teal strip above a blue column reads as two unrelated components,
     which is precisely the "nothing was considered" look this palette is being rebuilt out of. A header
     that sits slightly BELOW its page is an ordinary, quiet thing - and unlike the rail, which is a
     full-height column, a thin strip carrying one line of text loses nothing by being recessive. */
  bar: { dL: -0.024, ck: 0.50, dc: 0.040, h: 232, a: 0.46 },
  bubble: { dL: 0.022, ck: 1, dc: 0.050, h: 95, a: 0.50 },
  pane: { dL: 0.026, ck: 0.60, dc: 0.006, h: 'accent', a: 0.46 },
};

const DARK_RULES: MaterialRules = {
  /* The rail lifts to charcoal off a near-black ground; the top bar drops back toward the ground and is
     thinner, so the two stop competing. They used to sit 0.012 of lightness apart - closer to each other
     than either was to anything else on the page - and at Leh in the deep night that was the tightest
     pair in the whole palette at any hour, in either family. A rail and the bar directly above it are the
     two surfaces most often seen touching, so of all the pairs to let converge it was the worst one. */
  rail: { dL: 0.096, ck: 1, dc: 0.034, h: 'shade', a: 0.58 },
  bar: { dL: 0.040, ck: 0.46, dc: 0.012, h: 208, a: 0.30 },
  bubble: { dL: 0.168, ck: 1, dc: 0.050, h: 55, a: 0.46 },
  pane: { dL: 0.030, ck: 0.60, dc: 0.006, h: 'accent', a: 0.18 },
};

/* ---- the sky's saturation, held apart from its lightness -----------------------------------------------
   Three attempts at a richer palette failed the same way, and the reason was the operation, not the taste.
   Each one scaled a sky colour's DISTANCE FROM WHITE, which moves lightness and chroma together - so every
   step toward colour was also a step toward dark, contrast collapsed, and AA failed on four materials at
   once. Colour was being paid for with legibility, and there was never enough legibility to buy it.

   In OKLCH the two are separable. This takes a colour apart into lightness, chroma and hue, multiplies ONLY
   the chroma, and rebuilds it. Relative luminance is dominated by L, so contrast barely moves while the
   colour changes completely: a sky at the same lightness with three times the chroma is unmistakably blue
   and is read by every contrast check as very nearly the colour it replaced.

   `chromaTo` clamps to 0.16, which is what keeps the result inside sRGB instead of producing a hex that
   cannot exist and quietly rounding to something else.

   SKY_CHROMA is the single knob for "how colourful is the weather". It is applied to the sky BEFORE the
   materials are derived from it, so the rail, the bar, the bubble and the pane are films over the sky that
   is actually drawn - deriving them from the pale sky and then colouring the sky underneath would separate
   every material from its own ground. */
export const SKY_CHROMA = 1.9;
/* 1.9 was chosen by running the REAL invariants, not a model of them - every candidate below was applied
   to this constant and the whole spectrum suite run against it:

     1.5  1.7  1.8  1.9  2.0   all 84 pass
     2.1  2.3  2.4  2.5  3.0   material separation fails
     2.2                       passes, but with a failure on either side of it

   The ceiling is not monotonic because the four materials are films derived FROM the sky, so their
   separation from each other moves as the sky's chroma moves rather than simply shrinking. 2.2 passing
   between two failures is a knife edge and is worth nothing; 1.9 sits inside a band four samples wide,
   which is a value that will survive somebody changing a material rule by a hundredth. */

function saturate(hex: string, k: number): string {
  if (k === 1) return hex;
  const lab = okLabOf(hex);
  return chromaTo(lab.L, Math.hypot(lab.a, lab.b) * k, hueOf(lab));
}

function saturatedSky(sky: Sky, k: number): Sky {
  return k === 1 ? sky : { ...sky, sky1: saturate(sky.sky1, k), sky2: saturate(sky.sky2, k) };
}

/** Which family of rules is in force: the ink's own two altitudes again, so a material flips when the page
    flips and not at some third moment of its own. */
function rulesFor(altitude: number, ascending: boolean): MaterialRules {
  if (altitude >= HORIZON) return LIGHT_RULES;
  if (altitude < NIGHT_BELOW) return DARK_RULES;
  return ascending ? LIGHT_RULES : DARK_RULES;
}

/** How far an icon ink turns from its base ink: a third of the way to the material's own temperature, and
    nothing at all for the two hues that are not a temperature (the shade follows the ground, the pane follows
    the accent). */
function iconTurn(rule: MaterialRule, mist: string): number {
  if (rule.h === 'accent' || rule.h === 'shade') return 0;
  return (rule.h - hueOf(okLabOf(mist))) * 0.35;
}

/** What one material should look like over one ground, before the film that gets it there is solved. */
function lookOf(ground: string, rule: MaterialRule, accentHue: number): string {
  const lab = okLabOf(ground);
  const groundHue = hueOf(lab);
  const hue = rule.h === 'accent' ? accentHue : rule.h === 'shade' ? groundHue - 30 : rule.h;
  const lightness = lab.L + rule.dL;
  const wanted = Math.max(0, Math.hypot(lab.a, lab.b) * rule.ck + rule.dc);
  /* Clamped to what the screen can show at this lightness, so the film below can reach the colour asked for
     with a film thin enough to still be glass. */
  return chromaTo(lightness, Math.min(wanted, maxChromaAt(lightness, hue)), hue);
}

/** The four films at one solar position, and the two icon inks with them. Each film is solved from a target
    over the exact ground the element is drawn on — the rail and the bar over the top of the sky, the bubble
    and the pane over the middle of it, which is where they sit. `rules` is which family of offsets applies —
    LIGHT_RULES or DARK_RULES — decided by the caller: `rulesFor` for the system path, which reads it off the
    same altitude the ink and the ground just flipped on, or a scheme forced outright by the reader's own
    choice (spectrumAt below), which is never a function of altitude because a forced family has no altitude
    threshold to flip at. */
export function materialsAt(
  sky1: string, skyMid: string, accent: string, mist: string, rules: MaterialRules,
): Materials {
  const accentHue = hueOf(okLabOf(accent));
  /* Every material's LOOK is defined against the sky's own top colour, and only the film that gets there is
     solved against the band the element is actually drawn on. That distinction is the whole reason the gaps
     hold all day: with each material referenced to its own band, two of them converged as soon as their two
     bands differed — the rail against the top stop and the reader's bubble against the middle of the same
     gradient came within 0.0019 of each other in OKLab chroma at Kanyakumari on 21 December, because the
     gradient's own two stops differ by more than the gap between the materials. One reference, four offsets. */
  const film = (band: string, rule: MaterialRule) => filmOver(lookOf(sky1, rule, accentHue), band, rule.a);
  return {
    rail: film(sky1, rules.rail),
    bar: film(sky1, rules.bar),
    bubble: film(skyMid, rules.bubble),
    pane: film(skyMid, rules.pane),
    /* The icon inks are their base ink with a little of the material's own temperature in it, at the base
       ink's own lightness — which is what keeps a glyph in the rail findable (3:1) while making it not the
       same grey as a glyph in the bar. */
    railIcon: shifted(mist, 0, 0.008, iconTurn(rules.rail, mist)).hex,
    barIcon: shifted(mist, 0, 0.008, iconTurn(rules.bar, mist)).hex,
  };
}

/* ---- the atmosphere, on its own 24-hour clock -------------------------------------------------------- */

type DecorativePalette = {
  aura1: string; aura2: string; haloX: number;
  /* How much of a station's printed condition the ground takes. A dark ground has less light in it to move,
     so the dark hours take less. Read from the regime now rather than from the `[data-hour]` attribute, which
     no longer decides anything this module owns. */
  moodK: number;
  /* The condition watermark's own strength. A pale mark on a dark ground carries further than a dark one on
     paper, so the dark hours hold less. */
  markA: number;
};

/* The auras are the two soft lights that sit behind the greeting, and they were carrying more colour than
   the sky itself: a 36% orange at daybreak and a 34% blue at noon, which is where most of the sweetness in
   the old palette actually came from - the sky was pale and the aura painted over it. They are mineral now
   and roughly half as strong. A glow you can name the colour of is a decoration; a glow you can only
   notice is light. */
const NIGHT_D: DecorativePalette = {
  aura1: 'rgba(128, 146, 184, 0.10)', aura2: 'rgba(104, 118, 148, 0.07)', haloX: 32, moodK: 0.62, markA: 0.035,
};
const DAYBREAK_D: DecorativePalette = {
  aura1: 'rgba(206, 174, 138, 0.20)', aura2: 'rgba(166, 158, 178, 0.13)', haloX: 22, moodK: 1, markA: 0.045,
};
const NOON_D: DecorativePalette = {
  aura1: 'rgba(146, 166, 190, 0.19)', aura2: 'rgba(166, 180, 198, 0.13)', haloX: 64, moodK: 1, markA: 0.045,
};
const GOLDEN_D: DecorativePalette = {
  aura1: 'rgba(192, 150, 118, 0.15)', aura2: 'rgba(132, 118, 150, 0.10)', haloX: 78, moodK: 0.62, markA: 0.035,
};

function mixDecorative(a: DecorativePalette, b: DecorativePalette, t: number): DecorativePalette {
  return {
    aura1: mixRgbaValue(a.aura1, b.aura1, t),
    aura2: mixRgbaValue(a.aura2, b.aura2, t),
    haloX: mix(a.haloX, b.haloX, t),
    moodK: mix(a.moodK, b.moodK, t),
    markA: mix(a.markA, b.markA, t),
  };
}

/** 0 at solar midnight, 0.5 at solar noon, 1 at the next solar midnight — always true by the definition of
    the hour angle, whatever the latitude or the season, which is exactly why the atmosphere is keyed to this
    rather than to the wall clock. The quarter-points either side of noon stand in for dawn and dusk: an
    approximation (real sunrise is not always six solar hours from noon), and an acceptable one, because
    nothing this clock drives is ever asked to carry contrast — it is haze, the drift of a halo, and where the
    catch-light stands. */
function dayClockOf(hourAngle: number): number {
  return (((hourAngle + 180) % 360) + 360) % 360 / 360;
}

/** Four quarter-anchors — midnight, dawn, noon, dusk, and midnight again — blended by `dayClockOf` rather than
    by altitude. This is what a FORCED scheme walks (see the header's section 4): it has no regime to flip
    between, so the whole day is one continuous smoothstep chain through its own four keyframes, exactly the
    shape `decorativeAt` below already uses for the atmosphere. Generalised here so the ink, the ground and the
    atmosphere all walk the same shape of clock rather than three near-identical copies of the same loop. */
function atClock<T>(hourAngle: number, anchors: readonly (readonly [number, T])[], mix: (a: T, b: T, t: number) => T): T {
  const clock = dayClockOf(hourAngle);
  for (let i = 0; i < anchors.length - 1; i++) {
    const [from, fromValue] = anchors[i];
    const [to, toValue] = anchors[i + 1];
    if (clock >= from && clock <= to) return mix(fromValue, toValue, smoothstep(from, to, clock));
  }
  /* Unreachable — dayClockOf always returns a value in [0, 1] and the anchors span exactly that — but a
     function with a documented return type does not get to return undefined if the loop's own logic ever
     drifts, so the first anchor (always midnight, in every table this is called with) is the floor rather
     than a crash. */
  return anchors[0][1];
}

const DECO_ANCHORS: [number, DecorativePalette][] = [
  [0, NIGHT_D], [0.25, DAYBREAK_D], [0.5, NOON_D], [0.75, GOLDEN_D], [1, NIGHT_D],
];

function decorativeAt(hourAngle: number): DecorativePalette {
  return atClock(hourAngle, DECO_ANCHORS, mixDecorative);
}

/* ---- the two forced-scheme families: a whole day of dark, a whole day of light -------------------------
   Six of the eight anchors a forced scheme needs already exist above, doing double duty: NIGHT_C/NIGHT_SKY_DEEP
   anchor the dark family's midnight, GOLDEN_C/DUSK_SKY its evening; DAYBREAK_C/DAWN_SKY anchor the light
   family's morning, NOON_C/DAY_HIGH_SKY its midday. The four new ones fill the two gaps the system path never
   needed to fill, because the system path never asks the dark family what noon looks like or the light family
   what midnight looks like — a forced scheme asks exactly that. Each is hand-tuned against the ink-and-ground
   rules the header's section 1 states (near-black-or-near-white ink, a ground on the same side of the readable
   line at every point this file's own test sweeps), not against a formula, for the same reason the original
   four were: a target this file has to hit exactly is a target worth choosing by eye and then measuring,
   rather than deriving and hoping. */

/* Dark family, first light: a cool, quiet teal-blue rather than the night's blue-violet or the evening's
   violet — the third point on the same arc, so all three dark hours read as one family without repeating. */
const DARK_DAWN_C: CriticalPalette = {
  voidHex: '#050e12', bg: '#0a1a20', raise: '#0f242c', raise2: '#152e37', line: '#1e3944', lineSoft: '#152a33',
  paper: '#eef6f5', mist: '#9dc0bf', mist2: '#729695',
  accent: '#8fd6dc', accent2: '#69b8c0', accentWash: 'rgba(143, 214, 220, 0.10)', mark2: '#2b6b73',
  glass: 'rgba(11, 26, 33, 0.82)', glass2: 'rgba(12, 29, 37, 0.60)', scrim: 'rgba(4, 11, 14, 0.62)',
  railStop1: 'rgba(8, 19, 24, 0.86)', railStop2: 'rgba(5, 13, 17, 0.92)', grainA: 0.032,
};
/* Dark family, high sun: the dark register's own version of NOON_C's crisp, saturated blue — a page that
   reads as full day while staying dark, rather than the pale near-neutral NIGHT_C plateau standing in for
   noon because it is the only dark anchor there has ever been. */
const DARK_NOON_C: CriticalPalette = {
  voidHex: '#050a14', bg: '#0a1428', raise: '#0f1d34', raise2: '#13253f', line: '#20355c', lineSoft: '#172746',
  paper: '#eef2fb', mist: '#9fb1d1', mist2: '#7183a6',
  accent: '#7fb0f5', accent2: '#5a90e8', accentWash: 'rgba(127, 176, 245, 0.12)', mark2: '#2f5fb0',
  glass: 'rgba(10, 18, 34, 0.82)', glass2: 'rgba(11, 20, 36, 0.60)', scrim: 'rgba(3, 7, 15, 0.62)',
  railStop1: 'rgba(7, 13, 25, 0.86)', railStop2: 'rgba(4, 9, 18, 0.92)', grainA: 0.032,
};
/* Light family, night: a pale, cool, moonlit paper rather than daylight white — the same near-black ink the
   light family always carries, and an indigo accent in place of the day's blue, so a reader who reads at
   midnight in light mode is never told it is noon. */
const LIGHT_NIGHT_C: CriticalPalette = {
  voidHex: '#e7ebf6', bg: '#f0f2fa', raise: '#ffffff', raise2: '#ebeef8', line: '#d5dbee', lineSoft: '#e5e8f4',
  paper: '#171a2e', mist: '#4b5274', mist2: '#5f6688',
  accent: '#3d4cb0', accent2: '#2e3b93', accentWash: 'rgba(61, 76, 176, 0.10)', mark2: '#232d78',
  glass: 'rgba(255, 255, 255, 0.86)', glass2: 'rgba(255, 255, 255, 0.72)', scrim: 'rgba(20, 22, 42, 0.40)',
  railStop1: 'rgba(233, 236, 248, 0.86)', railStop2: 'rgba(225, 229, 245, 0.92)', grainA: 0.022,
};
/* Light family, dusk: pale and warm without ever being amber — the same "violet, not amber" rule GOLDEN_C
   keeps, so the light family's own dusk does not reach for a hue the dark family's already claimed. */
const LIGHT_DUSK_C: CriticalPalette = {
  voidHex: '#f2e9ee', bg: '#fdf6f8', raise: '#ffffff', raise2: '#f9eef2', line: '#e7d4dd', lineSoft: '#f1e2e8',
  paper: '#251527', mist: '#5d4a5f', mist2: '#715e73',
  accent: '#8054b8', accent2: '#68409c', accentWash: 'rgba(128, 84, 184, 0.10)', mark2: '#4f3080',
  glass: 'rgba(255, 252, 253, 0.86)', glass2: 'rgba(255, 253, 254, 0.72)', scrim: 'rgba(32, 20, 36, 0.40)',
  railStop1: 'rgba(247, 234, 238, 0.86)', railStop2: 'rgba(240, 224, 230, 0.92)', grainA: 0.022,
};

const DARK_DAWN_SKY: Sky = { sky1: '#0c1f26', sky2: '#08151a', vignette: 'rgba(4, 12, 15, 0.50)' };
const DARK_NOON_SKY: Sky = { sky1: '#0a1832', sky2: '#061020', vignette: 'rgba(3, 8, 17, 0.48)' };
const LIGHT_NIGHT_SKY: Sky = { sky1: '#ccd1d9', sky2: '#e4e7ec', vignette: 'rgba(98, 105, 122, 0.15)' };
const LIGHT_DUSK_SKY: Sky = { sky1: '#d8ccce', sky2: '#ece5e6', vignette: 'rgba(120, 100, 108, 0.16)' };

/** midnight, dawn, noon, dusk, midnight — the dark family never leaving its own register. */
const DARK_ANCHORS: [number, CriticalPalette][] = [
  [0, NIGHT_C], [0.25, DARK_DAWN_C], [0.5, DARK_NOON_C], [0.75, GOLDEN_C], [1, NIGHT_C],
];
const DARK_SKY_ANCHORS: [number, Sky][] = [
  [0, NIGHT_SKY_DEEP], [0.25, DARK_DAWN_SKY], [0.5, DARK_NOON_SKY], [0.75, DUSK_SKY], [1, NIGHT_SKY_DEEP],
];
/** midnight, dawn, noon, dusk, midnight — the light family never leaving its own register. */
const LIGHT_ANCHORS: [number, CriticalPalette][] = [
  [0, LIGHT_NIGHT_C], [0.25, DAYBREAK_C], [0.5, NOON_C], [0.75, LIGHT_DUSK_C], [1, LIGHT_NIGHT_C],
];
const LIGHT_SKY_ANCHORS: [number, Sky][] = [
  [0, LIGHT_NIGHT_SKY], [0.25, DAWN_SKY], [0.5, DAY_HIGH_SKY], [0.75, LIGHT_DUSK_SKY], [1, LIGHT_NIGHT_SKY],
];

/** A reader's colour-scheme choice. 'system' is every reader who has not overridden anything: the sun alone
    decides the family, exactly as this module always has. 'dark' and 'light' are an explicit, durable choice
    that outranks the sun's own position for the family — but never for the drift within it; see the header's
    section 4. */
export type Scheme = 'light' | 'dark' | 'system';

/* ---- the thirty-two custom properties this module owns ------------------------------------------------ */

const SPECTRUM_PROPERTIES = [
  '--g-void', '--g-bg', '--g-raise', '--g-raise-2', '--g-line', '--g-line-soft',
  '--g-paper', '--g-mist', '--g-mist-2',
  '--g-accent', '--g-accent-2', '--g-accent-wash', '--g-mark-2',
  '--g-glass', '--g-glass-2', '--g-scrim', '--g-rail-bg', '--g-grain-a',
  '--g-sky-1', '--g-sky-2', '--g-vignette',
  '--g-aura-1', '--g-aura-2', '--g-halo-x', '--g-mood-k', '--g-mark-a',
  '--g-rail-fill', '--g-bar-fill', '--g-bubble-fill', '--g-pane-fill',
  '--g-rail-icon', '--g-bar-icon',
  '--g-t1', '--g-t2', '--g-t3', '--g-t4', '--g-t5',
  '--g-fill', '--g-e1', '--g-e2', '--g-e3',
] as const;

export type SpectrumProperty = (typeof SPECTRUM_PROPERTIES)[number];
export type Spectrum = Record<SpectrumProperty, string>;

/** The continuous palette at one solar position. Every value here is a plain colour or gradient string,
    ready for `style.setProperty` — never a class, never an attribute. It is written on the document element,
    which is the one element that declares the four `:root[data-hour]` blocks, so an inline value outranks the
    static palette and an element below it that also carries `data-hour` cannot shadow it. It could, and did,
    while those blocks were written as a bare `[data-hour]`: a declaration on the element beats its parent's
    inline style, so every value here reached the root and nothing below it — the module worked, and the page
    showed the four static rooms. */
export function spectrumAt(position: SolarPosition, scheme: Scheme = 'system'): Spectrum {
  const ascending = position.hourAngle < 0;
  /* 'system' walks the altitude-keyed regime exactly as this module always has — criticalAt and skyAt below
     are untouched by the scheme axis. A forced scheme instead walks its own four-anchor clock (see the
     header's section 4), which never flips regime because it never leaves its own family, and hands the
     material rules straight to materialsAt rather than deriving them from an altitude a forced family does
     not consult for anything else either. */
  const c = scheme === 'dark' ? atClock(position.hourAngle, DARK_ANCHORS, mixCritical)
    : scheme === 'light' ? atClock(position.hourAngle, LIGHT_ANCHORS, mixCritical)
    : criticalAt(position.altitude, ascending);
  const s = saturatedSky(
    scheme === 'dark' ? atClock(position.hourAngle, DARK_SKY_ANCHORS, mixSky)
      : scheme === 'light' ? atClock(position.hourAngle, LIGHT_SKY_ANCHORS, mixSky)
      : skyAt(position.altitude, position.hourAngle, ascending),
    SKY_CHROMA);
  const rules = scheme === 'dark' ? DARK_RULES : scheme === 'light' ? LIGHT_RULES : rulesFor(position.altitude, ascending);
  /* The translucent ladder belongs to whoever decides whether this page is dark or light, and since the
     scheme arrived that is no longer the sun. It used to live only in the `[data-hour]` blocks, which
     still follow the sun - so a reader who forced dark at daybreak got a page painted dark by the
     spectrum and washes cut for a light one. On the welcome screen that showed as a pale slab across
     the "New conversation" row with its own shortcut invisible inside it. Same alphas as the static
     blocks; only the direction is decided here. */
  const wash = rules === DARK_RULES ? '255, 255, 255' : '16, 24, 40';
  const washAlpha = rules === DARK_RULES
    ? ['0.015', '0.04', '0.055', '0.08', '0.10']
    : ['0.022', '0.038', '0.055', '0.08', '0.105'];
  const t1 = 'rgba(' + wash + ', ' + washAlpha[0] + ')';
  const t2 = 'rgba(' + wash + ', ' + washAlpha[1] + ')';
  /* --g-fill and the three elevation shadows are the same trap the ladder above was just pulled out of:
     tokens.css declares them only inside the static `[data-hour]` blocks, which still follow the sun, so a
     forced scheme disagreeing with the sun's own hour got the WRONG family's card. `--g-fill` is a light-hour
     near-opaque white gradient on a light page, and the same value under a forced dark scheme at an actual
     light sun-hour is exactly the pale slab this ticket reported under the rail's "New conversation" row — a
     dark reader's pale ink landing on a card painted for paper. The three shadows carry the same two-value
     split (a bright inset highlight for a white card, a darker inset for a dark one) and were never reported
     only because a wrong highlight reads as an odd edge rather than as unreadable text — but it is the same
     bug, on every raised surface in the product, so it is fixed the same way and in the same commit. Two
     family values each, taken from the hand-tuned static blocks verbatim (dark: NIGHT_C's and GOLDEN_C's own
     values, which already agree; light: the shared daybreak/noon block's), so the fallback a reader with
     JavaScript off sees is unchanged — only which one a forced scheme's *inline* value now takes over. */
  const isDark = rules === DARK_RULES;
  const fill = isDark ? 'linear-gradient(180deg, ' + t2 + ', ' + t1 + ')'
    : 'linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.52))';
  /* THE THREE ELEVATIONS, and the two families state depth in completely different ways because the two
     grounds allow completely different things.

     On PAPER a surface floats by casting. The shadows are faint and WIDE - the far layer is a 30-80px
     blur at eight to thirty per cent - because a tight dark shadow under a white card on a pale field
     reads as a border, and a border does not lift anything. Measured on this page at the hour where the
     sky is palest: the rail, the field and the composer all sat within a few per cent of white, and with
     the old tight shadows nothing on the page had any height at all.

     In the DARK a shadow has nothing to fall on: black on near-black is invisible, so depth has to be
     drawn on the object itself. Each level takes a 1px inset ring of white - 6%, 8%, 10% - which defines
     the card's edge without lightening its middle. That is the difference between a dark card and a card
     that has been washed grey, which is what happens when you try to separate dark surfaces with fills.

     Both families keep the paper highlight on the top edge only where it belongs: on paper. */
  const e1 = isDark ? 'inset 0 0 0 1px rgba(255,255,255,0.06), 0 1px 2px rgba(0,0,0,0.34)'
    : 'inset 0 1px 0 rgba(255,255,255,0.95), 0 1px 2px rgba(16,24,40,0.05), 0 4px 12px -4px rgba(16,24,40,0.07)';
  const e2 = isDark ? 'inset 0 0 0 1px rgba(255,255,255,0.08), 0 2px 6px rgba(0,0,0,0.30), 0 14px 32px -12px rgba(0,0,0,0.55)'
    : 'inset 0 1px 0 rgba(255,255,255,0.95), 0 2px 6px rgba(16,24,40,0.06), 0 14px 34px -10px rgba(16,24,40,0.15)';
  const e3 = isDark ? 'inset 0 0 0 1px rgba(255,255,255,0.10), 0 6px 16px rgba(0,0,0,0.34), 0 36px 80px -30px rgba(0,0,0,0.76)'
    : 'inset 0 1px 0 rgba(255,255,255,0.95), 0 6px 16px rgba(16,24,40,0.07), 0 34px 76px -28px rgba(16,24,40,0.28)';
  const d = decorativeAt(position.hourAngle);
  /* The middle of the page is not the top of it: the gradient's second stop dominates the band the reader's
     own bubble and the machine's pane sit in, so a film over that band is solved against the mid colour
     rather than against the top stop. */
  /* In sRGB, because that is what the gradient itself does between its two stops: the film is solved
     against the colour actually behind the element, not against a perceptual ideal of it. */
  const mid = mixHexValue(s.sky1, s.sky2, 0.6);
  const m = materialsAt(s.sky1, mid, c.accent, c.mist, rules);
  return {
    '--g-void': c.voidHex, '--g-bg': c.bg, '--g-raise': c.raise, '--g-raise-2': c.raise2,
    '--g-line': c.line, '--g-line-soft': c.lineSoft,
    '--g-paper': c.paper, '--g-mist': c.mist, '--g-mist-2': c.mist2,
    '--g-accent': c.accent, '--g-accent-2': c.accent2, '--g-accent-wash': c.accentWash, '--g-mark-2': c.mark2,
    '--g-glass': c.glass, '--g-glass-2': c.glass2, '--g-scrim': c.scrim,
    '--g-rail-bg': 'linear-gradient(180deg, ' + c.railStop1 + ', ' + c.railStop2 + ')',
    '--g-grain-a': String(round3(c.grainA)),
    '--g-sky-1': s.sky1, '--g-sky-2': s.sky2, '--g-vignette': s.vignette,
    '--g-aura-1': d.aura1, '--g-aura-2': d.aura2,
    '--g-halo-x': round3(d.haloX).toFixed(1) + '%',
    '--g-mood-k': String(round3(d.moodK)), '--g-mark-a': String(round3(d.markA)),
    '--g-rail-fill': m.rail, '--g-bar-fill': m.bar, '--g-bubble-fill': m.bubble, '--g-pane-fill': m.pane,
    '--g-rail-icon': m.railIcon, '--g-bar-icon': m.barIcon,
    '--g-t1': t1,
    '--g-t2': t2,
    '--g-t3': 'rgba(' + wash + ', ' + washAlpha[2] + ')',
    '--g-t4': 'rgba(' + wash + ', ' + washAlpha[3] + ')',
    '--g-t5': 'rgba(' + wash + ', ' + washAlpha[4] + ')',
    '--g-fill': fill, '--g-e1': e1, '--g-e2': e2, '--g-e3': e3,
  };
}

/** Paints the continuous spectrum onto an element — the document element in practice, which is the element
    the `:root[data-hour]` blocks declare on, making this the single writer of every property in
    SPECTRUM_PROPERTIES and a `:root[data-hour]` block its single static owner. */
export function applySpectrum(el: HTMLElement, spectrum: Spectrum): void {
  SPECTRUM_PROPERTIES.forEach(name => el.style.setProperty(name, spectrum[name]));
}

/** Undoes exactly what applySpectrum set, so an element that stops painting the spectrum (Field unmounting)
    falls back to whatever `:root[data-hour]` or the base `:root` was already declaring, rather than freezing
    on the last instant it painted. */
export function clearSpectrum(el: HTMLElement): void {
  SPECTRUM_PROPERTIES.forEach(name => el.style.removeProperty(name));
}
