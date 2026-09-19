/* Which hour the ground is in.
   ============================================================================
   Astronomy decides, never a reading. The sun's altitude at the reader's own place and instant, by the
   standard NOAA/Meeus approximation with the equation of time included — so a place at 8°N and a place at
   34°N do not light identically, and dusk arrives when the sun sets rather than when a clock says so.

   Four names, because the ground has four palettes. Nothing here is a weather statement. */

export type Hour = 'daybreak' | 'noon' | 'golden' | 'night';

const rad = (d: number) => (d * Math.PI) / 180;
const deg = (r: number) => (r * 180) / Math.PI;

export type SolarPosition = {
  /** Degrees above the horizon. Negative is below it. */
  altitude: number;
  /** −90° at sunrise, 0° at solar noon, +90° at sunset. Morning is negative. */
  hourAngle: number;
};

/** Where the sun stands over a place at an instant: the same approximation the hour is decided by, and
    the only thing the welcome's dial is drawn from. It states the time of day, never the weather. */
export function solarPosition(latitude: number, longitude: number, at: Date): SolarPosition {
  const { altitude, hourAngle } = solarGeometry(latitude, longitude, at);
  return { altitude, hourAngle };
}

/** The sun's altitude above the horizon, in degrees. */
export function solarAltitude(latitude: number, longitude: number, at: Date): number {
  return solarGeometry(latitude, longitude, at).altitude;
}

function solarGeometry(latitude: number, longitude: number, at: Date): SolarPosition {
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
  return { altitude: 90 - deg(Math.acos(Math.min(1, Math.max(-1, cosZenith)))), hourAngle };
}

/* The bands, in degrees of solar altitude.

   -6 is civil twilight: the sun is down but there is still usable light, which is why it is the edge of
   night rather than 0. 8 is roughly forty minutes either side of the horizon at these latitudes — long
   enough for dawn and dusk to be their own hours, short enough that the day is the day.

   The previous version gave 'golden' everything from -6 up to 22 degrees, which at 23 degrees north is
   most of the morning and most of the afternoon. That was harmless while every palette was the same
   near-black. It is not harmless now that two of the hours are light pages: it would have put the middle
   of the morning into a dusk palette. Above HORIZON the page is simply day. */
const NIGHT_BELOW = -6;
const HORIZON = 8;

/** The ground's hour, from the sun's own altitude at this place. */
export function hourOf(at: Date, latitude = 23.0, longitude = 82.5): Hour {
  const altitude = solarAltitude(latitude, longitude, at);
  if (altitude < NIGHT_BELOW) return 'night';
  if (altitude >= HORIZON) return 'noon';
  /* A low sun is either arriving or leaving, and the two look nothing alike. Sampling fifteen minutes on
     is the cheapest way to ask which, and it needs no sunrise solver. */
  const later = solarAltitude(latitude, longitude, new Date(at.getTime() + 900_000));
  return later > altitude ? 'daybreak' : 'golden';
}

/* ---- where the light is coming from ----------------------------------------------------------------
   The ground is a real sun-driven gradient, so every raised surface in this product is a pane sitting in
   that light — and a pane lit from nowhere in particular is the thing that makes glassmorphism read as a
   texture rather than as glass.

   So the catch-light on a surface's border follows the sun: the left edge at dawn, the top at noon, the
   right edge at dusk, and the shadow falls away from it. One token drives every surface, which is what
   keeps it coherent instead of decorative, and it is derived from the reader's own sky rather than chosen.

   hourAngle is the input because it is already what it means: negative through the morning, zero at solar
   noon, positive through the afternoon. Nothing here is a weather statement. */

export type Light = {
  /** Where the light stands across the page, 0 at the left edge and 1 at the right. */
  x: number;
  /** The CSS gradient angle that puts the highlight on the lit edge. 90deg is left, 180deg is top. */
  angle: number;
  /** How far a shadow is pushed away from the light, in pixels, signed. */
  shadowX: number;
  /** How high the light is, 0 on the horizon and 1 overhead. Flattens the shadow as the sun climbs. */
  height: number;
};

/** Clamp, because an hourAngle before sunrise or after sunset must not push the light off the page. */
const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));

export function lightFrom(position: SolarPosition): Light {
  /* ±90° of hour angle is roughly sunrise to sunset, and the light is kept a little inside the edges so
     that a surface at the very edge of the window still has a lit side to show. */
  const x = clamp(0.5 + position.hourAngle / 200, 0.08, 0.92);
  const height = clamp(position.altitude / 75, 0, 1);
  return {
    x,
    /* 90deg puts the gradient's start at the left edge, 270deg at the right; the light rides between them
       and passes through 180deg — the top — at solar noon. */
    angle: 90 + 180 * x,
    shadowX: Number((((0.5 - x) * 2) * 7).toFixed(2)),
    height: Number(height.toFixed(3)),
  };
}

/** The light for a place and an instant, which is what a component actually has to hand. */
export function lightAt(at: Date, latitude = 23.0, longitude = 82.5): Light {
  return lightFrom(solarPosition(latitude, longitude, at));
}
