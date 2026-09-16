/* Which sky phase the clock is in, and nothing else. Sunrise and sunset would need a source, and this
   module deliberately has none: the phase is decoration derived from the machine's own clock. A caller
   that has a sourced sun time may pass it, and the phase then follows that evidence instead. */

export type SkyPhase = 'predawn' | 'dawn' | 'day' | 'dusk' | 'night' | 'storm';

export type SunTimes = { sunrise?: string; sunset?: string };

export function phaseFor(when: Date, sun: SunTimes = {}): SkyPhase {
  const hour = when.getHours() + when.getMinutes() / 60;
  if (sun.sunrise && sun.sunset) {
    const sunrise = new Date(sun.sunrise);
    const sunset = new Date(sun.sunset);
    if (!Number.isNaN(sunrise.getTime()) && !Number.isNaN(sunset.getTime())) {
      const sunriseHour = sunrise.getHours() + sunrise.getMinutes() / 60;
      const sunsetHour = sunset.getHours() + sunset.getMinutes() / 60;
      if (hour < sunriseHour - 1) return 'predawn';
      if (hour < sunriseHour + 1.5) return 'dawn';
      if (hour < sunsetHour - 1.5) return 'day';
      if (hour < sunsetHour + 1) return 'dusk';
      return 'night';
    }
  }
  if (hour < 5) return 'night';
  if (hour < 6.5) return 'predawn';
  if (hour < 8) return 'dawn';
  if (hour < 16.5) return 'day';
  if (hour < 18.5) return 'dusk';
  if (hour < 20) return 'night';
  return 'night';
}

export function applySky(phase: SkyPhase, root: HTMLElement = document.documentElement) {
  root.setAttribute('data-sky', phase);
  return phase;
}
