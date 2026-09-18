/* The two voices, self-hosted.
   ============================================================================
   The workspace serves under default-src 'self', so every face is bundled from node_modules and served
   from this origin; no font stylesheet can load from a CDN here.

   - Anek is the HUMAN voice: what a model wrote. It is a pan-Indic family drawn per script, so a Hindi or
     Tamil answer is set in a face made for it rather than a fallback. The Latin face loads here; the
     script faces load on demand below, so a reader who never asks for Tamil never pays for a Tamil face.
   - Martian Mono is the MACHINE voice: every value, unit, source id, locator and timestamp — what a tool
     owns and a model may never write. Tabular by construction.

   Loading a face is never a claim that the product can WRITE the language: that stays the engine's
   adherence gate, measured per direction. */

import '@fontsource-variable/anek-latin';
import '@fontsource-variable/martian-mono';

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
