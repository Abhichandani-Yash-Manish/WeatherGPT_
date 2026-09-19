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
  /**
   * A reader's own name for a place, keyed by the label the catalogue returned.
   *
   * The catalogue's labels are its own — \`Surat, Sūrat, State of Gujarāt\` — and a reader who thinks of it as
   * Surat should be able to say so. This is a display name and nothing else: what travels to the engine is
   * still the label the catalogue returned, and the alias is never presented as a place any source named.
   */
  aliases: Record<string, string>;
};

export const SHELL_KEY = 'weathergpt.shell';
const DEFAULTS: ShellPrefs = { rail: 'open', panel: false, pins: [], aliases: {} };

export function readShellPrefs(): ShellPrefs {
  try {
    const raw = window.localStorage.getItem(SHELL_KEY);
    if (!raw) return DEFAULTS;
    const value = JSON.parse(raw) as Partial<ShellPrefs>;
    const aliases = value.aliases && typeof value.aliases === 'object' ? value.aliases : {};
    return {
      rail: value.rail === 'collapsed' ? 'collapsed' : 'open',
      panel: value.panel === true,
      pins: Array.isArray(value.pins)
        ? value.pins.filter(id => typeof id === 'string' && id).slice(0, 20)
        : [],
      aliases: Object.fromEntries(
        Object.entries(aliases as Record<string, unknown>)
          .filter(([key, name]) => key && typeof name === 'string' && name)
          .slice(0, 40)
          .map(([key, name]) => [key, String(name).slice(0, 60)]),
      ),
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
