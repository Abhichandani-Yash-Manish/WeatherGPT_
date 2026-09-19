/* The chat routes, in one place. Every call carries the session token through src/api/client.ts and
   every answer is the engine's own object: nothing here reshapes a payload into a friendlier one. */

import { api as request, getJson, postJson, withQuery } from '../api/client';
import type { AnswerPacket, CancelResult, ChatPreview, ChatProgress, Ledger } from '../api/types';

export type AskBody = {
  question: string;
  conversation_id?: string;
  selection_id?: string;
  coordinates?: { latitude: number; longitude: number };
  output_language?: string;
  request_id?: string;
  persona?: string;
};

export function newRequestId(): string {
  const generator = window.crypto as Crypto | undefined;
  if (generator?.randomUUID) return generator.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, character => {
    const random = (Math.random() * 16) | 0;
    const value = character === 'x' ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

export function ask(body: AskBody, signal?: AbortSignal): Promise<AnswerPacket> {
  return postJson<AnswerPacket>('/api/chat', body, { signal });
}

export function preview(body: AskBody, signal?: AbortSignal): Promise<ChatPreview> {
  return postJson<ChatPreview>('/api/chat/preview', body, { signal });
}

export function progress(signal?: AbortSignal): Promise<ChatProgress> {
  return getJson<ChatProgress>('/api/chat/progress', { signal });
}

export function cancel(requestId: string): Promise<CancelResult> {
  return postJson<CancelResult>('/api/chat/cancel', { request_id: requestId });
}

/* The stored conversations, newest first. A q searches every stored turn rather than only the opening
   question, and the reply quotes the turn it matched so the search can say why a row is there. */
export function ledger(q?: string): Promise<Ledger> {
  const term = (q || '').trim();
  return getJson<Ledger>(term ? withQuery('/api/conversations', { q: term }) : '/api/conversations');
}

export type Transcript = { schema_version: string; id: string; updated?: string; turns: { role: string; content: string }[]; note?: string };

export function transcript(id: string): Promise<Transcript> {
  return getJson<Transcript>('/api/conversations/' + encodeURIComponent(id));
}

export function forgetConversation(id: string): Promise<unknown> {
  return request<unknown>('/api/conversations/' + encodeURIComponent(id), { method: 'DELETE' });
}

export type PlaceMatch = { label?: string; name?: string; latitude?: number; longitude?: number; state?: string; district?: string };

export function searchPlaces(query: string, signal?: AbortSignal): Promise<{ data?: { places?: PlaceMatch[] } }> {
  return getJson(withQuery('/api/places/search', { q: query }), { signal });
}

export function saveBrief(body: unknown): Promise<unknown> {
  return postJson('/api/briefs/save', body);
}

export type HeardSpeech = {
  transcript?: string;
  text?: string;
  detail?: string;
  state?: string;
  detected_language_code?: string;
  recognition_probability?: number;
};

/* The route takes the recording base64-encoded in JSON, so the caller encodes and the engine decodes.
   Recognition confidence travels with the transcript because it is the recogniser's own number. */
export function transcribe(audio: { audio_base64: string; content_type: string; language?: string }): Promise<HeardSpeech> {
  return postJson<HeardSpeech>('/api/speech/transcribe', audio, { timeoutMs: 120_000 });
}

export function speak(body: { text: string; language: string }): Promise<{ audio_url?: string; detail?: string; state?: string }> {
  return postJson('/api/speech/speak', body);
}

export function personas(): Promise<{ data?: { personas?: { id: string; label: string; who?: string; starters?: string[]; note?: string }[]; note?: string } }> {
  return getJson('/api/personas');
}
