import { useEffect, useState } from 'react';
import { applySky, phaseFor } from './sky';

/* Decoration, and it says so. The band shows the local time of day; it is never a condition, never a warning
   and never a progress indicator, so it is aria-hidden, it carries no weather glyph, and the note below is the
   sentence a reader can check against the machine's own clock. */
export function SkyBackground() {
  const [phase, setPhase] = useState(() => phaseFor(new Date()));

  useEffect(() => {
    const tick = () => setPhase(applySky(phaseFor(new Date())));
    tick();
    const timer = window.setInterval(tick, 60_000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div
      className="sky-band"
      data-sky-band={phase}
      aria-hidden="true"
      title="Background shows the local time of day. It is decoration, not a weather condition."
    />
  );
}
