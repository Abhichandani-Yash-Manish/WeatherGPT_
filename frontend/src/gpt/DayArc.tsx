/* The day arc.
   ============================================================================
   The front door's hero, and the third thing to stand there. It was a 96px moon in a blurred halo; then a
   240px clock face, which was better and still a widget - a small round object sitting in the corner of a
   wide screen while the type did all the work.

   This is the same astronomy drawn as what it actually is: a PLOT. The sun's altitude across today,
   spanning the full width of the column, with the daylight filled in.

     the horizon       a rule across the whole width, at altitude zero
     the curve         the sun's real altitude, sampled every ten minutes across the IST day at the
                       reader's own place. It is not a half-circle: at 23 degrees north in December the sun
                       neither rises due east nor passes through the zenith, and a drawn semicircle would
                       be claiming it does
     the fill          the daylight, in the one saturated colour this palette has. This is the only place
                       on the product where a large area of colour appears, and it is the reason the front
                       door has any force at all
     the night         the same curve below the horizon, compressed and dashed, because a true altitude
                       scale at midnight would need four times the height to say nothing
     the crossings     sunrise and sunset, marked and labelled where the curve actually crosses
     the sun          where it is now, filled above the horizon and hollow below it

   WHY THIS AND NOT A LOGO. Every number on it is true and checkable against an almanac, and it visibly
   moves over a morning. It is the one piece of iconography this product can wear without claiming anything
   it has not read: sunrise is not a forecast, and day length is not an opinion.

   WHAT IT DOES NOT SAY. Nothing about weather. No condition, no warning, no confidence, no temperature. A
   station's own reading is a separate element with a separate source line, and it always will be. */

import { useMemo } from 'react';
import { solarAltitude } from './fieldPaint';

/** India Standard Time, which every clock in this product is stated in. */
const IST_OFFSET_HOURS = 5.5;

/** The hour of the IST day, as a fraction, for an instant. */
export function istHour(at: Date): number {
  const shifted = at.getTime() / 3_600_000 + IST_OFFSET_HOURS;
  return ((shifted % 24) + 24) % 24;
}

/** Which IST calendar day an instant falls on, counted from the epoch. */
function istDay(at: Date): number {
  return Math.floor((at.getTime() / 3_600_000 + IST_OFFSET_HOURS) / 24);
}

/** An IST hour on the same IST calendar day as `at`, back as an instant. */
function atIstHour(at: Date, hour: number): Date {
  return new Date((istDay(at) * 24 + hour - IST_OFFSET_HOURS) * 3_600_000);
}

export type Daylight = {
  /** IST hours of the day, or null where the sun does not cross the horizon at all. */
  sunrise: number | null;
  sunset: number | null;
  /** Hours between them, or null when there is no crossing. */
  length: number | null;
};

/**
 * Today's sunrise and sunset at a place, as IST hours.
 *
 * Solved rather than assumed. The sun's altitude is sampled across the IST day at four-minute steps, every
 * sign change across the horizon is bisected to within a few seconds, and the first upward crossing and the
 * last downward one are the answer. A place and date where the sun never crosses returns nulls, and the
 * dial draws no arc rather than drawing a wrong one - which is the same rule the rest of this product
 * follows about absent readings, applied to astronomy.
 */
export function daylightAt(latitude: number, longitude: number, at: Date): Daylight {
  const altitudeAt = (hour: number) => solarAltitude(latitude, longitude, atIstHour(at, hour));
  const STEP = 1 / 15; // four minutes
  let rise: number | null = null;
  let set: number | null = null;
  let previous = altitudeAt(0);
  for (let h = STEP; h <= 24 + 1e-9; h += STEP) {
    const current = altitudeAt(h);
    if (previous < 0 && current >= 0 && rise === null) rise = bisect(altitudeAt, h - STEP, h);
    if (previous >= 0 && current < 0) set = bisect(altitudeAt, h - STEP, h);
    previous = current;
  }
  const length = rise !== null && set !== null && set > rise ? set - rise : null;
  return { sunrise: rise, sunset: set, length };
}

