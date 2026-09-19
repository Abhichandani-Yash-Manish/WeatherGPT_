/* The ground.
   ============================================================================
   Five layers, no canvas and no image. The hour is decided by the sun's real altitude at the reader's own
   place (fieldPaint.ts), so dusk arrives when the sun sets rather than when a clock says so — but nothing
   here ever states a condition, and there is no weather in this file.

   The grain layer is the one that earns its place: a large flat gradient on an 8-bit display bands into
   visible steps, and those bands are a real part of what makes a dark interface read as cheap. Three
   percent of monochrome turbulence removes them.

   `expanded` is the only input the conversation gives the ground: once an answer exists the light drops
   and the horizon nearly goes, because the answer is the subject. */

import type { Hour } from './fieldPaint';

export function Field({ expanded }: { hour: Hour; expanded: boolean }) {
  return (
    <div className="g-field" data-expanded={expanded ? 'true' : 'false'} aria-hidden="true">
      <div className="g-field-sky" />
      <div className="g-field-halo" />
      <div className="g-field-grain" />
      <div className="g-field-vignette" />
      <div className="g-field-horizon" />
    </div>
  );
}
