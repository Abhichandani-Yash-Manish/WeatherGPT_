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