/** Where a monotonic crossing sits, to within about a second. */
function bisect(f: (h: number) => number, low: number, high: number): number {
  let a = low;
  let b = high;
  for (let i = 0; i < 24; i += 1) {
    const mid = (a + b) / 2;
    if (f(a) < 0 === f(mid) < 0) a = mid;
    else b = mid;
  }
  return (a + b) / 2;
}

/** An IST hour as a clock reading. */
export function clockOf(hour: number | null): string {
  if (hour === null || !Number.isFinite(hour)) return '--:--';
  const total = Math.round(hour * 60) % (24 * 60);
  return String(Math.floor(total / 60)).padStart(2, '0') + ':' + String(total % 60).padStart(2, '0');
}

/** A span of hours as a duration. */
export function spanOf(hours: number | null): string {
  if (hours === null || !Number.isFinite(hours)) return '';
  const total = Math.round(hours * 60);
  return Math.floor(total / 60) + 'h ' + String(total % 60).padStart(2, '0') + 'm';
}

/* The plot's frame. Wide and shallow: this is a band across the top of the page, not an object in the
   corner of it. */
const W = 880;
const H = 208;
const LEFT = 26;
const RIGHT = W - 26;
const HORIZON = 150;
/* How far the curve rises at the day's own maximum, and how far it is allowed to dip at night. The night
   is compressed on purpose - a true scale would spend a hundred pixels drawing how far below the horizon
   the sun is at 2am, which is a fact nobody needs at that resolution. */
const RISE = 124;
const DIP = 34;

/** Where an IST hour sits across the band. */
function xOf(hour: number): number {
  return LEFT + (hour / 24) * (RIGHT - LEFT);
}

/** Where an altitude sits up the band, scaled to the day's own maximum so every latitude fills the frame. */
function yOf(altitude: number, peak: number): number {
  if (altitude >= 0) return HORIZON - (altitude / peak) * RISE;
  return HORIZON + Math.min(1, -altitude / 40) * DIP;
}

export type DayArcProps = {
  at: Date;
  latitude: number;
  longitude: number;
  /** The label under the day's length, translated by the caller. */
  lightLabel?: string;
};

