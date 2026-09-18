/* The field, mounted.
   ============================================================================
   One small canvas, scaled up pixelated, masked so it fades out by the middle of the page — the fade the
   user kept from 18 September. It repaints only when the hour changes and once a minute for the drift, so
   it costs nothing to keep on screen; under reduced motion it paints one still frame and stops. */

import { useEffect, useRef } from 'react';
import { hourOf, paintField, type Hour } from './fieldPaint';

export function useHour(at: Date, latitude?: number, longitude?: number): Hour {
  return hourOf(at, latitude, longitude);
}

export function Field({ hour, expanded }: { hour: Hour; expanded: boolean }) {
  const canvas = useRef<HTMLCanvasElement | null>(null);
  /* The hour that was showing, held on a canvas underneath, so a phase change is a cross-fade rather than a cut.
     paintField is deterministic in the hour, so the frame underneath is the exact one the reader was looking at,
     not an approximation of it. */
  const under = useRef<HTMLCanvasElement | null>(null);
  const previous = useRef<Hour | null>(null);

  useEffect(() => {
    const node = under.current;
    if (!node) return;
    if (previous.current && previous.current !== hour) paintField(node, { hour: previous.current, drift: 0 });
    previous.current = hour;
  }, [hour]);

  useEffect(() => {
    const node = canvas.current;
    if (!node) return;
    const still = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let frame = 0;
    let stopped = false;
    const start = Date.now();
    const draw = () => {
      if (stopped || !canvas.current) return;
      /* One full drift pass every six minutes: slow enough that it is never seen moving, present enough
         that the page is not a static image. */
      const drift = still ? 0 : ((Date.now() - start) / 360_000) % 1;
      paintField(canvas.current, { hour, drift });
      if (!still) frame = window.setTimeout(draw, 4000);
    };
    draw();
    return () => {
      stopped = true;
      window.clearTimeout(frame);
    };
  }, [hour]);

  return (
    <div className="g-field" data-expanded={expanded ? 'true' : 'false'} aria-hidden="true">
      <canvas ref={under} className="g-field-canvas g-field-under" />
      {/* Keyed on the hour, so a phase change mounts a fresh canvas and the fade in the stylesheet runs. */}
      <canvas key={hour} ref={canvas} className="g-field-canvas g-field-in" />
    </div>
  );
}
