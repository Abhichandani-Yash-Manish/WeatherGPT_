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
   decides the STRUCTURE of the page — `[data-hour]` in tokens.css is what a reader with JavaScript off sees,
   and what every colour below still falls back to — but with JavaScript on, this component repaints the
   twenty-four custom properties spectrum.ts owns every minute, from the sun's own position at the reader's
   own place, so the page drifts continuously through the day instead of stepping between four rooms. The
   place is read the same way Welcome.tsx reads it — this browser's held place, or the national default — so
   the two screens are never lit from two different suns. */

import { useEffect } from 'react';
import { SkyGlyphIcon, type SkyGlyph } from '../shell/icons';
import { solarPosition } from './fieldPaint';
import { applySpectrum, clearSpectrum, spectrumAt } from './spectrum';
import { useWorkingPlace } from '../modules/Evidence';

const DEFAULT_LATITUDE = 23.0;
const DEFAULT_LONGITUDE = 82.5;

export function Field({ expanded, sky = null }: { expanded: boolean; sky?: SkyGlyph | null }) {
  const held = useWorkingPlace();
  const latitude = held?.latitude ?? DEFAULT_LATITUDE;
  const longitude = held?.longitude ?? DEFAULT_LONGITUDE;

  useEffect(() => {
    const root = document.documentElement;
    const paint = () => applySpectrum(root, spectrumAt(solarPosition(latitude, longitude, new Date())));
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
  }, [latitude, longitude]);

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
