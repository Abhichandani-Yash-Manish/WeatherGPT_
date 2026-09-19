/* Which hour the ground is in.
   ============================================================================
   Astronomy decides, never a reading. The sun's altitude at the reader's own place and instant, by the
   standard NOAA/Meeus approximation with the equation of time included — so a place at 8°N and a place at
   34°N do not light identically, and dusk arrives when the sun sets rather than when a clock says so.

   Four names, because the ground has four palettes. Nothing here is a weather statement. */

export type Hour = 'daybreak' | 'noon' | 'golden' | 'night';

const rad = (d: number) => (d * Math.PI) / 180;
const deg = (r: number) => (r * 180) / Math.PI;

/** The sun's altitude above the horizon, in degrees. */
export function solarAltitude(latitude: number, longitude: number, at: Date): number {
  const ms = at.getTime();
  const jd = ms / 86_400_000 + 2_440_587.5;
  const t = (jd - 2_451_545) / 36_525;
  const L0 = (280.46646 + t * (36_000.76983 + t * 0.0003032)) % 360;
  const M = 357.52911 + t * (35_999.05029 - 0.0001537 * t);
  const e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t);
  const C =
    Math.sin(rad(M)) * (1.914602 - t * (0.004817 + 0.000014 * t)) +
    Math.sin(rad(2 * M)) * (0.019993 - 0.000101 * t) +
    Math.sin(rad(3 * M)) * 0.000289;
  const omega = 125.04 - 1934.136 * t;
  const lambda = L0 + C - 0.00569 - 0.00478 * Math.sin(rad(omega));
  const eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60;
  const eps = eps0 + 0.00256 * Math.cos(rad(omega));
  const decl = deg(Math.asin(Math.sin(rad(eps)) * Math.sin(rad(lambda))));
  const y = Math.tan(rad(eps / 2)) ** 2;
  /* The equation of time: up to sixteen minutes, which is four degrees near the horizon — enough to put
     the ground in the wrong phase at dawn if it is left out. */
  const eqTime =
    4 *
    deg(
      y * Math.sin(2 * rad(L0)) -
        2 * e * Math.sin(rad(M)) +
        4 * e * y * Math.sin(rad(M)) * Math.cos(2 * rad(L0)) -
        0.5 * y * y * Math.sin(4 * rad(L0)) -
        1.25 * e * e * Math.sin(2 * rad(M)),
    );
  const minutes = (((ms / 60_000) % 1440) + 1440) % 1440;
  const trueSolar = (minutes + eqTime + 4 * longitude + 1440) % 1440;
  const hourAngle = trueSolar / 4 - 180;
  const lat = rad(latitude);
  const cosZenith =
    Math.sin(lat) * Math.sin(rad(decl)) + Math.cos(lat) * Math.cos(rad(decl)) * Math.cos(rad(hourAngle));
  return 90 - deg(Math.acos(Math.min(1, Math.max(-1, cosZenith))));
}

/** The ground's hour, from the sun's own altitude at this place. */
export function hourOf(at: Date, latitude = 23.0, longitude = 82.5): Hour {
  const altitude = solarAltitude(latitude, longitude, at);
  if (altitude < -6) return 'night';
  if (altitude < 8) {
    /* Rising or setting decides which side of the day a low sun belongs to. */
    const later = solarAltitude(latitude, longitude, new Date(at.getTime() + 900_000));
    return later > altitude ? 'daybreak' : 'golden';
  }
  if (altitude < 22) return 'golden';
  return 'noon';
}
