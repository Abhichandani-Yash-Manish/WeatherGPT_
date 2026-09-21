/* Letting a finished answer arrive at reading pace.
   ============================================================================
   The engine composes an answer, checks it against the evidence it was given, and only then sends it.
   That order is the product: nothing a reader sees has skipped `generated_answer_problem`. It also means
   the answer lands as one complete block, and a block appearing whole reads as a page load rather than as
   something written for you — which is the complaint this exists to answer.

   So the REVEAL is the only thing that is progressive. The text is already final, already checked, and
   already stored; this walks a cursor through it so it arrives the way it would have been written. It
   invents nothing, reorders nothing, and cannot show a word the checks did not pass, because it has no
   access to anything but the finished string.

   What it does NOT do is fake thinking. The stages above the answer are the engine's own, streamed from
   `/api/chat/stream` as it reaches each one. This file only paces text that already exists.

   Two rules that are not decoration:

   - A reader who asked for reduced motion gets the whole answer at once. Text arriving in pieces is
     motion, and this is exactly the kind a vestibular reader asks to be spared.
   - The pace is bounded at both ends. A one-line answer must not finish so fast that the effect is a
     flicker, and a thousand-word marine briefing must not take twenty seconds to become readable. Long
     answers reveal faster per character; every answer finishes inside MAX_MS.
*/
import { useEffect, useRef, useState } from 'react';

/** The slowest an answer may finish, and the fastest. Both in milliseconds. */
export const MAX_MS = 2200;
export const MIN_MS = 450;
/** Characters a second at the unbounded pace, before the two limits above clamp it. */
export const PACE = 900;

export function revealDuration(length: number): number {
  if (length <= 0) return 0;
  return Math.min(MAX_MS, Math.max(MIN_MS, (length / PACE) * 1000));
}

export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false;
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}

/** How much of `text` has arrived at `elapsed` ms into a reveal of `duration` ms. */
export function revealedLength(text: string, elapsed: number, duration: number): number {
  if (duration <= 0) return text.length;
  const share = Math.min(1, Math.max(0, elapsed / duration));
  const cut = Math.round(text.length * share);
  if (cut >= text.length) return text.length;
  /* Stop on a boundary rather than mid-word. A cursor that lands inside "thunderstorm" prints
     "thunders", which reads as a different word for as long as the next frame takes to arrive. */
  const space = text.lastIndexOf(' ', cut);
  return space > 0 ? space : cut;
}

/**
 * The visible prefix of a finished answer.
 *
 * `active` false - or reduced motion, or no text - returns the whole thing immediately, so every caller
 * can render `shown` unconditionally and a restored conversation never re-types itself.
 */
export function useRevealed(text: string, active: boolean): { shown: string; revealing: boolean } {
  const whole = text || '';
  const instant = !active || !whole || prefersReducedMotion();
  const [cut, setCut] = useState(() => (instant ? whole.length : 0));

  /* Adjusted DURING render, not in an effect, and that is load-bearing.
     The answer lands and the turn stops working in the same commit, so on that commit the caller has not
     yet decided this is the answer to write out and `active` is still false - the cut starts at the full
     length. `active` flips on the very next render. If the reset to zero waited for an effect, that effect
     would run AFTER the browser had painted, and the reader would see the finished answer for one frame
     and then watch it restart from nothing. Measured 21 September 2026: 116 characters, then 0, then back
     up to 116. Setting state while rendering is React's own answer to this: it re-renders immediately,
     before anything is painted, so the first frame a reader sees is the first word.

     The comparison is keyed to the text as well as to `active`, because a retried question replaces the
     string and must start again rather than continue from wherever the last one had reached. */
  const source = useRef({ whole, instant });
  if (source.current.whole !== whole || source.current.instant !== instant) {
    source.current = { whole, instant };
    setCut(instant ? whole.length : 0);
  }

  useEffect(() => {
    if (instant) {
      setCut(whole.length);
      return;
    }
    const duration = revealDuration(whole.length);
    const started = performance.now();
    let frame = 0;
    const step = () => {
      const next = revealedLength(whole, performance.now() - started, duration);
      setCut(next);
      if (next < whole.length) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [whole, instant]);

  const shown = cut >= whole.length ? whole : whole.slice(0, cut);
  return { shown, revealing: shown.length < whole.length };
}
