/* What the reader has arranged, remembered on this machine.
   ============================================================================
   Three things only, and each is a real arrangement rather than a preference: whether the rail is expanded,
   whether the reading panel is open, and which conversations are pinned. It lives in one small key rather
   than three, so a reader who clears this browser's storage clears all of it at once.

   A stored value is read defensively. Storage is optional in this product — a browser can refuse it, and the
   workspace must work in one that does — so a corrupt or half-written record falls back to the default rather
   than taking the shell down with it. */

import { useCallback, useState } from 'react';

export type ShellPrefs = {
  rail: 'open' | 'collapsed';
  panel: boolean;
  /** Conversation ids, most recently pinned first. The list is capped; a rail of pins is not a rail. */
  pins: string[];
};

export const SHELL_KEY = 'weathergpt.shell';
const DEFAULTS: ShellPrefs = { rail: 'open', panel: false, pins: [] };

export function readShellPrefs(): ShellPrefs {
  try {
    const raw = window.localStorage.getItem(SHELL_KEY);
    if (!raw) return DEFAULTS;
    const value = JSON.parse(raw) as Partial<ShellPrefs>;
    return {
      rail: value.rail === 'collapsed' ? 'collapsed' : 'open',
      panel: value.panel === true,
      pins: Array.isArray(value.pins)
        ? value.pins.filter(id => typeof id === 'string' && id).slice(0, 20)
        : [],
    };
  } catch {
    return DEFAULTS;
  }
}

export function useShellPrefs(): { prefs: ShellPrefs; set: (patch: Partial<ShellPrefs>) => void } {
  const [prefs, setPrefs] = useState<ShellPrefs>(readShellPrefs);
  const set = useCallback((patch: Partial<ShellPrefs>) => {
    setPrefs(current => {
      const next = { ...current, ...patch };
      try {
        window.localStorage.setItem(SHELL_KEY, JSON.stringify(next));
      } catch {
        /* the browser refused storage: the arrangement still serves this page load */
      }
      return next;
    });
  }, []);
  return { prefs, set };
}
