/* One reducer for a turn, so a turn is one state machine rather than five refs.

   The shape follows the engine's own contract: a preview may arrive while the real turn is still
   working, the progress route names the stage the server is in now, and the answer replaces the whole
   working box when it lands. Nothing here fabricates a stage, a percentage or an ETA. */

import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react';
import { ApiError } from '../api/client';
import type { AnswerPacket, ChatPreview, ChatProgress } from '../api/types';
import * as chat from './api';
import { readRegister, writeRegister, type Register, type Turn, type Working } from './model';

export type ConversationState = {
  turns: Turn[];
  working: Working | null;
  conversationId: string | null;
  register: Register;
  draft: string;
  restoredNote: string | null;
};

type Action =
  | { type: 'ask'; turn: Turn; working: Working }
  | { type: 'preview'; key: string; preview: ChatPreview | null; failed: string | null }
  | { type: 'progress'; key: string; progress: ChatProgress }
  | { type: 'answer'; key: string; turn: Turn; conversationId: string | null }
  | { type: 'notice'; key: string; turn: Turn; draft: string }
  | { type: 'stopping'; key: string; detail: string }
  | { type: 'stopped'; key: string; detail: string }
  | { type: 'draft'; text: string }
  | { type: 'register'; value: Register }
  | { type: 'restore'; turns: Turn[]; conversationId: string; note: string | null }
  | { type: 'clear' };

const initial: ConversationState = { turns: [], working: null, conversationId: null, register: readRegister(), draft: '', restoredNote: null };

function reducer(state: ConversationState, action: Action): ConversationState {
  switch (action.type) {
    case 'ask':
      return { ...state, turns: [...state.turns, action.turn], working: action.working, draft: '', restoredNote: null };
    case 'preview':
      if (!state.working || state.working.key !== action.key) return state;
      return { ...state, working: { ...state.working, preview: action.preview, previewFailed: action.failed } };
    case 'progress':
      if (!state.working || state.working.key !== action.key) return state;
      return { ...state, working: { ...state.working, progress: action.progress } };
    /* The question and its answer are two turns, and the question stays: the answer replaces the working
       box, not the thing that was asked. */
    case 'answer':
      return { ...state, turns: [...state.turns, action.turn], working: null, conversationId: action.conversationId || state.conversationId };
    case 'notice':
      return { ...state, turns: [...state.turns, action.turn], working: null, draft: action.draft };
    case 'stopping':
      if (!state.working || state.working.key !== action.key) return state;
      return { ...state, working: { ...state.working, stopRequested: true, stopDetail: action.detail } };
    case 'stopped':
      if (!state.working || state.working.key !== action.key) return state;
      return { ...state, working: { ...state.working, stopDetail: action.detail } };
    case 'draft':
      return { ...state, draft: action.text };
    case 'register':
      return { ...state, register: action.value };
    case 'restore':
      return { ...state, turns: action.turns, conversationId: action.conversationId, working: null, restoredNote: action.note, draft: '' };
    case 'clear':
      return { ...state, turns: [], working: null, conversationId: null, draft: '', restoredNote: null };
    default:
      return state;
  }
}

function keyFor(requestId: string): string {
  return 'turn-' + requestId;
}

let counter = 0;
function nextKey(prefix: string): string {
  counter += 1;
  return prefix + '-' + Date.now().toString(36) + '-' + counter;
}

export type ConversationOptions = { outputLanguage?: string; persona?: string };

