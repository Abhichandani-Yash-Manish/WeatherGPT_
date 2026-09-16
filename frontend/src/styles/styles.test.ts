/* The stylesheet's own contract: the class vocabulary the components use by name is still declared.

   This exists because it was once lost: appending a block to styles/app.css by reading only the first lines
   silently truncated the file, and the components kept using classes that no longer existed. The page still
   rendered, which is exactly why nothing caught it. A check that names every class the components rely on
   turns that class of mistake into a failure. */

import { readFileSync } from 'node:fs';

const APP = readFileSync('src/styles/app.css', 'utf8');
const TRANSCRIPT = readFileSync('src/styles/transcript.css', 'utf8');
const PRINT = readFileSync('src/styles/print.css', 'utf8');

const DECLARED: [string, string, string[]][] = [
  ['app.css', APP, [
    '.skip-link',
    '.eyebrow',
    '.display',
    '.reading',
    '.evidence',
    '.card',
    '.card-raised',
    '.house',
    '.btn',
    '.btn-primary',
    '.btn-ghost',
    '.tag',
    '.chip',
    '.rise',
    '.rail',
    '@media (max-width: 64rem)',
    '[data-shell=' + "'react'" + ']',
  ]],
  ['transcript.css', TRANSCRIPT, [
    '.turn',
    '.turn-user',
    '.working-dot',
    '.stage-step',
    '.reading-line',
    '.receipt',
    '.receipt-row',
    '.ruler-covered',
    '.ruler-gap',
    '.fact-row',
    '.lead-value',
    '.machine-record',
    '.composer-shell',
  ]],
  ['print.css', PRINT, [
    "[data-print='drop']",
    '.machine-record',
    '.composer-shell',
  ]],
];

describe('the stylesheet vocabulary', () => {
  it.each(DECLARED)('declares every class the components use by name in %s', (name, text, classes) => {
    const missing = classes.filter(selector => !text.includes(selector));
    expect(missing, name + ' is missing: ' + missing.join(', ')).toEqual([]);
  });

  it('keeps the app stylesheet long enough to hold the vocabulary it declares', () => {
    /* A floor rather than a target: the block that was lost was ~200 lines. */
    expect(APP.split('\n').length).toBeGreaterThan(200);
  });
});
