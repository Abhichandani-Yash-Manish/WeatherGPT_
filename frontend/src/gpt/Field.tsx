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
      <canvas ref={canvas} className="g-field-canvas" />
    </div>
  );
}
