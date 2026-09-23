/* The workspace: one page, ChatGPT's architecture, our evidence.
   ============================================================================
   Empty: the hero sentence — the country's published picture as the machine's first line — with the composer
   directly under it and a few openings beneath that. Running: the composer docks to the foot, the field
   expands and recedes, and the turns fill the column.

   The rail, the column width, the docking composer, the transient hover actions and the streaming stop are
   ChatGPT's shape. The claim, the source line, the published colour and the work panel are ours. */

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getJson } from '../api/client';
import type { Languages } from '../api/types';
import { writableLanguages } from '../chat/voice';
import { ArrowDown, ArrowLeft, MapPin, Pencil } from 'lucide-react';

import { collectEvidence, personas as readPersonas, searchPlaces, type PlaceMatch } from '../chat/api';
import { useConversation } from '../chat/useConversation';
import { downloadFile, markdownTurn, stampName } from '../chat/actions';
import { changeNote, isHeld, noticeHint, questionFor, readingLine, WINDOW_CHOICES } from '../chat/model';
import { istStamp, istWindow } from '../lib/time';
import type { AnswerPacket } from '../api/types';
import { SurfaceHost } from '../shell/SurfaceHost';
import { viewById, type ViewEntry } from '../shell/views';
import { AnswerTurn } from '../chat/AnswerTurn';
import { Composer } from './Composer';
import { Field } from './Field';
import { PlacePicker } from './PlacePicker';
import { hourOf, lightAt } from './fieldPaint';
import { chromeFor, i18n } from '../i18n';
import { readSiteLanguage, subscribeSiteLanguage } from '../i18n/siteLanguage';
import { useSky } from './sky';
import { rememberPlace, useWorkingPlace } from '../modules/Evidence';
import { Rail } from './Rail';
import { ReadingPanel, type SourceRead } from './ReadingPanel';
import { useShellPrefs } from './shellState';
import { homeOf } from '../shell/homes';
import { Welcome } from './Welcome';
import { WorkingTurn } from './WorkingTurn';
import { TopBar } from './TopBar';
import './gpt.css';

/* The gap kept above the anchored question, so it reads as the top of a page rather than as a line
   jammed against the frame's edge. */
const ANCHOR_INSET = 12;

/* Three, not eight. The openings are a way in for someone who does not know what to type, not a menu of
   everything the machine can read — that is what the Board home is for. */
const STARTERS = [
  { label: 'Will it rain tomorrow?', id: 'forecast' },
  { label: 'Any warning near me?', id: 'warnings' },
  { label: 'My district advisory', id: 'advisories' },
]
  .map(entry => ({ label: entry.label, question: viewById(entry.id)?.intents?.[0] || '' }))
  .filter(entry => Boolean(entry.question));

/* Changing one thing about a turn, not the whole sentence.
   ============================================================================
   The place a question is read at and the window its claim covers are the two things a reader most often
   wants to move, and the only way to move either was to type the sentence again and hope the planner read
   it the same way. Both controls send the SAME question with the change carried as its own field: the
   engine resolves the change deterministically, records whether it applied it, and the line above the
   answer is written from the engine's own record rather than from what this interface believed it sent.
   Neither control rewrites the sentence.

   A control that sends a sentence carries that sentence in its title — the rule the notify chip already
   follows — so what a reader is about to ask is readable before it is sent. */

/* The place catalogue, read inside the turn being changed. A row that states coordinates can be chosen; a
   row that states none is shown as one rather than resolved somewhere else. */
function PlaceChoice({ onPick, onClose }: { onPick: (row: PlaceMatch) => void; onClose: () => void }) {
  const [term, setTerm] = useState('');
  const query = term.trim();
  const search = useQuery({
    queryKey: ['places', query],
    queryFn: () => searchPlaces(query),
    enabled: query.length >= 2,
    retry: false,
  });
  const rows = search.data?.data?.matches || [];
  return (
    <div className="g-picker-results" role="listbox" aria-label="Places">
      <label className="sr-only" htmlFor="turn-place">Place</label>
      <input
        id="turn-place"
        className="g-search"
        type="search"
        value={term}
        autoComplete="off"
        autoFocus
        onChange={event => setTerm(event.target.value)}
        placeholder="Type at least two characters"
      />
      {search.isFetching ? <p className="g-empty-note">Reading the place catalogue…</p> : null}
      {search.isError ? <p className="g-empty-note">The place catalogue did not answer, so nothing is listed. That is a read failure, not an empty catalogue.</p> : null}
      {!search.isFetching && !search.isError && query.length >= 2 && !rows.length ? (
        <p className="g-empty-note">The catalogue returned no place matching “{query}”.</p>
      ) : null}
      {rows.slice(0, 6).map((row, index) => {
        const latitude = typeof row.latitude === 'number' ? row.latitude : Number.NaN;
        const longitude = typeof row.longitude === 'number' ? row.longitude : Number.NaN;
        const usable = Number.isFinite(latitude) && Number.isFinite(longitude);
        const name = String(row.label || row.name || 'Unnamed row');
        return (
          <button
            key={name + index}
            type="button"
            className="g-picker-row"
            role="option"
            aria-selected={false}
            disabled={!usable}
            title={usable ? 'Asks the same question again, at ' + name + ' · ' + latitude + ', ' + longitude : 'This row states no coordinates'}
            onClick={() => onPick(row)}
          >
            <MapPin size={13} aria-hidden="true" />
            <span className="g-picker-name">{name}</span>
            <span className="g-picker-where">{usable ? 'coordinates in this row' : 'no coordinates in this row'}</span>
          </button>
        );
      })}
      <button type="button" className="g-quiet" onClick={onClose}>Close the place list</button>
    </div>
  );
}

