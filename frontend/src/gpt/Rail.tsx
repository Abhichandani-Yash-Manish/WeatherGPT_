/* The rail: the whole of this product's navigation, in one column.
   ============================================================================
   It replaces two stacked columns — a 56px strip of four homes beside a 264px list of conversations — which
   together took 320px of a 1440px window to say what one column says better. The shape is Codex's sidebar:
   a brand row with the controls, the four homes as a block, the place the answers are about, then the stored
   conversations grouped by recency with the reader's own pinned ones above them.

   Two things about it are deliberately not Codex's:

   1. The shortcuts are ⌥ rather than ⌘. A browser owns ⌘1–⌘9 for its tabs and ⌘N, ⌘T and ⌘W for its own
      windows; a page cannot take them, and printing a shortcut that does not fire is worse than printing
      none. ⌥ is ours, it survives every browser this product is opened in, and the rail shows it beside the
      row it belongs to.
   2. Deleting is still a real deletion of local evidence: it appears on hover, it names the conversation and
      it asks first. Pinning is the opposite — a pin is an arrangement, it is remembered in this browser, and
      it never touches the store. */

import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Bell, History, KeyRound, LayoutGrid, MapPin, MessageSquare, MessageSquarePlus, PanelLeft,
  Pin, PinOff, Search, Settings, Trash2, TriangleAlert, X,
} from 'lucide-react';
import { forgetConversation, ledger } from '../chat/api';
import type { ConversationRow } from '../api/types';
import { HOMES, viewsOf, type Home, type HomeId } from '../shell/homes';
import { useWorkingPlace } from '../modules/Evidence';

const DAY = 86_400_000;

export const HOME_GLYPH: Record<HomeId, typeof MessageSquare> = {
  ask: MessageSquare,
  warnings: TriangleAlert,
  history: History,
  board: LayoutGrid,
};

function groupOf(updated: string | undefined, now: number): string {
  const at = Date.parse(String(updated || ''));
  if (!Number.isFinite(at)) return 'Older';
  const days = Math.floor((now - at) / DAY);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days <= 7) return 'Previous 7 days';
  return 'Older';
}

const ORDER = ['Today', 'Yesterday', 'Previous 7 days', 'Older'];
/* ⌥1 to ⌥9: nine rows carry a number, and the tenth row is reached by scrolling like everything else. */
const SHORTCUTS = 9;

export type RailProps = {
  currentId: string | null;
  onOpen: (id: string) => void;
  onNew: () => void;
  onOpenView: (viewId: string) => void;
  onAsk: (question: string) => void;
  currentView: string;
  home: Home | null;
  collapsed: boolean;
  onToggle: () => void;
  pins: string[];
  onPin: (id: string, pinned: boolean) => void;
  onFindPlace: () => void;
  onPlans: () => void;
  onOwner: () => void;
  onClose?: () => void;
};

