/* The rail: the whole of this product's navigation, in one column.
   ============================================================================
   It replaces two stacked columns — a 56px strip of four homes beside a 264px list of conversations — which
   together took 320px of a 1440px window to say what one column says better. The shape is Codex's sidebar: a
   brand row with its controls, the four homes as a block, the two actions, the places this machine knows, then
   the stored conversations with the reader's own pinned ones above the recency groups.

   Three things about it are deliberately not Codex's:

   1. The shortcuts are ⌥ rather than ⌘. A browser owns ⌘1–⌘9 for its tabs and ⌘N, ⌘T and ⌘W for its own
      windows; a page cannot take them, and printing a shortcut that does not fire is worse than printing
      none. ⌥ is ours, it survives every browser this product is opened in, and the rail shows it beside the
      row it belongs to. ⌥/ opens the list of them.

   2. Deleting is still a real deletion of local evidence: it appears on hover, it names the conversation and
      it asks first, and a delete that did not happen is said rather than swallowed. Pinning is the opposite —
      a pin is an arrangement, it is remembered in this browser, and it never touches the store.

   3. **Places are the second entity.** A conversation row carries the place its own answers resolved, the
      places this machine has seen are listed with their counts, and one of them can be made the place the
      browser holds. The list is derived from the engine's own resolutions and from the reader's own pins —
      never from the words of a question, which is why a conversation that resolved no point carries no place
      at all rather than the city name it happened to mention. */

import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Bell, CornerDownLeft, History, KeyRound, Keyboard, LayoutGrid, MapPin, MessageSquare,
  MessageSquarePlus, PanelLeft, Pencil, Pin, PinOff, Search, Settings, Trash2, TriangleAlert, X, ArrowUpRight,
} from 'lucide-react';
import { placeHref } from '../place/place';
import { useTranslation } from 'react-i18next';
import { forgetConversation, ledger } from '../chat/api';
import type { ConversationRow } from '../api/types';
import { HOMES, viewsOf, type Home, type HomeId } from '../shell/homes';
import { pinPlace, rememberPlace, unpinPlace, usePinnedPlaces, useWorkingPlace, type PlaceChoice } from '../modules/Evidence';
import { useSky } from './sky';
import { stationSource } from './Welcome';
import { SkyGlyphIcon } from '../shell/icons';
import { ShortcutDialog } from './Shortcuts';
import { Mark } from './Mark';
import { shortPlace } from '../lib/locale';

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

/* The grouping keys are English because they are data — the grouping is computed from a timestamp and has
   to be stable whatever the interface is set to. These map them to the catalogue for rendering. */
const GROUP_KEY: Record<string, string> = {
  Pinned: 'rail.pinned',
  Today: 'rail.today',
  Yesterday: 'rail.yesterday',
  'Previous 7 days': 'rail.previous7',
  Older: 'rail.older',
};
/* ⌥1 to ⌥9: nine rows carry a number, and the tenth row is reached by scrolling like everything else. */
const SHORTCUTS = 9;
const PLACES_SHOWN = 5;

export type RailProps = {
  currentId: string | null;
  /** Open a conversation. \`match\` is the turn text a search sent the reader to, when there was one. */
  onOpen: (id: string, match?: string) => void;
  onNew: () => void;
  onOpenView: (viewId: string) => void;
  onAsk: (question: string) => void;
  currentView: string;
  home: Home | null;
  collapsed: boolean;
  onToggle: () => void;
  pins: string[];
  onPin: (id: string, pinned: boolean) => void;
  /** The reader's own names for places, keyed by the label the catalogue returned. Display only. */
  aliases: Record<string, string>;
  onAlias: (label: string, name: string) => void;
  onFindPlace: () => void;
  /** Put the place in the address, so the place the answers are about is a link somebody can open. */
  onHoldPlace?: (place: { label: string | null; latitude: number; longitude: number }) => void;
  onPlans: () => void;
  onOwner: () => void;
  onClose?: () => void;
};

/* One row per name the reader sees: the labels the catalogue returned underneath it, the coordinates of the
   first of them, and how many conversations resolved any of them. */
type Known = {
  name: string;
  labels: string[];
  label: string;
  latitude: number;
  longitude: number;
  pinned: boolean;
  count: number;
};