export function useConversation(options: ConversationOptions = {}) {
  const [state, dispatch] = useReducer(reducer, initial);
  const pollRef = useRef<number | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const previewRef = useRef<AbortController | null>(null);
  const conversationRef = useRef<string | null>(null);
  const languageRef = useRef(options.outputLanguage || '');
  const personaRef = useRef(options.persona || '');

  languageRef.current = options.outputLanguage || '';
  personaRef.current = options.persona || '';
  conversationRef.current = state.conversationId;

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const body = useCallback((question: string) => {
    const payload: chat.AskBody = { question };
    if (conversationRef.current) payload.conversation_id = conversationRef.current;
    if (languageRef.current) payload.output_language = languageRef.current;
    if (personaRef.current) payload.persona = personaRef.current;
    return payload;
  }, []);

  const send = useCallback(
    async (text: string, extra: { selectionId?: string; coordinates?: { latitude: number; longitude: number } } = {}) => {
      const question = text.trim();
      if (!question) return;
      stopPolling();
      const requestId = chat.newRequestId();
      const key = keyFor(requestId);
      const at = new Date().toISOString();
      dispatch({ type: 'ask', turn: { key: key + ':question', role: 'user', text: question, at }, working: { key, requestId, question, startedAt: Date.now(), preview: null, previewFailed: null, progress: null, stopRequested: false, stopDetail: null } });

      /* The first reading is asked for first and is allowed to fail quietly: it is a courtesy, never
         evidence, and a turn must not be held up by it. */
      const previewController = new AbortController();
      previewRef.current?.abort();
      previewRef.current = previewController;
      chat
        .preview({ ...body(question), selection_id: extra.selectionId, coordinates: extra.coordinates })
        .then(value => dispatch({ type: 'preview', key, preview: value, failed: null }))
        .catch(() => dispatch({ type: 'preview', key, preview: null, failed: 'The first reading did not come back; the answer is unaffected.' }));

      const controller = new AbortController();
      controllerRef.current = controller;
      const read = async () => {
        try {
          const value = await chat.progress();
          dispatch({ type: 'progress', key, progress: value });
        } catch {
          /* a progress read that fails changes nothing: the turn keeps working and the clock keeps running */
        }
      };
      void read();
      pollRef.current = window.setInterval(read, 900);

      try {
        const packet: AnswerPacket = await chat.ask({ ...body(question), request_id: requestId, selection_id: extra.selectionId, coordinates: extra.coordinates });
        stopPolling();
        dispatch({ type: 'answer', key, turn: { key: key + ':answer', role: 'answer', packet, at: packet.answered_at_utc || new Date().toISOString() }, conversationId: packet.conversation_id || null });
      } catch (error) {
        stopPolling();
        const message = error instanceof ApiError ? error.message : String((error as Error)?.message || error);
        const calm = error instanceof ApiError && (error.kind === 'busy' || error.kind === 'unavailable');
        dispatch({
          type: 'notice',
          key,
          turn: { key: key + ':notice', role: 'notice', tone: calm ? 'calm' : 'error', text: message, at: new Date().toISOString() },
          draft: question,
        });
      } finally {
        if (controllerRef.current === controller) controllerRef.current = null;
      }
    },
    [body, stopPolling],
  );

  /* A stop is a request, and the reply says what happened. The turn keeps owning its own outcome: if it
     finishes first, the answer lands and the request is reported as not_running rather than pretended. */
  const stop = useCallback(async () => {
    const working = state.working;
    if (!working) return;
    dispatch({ type: 'stopping', key: working.key, detail: 'Stop requested. The server stops this turn at its next stage boundary.' });
    try {
      const result = await chat.cancel(working.requestId);
      dispatch({ type: 'stopped', key: working.key, detail: result.detail });
    } catch (error) {
      dispatch({ type: 'stopped', key: working.key, detail: error instanceof ApiError ? error.message : 'The stop request did not reach the workspace.' });
    }
  }, [state.working]);

  const clear = useCallback(() => {
    previewRef.current?.abort();
    controllerRef.current = null;
    stopPolling();
    dispatch({ type: 'clear' });
  }, [stopPolling]);

  const setDraft = useCallback((text: string) => dispatch({ type: 'draft', text }), []);

  const setRegister = useCallback((value: Register) => {
    writeRegister(value);
    dispatch({ type: 'register', value });
  }, []);

  const restore = useCallback(async (id: string) => {
    stopPolling();
    const stored = await chat.transcript(id);
    const turns: Turn[] = (stored.turns || []).map((turn, index) => {
      if (turn.role === 'user') return { key: 'restored-user-' + index, role: 'user' as const, text: turn.content, at: '' };
      return { key: 'restored-answer-' + index, role: 'restored' as const, text: turn.content, at: '' };
    });
    dispatch({ type: 'restore', turns, conversationId: stored.id, note: stored.note || null });
  }, [stopPolling]);

  /* A notice the reader caused outside the transcript (a collection that was requested, for example).
     It states the server's own sentence and claims no answer. */
  const notify = useCallback((text: string, tone: 'calm' | 'error' = 'calm') => {
    const key = nextKey('notice');
    dispatch({ type: 'notice', key, turn: { key, role: 'notice', tone, text, at: new Date().toISOString() }, draft: '' });
  }, []);

  const ledger = useMemo(() => ({ clear, restore }), [clear, restore]);

  return { ...state, send, stop, clear, setDraft, setRegister, restore, ledger, notify };
}
