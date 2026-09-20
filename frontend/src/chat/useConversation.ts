/* One reducer for a turn, so a turn is one state machine rather than five refs.

   The shape follows the engine's own contract: a preview may arrive while the real turn is still
   working, the progress route names the stage of THE REQUEST THIS TURN MINTED — never another
   turn's — and the answer replaces the whole working box when it lands. Nothing here fabricates a
   stage, a percentage or an ETA.

   Three things a reader may do to a turn are also here, because each of them moves turns rather
   than only sending a request: the question may be edited (the turn and everything after it is
   dropped, so the answer that belonged to it is replaced rather than left beside it), a refusal may
   be retried and an answer re-asked (the answer is replaced in its own place, the question stays),
   and a place choice the engine offered is resolved inline instead of costing a whole turn. */

import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react';
import { ApiError } from '../api/client';
import type { AnswerPacket, ChatPreview, ChatProgress } from '../api/types';
import * as chat from './api';
import {
  clearInflight, freshnessNote, readInflight, readRegister, writeInflight, writeRegister,
  type Register, type Turn, type TurnChange, type Working,
} from './model';

export type ConversationState = {
  turns: Turn[];
  working: Working | null;
  conversationId: string | null;
  register: Register;
  draft: string;
  restoredNote: string | null;
};

type Action =
  /* `turn` is null when the question is already on screen and only its answer is being replaced. */
  | { type: 'ask'; turn: Turn | null; working: Working; replaces: string | null }
  | { type: 'preview'; key: string; preview: ChatPreview | null; failed: string | null }
  | { type: 'progress'; key: string; progress: ChatProgress }
  | { type: 'answer'; key: string; turn: Turn; conversationId: string | null; replaces: string | null }
  | { type: 'notice'; key: string; turn: Turn; draft: string; replaces: string | null }
  | { type: 'edit'; key: string }
  | { type: 'stopping'; key: string; detail: string }
  | { type: 'stopped'; key: string; detail: string }
  | { type: 'draft'; text: string }
  | { type: 'register'; value: Register }
  | { type: 'restore'; turns: Turn[]; conversationId: string; note: string | null }
  | { type: 'clear' };

/* The register is a stored preference, so it is read when a conversation surface mounts rather than once
   when this module is imported. A reader who sets it on the front door and then asks a question gets the
   register they chose, in the same session, without a reload. */
const freshConversation = (): ConversationState => ({
  turns: [],
  working: null,
  conversationId: null,
  register: readRegister(),
  draft: '',
  restoredNote: null,
});

/* Everything up to — but not including — the turn named. A replaced answer takes the turn and anything
   after it with it, so a later answer can never sit beside an outcome that was replaced. */
function upTo(turns: Turn[], key: string | null): Turn[] {
  if (!key) return turns;
  const index = turns.findIndex(turn => turn.key === key);
  return index < 0 ? turns : turns.slice(0, index);
}

function reducer(state: ConversationState, action: Action): ConversationState {
  switch (action.type) {
    case 'ask':
      return {
        ...state,
        turns: [...upTo(state.turns, action.replaces), ...(action.turn ? [action.turn] : [])],
        working: action.working,
        draft: '',
        restoredNote: null,
      };
    case 'preview':
      if (!state.working || state.working.key !== action.key) return state;
      return { ...state, working: { ...state.working, preview: action.preview, previewFailed: action.failed } };
    case 'progress':
      if (!state.working || state.working.key !== action.key) return state;
      return { ...state, working: { ...state.working, progress: action.progress } };
    /* The question and its answer are two turns, and the question stays: the answer replaces the working
       box, not the thing that was asked.

       Both are guarded by the turn's key, as preview and progress already were. A request that is still in
       flight when the reader starts a new conversation would otherwise land in that new conversation —
       minutes later, under a question no longer on screen — and a refusal would additionally put its
       question back into a composer the reader had moved on from. An abandoned turn owns nothing, and
       that includes the turn an edit or a retry has already replaced. */
    case 'answer':
      if (!state.working || state.working.key !== action.key) return state;
      return {
        ...state,
        turns: [...upTo(state.turns, action.replaces), action.turn],
        working: null,
        conversationId: action.conversationId || state.conversationId,
      };
    case 'notice':
      if (!state.working || state.working.key !== action.key) return state;
      return { ...state, turns: [...upTo(state.turns, action.replaces), action.turn], working: null, draft: action.draft };
    /* Editing the question the reader just asked: that turn and everything after it goes, and the
       question returns to the box so the correction is what is sent next. The working box goes with
       it — the request in flight is aborted by the caller, and if it answers anyway the key guard
       above drops it. */
    case 'edit': {
      const index = state.turns.findIndex(turn => turn.key === action.key);
      if (index < 0) return state;
      const turn = state.turns[index];
      return { ...state, turns: state.turns.slice(0, index), working: null, draft: turn.role === 'user' ? turn.text : state.draft, restoredNote: null };
    }
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
      clearInflight();
      return { ...state, turns: [], working: null, conversationId: null, draft: '', restoredNote: null };
    default:
      return state;
  }
}

