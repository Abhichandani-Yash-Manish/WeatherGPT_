/* The mark.
   ============================================================================
   A meridian is the line the sun crosses at local noon, and it is the one piece of iconography this
   product can wear honestly: it is about a place, and a time, and where the sun stands between them.

   So the mark is drawn rather than photographed, and the one thing that moves in it is true. The ring is
   the horizon; the vertical line is the meridian itself; the arc is the sun's path across this day at the
   reader's own held place; and the single filled dot is where the sun actually stands right now. Below the
   horizon the dot goes hollow and the arc dims, which is how the mark reads at midnight without anybody
   having to draw a moon.

   It replaces a 32x32 PNG that was being scaled to 150% of its own box in the rail and to 36px beside
   every answer, which is why it read as a grey smudge with a notch in it.

   WHAT IT DOES NOT SAY. Nothing about weather, ever. No condition, no warning, no confidence. A reader who
   reads anything meteorological off this mark has read something that is not there - it states the time of
   day, which is the same and only claim the welcome's dial has always made. */

import { useEffect, useId, useState } from 'react';
import { solarPosition } from './fieldPaint';
import { useWorkingPlace } from '../modules/Evidence';

const DEFAULT_LATITUDE = 23.0;
const DEFAULT_LONGITUDE = 82.5;

/** Where on the arc the sun sits, 0 at sunrise through 1 at sunset, and whether it is up at all. */
function sunOnArc(latitude: number, longitude: number, at: Date): { t: number; up: boolean } {
  const { altitude, hourAngle } = solarPosition(latitude, longitude, at);
  /* The hour angle runs −90° at sunrise to +90° at sunset, which is already the arc's own parameter. */
  return { t: Math.max(0, Math.min(1, (hourAngle + 90) / 180)), up: altitude > 0 };
}

export function Mark({ size = 32, className }: { size?: number; className?: string }) {
  const held = useWorkingPlace();
  const latitude = held?.latitude ?? DEFAULT_LATITUDE;
  const longitude = held?.longitude ?? DEFAULT_LONGITUDE;
  const [now, setNow] = useState(() => new Date());
  /* The mark is drawn in the rail and again beside every answer, so the clip path needs an id of its own
     per instance rather than one shared literal - identical geometry would have survived the collision,
     but a duplicate id in the document is a defect waiting for the geometry to stop being identical.
     React's own id carries delimiters that are legal in a fragment reference and illegal in a CSS selector,
     so they are stripped rather than trusted to stay resolvable. */
  const clip = 'g-mark' + useId().replace(/[^a-zA-Z0-9]/g, '');
  useEffect(() => {
    /* The same minute the ground repaints on. The sun does not need watching more closely than that, and a
       mark that re-renders on a timer faster than a reader can perceive is a timer spent on nothing. */
    const timer = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  const { t, up } = sunOnArc(latitude, longitude, now);
  /* The arc is a half-ellipse across the ring, sitting a little above centre so the horizon line has room
     to read as ground rather than as a diameter. */
  const cx = 2 + t * 28;
  const cy = 20 - Math.sin(t * Math.PI) * 11;

  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
      data-daylight={up ? 'true' : 'false'}
    >
      {/* The horizon. */}
      <circle cx="16" cy="16" r="14.25" stroke="currentColor" strokeWidth="1.1" opacity="0.38" />
      {/* The meridian: the line the sun crosses at local noon. */}
      <line x1="16" y1="1.75" x2="16" y2="30.25" stroke="currentColor" strokeWidth="1.1" opacity="0.18" />
      {/* The ground line. */}
      <line x1="3.6" y1="20" x2="28.4" y2="20" stroke="currentColor" strokeWidth="1.1" opacity="0.26" />
      {/* Today's path, clipped to the ring so a low sun does not push the arc outside the horizon. */}
      <clipPath id={clip}>
        <circle cx="16" cy="16" r="14.25" />
      </clipPath>
      <g clipPath={`url(#${clip})`}>
        <path
          d="M2 20 A 14 11 0 0 1 30 20"
          stroke="currentColor"
          strokeWidth="1.1"
          strokeLinecap="round"
          opacity={up ? 0.55 : 0.2}
        />
        {/* The sun itself. Filled above the horizon, hollow below it. */}
        <circle
          cx={cx}
          cy={cy}
          r="3.1"
          fill={up ? 'currentColor' : 'none'}
          stroke="currentColor"
          strokeWidth="1.1"
          opacity={up ? 0.95 : 0.5}
        />
      </g>
    </svg>
  );
}
