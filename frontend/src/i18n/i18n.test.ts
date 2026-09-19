/* The catalogues, held against each other and against the rules.

   The failure this prevents is the ordinary one for translated interfaces: English grows a string, the
   other languages do not, and nobody notices because the fallback quietly renders English inside a Tamil
   page. A fallback is the right behaviour at runtime and the wrong thing to rely on, so the shapes are
   compared here instead. */

import { readFileSync, readdirSync } from 'node:fs';
import { chromeFor, CHROME_LANGUAGES, hasChrome } from './index';

const load = (code: string) => JSON.parse(readFileSync('src/i18n/' + code + '.json', 'utf8')) as Record<string, unknown>;

/** Every leaf key, flattened, so two catalogues can be compared as sets. */
function keysOf(value: unknown, prefix = ''): string[] {
  if (value === null || typeof value !== 'object') return [prefix];
  return Object.entries(value as Record<string, unknown>)
    .flatMap(([key, held]) => keysOf(held, prefix ? prefix + '.' + key : key));
}

describe('the interface catalogues', () => {
  const english = load('en');
  const englishKeys = keysOf(english).sort();

  it('ships a catalogue for every language the interface claims', () => {
    const files = readdirSync('src/i18n').filter(name => name.endsWith('.json')).map(name => name.replace('.json', '')).sort();
    expect(files).toEqual([...CHROME_LANGUAGES].sort());
  });

  it.each(CHROME_LANGUAGES.filter(code => code !== 'en'))('carries exactly the English keys in %s', code => {
    const keys = keysOf(load(code)).sort();
    const missing = englishKeys.filter(key => !keys.includes(key));
    const extra = keys.filter(key => !englishKeys.includes(key));
    expect(missing, code + ' is missing: ' + missing.join(', ')).toEqual([]);
    expect(extra, code + ' has keys English does not: ' + extra.join(', ')).toEqual([]);
  });

  it.each(CHROME_LANGUAGES)('leaves no string empty in %s', code => {
    const empty: string[] = [];
    const walk = (value: unknown, prefix = '') => {
      if (typeof value === 'string') { if (!value.trim()) empty.push(prefix); return; }
      if (value && typeof value === 'object') {
        Object.entries(value as Record<string, unknown>).forEach(([key, held]) => walk(held, prefix ? prefix + '.' + key : key));
      }
    };
    walk(load(code));
    /* A blank label is a worse lie than an English one: it cannot even be reported. */
    expect(empty, 'blank strings in ' + code).toEqual([]);
  });

  it('translates the chrome and never a value, a unit or a source id', () => {
    /* The rule the catalogue exists under. A translated hazard wording would be a warning this product
       did not read, so no catalogue may carry one — these are the shapes that would betray the attempt. */
    const forbidden = /\b(°C|mm|km\/h|IMD district warning|thunderstorm|heavy rain|S\d{2}\b)/i;
    CHROME_LANGUAGES.forEach(code => {
      const text = readFileSync('src/i18n/' + code + '.json', 'utf8');
      expect(forbidden.test(text.replace(/"brand":[^,]+,/, '')), code + ' carries source wording or a unit').toBe(false);
    });
  });
});

describe('which language the chrome follows', () => {
  it('follows the answer language when the chrome has it', () => {
    expect(chromeFor('gu')).toBe('gu');
    expect(chromeFor('ta-IN')).toBe('ta');
  });

  it('falls back to English for a language the chrome does not have, rather than claiming it', () => {
    /* The engine answers in 22 languages; the chrome is translated into four. Claiming otherwise would be
       the same kind of lie this product exists to avoid. */
    expect(hasChrome('bn')).toBe(false);
    expect(chromeFor('bn')).toBe('en');
  });

  it("uses the browser's own language when the reader asked us to match their question", () => {
    expect(chromeFor('', ['ta-IN', 'en-GB'])).toBe('ta');
    expect(chromeFor(null, ['fr-FR'])).toBe('en');
  });
});
