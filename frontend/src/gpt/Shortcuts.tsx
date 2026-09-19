/* The keyboard reference.
   ============================================================================
   One short list of the keys this shell answers to, opened from the rail or with ⌥/. It is a native dialog,
   so focus, Escape and the accessibility tree come from the browser rather than from a reimplementation — the
   same reason the command palette is one.

   Every key here is one that fires. The list is short on purpose: a shortcut nobody can remember is a
   shortcut nobody uses, and a page cannot own ⌘1–⌘9 for its tabs, so the numbering is ⌥ and says so. */

import { useEffect, useRef } from 'react';

export type Shortcut = { keys: string; what: string };

export const SHORTCUTS: Shortcut[] = [
  { keys: '⌥K', what: 'Command palette — every surface and every stored conversation' },
  { keys: '⌥N', what: 'New conversation' },
  { keys: '⌥B', what: 'Collapse or expand the rail' },
  { keys: '⌥F', what: 'Search every stored turn' },
  { keys: '⌥1 … ⌥9', what: 'Open the n-th conversation in the rail' },
  { keys: '⌥/', what: 'This list' },
  { keys: 'Enter', what: 'Send the question · Shift+Enter makes a line' },
  { keys: 'Esc', what: 'Close a dialog' },
];

export function ShortcutDialog({ onClose }: { onClose: () => void }) {
  const box = useRef<HTMLDialogElement | null>(null);

  useEffect(() => {
    const node = box.current;
    if (!node) return;
    if (typeof node.showModal === 'function') node.showModal();
    else node.setAttribute('open', '');
  }, []);

  return (
    <dialog
      ref={box}
      className="g-keys"
      aria-label="Keyboard shortcuts"
      onClose={onClose}
      onCancel={onClose}
      onClick={event => { if (event.target === box.current) onClose(); }}
    >
      <h2 className="g-keys-title">Keys</h2>
      <p className="g-keys-note">
        A page cannot take ⌘1–⌘9 from the browser’s tabs, so the rail numbers its rows with ⌥. Every key here
        fires; none of them is a promise.
      </p>
      <dl className="g-keys-list">
        {SHORTCUTS.map(entry => (
          <div key={entry.keys} className="g-keys-row">
            <dt><kbd className="g-kbd">{entry.keys}</kbd></dt>
            <dd>{entry.what}</dd>
          </div>
        ))}
      </dl>
      <button type="button" className="g-quiet" onClick={onClose}>Close</button>
    </dialog>
  );
}