export function Rail({
  currentId, onOpen, onNew, onOpenView, onAsk, currentView, home,
  collapsed, onToggle, pins, onPin, aliases, onAlias, onFindPlace, onPlans, onOwner, onClose, onHoldPlace,
}: RailProps) {
  /* What a reader calls a place. The catalogue's label travels with it in the title, so the reader's own word
     is never mistaken for a name a source published. */
  const nameOf = (label: string) => aliases[label] || label;
  const labelsOf = (known: Known) => known.labels.join(' · ');
  const { t } = useTranslation();
  const [filter, setFilter] = useState('');
  const [term, setTerm] = useState('');
  const [searching, setSearching] = useState(false);
  const [failed, setFailed] = useState('');
  const [placeFilter, setPlaceFilter] = useState<string | null>(null);
  const [keysOpen, setKeysOpen] = useState(false);
  const client = useQueryClient();
  const rows = useQuery({ queryKey: ['conversations', term], queryFn: () => ledger(term), staleTime: 15_000 });
  const place = useWorkingPlace();
  const pinnedPlaces = usePinnedPlaces();
  const sky = useSky();
  const now = Date.now();

  /* A search waits for the typing to stop, because every keystroke would otherwise be a read of the store. */
  useEffect(() => {
    const timer = window.setTimeout(() => setTerm(filter.trim().length >= 2 ? filter.trim() : ''), 260);
    return () => window.clearTimeout(timer);
  }, [filter]);

  const found: ConversationRow[] = rows.data?.conversations || [];

  /* The places this machine knows, in one list: what the reader pinned, and what the conversations
     themselves resolved. A pin with no conversation still appears, and a resolved place with no pin still
     appears — they are two different facts about a place and neither implies the other.

     Rows are grouped by **display name**, so a reader who calls \`Nadiād, Kheda, State of Gujarāt\` and
     \`Nadiad\` the same thing gets one row with both labels under it. The name is the reader's; the labels
     are the catalogue's, and the row keeps every one of them so nothing is answered about a place it did not
     come from. */
  const places = useMemo(() => {
    const known = new Map<string, Known>();
    const upsert = (label: string, latitude: number, longitude: number, pinned: boolean) => {
      const name = aliases[label] || label;
      const existing = known.get(name);
      known.set(name, {
        name,
        labels: existing?.labels.includes(label) ? existing.labels : [...(existing?.labels || []), label],
        label: existing?.label || label,
        latitude: existing?.latitude || latitude,
        longitude: existing?.longitude || longitude,
        pinned: pinned || Boolean(existing?.pinned),
        count: existing?.count ?? 0,
      });
    };
    pinnedPlaces.forEach(pin => { if (pin.label) upsert(pin.label, pin.latitude, pin.longitude, true); });
    found.forEach(row => {
      const label = row.place?.label;
      if (!label) return;
      /* A conversation that resolved a place carries that place's coordinates; one that resolved nothing carries
         no place at all (docs/114). A label with no coordinates is therefore not a place this rail may offer to
         hold, to send, or to open: the old default of 0,0 is a real address in the Gulf of Guinea, so a row that
         said "Kochi" while holding 0,0 would substitute one place for another in silence - first in the address
         bar, and then in a page about the Gulf of Guinea. */
      const latitude = row.place?.latitude;
      const longitude = row.place?.longitude;
      if (typeof latitude !== 'number' || typeof longitude !== 'number') return;
      upsert(label, latitude, longitude, false);
      const name = aliases[label] || label;
      const entry = known.get(name);
      if (entry) entry.count += 1;
    });
    return Array.from(known.values())
      .sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.count - a.count || a.name.localeCompare(b.name))
      .slice(0, PLACES_SHOWN);
  }, [pinnedPlaces, found, aliases]);

  /* A filter is by display name too, so choosing a merged row shows the conversations of every label in it. */
  const shown = placeFilter
    ? found.filter(row => row.place?.label && (aliases[row.place.label] || row.place.label) === placeFilter)
    : found;

  const grouped = useMemo(() => {
    const out = new Map<string, ConversationRow[]>();
    const pinned = new Map<string, ConversationRow[]>();
    shown.forEach(row => {
      const bucket = pins.includes(row.id) ? pinned : out;
      const key = pins.includes(row.id) ? 'Pinned' : groupOf(row.updated, now);
      bucket.set(key, [...(bucket.get(key) || []), row]);
    });
    return [
      ...(pinned.get('Pinned') ? [['Pinned', pinned.get('Pinned') as ConversationRow[]] as [string, ConversationRow[]]] : []),
      ...ORDER.filter(key => out.has(key)).map(key => [key, out.get(key) as ConversationRow[]] as [string, ConversationRow[]]),
    ];
  }, [shown, pins, now]);

  const visible = grouped.flatMap(([, items]) => items).map(row => row.id);

  const forget = async (row: ConversationRow) => {
    const name = row.opening_question || row.id;
    if (!window.confirm('Delete “' + name + '” from this machine? The stored turns go with it.')) return;
    setFailed('');
    try {
      await forgetConversation(row.id);
      void client.invalidateQueries({ queryKey: ['conversations'] });
    } catch (error) {
      /* A delete that did not happen is said, in the server's own words. The list is left as it is rather than
         optimistically emptied: a row that disappears while the store still holds it is a worse lie than a row
         that stays with a sentence under it. */
      setFailed('The stored conversation was not deleted: ' + String((error as Error)?.message || error));
    }
  };

  /* The place that is held is a real label the catalogue returned, never the reader's name for it: the name
     is a display preference, and what answers are read with has to be the place itself. The address is
     rewritten with it, so the place the answers are about can be bookmarked and sent. */
  const hold = (known: Known) => {
    rememberPlace({ label: known.label, latitude: known.latitude, longitude: known.longitude } as PlaceChoice);
    onHoldPlace?.({ label: known.label, latitude: known.latitude, longitude: known.longitude });
  };

  /* ⌥1–⌥9 opens the n-th row the rail is showing, in the order it is showing them. Read from event.code for
     the reason the collapse is: ⌥1 on macOS is "¡". */
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!event.altKey || event.metaKey || event.ctrlKey) return;
      if (event.code === 'Slash') {
        event.preventDefault();
        setKeysOpen(value => !value);
        return;
      }
      if (event.code === 'KeyF') {
        event.preventDefault();
        setSearching(true);
        window.setTimeout(() => document.getElementById('rail-filter')?.focus(), 0);
        return;
      }
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
  const reading = sky.data;

  return (
    <aside className="g-rail" aria-label="Workspace" data-collapsed={collapsed ? 'true' : 'false'}>
      <div className="g-rail-head">
        <span className="g-brand">
          <Mark size={30} className="g-brand-mark" />
          <span className="g-brand-name">WeatherGPT</span>
        </span>
        <span className="g-rail-controls">
          <button
            type="button"
            className="g-act"
            aria-label={t('rail.search')}
            aria-pressed={searching}
            title={t('rail.search')}
            onClick={() => setSearching(value => !value)}
          >
            <Search size={15} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="g-act"
            aria-label={collapsed ? t('rail.expand') : t('rail.collapse')}
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
            placeholder={t('rail.searchPlaceholder')}
            autoComplete="off"
            autoFocus
          />
          {term ? (
            <p className="g-rail-note g-rail-note-search">
              {found.length
                ? found.length + (found.length === 1 ? ' conversation mentions ' : ' conversations mention ') + '“' + term + '”'
                : 'No stored turn mentions “' + term + '”'}
            </p>
          ) : null}
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
              title={t('home.' + entry.id, { defaultValue: entry.label }) + ' — ' + entry.blurb}
              onClick={() => onOpenView(entry.views[0])}
            >
              <Glyph size={16} aria-hidden="true" />
              {/* The registry is data and stays English; the interface renders its own name for it. */}
              <span className="g-home-label">{t('home.' + entry.id, { defaultValue: entry.label })}</span>
            </button>
          );
        })}
      </nav>

      <div className="g-rail-body">
        {/* The two actions, directly under the homes: a reader scanning the rail for "start something" or
            "what am I watching" should not have to look inside a section called Conversations for either. */}
        <div className="g-rail-actions-lead">
          <button type="button" className="g-new" onClick={onNew} title="New conversation (⌥N)">
            <MessageSquarePlus size={15} aria-hidden="true" />
            <span className="g-new-label">{t('rail.newConversation')}</span>
            <kbd className="g-kbd">⌥N</kbd>
          </button>
          <button type="button" className="g-row g-row-plain g-rail-action" onClick={onPlans} title="Plans, watches and the notification inbox">
            <Bell size={15} aria-hidden="true" />
            <span className="g-new-label">{t('rail.watch')}</span>
          </button>
        </div>

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
            reads it, the panel reads it — so the rail states it, with what the nearest station last printed
            there, rather than leaving a reader to infer it from the answers.

            The reading and the line that owns it are one region — the place row and its source line — and
            the region is `display:contents`, so the row is laid out by the rail exactly as it was and only
            the provenance is new. It was in a title attribute before, which is not a line a reader who does
            not hover ever sees. */}
        <section className="g-section" aria-label="Place">
          <p className="g-rail-label">{t('rail.thisPlace')}</p>
          <div className="g-claim" style={{ display: 'contents' }}>
            <div className="g-place" aria-current={place ? 'true' : undefined}>
              <MapPin size={14} aria-hidden="true" />
              {/* Shortened for display only: the catalogue's own label is kept in the title, and every value sent
                  to the engine or printed on a receipt still uses it in full. */}
              <span className="g-place-name" title={place?.label || undefined}>{place?.label ? shortPlace(place.label) : t('rail.noPlace')}</span>
              {reading && (reading.temperature || reading.glyph) ? (
                <span className="g-place-reading">
                  {reading.glyph ? <SkyGlyphIcon glyph={reading.glyph} size={13} strokeWidth={1.6} aria-hidden="true" /> : null}
                  {reading.temperature ? reading.temperature + (reading.unit || '') : null}
                </span>
              ) : null}
            </div>
            {/* The station's source line, kept, because the rail PRINTS A VALUE - "29°C" sits in the row
                above - and a value this product shows without its source is the one thing it may never
                do. Deleting this was the wrong correction and the provenance audit caught it: the
                number would have been left in a claim region with nothing owning it.

                What was actually wrong was its WEIGHT, not its presence. In a 268px column a 96-
                character monospace string wrapped to three lines and became the largest object in the
                rail - louder than the place it describes and louder than anything a reader came here
                to do. It is one quiet clipped line now, in the interface face, with the whole of it on
                hover. Same fact, same rigour, a tenth of the noise. */}
            {reading && (reading.temperature || reading.condition) ? (
              <p className="g-claim-source g-place-source" title={stationSource(reading)}>
                {stationSource(reading)}
              </p>
            ) : null}
          </div>
          <div className="g-rail-actions">
            <button type="button" className="g-quiet" onClick={onFindPlace}>{place ? t('rail.changePlace') : t('rail.setPlace')}</button>
            {place?.label ? (
              <button type="button" className="g-quiet" onClick={() => onAsk('What is it like in ' + place.label + ' right now?')}>
                Ask about it
              </button>
            ) : null}
            {place?.label ? (
              <button
                type="button"
                className="g-act g-place-pin"
                aria-pressed={pinnedPlaces.some(pin => pin.label === place.label)}
                aria-label={pinnedPlaces.some(pin => pin.label === place.label) ? 'Unpin this place' : 'Pin this place'}
                title={pinnedPlaces.some(pin => pin.label === place.label) ? 'Unpin this place' : 'Pin this place'}
                onClick={() => {
                  const held = { label: place.label, latitude: place.latitude, longitude: place.longitude };
                  if (pinnedPlaces.some(pin => pin.label === place.label)) unpinPlace(held);
                  else pinPlace(held);
                }}
              >
                {pinnedPlaces.some(pin => pin.label === place.label) ? <PinOff size={13} aria-hidden="true" /> : <Pin size={13} aria-hidden="true" />}
              </button>
            ) : null}
          </div>
        </section>

        {places.length ? (
          <section className="g-section g-section-joined" aria-label="Places this machine knows">
            {places.map(known => (
              <div
                key={known.label}
                className="g-row g-place-row"
                aria-current={placeFilter === known.label ? 'true' : undefined}
              >
                <button
                  type="button"
                  className="g-row-text g-row-plain"
                  title={known.name + ' — ' + labelsOf(known) + '. ' +
                    (known.pinned ? 'Pinned. ' : '') +
                    (known.count ? known.count + ' conversation' + (known.count === 1 ? '' : 's') + ' resolved this place' : 'Pinned in this browser')}
                  onClick={() => { hold(known); setPlaceFilter(current => (current === known.name ? null : known.name)); }}
                >
                  {known.name}
                  {known.pinned ? <Pin size={11} aria-hidden="true" className="g-place-pinned" /> : null}
                </button>
                {known.count ? <span className="g-place-count">{known.count}</span> : null}
                {/* The glance and the destination: the panel is a link to the place's own page (docs/115) and the
                    page itself is docs/122. A real anchor rather than a button that rewrites the address, because
                    "a link somebody can send" has to be copyable and openable in a new tab. */}
                <a
                  className="g-place-open"
                  href={placeHref({ label: known.label, latitude: known.latitude, longitude: known.longitude })}
                  aria-label={'Open the page for ' + known.name}
                  title={'Open the page for ' + known.name}
                >
                  <ArrowUpRight size={11} aria-hidden="true" />
                </a>
                <button
                  type="button"
                  className="g-row-drop"
                  aria-label={'Name ' + known.label + ' for yourself'}
                  title="Call this place something else, for this browser only"
                  onClick={() => {
                    const answer = window.prompt(
                      'A name for this place in this browser. The label the catalogue returned stays on the row and is what answers are read with. Two labels given the same name become one row.',
                      known.name,
                    );
                    if (answer !== null) onAlias(known.label, answer.trim());
                  }}
                >
                  <Pencil size={13} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className="g-row-drop"
                  aria-label={'Ask about ' + known.label}
                  title={'Ask about ' + known.label}
                  onClick={() => onAsk('What is it like in ' + known.label + ' right now?')}
                >
                  <CornerDownLeft size={13} aria-hidden="true" />
                </button>
              </div>
            ))}
          </section>
        ) : null}

        <section className="g-section" aria-label="Conversations">
          <p className="g-rail-label">
            {t('rail.conversations')}
            {placeFilter ? (
              <button type="button" className="g-quiet g-place-clear" onClick={() => setPlaceFilter(null)}>
                {placeFilter} ×
              </button>
            ) : null}
          </p>
          {failed ? <p className="g-notice" role="status">{failed}</p> : null}
          {rows.isPending ? <p className="g-empty-note">Reading the stored conversations…</p> : null}
          {rows.isError ? <p className="g-empty-note">The conversation store did not answer. Nothing is listed rather than an empty list being shown as none.</p> : null}
          {!rows.isPending && !rows.isError && !grouped.length ? (
            <p className="g-empty-note">
              {term
                ? 'No stored turn mentions that.'
                : placeFilter
                  ? 'No stored conversation resolved ' + placeFilter + '.'
                  : 'No conversation is stored on this machine yet. Ask a question and it is kept here.'}
            </p>
          ) : null}

          {grouped.map(([label, items]) => (
            <div key={label}>
              {/* The grouping key stays English in the data and is named here in the reader's language.
                  "Pinned" is a group too, so it is keyed the same way rather than being special-cased. */}
              <p className="g-group">{t(GROUP_KEY[label] || 'rail.older', { defaultValue: label })}</p>
              {items.map(row => {
                const index = visible.indexOf(row.id);
                const pinned = pins.includes(row.id);
                return (
                  <div key={row.id} className="g-row g-row-conversation" aria-current={row.id === currentId ? 'true' : undefined}>
                    <button
                      type="button"
                      className="g-row-text g-row-plain"
                      onClick={() => onOpen(row.id, row.match?.text)}
                      title={row.opening_question || 'Untitled conversation'}
                    >
                      {/* The place leads, and the question follows quieter.

                          Eight conversations about warnings all open with "Is any warning in force…", so a
                          list titled by the question is eight identical rows — unscannable, and the reason
                          the history read as noise. The fact that tells them apart is the place each one
                          resolved, and the row already carried it as a small line underneath. Inverted.

                          A conversation that resolved no place keeps the question as its title, because
                          there is nothing truer to lead with. */}
                      {row.place?.label ? (
                        <>
                          <span className="g-row-name">{nameOf(row.place.label)}</span>
                          <span className="g-row-sub">{row.opening_question || 'Untitled conversation'}</span>
                        </>
                      ) : (
                        <span className="g-row-name">{row.opening_question || 'Untitled conversation'}</span>
                      )}
                      {row.match ? (
                        <span className="g-row-match" data-role={row.match.role}>
                          {row.match_question ? 'in the question: ' : row.match.role === 'user' ? 'in a question: ' : 'in the answer: '}
                          {row.match.text}
                        </span>
                      ) : null}
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
          <span className="g-new-label">{t('rail.settings')}</span>
        </button>
        <button type="button" className="g-act" onClick={() => setKeysOpen(true)} aria-label="Keyboard shortcuts" title="Keyboard shortcuts (⌥/)">
          <Keyboard size={15} aria-hidden="true" />
        </button>
        <button type="button" className="g-act" onClick={onOwner} aria-label="Owner gate" title="Owner gate">
          <KeyRound size={15} aria-hidden="true" />
        </button>
      </div>
      <p className="g-rail-note">{t('rail.privacy')}</p>
      {keysOpen ? <ShortcutDialog onClose={() => setKeysOpen(false)} /> : null}
    </aside>
  );
}
