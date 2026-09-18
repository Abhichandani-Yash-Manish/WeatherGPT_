/* The sun, for a place and an instant.
   ============================================================================
   NOAA's solar position approximation (Meeus), accurate to well under a degree — enough to know whether it is
   night, dusk or day at a place, which is the only thing the atmosphere layer asks. This is astronomy, not
   weather: it is true everywhere and it cannot fabricate a condition. */

export type SolarPosition = { altitude: number; azimuth: number };
export type SkyPhase = 'night' | 'dawn' | 'day' | 'dusk';

const rad = (d: number) => (d * Math.PI) / 180;
const deg = (r: number) => (r * 180) / Math.PI;

export function solarPosition(latitude: number, longitude: number, at: Date): SolarPosition {
  const ms = at.getTime();
  const jd = ms / 86_400_000 + 2_440_587.5;
  const t = (jd - 2_451_545) / 36_525;
  const L0 = (280.46646 + t * (36_000.76983 + t * 0.0003032)) % 360;
  const M = 357.52911 + t * (35_999.05029 - 0.0001537 * t);
  const e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t);
  const C = Math.sin(rad(M)) * (1.914602 - t * (0.004817 + 0.000014 * t)) + Math.sin(rad(2 * M)) * (0.019993 - 0.000101 * t) + Math.sin(rad(3 * M)) * 0.000289;
  const trueLong = L0 + C;
  const omega = 125.04 - 1934.136 * t;
  const lambda = trueLong - 0.00569 - 0.00478 * Math.sin(rad(omega));
  const eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60;
  const eps = eps0 + 0.00256 * Math.cos(rad(omega));
  const decl = deg(Math.asin(Math.sin(rad(eps)) * Math.sin(rad(lambda))));
  const y = Math.tan(rad(eps / 2)) ** 2;
  const eqTime = 4 * deg(y * Math.sin(2 * rad(L0)) - 2 * e * Math.sin(rad(M)) + 4 * e * y * Math.sin(rad(M)) * Math.cos(2 * rad(L0)) - 0.5 * y * y * Math.sin(4 * rad(L0)) - 1.25 * e * e * Math.sin(2 * rad(M)));
  const minutes = ((ms / 60_000) % 1440 + 1440) % 1440;
  const trueSolar = (minutes + eqTime + 4 * longitude + 1440) % 1440;
  const hourAngle = trueSolar / 4 - 180;
  const lat = rad(latitude);
  const zenith = deg(Math.acos(Math.sin(lat) * Math.sin(rad(decl)) + Math.cos(lat) * Math.cos(rad(decl)) * Math.cos(rad(hourAngle))));
  let azimuth = deg(Math.acos(((Math.sin(lat) * Math.cos(rad(zenith))) - Math.sin(rad(decl))) / (Math.cos(lat) * Math.sin(rad(zenith)))));
  azimuth = hourAngle > 0 ? (azimuth + 180) % 360 : (540 - azimuth) % 360;
  return { altitude: 90 - zenith, azimuth };
}

export function phaseFor(altitude: number): SkyPhase {
  if (altitude < -8) return 'night';
  if (altitude < 4) return 'dawn';
  if (altitude < 12) return 'dusk';
  return 'day';
}

/** Dawn and dusk share a palette; which one it is comes from whether the sun is rising. */
export function phaseAt(latitude: number, longitude: number, at: Date): { phase: SkyPhase; position: SolarPosition; rising: boolean } {
  const position = solarPosition(latitude, longitude, at);
  const later = solarPosition(latitude, longitude, new Date(at.getTime() + 600_000));
  const rising = later.altitude > position.altitude;
  let phase = phaseFor(position.altitude);
  if ((phase === 'dawn' || phase === 'dusk') && position.altitude >= -8 && position.altitude < 12) phase = rising ? 'dawn' : 'dusk';
  return { phase, position, rising };
}
