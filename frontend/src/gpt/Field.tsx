/* The ground.
   ============================================================================
   Five CSS layers, no canvas and no image. The hour is decided by the sun's real altitude at the reader's
   own place (fieldPaint.ts), so dusk arrives when the sun sets rather than when a clock says so.

   The layer a reading can move is the mood, and it is deliberately the quietest: when the nearest station
   PRINTED a condition, the ground takes that condition's colour — a wash at a fifth of full strength over
   the hour's own sky, and a glyph at five percent. Nothing here invents a condition; a station that printed
   none leaves the ground as astronomy alone. That is what a subtle weather detail in the background can
   mean on a product where the answer has to stay the subject.

   The grain layer is the one that earns its place: a large flat gradient on an 8-bit display bands into
   visible steps, and those bands are a real part of what makes a dark interface read as cheap. Three
   percent of monochrome turbulence removes them.

   `expanded` is the only input the conversation gives the ground: the welcome commits — the auras open up
   and the gradient saturates — and the moment a question is asked it all steps back, because from then on
   the answer is the subject and the ground is only weather.

   There used to be a sixth layer, a horizon hairline, which was the whole of the depth when the ground was
   a flat near-black. The gradient carries that now, and at welcome strength the line read as a rule drawn
   across the middle of the greeting.

   The hour used to be the finest grain this page moved in: four palettes, a hard edge between each. It still
   decides the STRUCTURE of the page — `:root[data-hour]` in tokens.css is what a reader with JavaScript off
   sees, and what every colour below still falls back to — but with JavaScript on, this component repaints the
   thirty-two custom properties spectrum.ts owns every minute, from the sun's own position at the reader's own
   place, so the page drifts continuously through the day instead of stepping between four rooms. The place is
   read the same way Welcome.tsx reads it — this browser's held place, or the national default — so the two
   screens are never lit from two different suns.

   The element this paints is the document element, and that is exact rather than convenient: the four static
   hour blocks are declared as `:root[data-hour]`, so `<html>` is the one owner of every property in the list
   and this is its one writer. The `.g` element carries the same attribute for the scripts that read it and
   for the structural selectors that key off it, and it declares none of these properties — which is what
   makes the inline palette reach the reader. (It did not, before: a bare `[data-hour]` block matched `.g`
   too, and a declaration on the element beats its parent's inline style. docs/134 has the two values side by
   side.)

   THE SCHEME. A reader's colour-scheme choice is read from two places, in order: an explicit `data-theme`
   attribute on the document element — 'light' or 'dark' — for a future in-product control that has not been
   built yet but whose contract this component already honours; and failing that, the browser's own
   `prefers-color-scheme`, which is the one signal this product can already observe today and the one the
   evidence tool's own captures set (`colorScheme: 'dark' | 'light'` in tools/capture.mjs). Neither matching is
   what spectrumAt calls 'system': that is reserved for a browser that states no preference at all, which is
   rare but real (some Linux desktops, and jsdom's own stub), and it is the only case that still lets the sun
   alone choose the family. Everywhere else, a reader who set their OS or browser to dark does not want this
   page going white on them at noon — so their choice picks the family, and the sun is left only to drift
   inside it, which spectrum.ts's own header (section 4) explains. */

import { useEffect, useState } from 'react';
import { SkyGlyphIcon, type SkyGlyph } from '../shell/icons';
import { solarPosition } from './fieldPaint';
import { applySpectrum, clearSpectrum, spectrumAt, type Scheme } from './spectrum';
import { useWorkingPlace } from '../modules/Evidence';

const DEFAULT_LATITUDE = 23.0;
const DEFAULT_LONGITUDE = 82.5;

/** The scheme in force right now, read fresh each time it might have changed rather than cached — a reader's
    explicit choice and their OS preference can both change while this page stays open. */
function currentScheme(): Scheme {
  if (typeof document !== 'undefined') {
    const explicit = document.documentElement.dataset.theme;
    if (explicit === 'dark' || explicit === 'light') return explicit;
  }
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
    if (window.matchMedia('(prefers-color-scheme: light)').matches) return 'light';
  }
  return 'system';
}

export function Field({ expanded, sky = null }: { expanded: boolean; sky?: SkyGlyph | null }) {
  const held = useWorkingPlace();
  const latitude = held?.latitude ?? DEFAULT_LATITUDE;
  const longitude = held?.longitude ?? DEFAULT_LONGITUDE;
  const [scheme, setScheme] = useState<Scheme>(currentScheme);

  /* The browser's half of the scheme: a MediaQueryList fires 'change' the instant the OS toggles dark mode
     under this page, and both queries are watched because a reader can also go FROM an explicit OS preference
     TO none (rare, but the fallback above has to be re-read either way). */
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    const dark = window.matchMedia('(prefers-color-scheme: dark)');
    const light = window.matchMedia('(prefers-color-scheme: light)');
    const onChange = () => setScheme(currentScheme());
    dark.addEventListener('change', onChange);
    light.addEventListener('change', onChange);
    return () => {
      dark.removeEventListener('change', onChange);
      light.removeEventListener('change', onChange);
    };
  }, []);

  /* The product's own half: a future settings control sets `data-theme` on the document element rather than
     calling into this component directly, so this watches the attribute itself instead of assuming who wrote
     it. */
  useEffect(() => {
    if (typeof MutationObserver === 'undefined') return;
    const observer = new MutationObserver(() => setScheme(currentScheme()));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    const paint = () => applySpectrum(root, spectrumAt(solarPosition(latitude, longitude, new Date()), scheme));
    paint();
    /* A minute is finer than a reader can tell apart and coarse enough to cost nothing: the spectrum is a
       colour, not an animation, so nothing here needs a rAF loop or is gated by prefers-reduced-motion — the
       CSS transitions that turn this minute-to-minute change into a visible drift are the same ones the
       stylesheets already still under that preference (surfaces.css). */
    const timer = window.setInterval(paint, 60_000);
    return () => {
      window.clearInterval(timer);
      clearSpectrum(root);
    };
  }, [latitude, longitude, scheme]);

  return (
    <div className="g-field" data-expanded={expanded ? 'true' : 'false'} data-sky={sky || 'none'} aria-hidden="true">
      <div className="g-field-sky" />
      <div className="g-field-halo" />
      <div className="g-field-mood" />
      <div className="g-field-grain" />
      <div className="g-field-vignette" />
      {sky ? (
        <div className="g-field-mark">
          <SkyGlyphIcon glyph={sky} size={320} strokeWidth={0.32} />
        </div>
      ) : null}
    </div>
  );
}