function keyFor(requestId: string): string {
  return 'turn-' + requestId;
}

/* How many times a resumed turn may be asked what happened to it before the interface says it does
   not know. A minute of one-second reads: past that, "I could not collect it" is the honest answer. */
const RESUME_TICKS = 60;
const RESUME_INTERVAL_MS = 1000;

export type ConversationOptions = { outputLanguage?: string; persona?: string };

export type AskExtra = {
  selectionId?: string;
  coordinates?: { latitude: number; longitude: number };
  place?: { label: string; latitude: number; longitude: number; state?: string; district?: string };
  window?: string;
  change?: TurnChange;
  /* How this request sits in the transcript: a new question appends a turn, a replacement keeps the
     question already on screen and replaces the answer named. */
  placement?: { kind: 'replace'; key: string };
  /* For a re-ask: the answer that is being replaced, so the new one can say what it knows about
     freshness, and the engine's own sentence from a collection asked for first. */
  previous?: AnswerPacket;
  freshNote?: string | null;
};

export function useConversation(options: ConversationOptions = {}) {
  const [state, dispatch] = useReducer(reducer, undefined, freshConversation);
  const pollRef = useRef<number | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const previewRef = useRef<AbortController | null>(null);
  const conversationRef = useRef<string | null>(null);
  const languageRef = useRef(options.outputLanguage || '');
  const personaRef = useRef(options.persona || '');
  const resumedRef = useRef(false);

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
    async (text: string, extra: AskExtra = {}) => {
      const question = text.trim();
      if (!question) return;
      stopPolling();
      /* Whatever was in flight is abandoned here rather than left to resolve into a turn that has moved
         on. The reducer would drop its answer anyway; this stops the work as well as the update. */
      controllerRef.current?.abort();
      const requestId = chat.newRequestId();
      const key = keyFor(requestId);
      const at = new Date().toISOString();
      const replaces = extra.placement?.kind === 'replace' ? extra.placement.key : null;
      dispatch({
        type: 'ask',
        /* A replacement keeps the question already on screen: the reader asked it again, they did not
           ask it twice, so no second copy of it is added. */
        turn: replaces ? null : { key: key + ':question', role: 'user', text: question, at },
        working: { key, requestId, question, startedAt: Date.now(), preview: null, previewFailed: null, progress: null, stopRequested: false, stopDetail: null },
        replaces,
      });
      /* The pointer a reload needs: this tab's turn in flight, by the identifier the workspace will
         answer under. It is written before the request and cleared the moment the turn resolves. */
      writeInflight({ request_id: requestId, question, at, conversation_id: conversationRef.current });

      /* The first reading is asked for first and is allowed to fail quietly: it is a courtesy, never
         evidence, and a turn must not be held up by it. A re-ask is not a first reading, so it is not
         asked for again. */
      if (!replaces) {
        const previewController = new AbortController();
        previewRef.current?.abort();
        previewRef.current = previewController;
        chat
          .preview({ ...body(question), selection_id: extra.selectionId, coordinates: extra.coordinates })
          .then(value => dispatch({ type: 'preview', key, preview: value, failed: null }))
          .catch(() => dispatch({ type: 'preview', key, preview: null, failed: 'The first reading did not come back; the answer is unaffected.' }));
      }

      const controller = new AbortController();
      controllerRef.current = controller;
      const read = async () => {
        try {
          /* This turn's own request id: the stage a page shows is the stage of its own question, and
             never the stage of a turn running beside it. */
          dispatch({ type: 'progress', key, progress: await chat.progress(requestId) });
        } catch {
          /* a progress read that fails changes nothing: the turn keeps working and the clock keeps running */
        }
      };
      /* The stage as the engine reaches it. `/api/chat/stream` carries the same payloads the poll carries, so
         nothing here learns a stage the poll would not have stated; it simply hears it when it happens rather
         than up to 900 ms later. Measured against a live turn (docs/131): first frame 404 ms, the engine's own
         `retrieving` at 2825 ms, and the answer at 6000 ms.

         The poll stays, and starts ONLY after the stream has failed: a workspace that cannot stream must still
         be able to say which stage it is in, and a healthy stream must not double the reads. The answer is not
         taken from the stream even though the stream delivers it - the POST already answers with the packet, and
         applying one answer twice is a different bug from the one this fixes. */
      const follow = async () => {
        try {
          await chat.stream(requestId, { onProgress: progress => dispatch({ type: 'progress', key, progress }) }, controller.signal);
        } catch (error) {
          if ((error as Error)?.name === 'AbortError') return;
          void read();
          pollRef.current = window.setInterval(read, 900);
        }
      };
      void follow();

      const change = extra.change;
      try {
        /* The signal, which this never passed. The controller was created and stored and did nothing, so
           an abandoned turn's request kept running to completion against a server that had been asked for
           nothing. Stopping still asks the server to stop as well: that is what releases its work. */
        const packet: AnswerPacket = await chat.ask(
          {
            ...body(question),
            request_id: requestId,
            selection_id: extra.selectionId,
            coordinates: extra.coordinates,
            place: extra.place,
            window: extra.window,
          },
          controller.signal,
        );
        stopPolling();
        clearInflight();
        /* Only a re-ask says anything about freshness, and only from the two packets' own retrieval
           instants. A first answer states none. */
        const freshness = extra.previous
          ? [freshnessNote(extra.previous, packet), extra.freshNote].filter(Boolean).join(' ')
          : undefined;
        dispatch({
          type: 'answer',
          key,
          turn: {
            key: key + ':answer',
            role: 'answer',
            packet,
            at: packet.answered_at_utc || new Date().toISOString(),
            ...(freshness ? { freshness } : {}),
            ...(change ? { changed: change } : {}),
          },
          conversationId: packet.conversation_id || null,
          replaces,
        });
      } catch (error) {
        stopPolling();
        clearInflight();
        const message = error instanceof ApiError ? error.message : String((error as Error)?.message || error);
        const calm = error instanceof ApiError && (error.kind === 'busy' || error.kind === 'unavailable');
        dispatch({
          type: 'notice',
          key,
          turn: {
            key: key + ':notice',
            role: 'notice',
            tone: calm ? 'calm' : 'error',
            text: message,
            at: new Date().toISOString(),
            kind: error instanceof ApiError ? error.kind : undefined,
            ...(change ? { changed: change } : {}),
          },
          draft: question,
          replaces,
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
    controllerRef.current?.abort();
    controllerRef.current = null;
    stopPolling();
    dispatch({ type: 'clear' });
  }, [stopPolling]);

  /* Editing the question just asked: the turn and everything after it goes, the question comes back
     into the box, and any request still in flight is aborted. What answers next answers the corrected
     question, and the answer that belonged to the old one is not left beside it. */
  const edit = useCallback((key: string) => {
    previewRef.current?.abort();
    controllerRef.current?.abort();
    controllerRef.current = null;
    stopPolling();
    clearInflight();
    dispatch({ type: 'edit', key });
  }, [stopPolling]);

  /* Asking a question again in place of the answer it had: a refusal retried, an answer regenerated, or
     one thing about the turn changed. The question on screen stays and the answer is replaced where it
     stood, so a retry can never leave the refused answer beside the fresh one. */
  const reask = useCallback(
    (
      turnKey: string,
      question: string,
      options: { previous?: AnswerPacket; freshNote?: string | null; change?: TurnChange; place?: AskExtra['place']; window?: string } = {},
    ) =>
      send(question, {
        placement: { kind: 'replace', key: turnKey },
        previous: options.previous,
        freshNote: options.freshNote,
        change: options.change,
        place: options.place,
        window: options.window,
      }),
    [send],
  );

  /* A place the engine offered, resolved inside the turn that offered it rather than by asking a new
     question. The engine binds the choice to the question it was offered for, so the client sends that
     same question and the engine records one answer, not a second turn. */
  const resolveSelection = useCallback(
    (selectionId: string, turnKey: string, question: string, change?: TurnChange) =>
      send(question, { selectionId, placement: { kind: 'replace', key: turnKey }, change }),
    [send],
  );

  const setDraft = useCallback((text: string) => dispatch({ type: 'draft', text }), []);

  const setRegister = useCallback((value: Register) => {
    writeRegister(value);
    dispatch({ type: 'register', value });
  }, []);

  const restore = useCallback(async (id: string) => {
    stopPolling();
    clearInflight();
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
    const key = 'notice-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 7);
    dispatch({ type: 'notice', key, turn: { key, role: 'notice', tone, text, at: new Date().toISOString() }, draft: '', replaces: null });
  }, []);

  /* A turn that outlived the page. The tab kept the request id it minted; this asks the workspace what
     became of that exact turn. Every answer is one of the workspace's own states, and the turn is put
     on screen only once the workspace has confirmed it: a pointer this process cannot confirm is a
     stale line in this browser's storage, not evidence that anything was lost, so it produces nothing
     on screen rather than a question or an error about a turn nobody can name. A turn the workspace
     does confirm is shown with its own question, polled for its own stage, and landed when it lands. */
  const resume = useCallback(async () => {
    if (resumedRef.current) return;
    const stored = readInflight();
    if (!stored) return;
    resumedRef.current = true;
    const key = keyFor(stored.request_id);
    let shown = false;
    const show = () => {
      if (shown) return;
      shown = true;
      dispatch({
        type: 'ask',
        turn: { key: key + ':question', role: 'user', text: stored.question, at: stored.at },
        working: {
          key, requestId: stored.request_id, question: stored.question, startedAt: Date.now(),
          preview: null, previewFailed: null, progress: null, stopRequested: false, stopDetail: null,
        },
        replaces: null,
      });
    };
    let ticks = 0;
    const giveUp = () => {
      stopPolling();
      clearInflight();
    };
    const read = async () => {
      ticks += 1;
      let held;
      try {
        held = await chat.result(stored.request_id);
      } catch {
        /* The workspace did not answer this read, so nothing is known about the turn: no claim and no
           question are put on screen from a read that failed. */
        giveUp();
        return;
      }
      if (held.state === 'ready' || held.state === 'cancelled') {
        const packet = held.packet;
        if (!packet) {
          giveUp();
          return;
        }
        show();
        stopPolling();
        clearInflight();
        dispatch({
          type: 'answer',
          key,
          turn: { key: key + ':answer', role: 'answer', packet, at: packet.answered_at_utc || new Date().toISOString() },
          conversationId: packet.conversation_id || null,
          replaces: null,
        });
        return;
      }
      if (held.state === 'expired' || held.state === 'unknown') {
        giveUp();
        return;
      }
      /* The workspace holds this turn and it is still running. */
      show();
      if (ticks > RESUME_TICKS) {
        stopPolling();
        clearInflight();
        dispatch({
          type: 'notice',
          key,
          turn: {
            key: key + ':notice',
            role: 'notice',
            tone: 'calm',
            text: 'This turn was still running when this page stopped waiting for it, and after ' + RESUME_TICKS +
              ' reads the workspace has still not finished it. The question is back in the box; nothing is being claimed about the turn.',
            at: new Date().toISOString(),
          },
          draft: stored.question,
          replaces: null,
        });
        return;
      }
      try {
        dispatch({ type: 'progress', key, progress: await chat.progress(stored.request_id) });
      } catch {
        /* the stage read failing changes nothing about the turn */
      }
    };
    void read();
    pollRef.current = window.setInterval(read, RESUME_INTERVAL_MS);
  }, [stopPolling]);

  const ledger = useMemo(() => ({ clear, restore }), [clear, restore]);

  return { ...state, send, stop, clear, edit, reask, resolveSelection, setDraft, setRegister, restore, resume, ledger, notify };
}
