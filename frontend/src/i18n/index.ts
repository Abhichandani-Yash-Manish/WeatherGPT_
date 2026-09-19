/* The interface's own language.
   ============================================================================
   The engine answers in 22 languages. Until now the interface around those answers was entirely English:
   a Gujarati farmer received a Gujarati answer wrapped in "New conversation", "Warnings" and "What it's
   doing". That is the largest gap between what this product claims and what it is.

   Three rules govern what may be translated here, and they come from the same place every other rule in
   this product comes from — that nothing is stated which a source did not state.

   1. **Chrome only.** Navigation, buttons, headings, empty states, the words this interface wrote about
      itself. Everything a SOURCE wrote stays exactly as the source wrote it: hazard wording, place names
      as the resolver returned them, units, source ids, status lines, the engine's own sentences. A
      translated warning is a warning this product did not read.
   2. **Values never.** A number, a unit and a timestamp are formatted, not translated, and the formatting
      is the reader's locale acting on the source's own value.
   3. **Absence stays absence.** A missing translation falls back to English rather than to an empty
      string, because a blank label is a worse lie than an English one.

   The interface follows the answer language the reader already chose, so picking Gujarati for answers
   moves the whole product rather than half of it. Choosing "Match my question" leaves the interface in
   the browser's own language where we have it, and English where we do not. */

import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './en.json';
import hi from './hi.json';
import gu from './gu.json';
import ta from './ta.json';

/* The languages the CHROME is translated into. This is deliberately not the list of languages the engine
   can answer in: the engine's list is measured per direction and lives in the language registry, and
   claiming the interface speaks a language it has no strings for would be the same kind of lie this
   product exists to avoid. */
export const CHROME_LANGUAGES = ['en', 'hi', 'gu', 'ta'] as const;
export type ChromeLanguage = (typeof CHROME_LANGUAGES)[number];

export const hasChrome = (code: string | null | undefined): code is ChromeLanguage =>
  Boolean(code) && (CHROME_LANGUAGES as readonly string[]).includes(String(code).toLowerCase().split('-')[0]);

/** The chrome language for an answer-language choice: the same language where we have it, English where
    we do not, and the browser's own when the reader asked us to match their question. */
export function chromeFor(answerLanguage: string | null | undefined, browser: readonly string[] = navigator.languages || []): ChromeLanguage {
  if (answerLanguage) {
    const tag = String(answerLanguage).toLowerCase().split('-')[0];
    return hasChrome(tag) ? tag : 'en';
  }
  const matched = browser.map(tag => String(tag).toLowerCase().split('-')[0]).find(hasChrome);
  return matched || 'en';
}

void i18next.use(initReactI18next).init({
  resources: { en: { t: en }, hi: { t: hi }, gu: { t: gu }, ta: { t: ta } },
  ns: ['t'],
  defaultNS: 't',
  lng: 'en',
  fallbackLng: 'en',
  /* A key that is missing in a language falls through to English rather than rendering as the key or as
     nothing: an English label is legible, and a blank one is a defect a reader cannot report. */
  returnEmptyString: false,
  interpolation: { escapeValue: false },
});

export const i18n = i18next;
