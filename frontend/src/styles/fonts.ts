/* The two voices, self-hosted.
   ============================================================================
   The workspace serves under a strict CSP (default-src 'self'), so a font file has to be part of the
   build: no Google Fonts stylesheet and no CDN face can load here. Every face below is bundled by Vite
   from node_modules and served from this origin, which is why these are imports rather than a <link>.

   Two families, because the product has two voices and they must not be confused:

   - Tiro Devanagari Hindi is the HUMAN voice: the invitation, the written sentence, the prose a model
     composed. It was drawn for Indian scripts, and it carries Latin and Devanagari in one set of
     proportions, which matters in a product that answers in Hindi and Marathi as readily as in English.
   - IBM Plex Mono is the MACHINE voice: every value, unit, locator, timestamp and source id — the things
     a governed tool owns and a model may never write. Tabular by construction, so a column of readings
     does not shimmy.
   - IBM Plex Sans is the interface voice: controls and labels, which are neither.

   The other Indian scripts are NOT loaded here. A reader who never asks for Tamil should not pay for a
   Tamil face, so those load on demand through scriptFace() below, which is also why this module exports
   a function rather than importing all nine faces up front. */

import '@fontsource/tiro-devanagari-hindi/400.css';
import '@fontsource/tiro-devanagari-hindi/devanagari-400.css';
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-sans/600.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';

/* The script a language is written in, and the face that can write it. A language whose face is not
   listed here is not refused — it falls back to the human voice's own coverage and the system stack
   beneath it, exactly as it does today. Loading a face is never a claim that the product can WRITE the
   language: that remains the engine's adherence gate, measured per direction, and a face that renders
   the script does not make an unverified rendering shippable. */
const FACES: Record<string, () => Promise<unknown>> = {
  bn: () => import('@fontsource/tiro-bangla/400.css'),
  as: () => import('@fontsource/tiro-bangla/400.css'),
  ta: () => import('@fontsource/tiro-tamil/400.css'),
  te: () => import('@fontsource/tiro-telugu/400.css'),
  kn: () => import('@fontsource/tiro-kannada/400.css'),
  gu: () => import('@fontsource/noto-serif-gujarati/400.css'),
};

const loaded = new Set<string>();

/** Load the face for a language tag, once. Unknown tags are a no-op, never an error. */
export function scriptFace(language: string | null | undefined): void {
  if (!language) return;
  const tag = String(language).toLowerCase().split('-')[0];
  const face = FACES[tag];
  if (!face || loaded.has(tag)) return;
  loaded.add(tag);
  /* A face that fails to load leaves the fallback stack in place. It is a rendering nicety, so it must
     never reject into the app and never block an answer that is already verified. */
  void face().catch(() => loaded.delete(tag));
}
