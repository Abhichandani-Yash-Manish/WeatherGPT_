/* The chat routes, in one place. Every call carries the session token through src/api/client.ts and
   every answer is the engine's own object: nothing here reshapes a payload into a friendlier one. */

import { api as request, getJson, postJson, streamFrames, withQuery } from '../api/client';
import type { AnswerPacket, CancelResult, ChatPreview, ChatProgress, ChatResult, Ledger } from '../api/types';


export type AskBody = {
  question: string;
  conversation_id?: string;
  selection_id?: string;
  coordinates?: { latitude: number; longitude: number };
  output_language?: string;
  request_id?: string;
  persona?: string;
  /* The place the reader set for this turn: a label with its own point, which the engine records as
     supplied by the reader rather than resolved from the sentence. */
  place?: { label: string; latitude: number; longitude: number; state?: string; district?: string };
  /* One of the engine's own day or part-of-day phrases. The engine resolves it from its own tables
     and reports whether it applied; the question text is never rewritten to carry it. */
  window?: string;
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

/* The stage of ONE turn. The identifier the client minted is sent with the read, so a page waiting
   on its own question is never told another turn's stage; without one the route keeps its old
   reading of the workspace's newest turn. */
export function progress(requestId?: string, signal?: AbortSignal): Promise<ChatProgress> {
  return getJson<ChatProgress>(requestId ? withQuery('/api/chat/progress', { request_id: requestId }) : '/api/chat/progress', { signal });
}

/* The turn's own stage, as it happens.

   `/api/chat/stream` answers the same frames the progress route answers, written as the engine reaches each one,
   and the payloads inside them are the read routes' own - so nothing here states a stage, a fraction or a
   confidence the poll would not have stated. Measured against a live turn on 20 September 2026: the first frame
   arrived 404 ms after the ask and the engine's `retrieving` stage at 2825 ms, while the answer came at 6000 ms,
   which is the whole point of it - the wait can say what is happening while it happens.

   It resolves when the stream ends and REJECTS when the route cannot be streamed at all, because the caller
   keeps its poll as the fallback: a wait that cannot be streamed must still be able to say which stage it is in.
   The frame reader is deliberately tolerant of a partial chunk - TCP splits where it likes, and a frame split
   across two reads is the normal case rather than an error. */
export type StreamHandlers = {
  onProgress?: (progress: ChatProgress) => void;
  onResult?: (result: ChatResult) => void;
};

export async function stream(requestId: string, handlers: StreamHandlers, signal?: AbortSignal): Promise<void> {
  await streamFrames(withQuery('/api/chat/stream', { request_id: requestId }), frame => {
    const typed = frame as { kind?: string; progress?: ChatProgress; result?: ChatResult };
    if (typed.kind === 'progress' && typed.progress) handlers.onProgress?.(typed.progress);
    if (typed.kind === 'result' && typed.result) handlers.onResult?.(typed.result);
  }, { signal });
}
/* The packet a finished turn produced, or the state that explains why there is none: pending,
   ready, cancelled, expired or unknown. Used when a reload has to find the turn it was waiting on. */
export function result(requestId: string, signal?: AbortSignal): Promise<ChatResult> {
  return getJson<ChatResult>(withQuery('/api/chat/result', { request_id: requestId }), { signal });
}

/* Ask the workspace to collect fresh evidence for a point. The route answers with its own sentence
   and state; nothing here turns that into a claim that anything was re-read. */
export function collectEvidence(body: { question?: string; coordinates: { latitude: number; longitude: number } }): Promise<{ refresh?: { message?: string; state?: string } }> {
  return postJson('/api/refresh', body);
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

/* The place catalogue's own rows. The route answers `data.matches`; this read named `data.places`,
   which is not a field any response has ever carried, so a caller reading it saw an empty list. */
export function searchPlaces(query: string, signal?: AbortSignal): Promise<{ data?: { matches?: PlaceMatch[] } }> {
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
