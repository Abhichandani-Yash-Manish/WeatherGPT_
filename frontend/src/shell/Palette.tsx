/* The command palette: one keyboard route to every surface, to the places the catalogue returns and to
   the conversations this machine stored, plus the shell actions a reader needs most.

   It is a native dialog, so focus, Escape and the accessibility tree come from the browser rather than
   from a reimplementation. The commands are generated from the surface registry. A place entry asks the
   conversation about the place the payload named, through the control the shell passes in onAsk; a
   stored-conversation entry opens exactly that conversation through onOpenConversation. When the shell
   passes neither, the entry moves to the conversation surface and its own note says it did not fill a
   question, rather than pretending it did. A read that fails is the server's own sentence with a retry,
   never an empty list. */

import { useEffect, useMemo, useRef, useState } from 'react';
import { CornerDownLeft, Search, Sparkles } from 'lucide-react';
import { SURFACE_ICONS } from '../ui/icons';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope, Ledger } from '../api/types';
import { failureSentence } from '../modules/Evidence';
import { VIEWS } from './views';

export type PaletteAction = { id: string; group?: string; label: string; hint?: string; run: () => void; viewId?: string };

type PlaceRow = {
  label?: string | null; name?: string | null; source_id?: string | null; kind?: string | null;
  latitude?: number | null; longitude?: number | null;
  coordinates?: { latitude?: number | null; longitude?: number | null } | null;
};

/* The same two shapes the composer's place picker reads: a row that states its own coordinates, or a row
   that carries them in a coordinates object. A row that states neither is shown as one. */
function placeCoordinates(row: PlaceRow): string {
  const latitude = typeof row.latitude === 'number' ? row.latitude : row.coordinates?.latitude;
  const longitude = typeof row.longitude === 'number' ? row.longitude : row.coordinates?.longitude;
  return typeof latitude === 'number' && typeof longitude === 'number'
    ? latitude + ', ' + longitude
    : 'coordinates not recorded in this row';
}

