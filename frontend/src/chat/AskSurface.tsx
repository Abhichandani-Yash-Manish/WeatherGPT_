/* The Ask surface: the conversation, the composer, and the stored conversations beside them.

   A choice a card offers is sent with its selection identifier when the engine supplied one, so the
   follow-up continues the same conversation rather than re-resolving the name from scratch. */

import { useEffect, useRef } from 'react';
import type { AnswerPacket, Languages } from '../api/types';
import { postJson } from '../api/client';
import { Composer } from './Composer';
import { ConversationRail } from './ConversationRail';
import { Transcript } from './Transcript';
import { Welcome } from './Welcome';
import { useConversation } from './useConversation';
import { useWideScreen } from '../shell/useWideScreen';

export type AskSurfaceProps = {
  language: string;
  persona: string;
  personas?: { id: string; label: string; who?: string; starters?: string[]; note?: string }[];
  languages?: Languages;
  seed?: { question: string; nonce: number } | null;
  /** A stored conversation to open on arrival, from #/assistant?conversation=<id>. */
  restoreId?: string | null;
};

export function AskSurface({ language, persona, personas, languages, seed, restoreId = null }: AskSurfaceProps) {
  const conversation = useConversation({ outputLanguage: language, persona });
  const wide = useWideScreen();
  const sentSeed = useRef<number | null>(null);
  const restored = useRef<string | null>(null);

  /* A conversation named in the address is opened once, so a reader can be sent to one and then
     keep reading without the address fighting every later turn. */
  useEffect(() => {
    if (!restoreId || restored.current === restoreId) return;
    restored.current = restoreId;
    void conversation.restore(restoreId);
  }, [restoreId, conversation]);

  useEffect(() => {
    if (!seed || sentSeed.current === seed.nonce) return;
    sentSeed.current = seed.nonce;
    void conversation.send(seed.question);
  }, [seed, conversation]);

  const reading = (personas || []).find(entry => entry.id === persona) || null;

  const followUp = (text: string) => {
    const lastAnswer = [...conversation.turns].reverse().find(turn => turn.role === 'answer') as { packet: AnswerPacket } | undefined;
    const choices = lastAnswer?.packet.choices || [];
    const match = choices.find(choice => {
      const record = choice as Record<string, unknown>;
      const value = String(record.value || record.label || record.place || '');
      return value === text;
    }) as Record<string, unknown> | undefined;
    const selectionId = match?.selection_id ? String(match.selection_id) : undefined;
    void conversation.send(text, selectionId ? { selectionId } : undefined);
  };

  const refresh = async (packet: AnswerPacket) => {
    const point = Object.values(packet.resolved_points || {})[0];
    const latitude = point?.coordinates?.latitude ?? point?.latitude;
    const longitude = point?.coordinates?.longitude ?? point?.longitude;
    if (typeof latitude !== 'number' || typeof longitude !== 'number') {
      conversation.notify('This answer did not resolve a single place point, so a collection cannot be requested for it.', 'error');
      return;
    }
    try {
      const result = await postJson<{ refresh?: { message?: string; state?: string; claims_this_action?: number } }>('/api/refresh', {
        question: packet.question,
        coordinates: { latitude, longitude },
      });
      const refresh = result.refresh || {};
      conversation.notify(
        (refresh.message || 'A collection was requested.') +
          (refresh.state === 'already_fresh' ? ' Nothing had to be collected: the stored evidence is still within its serving lifetime.' : ''),
        'calm',
      );
    } catch (error) {
      conversation.notify(String((error as Error)?.message || error), 'error');
    }
  };

  return (
    <div className="flex min-h-0 flex-1 gap-4" data-surface="assistant">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {conversation.turns.length || conversation.working ? (
          <Transcript
            turns={conversation.turns}
            working={conversation.working}
            register={conversation.register}
            onFollowUp={followUp}
            onStop={() => void conversation.stop()}
            onRefresh={packet => void refresh(packet)}
          />
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto">
            <Welcome onAsk={question => void conversation.send(question)} reading={reading} />
          </div>
        )}
        {conversation.restoredNote ? <p className="text-[11px] quiet">{conversation.restoredNote}</p> : null}
        <div className="pb-2 pt-2">
          <Composer
            draft={conversation.draft}
            onDraft={conversation.setDraft}
            onSend={text => void conversation.send(text)}
            busy={Boolean(conversation.working)}
            language={language}
            languages={languages}
            onStop={() => void conversation.stop()}
          />
        </div>
        {!wide ? (
          /* The stored-conversation column belongs to this column at narrow widths. As a sibling of the
             conversation it took width from the composer, which collapsed the question box. */
          <details className="card mb-2 px-3 py-2" data-testid="rail-narrow">
            <summary className="cursor-pointer text-xs font-semibold text-ink-soft">
              Reading register and stored conversations
            </summary>
            <div className="mt-2 flex">
              <ConversationRail
                currentId={conversation.conversationId}
                onOpen={id => void conversation.restore(id)}
                onNew={conversation.clear}
                register={conversation.register}
                onRegister={conversation.setRegister}
                wide
              />
            </div>
          </details>
        ) : null}
      </div>
      {wide ? (
        <ConversationRail
          currentId={conversation.conversationId}
          onOpen={id => void conversation.restore(id)}
          onNew={conversation.clear}
          register={conversation.register}
          onRegister={conversation.setRegister}
        />
      ) : null}
    </div>
  );
}
