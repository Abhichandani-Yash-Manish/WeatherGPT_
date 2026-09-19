/* The conversation rail.
   ============================================================================
   ChatGPT's left rail, targeted deliberately: a new-conversation control, a filter, and the stored
   conversations grouped by recency — Today, Yesterday, Previous 7 days, Older. Each row is the question the
   conversation opened with, which is the only name a conversation here has ever had.

   Deleting is a real deletion of local evidence, so it is not a button sitting at content weight: it appears
   on hover, it names the conversation, and it asks first. */

import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { MessageSquarePlus, Search, Trash2, X } from 'lucide-react';
import { forgetConversation, ledger } from '../chat/api';
import type { ConversationRow } from '../api/types';
import { type Home, viewsOf } from '../shell/homes';

const DAY = 86_400_000;

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

export function Rail({
  currentId,
  onOpen,
  onNew,
  onClose,
  home,
  currentView,
  onOpenView,
}: {
  currentId: string | null;
  onOpen: (id: string) => void;
  onNew: () => void;
  onClose?: () => void;
  home: Home | null;
  currentView: string;
  onOpenView: (id: string) => void;
}) {
  const [filter, setFilter] = useState('');
  const client = useQueryClient();
  const rows = useQuery({ queryKey: ['conversations'], queryFn: () => ledger(), staleTime: 15_000 });
  const now = Date.now();

  const groups = useMemo(() => {
    const all: ConversationRow[] = rows.data?.conversations || [];
    const needle = filter.trim().toLowerCase();
    const kept = needle
      ? all.filter(row => String(row.opening_question || '').toLowerCase().includes(needle))
      : all;
    const out = new Map<string, ConversationRow[]>();
    kept.forEach(row => {
      const key = groupOf(row.updated, now);
      out.set(key, [...(out.get(key) || []), row]);
    });
    return ORDER.filter(key => out.has(key)).map(key => [key, out.get(key) as ConversationRow[]] as const);
  }, [rows.data, filter, now]);

  const forget = async (row: ConversationRow) => {
    const name = row.opening_question || row.id;
    if (!window.confirm('Delete “' + name + '” from this machine? The stored turns go with it.')) return;
    await forgetConversation(row.id);
    void client.invalidateQueries({ queryKey: ['conversations'] });
  };

  /* Outside Ask the rail lists the home's own surfaces instead of the reader's conversations. Same slot,
     same width, different subject — a reader in Warnings is choosing a view, not a past question. */
  if (home && home.id !== 'ask') {
    return (
      <aside className="g-rail" aria-label={home.label}>
        <div className="g-rail-head">
          <span className="g-brand">
            <span className="g-brand-mark" aria-hidden="true" />
            {home.label}
            {onClose ? (
              <button type="button" className="g-act g-rail-toggle" style={{ marginLeft: 'auto' }} onClick={onClose} aria-label="Close the section list">
                <X size={16} aria-hidden="true" />
              </button>
            ) : null}
          </span>
          <p className="g-empty-note" style={{ padding: '0 8px 4px' }}>{home.blurb}</p>
        </div>
        <div className="g-history">
          {viewsOf(home).map(view => (
            <div key={view.id} className="g-row" aria-current={view.id === currentView ? 'true' : undefined}>
              <button
                type="button"
                className="g-row-text g-row-plain"
                onClick={() => onOpenView(String(view.id))}
              >
                {view.label}
              </button>
            </div>
          ))}
        </div>
        <div className="g-rail-foot">
          <p className="g-empty-note" style={{ padding: 0 }}>Every value keeps its source and the time it was read.</p>
        </div>
      </aside>
    );
  }

  return (
    <aside className="g-rail" aria-label="Conversations">
      <div className="g-rail-head">
        <span className="g-brand">
          <span className="g-brand-mark" aria-hidden="true" />
          WeatherGPT
          {onClose ? (
            <button type="button" className="g-act g-rail-toggle" style={{ marginLeft: 'auto' }} onClick={onClose} aria-label="Close the conversation list">
              <X size={16} aria-hidden="true" />
            </button>
          ) : null}
        </span>
        <button type="button" className="g-new" onClick={onNew}>
          <MessageSquarePlus size={16} aria-hidden="true" />
          New conversation
        </button>
        <label className="sr-only" htmlFor="rail-filter">Filter conversations</label>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Search size={14} aria-hidden="true" style={{ position: 'absolute', left: 11, color: 'var(--g-mist-2)' }} />
          <input
            id="rail-filter"
            className="g-search"
            style={{ paddingLeft: 32 }}
            value={filter}
            onChange={event => setFilter(event.target.value)}
            placeholder="Search conversations"
            autoComplete="off"
          />
        </div>
      </div>

      <div className="g-history">
        {rows.isPending ? <p className="g-empty-note">Reading the stored conversations…</p> : null}
        {rows.isError ? <p className="g-empty-note">The conversation store did not answer. Nothing is listed rather than an empty list being shown as none.</p> : null}
        {!rows.isPending && !rows.isError && !groups.length ? (
          <p className="g-empty-note">{filter ? 'No stored conversation matches that.' : 'No conversation is stored on this machine yet.'}</p>
        ) : null}
        {groups.map(([label, items]) => (
          <div key={label}>
            <p className="g-group">{label}</p>
            {items.map(row => (
              <div key={row.id} className="g-row" aria-current={row.id === currentId ? 'true' : undefined}>
                <button
                  type="button"
                  className="g-row-text g-row-plain"
                  onClick={() => onOpen(row.id)}
                >
                  {row.opening_question || 'Untitled conversation'}
                </button>
                <button type="button" className="g-row-drop" onClick={() => void forget(row)} aria-label={'Delete ' + (row.opening_question || row.id)}>
                  <Trash2 size={14} aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="g-rail-foot">
        <p className="g-empty-note" style={{ padding: 0 }}>
          Questions and answers stay on this machine.
        </p>
      </div>
    </aside>
  );
}