/** The window a claim currently covers, in the engine's own label, for the control that moves it. */
function claimWindow(packet: AnswerPacket): string | null {
  const fact = (packet.facts || []).find(entry => entry.start && entry.end);
  return fact ? istWindow(String(fact.start), String(fact.end)) : null;
}

export type WorkspaceProps = {
  onOpen: (id: string) => void;
  language: string;
  onLanguage: (code: string) => void;
  persona: string;
  onPersona: (id: string) => void;
  /** Opens the shell's place search — the palette, which is the one place surface the product has. */
  onFindPlace?: () => void;
  /** The place an address named, as its own strings: read on arrival, never inferred. */
  placeParam?: { label: string | null; latitude: string | null; longitude: string | null };
  /** Put the place in the address, so the place the answers are about is a link somebody can open. */
  onHoldPlace?: (place: { label: string | null; latitude: number; longitude: number }) => void;
  view?: ViewEntry;
  onAsk?: (question: string) => void;
  onNew?: () => void;
  onPlans?: () => void;
  onOwner?: () => void;
  seed?: { question: string; nonce: number } | null;
  restoreId?: string | null;
  unknownRoute?: string | null;
};

/* Every source this conversation has read, newest read first.
   ============================================================================
   Each claim already carries the source that proves it, folded under the answer. What no surface showed
   was the set: a reader three turns in could not say what the whole conversation rested on without
   opening every fold, which is a strange gap in a product whose proposition is chain of custody.

   This states only what the citations stated. A citation with no product or provider is listed as having
   named none rather than being given one, and the count is how many claims in the thread cite it — which
   is a fact about this conversation, not a judgement about the source. */
export function sourcesRead(turns: { role: string; packet?: AnswerPacket }[]): SourceRead[] {
  const byId = new Map<string, SourceRead>();
  turns.forEach(turn => {
    if (turn.role !== 'answer' || !turn.packet) return;
    const packet = turn.packet;
    const cited = new Map<string, number>();
    (packet.facts || []).forEach(fact => {
      const id = String((fact as { source_id?: string }).source_id || '');
      if (id) cited.set(id, (cited.get(id) || 0) + 1);
    });
    (packet.citations || []).forEach(citation => {
      const id = String(citation.source_id || '');
      if (!id) return;
      const held = byId.get(id);
      const claims = (held?.claims || 0) + (cited.get(id) || 0);
      const retrievedAt = citation.retrieved_at_utc ? String(citation.retrieved_at_utc) : held?.retrievedAt || null;
      byId.set(id, {
        sourceId: id,
        provider: citation.provider ? String(citation.provider) : held?.provider || null,
        product: citation.product ? String(citation.product) : held?.product || null,
        /* The newest read wins: a source read again later is as fresh as its latest read. */
        retrievedAt: held?.retrievedAt && retrievedAt && held.retrievedAt > retrievedAt ? held.retrievedAt : retrievedAt,
        claims,
      });
    });
  });
  return [...byId.values()].sort((a, b) => String(b.retrievedAt || '').localeCompare(String(a.retrievedAt || '')));
}

