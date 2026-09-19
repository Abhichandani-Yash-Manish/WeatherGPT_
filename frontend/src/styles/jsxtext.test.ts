/* No comment may reach the page as text.

   App.tsx carried a three-line /* … *​/ comment sitting directly between two JSX children. In that position
   JSX has no comment syntax, so the compiler took it as text and React printed it: the whole comment,
   describing a shell wiring fix, rendered at the foot of every answer in the front door. Nothing failed —
   tsc is happy, the lint rules were happy, the page rendered — and it was visible only by looking at it.

   A grep cannot tell that position apart from a comment between two attributes, where the same syntax is
   legal and prints nothing. So this parses instead: TypeScript's own scanner marks the children of a JSX
   element as JsxText nodes, and a JsxText node that contains a comment opener is a comment that escaped. */

import ts from 'typescript';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

function tsxUnder(dir: string): string[] {
  return readdirSync(dir).flatMap(entry => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) return tsxUnder(path);
    return path.endsWith('.tsx') ? [path] : [];
  });
}

function escapedComments(path: string): string[] {
  const source = ts.createSourceFile(path, readFileSync(path, 'utf8'), ts.ScriptTarget.ESNext, true, ts.ScriptKind.TSX);
  const found: string[] = [];
  const visit = (node: ts.Node) => {
    if (ts.isJsxText(node) && /\/\*|\*\//.test(node.text)) {
      const line = source.getLineAndCharacterOfPosition(node.getStart()).line + 1;
      found.push(path + ':' + line + ' — ' + node.text.trim().slice(0, 70));
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return found;
}

describe('comments stay out of the page', () => {
  it('has no comment sitting in JSX children position', () => {
    const files = tsxUnder('src');
    expect(files.length, 'this check is not reading the components').toBeGreaterThan(20);
    const escaped = files.flatMap(escapedComments);
    expect(escaped, 'these comments render to the reader as text:\n' + escaped.join('\n')).toEqual([]);
  });
});
