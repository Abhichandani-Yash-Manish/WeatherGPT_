/* The stored conversations beside the transcript, and the register switch.

   The register changes how much of a card is unfolded and nothing else: no value, source or warning level
   depends on it. Its default is conversational and the choice is remembered per browser. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { getJson } from '../api/client';
import type { Ledger } from '../api/types';
import { forgetConversation } from './api';
import { REGISTER_ORDER, type Register } from './model';

const REGISTER_LABEL: Record<Register, string> = { brief: 'Brief', conversational: 'Conversational', full: 'Full evidence' };
const REGISTER_NOTE: Record<Register, string> = {
  brief: 'the answer and its leading value',
  conversational: 'adds the window, the other facts, the receipt and the sources',
  full: 'adds the requested tasks, the retrieval choices and the machine record',
};

export function ConversationRail({
  currentId,
  onOpen,
  onNew,
  register,
  onRegister,
  wide = false,
}: {
  currentId: string | null;
  onOpen: (id: string) => void;
  onNew: () => void;
  register: Register;
  onRegister: (value: Register) => void;
  /** Full width when it sits under the composer instead of beside the transcript. */
  wide?: boolean;
}) {
  const client = useQueryClient();
  const [query, setQuery] = useState('');
  const ledger = useQuery({ queryKey: ['conversations'], queryFn: () => getJson<Ledger>('/api/conversations'), staleTime: 20_000 });
  const remove = useMutation({
    mutationFn: (id: string) => forgetConversation(id),
    onSuccess: () => client.invalidateQueries({ queryKey: ['conversations'] }),
  });

  const rows = (ledger.data?.conversations || []).filter(row =>
    query ? (row.opening_question || '').toLowerCase().includes(query.toLowerCase()) : true,
  );

  return (
    <aside
      className={
        'card flex shrink-0 flex-col gap-3 px-3 py-3 ' +
        (wide ? 'w-full' : 'w-64')
      }
      aria-label="Stored conversations and reading register"
    >
      <div>
        <p className="eyebrow">Reading register</p>
        <div className="mt-1 flex flex-wrap gap-1">
          {REGISTER_ORDER.map(option => (
            <button
              key={option}
              type="button"
              className={option === register ? 'chip border-data bg-data-wash' : 'chip'}
              aria-pressed={option === register}
              data-register={option}
              onClick={() => onRegister(option)}
            >
              {REGISTER_LABEL[option]}
            </button>
          ))}
        </div>
        <p className="mt-1 text-[11px] quiet">
          A register changes how much of the evidence is unfolded: {REGISTER_NOTE[register]}. It changes no value,
          no source and no warning level.
        </p>
      </div>

      <div className="hairline pt-2">
        <div className="flex items-center justify-between">
          <p className="eyebrow">Stored conversations</p>
          <button type="button" className="btn btn-ghost" onClick={onNew}>
            New
          </button>
        </div>
        <label className="sr-only" htmlFor="ledger-search">Filter stored conversations</label>
        <input
          id="ledger-search"
          value={query}
          onChange={event => setQuery(event.target.value)}
          placeholder="Filter by first question"
          className="mt-1 w-full rounded-card border border-line bg-paper px-2 py-1 text-xs"
        />
        {ledger.isPending ? <p className="mt-2 text-xs quiet">Reading the local store…</p> : null}
        {ledger.isError ? (
          <p className="mt-2 text-xs" role="status">
            The stored conversations could not be read: {String((ledger.error as Error).message)}
          </p>
        ) : null}
        {ledger.data && !rows.length && !(ledger.data.conversations || []).length ? (
          <p className="mt-2 text-xs quiet">Nothing is stored yet. The first question you ask is kept here, on this machine.</p>
        ) : null}
        {ledger.data && !rows.length && (ledger.data.conversations || []).length ? (
          <p className="mt-2 text-xs quiet">No stored conversation matches that filter.</p>
        ) : null}
        <ul className="mt-1 space-y-1">
          {rows.map(row => (
            <li key={row.id} className={row.id === currentId ? 'card border-data px-2 py-1' : 'card px-2 py-1'}>
              <button type="button" className="w-full text-left text-xs" onClick={() => onOpen(row.id)} aria-label={'Open the stored conversation: ' + (row.opening_question || 'Conversation')}>
                <span className="line-clamp-2">{row.opening_question || 'Conversation'}</span>
                <span className="mt-1 block text-[11px] quiet">
                  {row.asked || 0} asked · {row.turns || 0} stored turns
                </span>
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-danger mt-1 opacity-60 hover:opacity-100"
                onClick={() => remove.mutate(row.id)}
                aria-label={'Delete the stored conversation: ' + (row.opening_question || 'Conversation')}
              >
                Delete from this machine
              </button>
            </li>
          ))}
        </ul>
        {ledger.data ? (
          <p className="mt-2 text-[11px] quiet">
            {ledger.data.total} stored on this machine · {ledger.data.limit} listed. {ledger.data.note}
          </p>
        ) : null}
        {remove.isError ? (
          <p className="mt-1 text-[11px]" role="status">
            The stored conversation was not deleted: {String((remove.error as Error).message)}
          </p>
        ) : null}
      </div>
    </aside>
  );
}
