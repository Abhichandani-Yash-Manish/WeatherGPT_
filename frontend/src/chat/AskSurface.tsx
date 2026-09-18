/* The Ask surface: the conversation, the composer, and the stored conversations beside them.

   A choice a card offers is sent with its selection identifier when the engine supplied one, so the
   follow-up continues the same conversation rather than re-resolving the name from scratch. */

import { useEffect, useRef, type ReactNode } from 'react';
import type { AnswerPacket, Languages } from '../api/types';
import { postJson } from '../api/client';
import { Composer } from './Composer';
import { Transcript } from './Transcript';
import { Welcome } from './Welcome';
import { useConversation } from './useConversation';

export type AskSurfaceProps = {
  language: string;
  persona: string;
  personas?: { id: string; label: string; who?: string; starters?: string[]; note?: string }[];
  languages?: Languages;
  seed?: { question: string; nonce: number } | null;
  /** A stored conversation to open on arrival, from #/assistant?conversation=<id>. */
  restoreId?: string | null;
  /** What the machine says before the reader has asked anything. Rendered only while the transcript is empty,
      so it opens the conversation and then gets out of the way. */
  opening?: ReactNode;
  /** Openings offered under the question box, the way a generative tool offers them: a way in, not a menu. */
  suggestions?: { label: string; question: string }[] | null;
  /** Whether this surface is holding a conversation rather than standing at its welcome. The page around it
      changes when it does: the sky expands and recedes so the transcript owns the screen. */
  onChatState?: (chatting: boolean) => void;
};

export function AskSurface({
  language,
  persona,
  personas,
  languages,
  seed,
  restoreId = null,
  opening = null,
  suggestions = null,
  onChatState,
}: AskSurfaceProps) {
  const conversation = useConversation({ outputLanguage: language, persona });
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

  /* One effect, one boolean, so the page around the conversation never has to know how a transcript is stored. */
  const chatting = conversation.turns.length > 0 || Boolean(conversation.working);
  useEffect(() => {
    onChatState?.(chatting);
  }, [chatting, onChatState]);

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
    <div className="flex min-h-0 flex-1 gap-4" data-chat={chatting ? 'true' : 'false'} data-surface="assistant" data-reading={reading?.id || ''}>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {chatting ? (
          <Transcript
            turns={conversation.turns}
            working={conversation.working}
            onFollowUp={followUp}
            onStop={() => void conversation.stop()}
            onRefresh={packet => void refresh(packet)}
          />
        ) : (
          /* The shape every reader already knows: at the empty state the question box is the hero, sitting in the
             middle of the screen with the opening above it; once there are turns it drops to the foot of the column
             and the conversation takes the room. */
          <div className="flex flex-col">
            {opening ?? <Welcome onAsk={question => void conversation.send(question)} reading={reading} />}
          </div>
        )}
        {conversation.restoredNote ? <p className="text-[11px] quiet">{conversation.restoredNote}</p> : null}
        <div className="f-dock">
          <Composer
            draft={conversation.draft}
            onDraft={conversation.setDraft}
            onSend={text => void conversation.send(text)}
            busy={Boolean(conversation.working)}
            language={language}
            languages={languages}
            onStop={() => void conversation.stop()}
          />
          {chatting ? (
            <div className="f-starters">
              <button type="button" className="f-starter" onClick={conversation.clear}>
                New
              </button>
            </div>
          ) : null}
          {/* Openings live under the box, where they are a way into the conversation rather than a menu above it. */}
          {!chatting && suggestions?.length ? (
            <div className="f-starters">
              {suggestions.map((suggestion: { label: string; question: string }) => (
                <button
                  key={suggestion.label}
                  type="button"
                  className="f-starter"
                  aria-label={suggestion.question}
                  title={suggestion.question}
                  onClick={() => void conversation.send(suggestion.question)}
                >
                  {suggestion.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