export function DayArc({ at, latitude, longitude, lightLabel = 'of light' }: DayArcProps) {
  const dayKey = istDay(at);
  const day = useMemo(
    () => daylightAt(latitude, longitude, at),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [latitude, longitude, dayKey],
  );

  /* The curve, sampled every ten minutes. Solved once per calendar day rather than once per minute: the
     sun's path does not change between 09:14 and 09:15, only the reader's position along it does. */
  const curve = useMemo(() => {
    const points: { h: number; a: number }[] = [];
    for (let h = 0; h <= 24.0001; h += 1 / 6) {
      points.push({ h, a: solarAltitude(latitude, longitude, atIstHour(at, h)) });
    }
    return points;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latitude, longitude, dayKey]);

  const peak = Math.max(6, ...curve.map(p => p.a));
  const now = istHour(at);
  const nowAltitude = solarAltitude(latitude, longitude, at);
  const up = nowAltitude > 0;

  const path = (from: number, to: number, only: 'day' | 'night') => {
    const kept = curve.filter(p => p.h >= from && p.h <= to && (only === 'day' ? p.a >= 0 : p.a < 0));
    if (kept.length < 2) return '';
    return kept.map((p, i) => (i ? 'L' : 'M') + xOf(p.h).toFixed(1) + ' ' + yOf(p.a, peak).toFixed(1)).join(' ');
  };

  /* The lit area: the day curve, closed down to the horizon at both crossings. */
  const daylight = day.sunrise !== null && day.sunset !== null
    ? 'M' + xOf(day.sunrise).toFixed(1) + ' ' + HORIZON
      + ' ' + path(day.sunrise, day.sunset, 'day').slice(1)
      + ' L' + xOf(day.sunset).toFixed(1) + ' ' + HORIZON + ' Z'
    : '';

  const sunX = xOf(now);
  const sunY = yOf(nowAltitude, peak);

  return (
    <svg
      className="w-dayarc"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      data-daylight={up ? 'true' : 'false'}
      aria-label={
        day.sunrise === null || day.sunset === null
          ? 'A plot of the sun through today. The sun does not cross the horizon here today.'
          : `A plot of the sun through today at this place. Sunrise ${clockOf(day.sunrise)}, sunset `
            + `${clockOf(day.sunset)} IST, ${spanOf(day.length)} of daylight. The sun is currently `
            + `${up ? 'above' : 'below'} the horizon.`
      }
    >
      <defs>
        <linearGradient id="w-daylight" x1="0" y1={HORIZON - RISE} x2="0" y2={HORIZON} gradientUnits="userSpaceOnUse">
          <stop offset="0" className="w-daylight-top" />
          <stop offset="1" className="w-daylight-base" />
        </linearGradient>
      </defs>

      {/* The hours. Every three, labelled every six. */}
      {[0, 3, 6, 9, 12, 15, 18, 21, 24].map(h => (
        <line key={h} className="w-arc-tick" data-major={h % 6 === 0 ? 'true' : undefined}
              x1={xOf(h).toFixed(1)} y1={HORIZON} x2={xOf(h).toFixed(1)} y2={HORIZON + (h % 6 === 0 ? 9 : 5)} />
      ))}
      {[6, 12, 18].map(h => (
        <text key={h} className="w-arc-hour" x={xOf(h).toFixed(1)} y={HORIZON + 26} textAnchor="middle">
          {String(h).padStart(2, '0')}
        </text>
      ))}

      {/* The daylight, and it is the only large area of colour on this product. */}
      {daylight ? <path className="w-arc-fill" d={daylight} fill="url(#w-daylight)" /> : null}
      {/* The night, compressed and dashed: present, and not pretending to be to scale. */}
      <path className="w-arc-night" d={path(0, 24, 'night')} />
      {daylight ? <path className="w-arc-line" d={path(day.sunrise as number, day.sunset as number, 'day')} /> : null}

      {/* The horizon. */}
      <line className="w-arc-horizon" x1={LEFT} y1={HORIZON} x2={RIGHT} y2={HORIZON} />

      {/* Where the sun actually crosses it. */}
      {day.sunrise !== null && day.sunset !== null
        ? ([[day.sunrise, 'start'], [day.sunset, 'end']] as const).map(([h, anchor], i) => (
          <g key={i}>
            <line className="w-arc-cross" x1={xOf(h).toFixed(1)} y1={HORIZON - 7} x2={xOf(h).toFixed(1)} y2={HORIZON + 7} />
            <text className="w-arc-edge" x={(xOf(h) + (anchor === 'start' ? 8 : -8)).toFixed(1)}
                  y={HORIZON - 21} textAnchor={anchor}>
              {clockOf(h)}
            </text>
          </g>
        ))
        : null}

      {/* Now: a dropped line to the horizon and the sun on the curve. */}
      <line className="w-arc-now" x1={sunX.toFixed(1)} y1={sunY.toFixed(1)} x2={sunX.toFixed(1)} y2={HORIZON} />
      <circle className="w-arc-halo" cx={sunX.toFixed(1)} cy={sunY.toFixed(1)} r="9" data-up={up ? 'true' : 'false'} />
      <circle className="w-arc-sun" cx={sunX.toFixed(1)} cy={sunY.toFixed(1)} r="9" data-up={up ? 'true' : 'false'} />

      {/* The day's length, set beside the peak rather than in a corner. */}
      {day.length !== null ? (
        <text className="w-arc-span" x={xOf(12).toFixed(1)} y={HORIZON - RISE - 14} textAnchor="middle">
          {spanOf(day.length) + ' ' + lightLabel}
        </text>
      ) : null}
    </svg>
  );
}
