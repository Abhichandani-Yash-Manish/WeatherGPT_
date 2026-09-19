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
   across the middle of the greeting. */

import { SkyGlyphIcon, type SkyGlyph } from '../shell/icons';

export function Field({ expanded, sky = null }: { expanded: boolean; sky?: SkyGlyph | null }) {
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
