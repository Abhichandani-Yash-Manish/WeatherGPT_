/* The locale the interface FORMATS with, as against the language it is written in.
   ============================================================================
   The product's rule for values is that a number, a unit and a timestamp are formatted, never translated:
   what a source stated must survive the rendering. That makes the formatter a different concern from the
   catalogue. i18n/ decides which WORDS the interface uses; this decides which CONVENTIONS it reads an
   instant or a number in, and neither is allowed to touch the other.

   Every tag is Indian, for every language the chrome speaks, because the product is about India: en-IN
   groups 12,34,567 rather than 1,234,567. That is the reader's convention rather than a translation, and
   it is why the mapping is not simply the language code.

   Defaulting to en-IN is what keeps this change invisible to everything already recorded: every existing
   spec, screenshot and doc states "18 Sep 2026, 00:30 IST", and a locale-aware formatter must still print
   exactly that until someone chooses another language. */

export const LOCALE_TAGS: Record<string, string> = { en: 'en-IN', hi: 'hi-IN', gu: 'gu-IN', ta: 'ta-IN' };
export const DEFAULT_LOCALE = 'en-IN';

let active = DEFAULT_LOCALE;

export function localeTag(language?: string | null): string {
  const base = String(language || '').toLowerCase().split('-')[0];
  return LOCALE_TAGS[base] || DEFAULT_LOCALE;
}

export function setLocale(language?: string | null): void {
  active = localeTag(language);
}

export function currentLocale(): string {
  return active;
}

/* True for the product's own default rendering, which is a CONVENTION and not a fallback: its recorded
   evidence and its specs state three-letter months ("18 Sep 2026"), and Intl's short month for en is
   "Sept" on this ICU. Churning every recorded example for a letter is not a reader benefit, so the default
   keeps the product's own table and every other language uses the browser's. */
export function isDefaultLocale(): boolean {
  return active === DEFAULT_LOCALE;
}

/**
 * A place label as a reader should see it, rather than as the catalogue stores it.
 *
 * The catalogue returns the full administrative path - "Anand, Anand, State of Gujarāt" - because it has
 * to: a city, its district and its state are three different things and two of them share a name. On
 * screen that reads as a stutter, and the front door was printing it three times over, so a reader met
 * the word "Anand" five times before they had asked anything.
 *
 * This collapses it for DISPLAY ONLY. Every value sent to the engine, every source line and every
 * citation keeps the catalogue's own label, because that is the thing the resolver matched and the thing
 * a receipt has to be able to name.
 *
 *   Anand, Anand, State of Gujarāt      -> Anand, Gujarāt
 *   Pune, Pune Division, State of ...   -> Pune, Mahārāshtra
 *   Surat, Sūrat, State of Gujarāt      -> Surat, Gujarāt      (diacritics do not hide a repeat)
 *   Ban Sarkāri, Hoshiārpur, Punjab     -> Ban Sarkāri, Punjab
 */
export function shortPlace(label: string | null | undefined): string {
  const full = String(label || '').trim();
  if (!full) return '';
  /* Compared without diacritics or case, so "Surat" and "Sūrat" are recognised as the same word. */
  const bare = (part: string) => part.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const parts = full.split(',').map(part => part.trim()).filter(Boolean);
  if (parts.length < 2) return full;
  /* The last segment is the state, and its administrative prefix is noise on a screen this small. */
  const state = parts[parts.length - 1].replace(/^(State of|Union Territory of|National Capital Territory of)\s+/i, '');
  const kept: string[] = [];
  for (const part of parts.slice(0, -1)) {
    const key = bare(part);
    /* A segment that repeats the one before it, or merely qualifies it ("Pune" then "Pune Division"),
       adds nothing a reader needs here. */
    if (kept.some(held => bare(held) === key || key.startsWith(bare(held) + ' ') || bare(held).startsWith(key + ' '))) continue;
    kept.push(part);
  }
  const head = kept.length ? kept[0] : parts[0];
  return bare(head) === bare(state) ? head : head + ', ' + state;
}
