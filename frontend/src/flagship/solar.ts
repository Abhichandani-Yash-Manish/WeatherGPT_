/* The sun, as the atmosphere needs it.
   ============================================================================
   docs/110 is explicit about what the sky is: an atmosphere computed from the sun at the reader's own place and
   hour, resolved to four phases, with the sun's glow positioned by its real azimuth and altitude. The shell was
   bucketing the clock instead — a local solar hour, with latitude explicitly discarded — so a place at 8°N and a
   place at 34°N lit identically, and the glow had no position to sit at.

   This is the NOAA/Meeus low-precision solar position: declination from the day of year, the equation of time, the
   hour angle, then altitude and azimuth. It is accurate to a few arc-minutes, which is far finer than a gradient
   can show, and it is deterministic, so the same instant renders the same light in a test and in a browser.

   Nothing here reads a weather source. Astronomy is true everywhere, which is what makes it safe to paint. */

export type SolarPosition = { altitude: number; azimuth: number };

const RAD = Math.PI / 180;
const DEG = 180 / Math.PI;

export function solarPosition(latitude: number, longitude: number, at: Date): SolarPosition {
  const dayOfYear = Math.floor((at.getTime() - Date.UTC(at.getUTCFullYear(), 0, 0)) / 86_400_000);
  const declination = 23.44 * Math.sin((2 * Math.PI * (dayOfYear - 81)) / 365) * RAD;
  const utcHours = at.getUTCHours() + at.getUTCMinutes() / 60 + at.getUTCSeconds() / 3600;
  /* Apparent solar time, not mean: the equation of time is worth up to sixteen minutes, and near the horizon
     sixteen minutes is four degrees of altitude — enough to move a sunrise out of its own phase. */
  const b = (2 * Math.PI * (dayOfYear - 81)) / 364;
  const equationOfTime = (9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b)) / 60;
  const solarHours = utcHours + longitude / 15 + equationOfTime;
  const hourAngle = (solarHours - 12) * 15 * RAD;
  const lat = latitude * RAD;
  const altitude =
    Math.asin(Math.sin(lat) * Math.sin(declination) + Math.cos(lat) * Math.cos(declination) * Math.cos(hourAngle)) * DEG;
  const azimuth =
    (180 +
      Math.atan2(Math.sin(hourAngle), Math.cos(hourAngle) * Math.sin(lat) - Math.tan(declination) * Math.cos(lat)) * DEG +
      360) %
    360;
  return { altitude, azimuth };
}

/** The four phases of the sky, from the sun itself rather than from the clock. */
export type SkyPhase = 'night' | 'dawn' | 'day' | 'dusk';

export function phaseOf({ altitude, azimuth }: SolarPosition): SkyPhase {
  if (altitude < -6) return 'night';
  if (altitude < 8) return azimuth < 180 ? 'dawn' : 'dusk';
  return 'day';
}

/** Where the light comes from, as a point on the page: 0..1 across and 0..1 down. */
export function glowPoint({ altitude, azimuth }: SolarPosition): { x: number; y: number } {
  /* The azimuth is mapped across the page with east on the left, and the altitude down it with the horizon a
     fifth of the way up from the foot — so a low sun sits near the horizon and a high one near the top. */
  const x = Math.min(0.94, Math.max(0.06, 0.5 - Math.sin(azimuth * RAD) * 0.44));
  const y = Math.min(0.9, Math.max(0.08, 0.78 - Math.max(0, altitude) / 90 * 0.62 + Math.max(0, -altitude) / 18 * 0.12));
  return { x, y };
}

/** How strong the glow is: a sun on the horizon is the strongest light of the day, and a deep night has none. */
export function glowStrength({ altitude }: SolarPosition): number {
  if (altitude < -6) return 0;
  return Math.min(1, Math.max(0, 1 - Math.abs(altitude) / 26));
}
