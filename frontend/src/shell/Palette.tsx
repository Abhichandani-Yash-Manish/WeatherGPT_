/* The command palette: one keyboard route to every surface, plus the two actions a reader needs most.

   It is a native dialog, so focus, Escape and the accessibility tree come from the browser rather than
   from a reimplementation. The list is generated from the surface registry. */

import { useEffect, useMemo, useRef, useState } from 'react';
import { VIEWS } from './views';

export type PaletteAction = { id: string; label: string; hint?: string; run: () => void };

export function Palette({
  open,
  onClose,
  onOpenView,
  onNewConversation,
  actions = [],
}: {
  open: boolean;
  onClose: () => void;
  onOpenView: (id: string) => void;
  onNewConversation: () => void;
  actions?: PaletteAction[];
}) {
  const dialog = useRef<HTMLDialogElement | null>(null);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);

  const items = useMemo(() => {
    const rows: PaletteAction[] = [
      { id: 'new-conversation', label: 'Start a new conversation', hint: 'the workspace keeps every stored conversation', run: onNewConversation },
      ...VIEWS.map(view => ({ id: view.id, label: 'Open ' + view.label, hint: view.intents[0], run: () => onOpenView(view.id) })),
      ...actions,
    ];
    const needle = query.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter(row => (row.label + ' ' + (row.hint || '')).toLowerCase().includes(needle));
  }, [actions, onNewConversation, onOpenView, query]);

  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (open && !node.open) {
      setQuery('');
      setActive(0);
      node.showModal();
    }
    if (!open && node.open) node.close();
  }, [open]);

  useEffect(() => {
    if (active >= items.length) setActive(0);
  }, [active, items.length]);

  return (
    <dialog ref={dialog} className="card w-[min(38rem,92vw)] p-0 backdrop:bg-[var(--scrim)]" onClose={onClose} aria-label="Command palette">
      <div className="px-3 py-3">
        <label className="sr-only" htmlFor="palette-search">Search commands and surfaces</label>
        <input
          id="palette-search"
          value={query}
          autoFocus
          onChange={event => setQuery(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'ArrowDown') { event.preventDefault(); setActive(value => Math.min(items.length - 1, value + 1)); }
            if (event.key === 'ArrowUp') { event.preventDefault(); setActive(value => Math.max(0, value - 1)); }
            if (event.key === 'Enter') {
              event.preventDefault();
              const item = items[active];
              if (item) { item.run(); onClose(); }
            }
          }}
          placeholder="Where do you want to go?"
          className="w-full rounded-card border border-line bg-paper px-3 py-2 text-sm"
        />
        <ul className="mt-2 max-h-80 overflow-y-auto" role="listbox" aria-label="Surfaces">
          {items.map((item, index) => (
            <li key={item.id} role="option" aria-selected={index === active}>
              <button
                type="button"
                className={'w-full rounded-card px-2 py-2 text-left text-sm ' + (index === active ? 'bg-sand' : 'hover:bg-sand/40')}
                onMouseEnter={() => setActive(index)}
                onClick={() => { item.run(); onClose(); }}
              >
                <span>{item.label}</span>
                {item.hint ? <span className="mt-0.5 block text-[11px] quiet">{item.hint}</span> : null}
              </button>
            </li>
          ))}
          {!items.length ? <li className="px-2 py-3 text-xs quiet">No surface or command matches that.</li> : null}
        </ul>
        <p className="mt-2 text-[11px] quiet">Alt+K opens this anywhere. Alt+1…9 opens a numbered surface.</p>
      </div>
    </dialog>
  );
}
