/* Theme and sky phase. Both are preferences of this machine, not facts about the weather: the sky band is
   decoration derived from the local clock, and it says so. */

import { useEffect, useState } from 'react';
import { applySky, phaseFor, type SkyPhase, type SunTimes } from './sky';

export type Theme = 'light' | 'dark' | 'system';
export const THEME_KEY = 'weathergpt.theme';

export function readTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(THEME_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  } catch {
    /* a browser that refuses storage keeps the system theme */
  }
  return 'system';
}

export function applyTheme(theme: Theme, root: HTMLElement = document.documentElement): void {
  if (theme === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', theme);
}

export function nextTheme(theme: Theme): Theme {
  return theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system';
}

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => readTheme());
  useEffect(() => {
    applyTheme(theme);
    try {
      window.localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* the choice simply does not survive this session */
    }
  }, [theme]);
  return [theme, () => setTheme(current => nextTheme(current))];
}

/* The phase follows the clock, refreshed every ten minutes, and follows a sourced sun time when a caller
   has one. It is applied as data-sky; nothing reads it back as a condition. */
export function useSkyPhase(sun: SunTimes = {}): SkyPhase {
  const [phase, setPhase] = useState<SkyPhase>(() => phaseFor(new Date(), sun));
  useEffect(() => {
    const tick = () => setPhase(applySky(phaseFor(new Date(), sun)));
    tick();
    const timer = window.setInterval(tick, 600_000);
    return () => window.clearInterval(timer);
  }, [sun.sunrise, sun.sunset]);
  return phase;
}
