/* The language the PRODUCT is in, as a choice the reader makes and this machine remembers.
   ============================================================================
   Until now the interface language was derived: it followed whatever language answers were set to, and
   when that was "match my question" it followed the browser. Both are reasonable defaults and neither
   is a choice. A reader who wants to read the product in Gujarati while asking in English, or who is
   handed a laptop set to a language they do not read, had no way to say so.

   So there are two settings now and they are genuinely different questions:

     - the ANSWER language, which the engine honours per turn and measures per direction; and
     - the SITE language, here, which is the chrome - the rail, the controls, the labels, the empty
       states. It states nothing about the weather, so it is a preference rather than a claim, and it
       is kept in this browser like every other preference this product holds.

   UNSET IS NOT ENGLISH. With no choice recorded the old behaviour stands exactly: follow the answer
   language, and the browser when that is unset. Choosing a language pins it; choosing "Follow my
   answers" clears the pin and returns to the derived behaviour. That is why the stored value is a
   nullable tag rather than a language with 'en' as its default - a reader whose browser is Hindi
   should not be switched to English by the mere existence of this control.
*/
import { CHROME_LANGUAGES, hasChrome, type ChromeLanguage } from './index';

export const SITE_LANGUAGE_KEY = 'weathergpt.siteLanguage';

/** Every language the chrome is translated into, with its own name for itself. */
export const SITE_LANGUAGES: { code: ChromeLanguage; own: string; english: string }[] = [
  { code: 'en', own: 'English', english: 'English' },
  { code: 'hi', own: 'हिन्दी', english: 'Hindi' },
  { code: 'gu', own: 'ગુજરાતી', english: 'Gujarati' },
  { code: 'ta', own: 'தமிழ்', english: 'Tamil' },
];

let pinned: ChromeLanguage | null | undefined;
const listeners = new Set<() => void>();

/** The pinned site language, or null when the reader has not chosen one. */
export function readSiteLanguage(): ChromeLanguage | null {
  if (pinned !== undefined) return pinned;
  try {
    const stored = window.localStorage.getItem(SITE_LANGUAGE_KEY);
    pinned = hasChrome(stored) ? (String(stored).toLowerCase().split('-')[0] as ChromeLanguage) : null;
  } catch {
    /* A browser that refuses storage still gets a working product, in the derived language. */
    pinned = null;
  }
  return pinned;
}

/** Pin the site language, or pass null to follow the answer language again. */
export function writeSiteLanguage(code: ChromeLanguage | null): void {
  pinned = code;
  try {
    if (code) window.localStorage.setItem(SITE_LANGUAGE_KEY, code);
    else window.localStorage.removeItem(SITE_LANGUAGE_KEY);
  } catch {
    /* The choice still holds for this page load. */
  }
  listeners.forEach(notify => notify());
}

export function subscribeSiteLanguage(notify: () => void): () => void {
  listeners.add(notify);
  return () => listeners.delete(notify);
}

/** For a spec: forget what was read, so the next read goes back to storage. */
export function resetSiteLanguage(): void {
  pinned = undefined;
}

export { CHROME_LANGUAGES };