export function Palette({
  open,
  onClose,
  onOpenView,
  onNewConversation,
  onAsk,
  onOpenConversation,
  actions = [],
}: {
  open: boolean;
  onClose: () => void;
  onOpenView: (id: string) => void;
  onNewConversation: () => void;
  /* A place entry fills the question with the place the payload named and asks it. */
  onAsk?: (question: string) => void;
  /* A stored-conversation entry opens exactly that stored conversation. */
  onOpenConversation?: (id: string) => void;
  actions?: PaletteAction[];
}) {
  const dialog = useRef<HTMLDialogElement | null>(null);
  const [query, setQuery] = useState('');
  const [needle, setNeedle] = useState('');
  const [active, setActive] = useState(0);

  /* The place catalogue is asked only for a term of at least two characters, and only after the reader
     stopped typing: the same contract the recorded palette check held, so a surface name being typed
     does not become a place read on every keystroke. */
  useEffect(() => {
    if (!open) { setNeedle(''); return; }
    const trimmed = query.trim();
    if (trimmed.length < 2) { setNeedle(''); return; }
    const timer = window.setTimeout(() => setNeedle(trimmed), 200);
    return () => window.clearTimeout(timer);
  }, [open, query]);

  const places = useQuery({
    queryKey: ['palette-places', needle],
    queryFn: () => getJson<Envelope<{ matches?: PlaceRow[] }>>(withQuery('/api/places/search', { q: needle })),
    enabled: open && needle.length >= 2,
    retry: false,
  });

  const conversations = useQuery({
    queryKey: ['palette-conversations'],
    queryFn: () => getJson<Ledger>('/api/conversations'),
    enabled: open,
    retry: false,
  });

  const items = useMemo(() => {
    const rows: PaletteAction[] = [
      { id: 'new-conversation', group: 'Start', label: 'Start a new conversation', hint: 'the workspace keeps every stored conversation', run: onNewConversation },
      ...VIEWS.map(view => ({ id: view.id, group: 'Surfaces', label: 'Open ' + view.label, hint: view.intents[0], viewId: view.id, run: () => onOpenView(view.id) })),
      ...actions.map(action => ({ ...action, group: action.group || 'Actions' })),
    ];
    (conversations.data?.conversations || []).slice(0, 6).forEach(row => {
      const counted = row.asked !== undefined ? row.asked + ' asked'
        : row.turns !== undefined ? row.turns + ' turns' : 'stored turn';
      rows.push({
        id: 'conversation-' + row.id,
        group: 'Recent conversations',
        label: row.opening_question || 'Stored conversation',
        hint: counted + ' · ' + (onOpenConversation ? 'opens this stored conversation' : 'opens the conversation surface; it was not opened here'),
        run: () => {
          if (onOpenConversation) onOpenConversation(row.id);
          else window.location.hash = '#/assistant';
        },
      });
    });
    (places.data?.data?.matches || []).filter(row => row.label || row.name).forEach(row => {
      const label = row.label || row.name || '';
      const source = [row.source_id, row.kind].filter(Boolean).join(' · ');
      rows.push({
        id: 'place-' + label,
        group: 'Places',
        label,
        hint: source + ' · ' + placeCoordinates(row) + (onAsk ? ' · asks the conversation about this place' : ' · opens the conversation; no question was filled'),
        run: () => {
          if (onAsk) onAsk('What is it like right now in ' + label + '?');
          else window.location.hash = '#/assistant';
        },
      });
    });
    const term = query.trim().toLowerCase();
    if (!term) return rows;
    return rows.filter(row => (row.label + ' ' + (row.hint || '')).toLowerCase().includes(term));
  }, [actions, conversations.data, onAsk, onNewConversation, onOpenConversation, onOpenView, places.data, query]);

  /* Grouping is display only: the flat item order is what the arrow keys and Enter move through. */
  const groups = useMemo(() => {
    const ordered: { name: string; rows: { item: PaletteAction; index: number }[] }[] = [];
    items.forEach((item, index) => {
      const name = item.group || 'Commands';
      let group = ordered.find(entry => entry.name === name);
      if (!group) { group = { name, rows: [] }; ordered.push(group); }
      group.rows.push({ item, index });
    });
    return ordered;
  }, [items]);

  const failures: { what: string; error: unknown; retry: () => void }[] = [];
  if (places.isError && needle.length >= 2) failures.push({ what: 'place catalogue', error: places.error, retry: () => void places.refetch() });
  if (conversations.isError) failures.push({ what: 'stored conversations', error: conversations.error, retry: () => void conversations.refetch() });

  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (open && !node.open) {
      setQuery('');
      setActive(0);
      node.showModal();
      /* The search field takes focus when the palette opens, so a keyboard reader can type straight away. */
      node.querySelector<HTMLInputElement>('#palette-search')?.focus();
    }
    if (!open && node.open) node.close();
  }, [open]);

  useEffect(() => {
    if (active >= items.length) setActive(0);
  }, [active, items.length]);

  return (
    <dialog ref={dialog} className="glass-strong w-[min(40rem,94vw)] p-0 backdrop:bg-[var(--scrim)]" onClose={onClose} aria-label="Command palette">
      <div className="px-3 py-3">
        <label className="sr-only" htmlFor="palette-search">Search commands, surfaces, places and stored conversations</label>
        <div className="relative">
          <Search size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-mute" aria-hidden="true" />
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
          className="w-full rounded-full border border-glass-line bg-glass-2 py-2.5 pl-10 pr-4 text-[length:var(--step-0)] text-ink"
        />
        </div>
        {failures.map(entry => (
          <div key={entry.what} className="mt-2 rounded-card border border-line px-2 py-2 text-xs" role="alert">
            <p className="reading">{failureSentence(entry.error)}</p>
            <p className="mt-0.5 quiet">
              The {entry.what} read failed; this list states that failure rather than showing an empty result.
            </p>
            <button type="button" className="btn btn-ghost mt-1" onClick={entry.retry}>Retry this read</button>
          </div>
        ))}
        <ul className="mt-2 max-h-80 overflow-y-auto" role="listbox" aria-label="Surfaces, places and stored conversations">
          {groups.map(group => (
            <li key={group.name} role="group" aria-label={group.name}>
              {/* Sentence case, like every other group label in the product. A tracked-out all-caps label
                  above a list is the template chrome this system removed everywhere else; the palette was
                  the last place still carrying it, because the rule lived in a utility and not a stylesheet. */}
              <p className="px-2 pt-2 text-[11px] font-semibold quiet" aria-hidden="true">{group.name}</p>
              <ul role="presentation">
                {group.rows.map(({ item, index }) => (
                  <li key={item.id} role="option" aria-selected={index === active}>
                    <button
                      type="button"
                      className={'flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-left text-[length:var(--step-0)] transition-colors ' + (index === active ? 'bg-glass border border-glass-line' : 'hover:bg-glass-3')}
                      onMouseEnter={() => setActive(index)}
                      onClick={() => { item.run(); onClose(); }}
                    >
                      {<PaletteIcon viewId={item.viewId} />}
                      <span className="min-w-0 flex-1">
                        <span className="block truncate">{item.label}</span>
                        {item.hint ? <span className="mt-0.5 block truncate text-[11px] quiet">{item.hint}</span> : null}
                      </span>
                      {index === active ? <CornerDownLeft size={14} className="shrink-0 text-mute" aria-hidden="true" /> : null}
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
        {!items.length ? (
          <p className="mt-2 px-2 py-3 text-xs quiet">
            {needle.length >= 2 && places.isFetching
              ? 'Reading the place catalogue for that name…'
              : 'Nothing matches that yet. Try a surface name, a place, an action, or a recent question.'}
          </p>
        ) : null}
        <p className="mt-2 text-[11px] quiet">Alt+K opens this anywhere. Alt+1…9 opens a numbered surface.</p>
      </div>
    </dialog>
  );
}

/* The palette draws the same icon a surface is drawn with; an entry that is not a surface gets the
   sparkle the product uses for its own actions. */
function PaletteIcon({ viewId }: { viewId?: string }) {
  const Icon = (viewId && SURFACE_ICONS[viewId]) || Sparkles;
  return <span className="icon-tile icon-tile-sm shrink-0" aria-hidden="true"><Icon size={14} /></span>;
}