export function Rail({
  currentId, onOpen, onNew, onOpenView, onAsk, currentView, home,
  collapsed, onToggle, pins, onPin, onFindPlace, onPlans, onOwner, onClose,
}: RailProps) {
  const [filter, setFilter] = useState('');
  const [searching, setSearching] = useState(false);
  const [failed, setFailed] = useState('');
  const client = useQueryClient();
  const rows = useQuery({ queryKey: ['conversations'], queryFn: () => ledger(), staleTime: 15_000 });
  const place = useWorkingPlace();
  const now = Date.now();

  const { grouped, visible } = useMemo(() => {
    const all: ConversationRow[] = rows.data?.conversations || [];
    const needle = filter.trim().toLowerCase();
    const kept = needle
      ? all.filter(row => String(row.opening_question || '').toLowerCase().includes(needle))
      : all;
    const out = new Map<string, ConversationRow[]>();
    const pinned = new Map<string, ConversationRow[]>();
    kept.forEach(row => {
      const bucket = pins.includes(row.id) ? pinned : out;
      const key = pins.includes(row.id) ? 'Pinned' : groupOf(row.updated, now);
      bucket.set(key, [...(bucket.get(key) || []), row]);
    });
    const groups: [string, ConversationRow[]][] = [
      ...(pinned.get('Pinned') ? [['Pinned', pinned.get('Pinned') as ConversationRow[]] as [string, ConversationRow[]]] : []),
      ...ORDER.filter(key => out.has(key)).map(key => [key, out.get(key) as ConversationRow[]] as [string, ConversationRow[]]),
    ];
    const flat = groups.flatMap(([, items]) => items);
    return { grouped: groups, visible: flat.map(row => row.id) };
  }, [rows.data, filter, now, pins]);

  const forget = async (row: ConversationRow) => {
    const name = row.opening_question || row.id;
    if (!window.confirm('Delete “' + name + '” from this machine? The stored turns go with it.')) return;
    setFailed('');
    try {
      await forgetConversation(row.id);
      void client.invalidateQueries({ queryKey: ['conversations'] });
    } catch (error) {
      /* A delete that did not happen is said, in the server's own words. The list is left as it is rather than
         optimistically emptied: a row that disappears while the store still holds it is a worse lie than a
         row that stays with a sentence under it. */
      setFailed('The stored conversation was not deleted: ' + String((error as Error)?.message || error));
    }
  };

  /* ⌥1–⌥9 opens the n-th row the rail is showing, in the order it is showing them. Read from event.code for
     the reason the collapse is: ⌥1 on macOS is "¡". */
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!event.altKey || event.metaKey || event.ctrlKey) return;
      const digit = /^Digit([1-9])$/.exec(event.code);
      if (!digit) return;
      const id = visible[Number(digit[1]) - 1];
      if (!id) return;
      event.preventDefault();
      onOpen(id);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [visible, onOpen]);

  const here = home?.id ?? 'ask';

  return (
    <aside className="g-rail" aria-label="Workspace" data-collapsed={collapsed ? 'true' : 'false'}>
      <div className="g-rail-head">
        <span className="g-brand">
          <span className="g-brand-mark" aria-hidden="true" />
          <span className="g-brand-name">WeatherGPT</span>
        </span>
        <span className="g-rail-controls">
          <button
            type="button"
            className="g-act"
            aria-label="Search conversations"
            aria-pressed={searching}
            title="Search conversations"
            onClick={() => setSearching(value => !value)}
          >
            <Search size={15} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="g-act"
            aria-label={collapsed ? 'Expand the rail' : 'Collapse the rail'}
            aria-expanded={!collapsed}
            title={collapsed ? 'Expand the rail (⌥B)' : 'Collapse the rail (⌥B)'}
            onClick={onToggle}
          >
            <PanelLeft size={15} aria-hidden="true" />
          </button>
          {onClose ? (
            <button type="button" className="g-act" onClick={onClose} aria-label="Close the conversation list">
              <X size={16} aria-hidden="true" />
            </button>
          ) : null}
        </span>
      </div>

      {searching ? (
        <div className="g-rail-search">
          <label className="sr-only" htmlFor="rail-filter">Filter conversations</label>
          <input
            id="rail-filter"
            className="g-search"
            value={filter}
            onChange={event => setFilter(event.target.value)}
            placeholder="Search conversations"
            autoComplete="off"
            autoFocus
          />
        </div>
      ) : null}

      <nav className="g-homes" aria-label="Homes">
        {HOMES.map(entry => {
          const Glyph = HOME_GLYPH[entry.id];
          return (
            <button
              key={entry.id}
              type="button"
              className="g-home"
              aria-current={entry.id === here ? 'page' : undefined}
              title={entry.label + ' — ' + entry.blurb}
              onClick={() => onOpenView(entry.views[0])}
            >
              <Glyph size={16} aria-hidden="true" />
              <span className="g-home-label">{entry.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="g-rail-body">
        {home && home.id !== 'ask' ? (
          <section className="g-section" aria-label={home.label}>
            <p className="g-rail-label">In {home.label}</p>
            {viewsOf(home).map(view => (
              <div key={view.id} className="g-row" aria-current={view.id === currentView ? 'true' : undefined}>
                <button type="button" className="g-row-text g-row-plain" onClick={() => onOpenView(String(view.id))}>
                  {view.label}
                </button>
              </div>
            ))}
          </section>
        ) : null}

        {/* The place the answers are about. It is the shell's own fact — the composer reads it, the welcome
            reads it, the panel reads it — so the rail states it rather than leaving a reader to infer it. */}
        <section className="g-section" aria-label="Place">
          <p className="g-rail-label">This place</p>
          <p className="g-place">
            <MapPin size={14} aria-hidden="true" />
            <span className="g-place-name">{place?.label || 'No place held'}</span>
          </p>
          <div className="g-rail-actions">
            <button type="button" className="g-quiet" onClick={onFindPlace}>{place ? 'Change' : 'Set a place'}</button>
            {place?.label ? (
              <button type="button" className="g-quiet" onClick={() => onAsk('What is it like in ' + place.label + ' right now?')}>
                Ask about it
              </button>
            ) : null}
          </div>
        </section>

        <section className="g-section" aria-label="Conversations">
          <p className="g-rail-label">Conversations</p>
          <div className="g-rail-actions g-rail-actions-lead">
            <button type="button" className="g-new" onClick={onNew} title="New conversation (⌥N)">
              <MessageSquarePlus size={15} aria-hidden="true" />
              <span className="g-new-label">New conversation</span>
              <kbd className="g-kbd">⌥N</kbd>
            </button>
            <button type="button" className="g-row g-row-plain g-rail-action" onClick={onPlans} title="Plans, watches and the notification inbox">
              <Bell size={15} aria-hidden="true" />
              <span className="g-new-label">Watch</span>
            </button>
          </div>

          {failed ? <p className="g-notice" role="status">{failed}</p> : null}
          {rows.isPending ? <p className="g-empty-note">Reading the stored conversations…</p> : null}
          {rows.isError ? <p className="g-empty-note">The conversation store did not answer. Nothing is listed rather than an empty list being shown as none.</p> : null}
          {!rows.isPending && !rows.isError && !grouped.length ? (
            <p className="g-empty-note">{filter ? 'No stored conversation matches that.' : 'No conversation is stored on this machine yet.'}</p>
          ) : null}

          {grouped.map(([label, items]) => (
            <div key={label}>
              <p className="g-group">{label}</p>
              {items.map(row => {
                const index = visible.indexOf(row.id);
                const pinned = pins.includes(row.id);
                return (
                  <div key={row.id} className="g-row" aria-current={row.id === currentId ? 'true' : undefined}>
                    <button type="button" className="g-row-text g-row-plain" onClick={() => onOpen(row.id)} title={row.opening_question || 'Untitled conversation'}>
                      {row.opening_question || 'Untitled conversation'}
                    </button>
                    {index >= 0 && index < SHORTCUTS ? <kbd className="g-kbd g-kbd-row">⌥{index + 1}</kbd> : null}
                    <button
                      type="button"
                      className="g-row-drop"
                      aria-pressed={pinned}
                      aria-label={(pinned ? 'Unpin ' : 'Pin ') + (row.opening_question || row.id)}
                      title={pinned ? 'Unpin' : 'Pin to the top'}
                      onClick={() => onPin(row.id, !pinned)}
                    >
                      {pinned ? <PinOff size={14} aria-hidden="true" /> : <Pin size={14} aria-hidden="true" />}
                    </button>
                    <button type="button" className="g-row-drop" onClick={() => void forget(row)} aria-label={'Delete ' + (row.opening_question || row.id)}>
                      <Trash2 size={14} aria-hidden="true" />
                    </button>
                  </div>
                );
              })}
            </div>
          ))}
        </section>
      </div>

      <div className="g-rail-foot">
        <button type="button" className="g-row g-row-plain g-rail-action" onClick={() => onOpenView('settings')} title="Sources, settings and this machine's state">
          <Settings size={15} aria-hidden="true" />
          <span className="g-new-label">Settings</span>
        </button>
        <button type="button" className="g-act" onClick={onOwner} aria-label="Owner gate" title="Owner gate">
          <KeyRound size={15} aria-hidden="true" />
        </button>
      </div>
      <p className="g-rail-note">Questions and answers stay on this machine.</p>
    </aside>
  );
}