export function Workspace({
  onOpen, language, onLanguage, persona, onPersona, view, onAsk, onNew, onPlans, onOwner, onFindPlace,
  placeParam = { label: null, latitude: null, longitude: null }, onHoldPlace,
  seed = null, restoreId = null, unknownRoute = null,
}: WorkspaceProps) {
  const conversation = useConversation({ outputLanguage: language, persona });
  const client = useQueryClient();
  const [railOpen, setRailOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { prefs, set: setPrefs } = useShellPrefs();
  /* The turn a search sent the reader to. Null unless a row was opened from a search with a match under it. */
  const [spotlight, setSpotlight] = useState<string | null>(null);
  const sentSeed = useRef<number | null>(null);
  const restored = useRef<string | null>(null);
  const thread = useRef<HTMLDivElement | null>(null);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 120_000);
    return () => window.clearInterval(timer);
  }, []);
  /* The reader's own place when one is held, the national default otherwise. The sun is the same sun either way;
     what changes is where it stands over the page. */
  const workingPlace = useWorkingPlace();
  const latitude = workingPlace?.latitude ?? 23.0;
  const longitude = workingPlace?.longitude ?? 82.5;
  const hour = hourOf(now, latitude, longitude);

  /* The hour is put on the document element as well as on the workspace. Two reasons: html and body take
     their background from it, so the page behind a short thread is the right hour rather than a strip of
     the old one; and color-scheme has to reach the document for native controls — a select's dropdown and
     the scrollbars — to render light on the light hours. */
  /* The interface follows the answer language. A reader who picks Gujarati for answers gets a Gujarati
     product rather than half of one — and the document's lang attribute follows too, because that is what
     a screen reader and the browser's own hyphenation read. */
  /* A pinned SITE language wins; with none pinned this is exactly the old behaviour - follow the answer
     language, and the browser when that is unset. See i18n/siteLanguage.ts for why unset is not English. */
  const pinnedSite = useSyncExternalStore(subscribeSiteLanguage, readSiteLanguage, readSiteLanguage);
  const chrome = pinnedSite || chromeFor(language);
  useEffect(() => {
    void i18n.changeLanguage(chrome);
    document.documentElement.lang = chrome;
  }, [chrome]);

  /* Where the light is standing, from the reader's own sun. Every pane's catch-light and every shadow is
     derived from these four numbers, so the whole surface system is lit from one place and that place is
     the real one. The hour blocks in the stylesheet carry a sensible default for each of the four hours,
     so a pane is lit correctly before this ever runs and stays lit if it never does. */
  const light = lightAt(now, latitude, longitude);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.hour = hour;
    root.style.setProperty('--g-light-x', (light.x * 100).toFixed(1) + '%');
    root.style.setProperty('--g-light-angle', light.angle.toFixed(1) + 'deg');
    root.style.setProperty('--g-light-shadow-x', light.shadowX + 'px');
    root.style.setProperty('--g-light-height', String(light.height));
    return () => {
      delete root.dataset.hour;
      ['--g-light-x', '--g-light-angle', '--g-light-shadow-x', '--g-light-height']
        .forEach(name => root.style.removeProperty(name));
    };
  }, [hour, light.x, light.angle, light.shadowX, light.height]);

  useEffect(() => {
    if (!restoreId || restored.current === restoreId) return;
    restored.current = restoreId;
    void conversation.restore(restoreId);
  }, [restoreId, conversation]);

  /* A place named in the address is held on arrival, and the panel is opened to show what it means — the
     station, the published district days and the hours. It is read once per address, and a malformed or
     half-written one is refused rather than half-applied: a place is either a pair of coordinates that parse
     as numbers or it is nothing. */
  const addressed = `${placeParam.latitude ?? ''},${placeParam.longitude ?? ''},${placeParam.label ?? ''}`;
  const heldFromAddress = useRef<string | null>(null);
  useEffect(() => {
    if (!placeParam.latitude || !placeParam.longitude) return;
    if (heldFromAddress.current === addressed) return;
    heldFromAddress.current = addressed;
    const latitude = Number(placeParam.latitude);
    const longitude = Number(placeParam.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
    if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return;
    rememberPlace({ label: placeParam.label, latitude, longitude });
    setPrefs({ panel: true });
  }, [addressed, placeParam.latitude, placeParam.longitude, placeParam.label, setPrefs]);

  useEffect(() => {
    if (!seed || sentSeed.current === seed.nonce) return;
    sentSeed.current = seed.nonce;
    void conversation.send(seed.question);
  }, [seed, conversation]);

  /* A turn that outlived the page: the tab kept the request id it minted, and this asks the workspace
     what became of that exact turn. Once per mount, because the question it restores is a turn. */
  const resumed = useRef(false);
  useEffect(() => {
    if (resumed.current) return;
    resumed.current = true;
    void conversation.resume();
  }, [conversation]);

  /* Which turn has one of the two change controls open, and which one. */
  const [changing, setChanging] = useState<{ key: string; kind: 'place' | 'window' } | null>(null);

  const chatting = conversation.turns.length > 0 || Boolean(conversation.working);

  /* Which answer is written out at reading pace, and which is simply shown.
     ------------------------------------------------------------------------------------------------
     Exactly one qualifies: the answer that landed while THIS page was watching the turn work. A
     conversation restored from the rail, a reload, and every older turn in the thread are shown whole and
     at once - performing a transcript the reader has already read would be a trick rather than a feature.

     Decided DURING RENDER, which is the only place it can be decided correctly. The answer turn and the
     end of the working state arrive in one commit, so an effect - passive or layout - necessarily runs
     after the answer card has already rendered itself whole. Measured 21 September 2026 at frame rate:
     the lead painted its full 96 characters, then dropped to 3 and typed back up. Setting state while
     rendering is React's own answer to this: it re-renders before committing anything, so the card's
     FIRST render already knows, and the first frame a reader sees is the first word.

     `seen` makes it idempotent, which is what keeps a render-phase update honest: a key is acted on once,
     so a double-invoked render in development reaches the same state as a single one. */
  const [revealKey, setRevealKey] = useState<string | null>(null);
  const [seen, setSeen] = useState<Set<string>>(() => new Set());
  const watched = useRef(false);
  if (conversation.working) watched.current = true;
  const answered = conversation.turns.filter(entry => entry.role === 'answer');
  const newestAnswer = answered[answered.length - 1];
  if (newestAnswer && !seen.has(newestAnswer.key)) {
    setSeen(previous => new Set(previous).add(newestAnswer.key));
    if (watched.current && newestAnswer.role === 'answer' && !newestAnswer.restored) {
      setRevealKey(newestAnswer.key);
    }
    watched.current = false;
  }

  /* The thread follows the newest turn, the way a chat should — unless a reader arrived from a search, in
     which case it follows the turn they were looking for and holds it for a moment. Landing at the foot of a
     long conversation when the search said the match is in the middle is a worse answer than the search. */
  useEffect(() => {
    const node = thread.current;
    if (!node || !chatting) return;
    const behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
    if (spotlight) {
      const target = Array.from(node.querySelectorAll('.g-turn')).find(turn => turn.textContent?.includes(spotlight));
      if (target) {
        /* jsdom has no layout and therefore no scrollIntoView; the mark is what the check can see. */
        if (typeof target.scrollIntoView === 'function') target.scrollIntoView({ block: 'center', behavior });
        target.classList.add('g-found');
        const timer = window.setTimeout(() => target.classList.remove('g-found'), 2600);
        return () => window.clearTimeout(timer);
      }
    }
    /* The thread follows the newest QUESTION to the top of the frame, not the foot of the newest answer.
       It used to scroll to scrollHeight, which put the reader at the END of a reply they had not read a
       word of: a seven-paragraph marine briefing landed with its last sentence on screen and the reader
       had to scroll back up to find where it started. Anchoring the question at the top means the answer
       grows downward underneath it and is read in the order it was written, which is what every
       conversational product does and what this one was measured against.

       The question, not the answer: the question is short and fixed in height, so it is a stable anchor
       from the moment the turn begins until the answer has finished arriving, and the view does not jump
       when the reply replaces the working state. */
    /* `.g-you` and then its turn, rather than a `:has()` selector: jsdom does not implement `:has()` and
       throws on it, which would take the whole effect down inside every component spec. */
    const questions = node.querySelectorAll('.g-you');
    const anchor = questions[questions.length - 1]?.closest('.g-turn') as HTMLElement | null;
    if (anchor && typeof anchor.getBoundingClientRect === 'function') {
      const top = anchor.getBoundingClientRect().top - node.getBoundingClientRect().top + node.scrollTop;
      node.scrollTo({ top: Math.max(0, top - ANCHOR_INSET), behavior });
      return;
    }
    node.scrollTo({ top: node.scrollHeight, behavior });
  }, [conversation.turns.length, conversation.working?.key, chatting, spotlight]);

  /* A finished turn is a new stored conversation: the rail has to hear about it. */
  useEffect(() => {
    if (!conversation.conversationId) return;
    void client.invalidateQueries({ queryKey: ['conversations'] });
  }, [conversation.conversationId, conversation.turns.length, client]);

  const catalogue = useQuery({ queryKey: ['personas'], queryFn: () => readPersonas(), staleTime: 300_000 });
  const personaOptions = catalogue.data?.data?.personas || [];
  const sheet = view && view.id !== 'assistant' ? view : null;
  const home = homeOf(String(view?.id || 'assistant'));
  const sky = useSky();

  /* The condition the ground may take its colour from, and the one rule about where it may: the sky
     belongs to the conversation. A warnings or history surface carries the four published hazard colours,
     and no ambient tint from a station's weather belongs beside them. */
  const mood = home?.id === 'ask' ? sky.data?.glyph ?? null : null;

  /* The rail's collapse is a keyboard action as well as a control, and ⌥ rather than ⌘ for the reason the
     rail records: a browser owns ⌘B and will not give it up.

     The key is read from event.code, not event.key, and that is not a style preference: on macOS ⌥B produces
     "∫" in event.key, so a handler written against the letter works on every machine except the one this
     product was built on. The code is the physical key and is the same everywhere. */
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!event.altKey || event.metaKey || event.ctrlKey) return;
      if (event.code === 'KeyB') {
        event.preventDefault();
        setPrefs({ rail: prefs.rail === 'collapsed' ? 'open' : 'collapsed' });
      }
      if (event.code === 'KeyN') {
        event.preventDefault();
        conversation.clear();
        onNew?.();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [prefs.rail, setPrefs, conversation, onNew]);

  const toEnd = useCallback(() => {
    thread.current?.scrollTo({ top: thread.current.scrollHeight, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, []);

  /* A chip on the card. A place choice the engine offered is resolved inside the turn that offered it —
     the engine binds the choice to the question it was offered for, so the client sends that same
     question and the turn keeps one answer instead of growing a second turn. Anything else a chip sends
     (a quick reply, a follow-up sentence) is an ordinary new question. */
  const followUp = (turnKey: string, text: string) => {
    const turn = conversation.turns.find(entry => entry.key === turnKey);
    const packet = turn && turn.role === 'answer' ? turn.packet : null;
    const match = (packet?.choices || []).find(choice => {
      const record = choice as Record<string, unknown>;
      return String(record.value || record.label || record.place || '') === text;
    }) as Record<string, unknown> | undefined;
    const selectionId = match?.selection_id ? String(match.selection_id) : undefined;
    if (selectionId && packet) void conversation.resolveSelection(selectionId, turnKey, packet.question);
    else void conversation.send(text);
  };

  /* Collect fresh evidence. The answer card has always offered it, and the shell that replaced the old Ask
     surface dropped the wire: the control was drawn only when a handler was passed, and none was, so the
     feature existed in the component and nowhere in the product. It is re-connected here, with the same two
     conditions the old surface held it to — the answer must have resolved exactly one point, and a failure is
     the server's own sentence rather than a generic one. It returns that sentence, because "ask the sources
     again" needs to say what the workspace was asked and what it answered. */
  const collect = async (packet: AnswerPacket): Promise<{ text: string; tone: 'calm' | 'error' }> => {
    const point = Object.values(packet.resolved_points || {})[0];
    const latitude = point?.coordinates?.latitude ?? point?.latitude;
    const longitude = point?.coordinates?.longitude ?? point?.longitude;
    if (typeof latitude !== 'number' || typeof longitude !== 'number') {
      return { text: 'This answer did not resolve a single place point, so a collection cannot be requested for it.', tone: 'error' };
    }
    try {
      const result = await collectEvidence({ question: packet.question, coordinates: { latitude, longitude } });
      const refresh = result.refresh || {};
      return {
        text: (refresh.message || 'A collection was requested.') +
          (refresh.state === 'already_fresh' ? ' Nothing had to be collected: the stored evidence is still within its serving lifetime.' : ''),
        tone: 'calm',
      };
    } catch (error) {
      return { text: String((error as Error)?.message || error), tone: 'error' };
    }
  };

  /* Asking the same question again in place of the answer it had. For a refusal that is the whole of it;
     for an answer the sources are asked for fresh evidence first, because that is the point of the button
     — and the answer that comes back states, from its own retrieval instant and the collection's reply,
     whether anything was actually read again. */
  const reask = async (turnKey: string, question: string, packet: AnswerPacket | null) => {
    setChanging(null);
    if (!packet) {
      await conversation.reask(turnKey, question);
      return;
    }
    const outcome = await collect(packet);
    await conversation.reask(turnKey, question, { previous: packet, freshNote: outcome.text });
  };

  /* Just the place: the reader picks a catalogue row (or the place the panel already holds) and the same
     question is asked again there. The sentence is untouched, and the answer states the change from the
     engine's own record of it. */
  const changePlace = (turnKey: string, question: string, packet: AnswerPacket | null, place: { label: string; latitude: number; longitude: number; state?: string; district?: string }) => {
    setChanging(null);
    void conversation.reask(turnKey, question, {
      previous: packet || undefined,
      change: { field: 'place', to: place.label },
      place,
    });
  };

  const acceptPlaceRow = (turnKey: string, question: string, packet: AnswerPacket | null) => (row: PlaceMatch) => {
    const latitude = typeof row.latitude === 'number' ? row.latitude : Number.NaN;
    const longitude = typeof row.longitude === 'number' ? row.longitude : Number.NaN;
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      conversation.notify('That row states no coordinates, so the question cannot be re-read there.', 'error');
      return;
    }
    changePlace(turnKey, question, packet, {
      label: String(row.label || row.name || '').trim() || 'the place the reader chose',
      latitude, longitude,
      state: row.state ? String(row.state) : undefined,
      district: row.district ? String(row.district) : undefined,
    });
  };

  /* Just the window: the phrase is one of the engine's own, sent beside the unchanged question. The engine
     resolves it from its own day tables and says whether it applied it. */
  const changeWindow = (turnKey: string, question: string, packet: AnswerPacket | null, phrase: string) => {
    setChanging(null);
    void conversation.reask(turnKey, question, {
      previous: packet || undefined,
      change: { field: 'window', to: phrase },
      window: phrase,
    });
  };

  /* THE PLACE PICKER LIVES HERE NOW.
     Every "Change" and "Set a place" control in the shell called `onFindPlace`, an OPTIONAL prop that no
     caller has ever supplied - so `onFindPlace?.()` ran, did nothing, and three separate controls in the
     rail and the composer did nothing when pressed. Owning the picker in the shell that owns those
     controls means they work on their own; the optional prop is still called, for a host that wants to
     know, but nothing depends on it any more. */
  const [pickingPlace, setPickingPlace] = useState(false);
  const openPlacePicker = useCallback(() => {
    setPickingPlace(true);
    onFindPlace?.();
  }, [onFindPlace]);
  /* The languages the server says it can answer in. The reading panel already reads this endpoint; asking
     for it here costs nothing because React Query returns the same cached entry, and it means the
     composer's menu and the panel's list can never disagree about what is on offer. */
  const languageList = useQuery({
    queryKey: ['languages'],
    queryFn: () => getJson<Languages>('/api/languages'),
    staleTime: 300_000,
  });
  /* `writableLanguages` is the existing rule for this and it is the right one: only a language whose
     WRITING this project has actually measured may be offered as an answer language. The first version of
     this menu read a `answer` key off the payload that has never existed, so it always found nothing and
     offered "Auto" alone - which is exactly what a reader reported. */
  const answerLanguages = writableLanguages(languageList.data)
    .map(entry => ({ code: entry.code, label: entry.native_name || entry.english_name || entry.code }));
  const working = conversation.working;
  const progress = working?.progress;
  /* The stages the engine has been through, with the one it is on marked. A single stage is shown as a single
     stage rather than as a list of one. */
  const stages = progress?.stages_seen?.length ? progress.stages_seen : progress?.stage ? [progress.stage] : ['started'];
  const current = progress?.stage || null;
  const firstReading = working ? readingLine(working.preview) : null;
  const queue = progress?.queue;
  const queueLine = queue && (queue.waiting > 0 || queue.capacity)
    ? [
        queue.active ? 'One turn is running on this workspace.' : '',
        queue.waiting > 0 ? queue.waiting + ' question' + (queue.waiting === 1 ? '' : 's') + ' waiting' : 'No question is waiting',
        queue.capacity ? 'the queue holds ' + queue.capacity + ' waiting' : '',
        queue.wait_seconds_before_refusal ? 'a wait longer than ' + queue.wait_seconds_before_refusal + ' s is refused rather than queued' : '',
      ].filter(Boolean).join(' · ') + '.'
    : '';
  /* The server's own sentence about a turn that is not running yet — accepted and waiting, or not on this
     process at all. It is stated in the server's words rather than left to look like a turn that started,
     and it rides the fold that already holds the queue's facts. Nothing is added while the turn runs: the
     stage line above is then the whole of what the server has said. */
  const stateLine = progress && progress.state !== 'running' && progress.stage_note ? progress.stage_note : '';
  const waitFacts = [stateLine, queueLine].filter(Boolean).join(' ');

  const composer = (
    <div className="g-dock">
      {chatting && scrolled ? (
        <button type="button" className="g-to-end" onClick={toEnd} aria-label="Go to the newest turn">
          <ArrowDown size={16} aria-hidden="true" />
        </button>
      ) : null}
      <Composer
        draft={conversation.draft}
        onDraft={conversation.setDraft}
        onSend={text => void conversation.send(text)}
        onStop={() => void conversation.stop()}
        busy={Boolean(working)}
        language={language}
        place={workingPlace?.label}
        onContext={() => setPrefs({ panel: true })}
        onPlace={openPlacePicker}
        onLanguage={onLanguage}
        languages={answerLanguages}
        languageState={languageList.isPending ? 'loading' : languageList.isError ? 'error' : 'ready'}
        onRetryLanguages={() => void languageList.refetch()}
      />
      {chatting ? (
        <p className="g-hint" id="composer-hint">
          Every value keeps its source and the time it was read.
        </p>
      ) : (
        /* The same sentence, for a screen reader only. It is the composer's described-by target, and a
           described-by that points at nothing is an accessibility defect rather than a piece of design. */
        <p className="sr-only" id="composer-hint">Every value keeps its source and the time it was read.</p>
      )}
    </div>
  );

  const turns = useMemo(() => conversation.turns, [conversation.turns]);

  /* What this thread is called. A conversation has one name — the question it opened with — taken from the
     turns in front of us rather than re-read from the store, so the bar and the thread can never disagree. */
  const opening = turns.find(turn => turn.role === 'user') as { text: string } | undefined;
  const title = sheet ? sheet.label
    : chatting && opening ? opening.text
    : 'New conversation';

  /* The whole exchange as one file, for a reader who wants the conversation rather than one answer. Each
     answer keeps its own markdown — the values, the windows, the source ids and the status line — so the
     export carries the same evidence a printout of that turn would, in the order it was asked. */
  const exportConversation = useCallback(() => {
    const parts: string[] = ['# WeatherGPT — ' + title, '', '_Exported ' + istStamp(new Date().toISOString()) + ' from this machine._'];
    turns.forEach(turn => {
      if (turn.role === 'user') parts.push('## ' + turn.text);
      else if (turn.role === 'answer') parts.push(markdownTurn(turn.packet));
      else if (turn.role === 'restored') parts.push(
        '### Older answer · receipt unavailable', '', turn.text, '',
        '_Its sources, reading time and limits were not stored. Ask it again before relying on it._',
      );
      else if (turn.role === 'notice') parts.push('> ' + turn.text);
    });
    downloadFile(stampName('weathergpt-conversation', 'md'), parts.join('\n\n---\n\n'));
  }, [turns, title]);

  return (
    <div
      className="g"
      data-rail={railOpen ? 'open' : 'closed'}
      data-hour={hour}
      data-scrolled={scrolled ? 'true' : 'false'}
      data-design="meridian"
      data-atmosphere="paused"
      data-busy={Boolean(working && !working.stopRequested)}
    >
      <Field expanded={chatting} sky={mood} />
      {pickingPlace ? <PlacePicker onClose={() => setPickingPlace(false)} /> : null}
      <button type="button" className="g-scrim" aria-label="Close the conversation list" onClick={() => setRailOpen(false)} />
      {/* One rail for the whole product: the four homes, the place the answers are about, and the reader's
          own conversations. It replaces a 56px strip and a 264px list standing side by side. */}
      <Rail
        currentId={conversation.conversationId}
        onOpen={(id, match) => {
          setSpotlight(match || null);
          void conversation.restore(id);
          setRailOpen(false);
        }}
        onNew={() => { conversation.clear(); setSpotlight(null); onNew?.(); setRailOpen(false); }}
        onClose={() => setRailOpen(false)}
        home={home ?? null}
        currentView={String(view?.id || 'assistant')}
        onOpenView={id => { onOpen(id); setRailOpen(false); }}
        onAsk={question => { onAsk?.(question); setRailOpen(false); }}
        collapsed={prefs.rail === 'collapsed'}
        onToggle={() => setPrefs({ rail: prefs.rail === 'collapsed' ? 'open' : 'collapsed' })}
        pins={prefs.pins}
        onPin={(id, pinned) => setPrefs({ pins: pinned ? [id, ...prefs.pins.filter(entry => entry !== id)].slice(0, 20) : prefs.pins.filter(entry => entry !== id) })}
        onHoldPlace={onHoldPlace}
        aliases={prefs.aliases}
        onAlias={(label, name) => setPrefs({
          aliases: name
            ? { ...prefs.aliases, [label]: name }
            : Object.fromEntries(Object.entries(prefs.aliases).filter(([key]) => key !== label)),
        })}
        onFindPlace={openPlacePicker}
        onPlans={() => onPlans?.()}
        onOwner={() => onOwner?.()}
      />

      <main className="g-main" data-panel={prefs.panel ? 'open' : 'closed'}>
        <TopBar
          title={title}
          chatting={chatting}
          sky={sky.data}
          panelOpen={prefs.panel}
          onTogglePanel={() => setPrefs({ panel: !prefs.panel })}
          onToggleRail={() => setRailOpen(value => !value)}
          onExport={chatting && turns.some(turn => turn.role === 'answer' || turn.role === 'restored') ? exportConversation : null}
        />

        {/* The conversation stays on the matte ground; each answer owns its evidence margin. */}
        <div className="g-panel" data-chatting={chatting ? 'true' : 'false'}>
          <div className="g-thread" ref={thread} onScroll={event => setScrolled(event.currentTarget.scrollTop > 8)}>
            <div className="g-col">
            {unknownRoute ? (
              <p className="g-notice" role="status">There is no page called “{unknownRoute}”. This is the conversation — ask your question here.</p>
            ) : null}

            {sheet ? (
              <section className="g-turn g-in" data-surface={sheet.id}>
                <div className="g-sheet-actions">
                  <span className="g-chips">
                    <button type="button" className="g-chip" onClick={() => onOpen('assistant')}>
                      <ArrowLeft size={13} aria-hidden="true" /> Back to the conversation
                    </button>
                    <button type="button" className="g-chip" onClick={() => onAsk?.(sheet.intents[0] || 'What is it like right now?')}>
                      Ask about this
                    </button>
                  </span>
                </div>
                <SurfaceHost view={sheet} onAsk={question => onAsk?.(question)} />
              </section>
            ) : null}

            {!chatting ? (
              <div className="g-welcome" data-surface={sheet ? 'true' : 'false'}>
                {/* A module page carries its own title and its own first reading, so the greeting, the
                    verse and the starters are not drawn under it. The composer is, because the front
                    door is the front door on every page. */}
                {sheet ? composer : (
                  <Welcome hour={hour}>
                    {composer}
                    <div className="g-chips g-starters">
                      {STARTERS.map(starter => (
                        <button key={starter.label} type="button" className="g-chip" title={starter.question} onClick={() => void conversation.send(starter.question)}>
                          {starter.label}
                        </button>
                      ))}
                    </div>
                    <p className="g-welcome-foot">
                      <button type="button" className="g-quiet" onClick={() => onOpen('overview')}>Today across India</button>
                    </p>
                  </Welcome>
                )}
              </div>
            ) : (
              <>
                {turns.map((turn, index) => {
                  /* The affordances belong to the newest turn: a reader corrects, retries or re-reads the
                     question they just asked. An older turn's controls would rewrite a transcript that has
                     already moved on. Editing the question is offered while its turn is still running —
                     that is when a reader most often wants to correct it — and the request in flight is
                     abandoned at the same moment, so what answers next answers the corrected question. */
                  const newest = index === turns.length - 1;
                  const settled = newest && !working;
                  /* Editing belongs to the newest QUESTION, which is not the newest turn once its answer
                     has landed. */
                  const lastQuestion = [...turns].reverse().find(entry => entry.role === 'user')?.key;
                  if (turn.role === 'user') {
                    return (
                      <div key={turn.key} className="g-turn g-question-turn g-in">
                        <div className="g-you"><p>{turn.text}</p></div>
                        {turn.key === lastQuestion ? (
                          <div className="g-chips no-print" data-print="drop">
                            <button
                              type="button"
                              className="g-chip g-edit-question"
                              aria-label="Edit this question"
                              title={'Puts this question back in the box and removes its answer, so the corrected question is what is asked next: “' + turn.text + '”'}
                              onClick={() => conversation.edit(turn.key)}
                            >
                              <Pencil size={14} aria-hidden="true" /><span>Edit</span>
                            </button>
                          </div>
                        ) : null}
                      </div>
                    );
                  }
                  if (turn.role === 'notice') {
                    /* A failed read says two things: what the server said, and what state that leaves the reader
                       in. The second sentence is the difference between an expired session and a store that did
                       not answer — they call for different actions — and it was carried by the surface this
                       shell replaced but never rendered by the shell itself. */
                    const hint = noticeHint(turn.kind);
                    const question = questionFor(turns, turn.key) || '';
                    return (
                      <div key={turn.key} className="g-turn g-in" data-tone={turn.tone}>
                        {turn.changed ? <p className="g-claim-note">{changeNote(null, turn.changed)}</p> : null}
                        <p className="g-notice">{turn.text}</p>
                        {hint ? <p className="g-claim-note">{hint}</p> : null}
                        <p className="g-claim-note">Your question is back in the box so it stays editable.</p>
                        {settled && question ? (
                          <div className="g-chips no-print" data-print="drop">
                            <button
                              type="button"
                              className="g-chip"
                              title={'Asks this question again, unchanged: “' + question + '”'}
                              onClick={() => void reask(turn.key, question, null)}
                            >
                              Ask again
                            </button>
                          </div>
                        ) : null}
                      </div>
                    );
                  }
                  if (turn.role === 'restored') {
                    const question = questionFor(turns, turn.key) || '';
                    return (
                      <div key={turn.key} className="g-turn g-in">
                        <p className="g-eyebrow">Older answer · receipt unavailable</p>
                        <p className="g-prose">{turn.text}</p>
                        <p className="g-claim-note">This stored sentence predates answer receipts, so its sources, reading time and limits cannot be reconstructed. Ask it again before relying on it.</p>
                        {settled && question ? (
                          <div className="g-chips no-print" data-print="drop">
                            <button
                              type="button"
                              className="g-chip"
                              title={'Retrieves a new answer for this older stored question: “' + question + '”'}
                              onClick={() => void reask(turn.key, question, null)}
                            >
                              Read it again
                            </button>
                          </div>
                        ) : null}
                      </div>
                    );
                  }
                  const question = questionFor(turns, turn.key) || turn.packet.question;
                  const denied = isHeld(turn.packet.status);
                  const window = claimWindow(turn.packet);
                  return (
                    <div key={turn.key} className="g-turn g-in">
                      {turn.restored ? <p className="g-claim-note">Restored with its original answer receipt. Values below keep the sources and reading time recorded for that turn.</p> : null}
                      {/* What the reader changed beyond the sentence, from the engine's own record of it —
                          so a re-asked turn never looks like the same question answered about elsewhere. */}
                      {turn.changed ? <p className="g-claim-note">{changeNote(turn.packet, turn.changed)}</p> : null}
                      <AnswerTurn
                        packet={turn.packet}
                        reveal={turn.key === revealKey}
                        onFollowUp={text => followUp(turn.key, text)}
                        onRefresh={packet => void collect(packet).then(outcome => conversation.notify(outcome.text, outcome.tone))}
                      />
                      {turn.freshness ? <p className="g-claim-note">{turn.freshness}</p> : null}
                      {settled ? (
                        <div className="g-chips no-print" data-print="drop">
                          <button
                            type="button"
                            className="g-chip"
                            title={'Asks the sources again: requests a fresh collection for the point this answer read' +
                              (window ? ' (its window is ' + window + ')' : '') + ', then sends: “' + question + '”. The answer says whether anything was read again.'}
                            onClick={() => void reask(turn.key, question, turn.packet)}
                          >
                            {denied ? 'Ask again' : 'Ask the sources again'}
                          </button>
                          <button
                            type="button"
                            className="g-chip"
                            title={'Asks the same question again at a place you choose, without rewriting the sentence: “' + question + '”'}
                            aria-expanded={changing?.key === turn.key && changing.kind === 'place'}
                            onClick={() => setChanging(changing?.key === turn.key && changing.kind === 'place' ? null : { key: turn.key, kind: 'place' })}
                          >
                            Change the place
                          </button>
                          <button
                            type="button"
                            className="g-chip"
                            title={'Asks the same question again for a different window' + (window ? ', where this answer covers ' + window : '') + ': “' + question + '”'}
                            aria-expanded={changing?.key === turn.key && changing.kind === 'window'}
                            onClick={() => setChanging(changing?.key === turn.key && changing.kind === 'window' ? null : { key: turn.key, kind: 'window' })}
                          >
                            Change the window
                          </button>
                        </div>
                      ) : null}
                      {changing?.key === turn.key && changing.kind === 'place' ? (
                        <div className="g-chips no-print" data-print="drop">
                          {workingPlace ? (
                            <button
                              type="button"
                              className="g-chip"
                              title={'Asks the same question again at ' + (workingPlace.label || 'the place the panel holds') + ' (' + workingPlace.latitude + ', ' + workingPlace.longitude + '), the place the panel already holds: “' + question + '”'}
                              onClick={() => changePlace(turn.key, question, turn.packet, {
                                label: String(workingPlace.label || 'the place the panel holds'),
                                latitude: workingPlace.latitude, longitude: workingPlace.longitude,
                              })}
                            >
                              Use the place the panel holds: {workingPlace.label || 'unnamed'}
                            </button>
                          ) : null}
                          <PlaceChoice
                            onPick={acceptPlaceRow(turn.key, question, turn.packet)}
                            onClose={() => setChanging(null)}
                          />
                        </div>
                      ) : null}
                      {changing?.key === turn.key && changing.kind === 'window' ? (
                        <div className="g-chips no-print" data-print="drop">
                          {WINDOW_CHOICES.map(choice => (
                            <button
                              key={choice.phrase}
                              type="button"
                              className="g-chip"
                              title={'Sends the same question with the window set to ' + choice.label + ': “' + question + '”'}
                              onClick={() => changeWindow(turn.key, question, turn.packet, choice.phrase)}
                            >
                              {choice.label}
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
                {working ? (
                  <WorkingTurn
                    working={working}
                    current={current}
                    stages={stages}
                    firstReading={firstReading}
                    queueLine={waitFacts}
                  />
                ) : null}
              </>
            )}
          </div>
        </div>

          {chatting ? <div className="g-col">{composer}</div> : null}
        </div>
        {/* No legend: the ground states the hour by being that hour, and it draws no condition to disclaim.
            What leaves this machine is said once, under the composer, where a reader is about to send. */}
      </main>

      {prefs.panel ? (
        <ReadingPanel
          sources={sourcesRead(turns)}
          language={language}
          onLanguage={onLanguage}
          persona={persona}
          onPersona={onPersona}
          personas={personaOptions}
          onFindPlace={openPlacePicker}
          onOpenView={id => onOpen(id)}
          onClose={() => setPrefs({ panel: false })}
        />
      ) : null}
    </div>
  );
}
