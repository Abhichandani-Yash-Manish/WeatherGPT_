/* The atmosphere.
   ============================================================================
   The page's ground is the reader's own sky: the phase comes from the sun's altitude at the place and the
   hour (astronomy, true everywhere), and the horizon takes a tint only when a read returned a severe
   published day. It is CSS — gradients, one slow drift, grain — so it costs no bytes and states no condition.
   The one line that names its inputs lives in the footer, not on the picture. */

import { useEffect, useState, type ReactNode } from 'react';
import { phaseAt, type SkyPhase } from './solar';

export type Place = { label: string; latitude: number; longitude: number };
export const INDIA: Place = { label: 'India', latitude: 23.0, longitude: 82.5 };

export function useNow(intervalMs = 60_000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);
  return now;
}

export function useSky(place: Place, at: Date): { phase: SkyPhase; altitude: number; azimuth: number } {
  const { phase, position } = phaseAt(place.latitude, place.longitude, at);
  return { phase, altitude: position.altitude, azimuth: position.azimuth };
}

export type SkyProps = {
  place: Place;
  at: Date;
  /** The most severe published colour a read returned for today, if any. Never inferred. */
  mood?: 'red' | 'orange' | 'yellow' | null;
  children: ReactNode;
};

export function Sky({ place, at, mood = null, children }: SkyProps) {
  const sky = useSky(place, at);
  /* The body behind the stage takes the phase too, so nothing outside the frame is ever the wrong colour. */
  useEffect(() => {
    document.body.dataset.phase = sky.phase;
    return () => {
      delete document.body.dataset.phase;
    };
  }, [sky.phase]);
  /* The sun's disc sits where the sun is: azimuth east to west across the width, altitude up the height. */
  const x = 50 + Math.sin((sky.azimuth * Math.PI) / 180) * 40;
  const y = 30 - Math.max(-10, Math.min(60, sky.altitude)) * 0.6;
  return (
    <div className="f" data-phase={sky.phase} data-mood={mood || undefined} data-design="flagship">
      <div className="f-sky" aria-hidden="true">
        <div className="f-sun" style={{ ['--f-sun-x' as string]: x + '%', ['--f-sun-y' as string]: y + '%' }} />
        {mood ? <div className="f-mood" /> : null}
        <div className="f-grain" />
      </div>
      {children}
    </div>
  );
}

export const PHASE_WORD: Record<SkyPhase, string> = { night: 'night', dawn: 'dawn', day: 'day', dusk: 'dusk' };
