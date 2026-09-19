/* The ground.
   ============================================================================
   Three layers, all CSS: a gradient that shifts with the hour, one halo where the light is, and a single
   horizon hairline. That hairline is the whole of the depth — Firewatch's six parallax planes reduced to
   the one edge that actually creates the illusion, because at this contrast range anything more reads as
   an illustration, and six directions have now proved an illustration is wrong here.

   It states the hour and nothing else. No condition is ever drawn. */

import { hourOf, type Hour } from './fieldPaint';

export function useHour(at: Date, latitude?: number, longitude?: number): Hour {
  return hourOf(at, latitude, longitude);
}

export function Field({ expanded }: { hour: Hour; expanded: boolean }) {
  return (
    <div className="g-field" data-expanded={expanded ? 'true' : 'false'} aria-hidden="true">
      <div className="g-field-sky" />
      <div className="g-field-halo" />
      <div className="g-field-horizon" />
    </div>
  );
}
