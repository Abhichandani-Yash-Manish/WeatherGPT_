/* The stylesheet's own contract: the class vocabulary the components use by name is still declared.

   This exists because it was once lost: appending a block to styles/app.css by reading only the first lines
   silently truncated the file, and the components kept using classes that no longer existed. The page still
   rendered, which is exactly why nothing caught it. A check that names every class the components rely on
   turns that class of mistake into a failure. */

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

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

/* The same check as above, but derived rather than listed.

   The list above is written by hand, and a hand-written list goes stale in exactly one direction: a class
   gets used and nobody adds it. That happened. Workspace.tsx rendered .g-panel, .g-sun, .g-disc, .g-scene,
   .g-dots and .g-eyebrow while gpt.css declared none of the six — the JSX was left from the illustrated
   scene direction and the stylesheet had been rewritten without it. The page still rendered, so nothing
   failed: the thread lost its flex parent, the typing indicator became three zero-sized elements, and a
   status line meant to be a quiet label printed at body weight like console output.

   So this one reads the components instead of a list. Every g- class any component names has to be declared
   in gpt.css, and the day one is not, this fails. */

const GPT = readFileSync('src/gpt/gpt.css', 'utf8');

function tsxUnder(dir: string): string[] {
  return readdirSync(dir).flatMap(entry => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) return tsxUnder(path);
    return path.endsWith('.tsx') && !path.includes('.test.') ? [path] : [];
  });
}

function classesNamed(): Map<string, string[]> {
  const out = new Map<string, string[]>();
  tsxUnder('src').forEach(path => {
    const text = readFileSync(path, 'utf8');
    /* Every className value, whether a plain string, a template or an expression with literals in it. */
    for (const attribute of text.matchAll(/className=(?:"([^"]*)"|\{([^}]*)\})/g)) {
      const value = attribute[1] ?? attribute[2] ?? '';
      for (const token of value.matchAll(/\bg-[a-z0-9-]+/g)) {
        const name = token[0];
        out.set(name, [...(out.get(name) || []), path]);
      }
    }
  });
  return out;
}

describe('the workspace vocabulary, derived from the components', () => {
  it('declares every g- class the components name', () => {
    const used = classesNamed();
    expect(used.size, 'no g- classes were found, so this check is not reading the components').toBeGreaterThan(30);
    const missing = [...used.entries()]
      .filter(([name]) => !new RegExp('\\.' + name + '(?![a-z0-9-])').test(GPT))
      .map(([name, where]) => name + ' (used in ' + where.join(', ') + ')');
    expect(missing, 'gpt.css declares no rule for: ' + missing.join('; ')).toEqual([]);
  });

  it('leaves the composer and the rail filter to the workspace, not to the module field rule', () => {
    /* `.g textarea` and `.g-composer textarea` have the same specificity, so the later of the two wins on
       source order alone. The module block is later, so without an explicit exclusion it silently drew a
       second bordered box inside the composer and reset the rail filter's radius. */
    expect(GPT).toContain('.g textarea:not(.g-composer textarea)');
    expect(GPT).toContain(".g input[type='search']:not(.g-search)");
  });
});
