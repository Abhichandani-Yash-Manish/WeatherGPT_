/* The three voices, self-hosted.
   ============================================================================
   The workspace serves under default-src 'self', so every face is bundled from node_modules and served
   from this origin; no font stylesheet can load from a CDN here.

   - OUTFIT is the DISPLAY voice: the greeting, the hour, a reading's own numeral, a surface title. A
     geometric sans with a high x-height and flat terminals - warm without being soft. It replaced
     Nunito, whose roundness read as a children's product rather than as an instrument, which is a real
     problem for something presented to a meteorological department.
   - INTER is the INTERFACE voice: the rail, the controls, the chips, and the sentences a model wrote.
     It is drawn for screens at small sizes, and this product is mostly small text that has to be read
     exactly - a source id, a district name, a caveat.
   - ANEK sits BEHIND Inter in the same stack rather than being replaced by it, and that is deliberate.
     It is a pan-Indic family drawn per script, so a Hindi or Gujarati answer is set in a face made for
     it. Inter carries no Devanagari, so Latin resolves to Inter and Indic scripts fall through to Anek
     and then to the per-script faces below. One stack, both jobs, nothing lost.
   - JETBRAINS MONO is the MACHINE voice: every value, unit, source id, locator and timestamp - what a
     tool owns and a model may never write. Its figures are unambiguous at 11px, which is the size this
     product states most of its evidence at.

   Loading a face is never a claim that the product can WRITE the language: that stays the engine's
   adherence gate, measured per direction. */

import '@fontsource-variable/outfit';
import '@fontsource-variable/inter';
import '@fontsource-variable/anek-latin';
import '@fontsource-variable/jetbrains-mono';

/* Script faces. Anek's own per-script faces are used where installed; the Tiro/Noto faces already in the
   tree cover the rest. Unknown tags are a no-op, never an error. */
const FACES: Record<string, () => Promise<unknown>> = {
  hi: () => import('@fontsource/tiro-devanagari-hindi/devanagari-400.css'),
  mr: () => import('@fontsource/tiro-devanagari-hindi/devanagari-400.css'),
  bn: () => import('@fontsource/tiro-bangla/400.css'),
  as: () => import('@fontsource/tiro-bangla/400.css'),
  ta: () => import('@fontsource/tiro-tamil/400.css'),
  te: () => import('@fontsource/tiro-telugu/400.css'),
  kn: () => import('@fontsource/tiro-kannada/400.css'),
  gu: () => import('@fontsource/noto-serif-gujarati/400.css'),
};

const loaded = new Set<string>();

export function scriptFace(language: string | null | undefined): void {
  if (!language) return;
  const tag = String(language).toLowerCase().split('-')[0];
  const face = FACES[tag];
  if (!face || loaded.has(tag)) return;
  loaded.add(tag);
  void face().catch(() => loaded.delete(tag));
}
