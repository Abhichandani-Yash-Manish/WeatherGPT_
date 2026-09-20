/* The place, on its own page.
   ============================================================================
   docs/115 ended with the hole: the place was in the address, and the reading panel was the place's own page
   in miniature, but there was no destination — "the panel is a glance and the panel is now also a link, but
   there is no destination". This is it: `#/place?place=…&plat=…&plon=…`, the same three names the panel
   writes, so the link a reader already has differs by one word.

   It is the place stated by sources and nothing else. Every block is a read this product already makes for
   the point the address names — the nearest station's own report, what is published for its district, the
   hours the model returned — and every block keeps its own source line. A district with no published day says
   so in words; a read that returned no hour says so in words. Nothing is drawn as a zero, a dash or an empty
   list, because a missing state rendered as a value is the one lie this page could tell.

   Two things it deliberately does not do. It does not become a second dashboard: the blocks are the panel's
   own blocks, rendered for this page rather than copied, and the depth stays where it was. And it does not
   read the place out of anybody's question: the label and the coordinates come from the address, and the
   reads come from the payloads, so a place is never inferred from the words of a question.

   The address is held as this browser's place when it arrives, which is what the product already does with a
   place named in an address (`#/assistant?place=…`, docs/115 §3), and the rule is the same one: a name and a
   coordinate pair that parse as numbers and fall inside the world, or nothing at all is applied. */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { ledger } from '../chat/api';
import { failureSentence, rememberPlace, PinPlaceButton } from '../modules/Evidence';
import { Field } from '../gpt/Field';
import { hourOf } from '../gpt/fieldPaint';
import { DistrictBlock, HoursBlock, StationBlock } from '../gpt/ReadingPanel';
import { istStamp } from '../lib/time';
import { conversationHref, placeHref, readPlaceAddress, storedConversationHref, type PlaceAddress } from './place';

export type PlaceParams = { label: string | null; latitude: string | null; longitude: string | null };

/* The page's own frame: the ground, the hour's palette on the document element, and one main landmark with a
   reading column in it. The place page is a shell route rather than a surface, so it brings the frame the
   conversation would otherwise have given it — and, being one, it carries no skip link: there is no rail here
   to skip past. */
function PageFrame({ hour, children }: { hour: string; children: React.ReactNode }) {
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.hour = hour;
    return () => {
      delete root.dataset.hour;
    };
  }, [hour]);

  return (
    <div className="g" data-hour={hour} data-design="gpt">
      <Field expanded={false} />
      <main id="main" tabIndex={-1} className="g-main">
        <div className="g-thread">
          <div className="g-col">{children}</div>
        </div>
      </main>
    </div>
  );
}

/* The page the shell renders at `#/place`. The three strings are the address's own, never a parsed place:
   the refusal happens here, against the raw address, so a half-written link is answered in words. */
export function PlacePage({ params }: { params: PlaceParams }) {
  const addressed = useMemo(() => {
    const search = new URLSearchParams();
    if (params.label !== null) search.set('place', params.label);
    if (params.latitude !== null) search.set('plat', params.latitude);
    if (params.longitude !== null) search.set('plon', params.longitude);
    return search;
  }, [params.label, params.latitude, params.longitude]);
  const found = useMemo(() => readPlaceAddress(addressed), [addressed]);
  const place = found.place;

  /* Astronomy, not weather: the hour decides the ground's palette and nothing on the page states it as a
     condition. With no usable point the sun is read over the centre of the country, the way the shell does it
     with no place held. */
  const [now] = useState(() => new Date());
  const hour = hourOf(now, place?.latitude ?? 23.0, place?.longitude ?? 82.5);

  /* Arriving here is choosing this place, exactly as arriving at `#/assistant?place=…` is: it is held once
     per address, and only when the address named one. A refused address holds nothing. */
  const heldKey = useRef<string | null>(null);
  useEffect(() => {
    if (!place) return;
    const key = placeHref(place);
    if (heldKey.current === key) return;
    heldKey.current = key;
    rememberPlace(place);
  }, [place]);

  /* The tab names the place, so a bookmark of this page is identifiable in a browser's own list. */
  useEffect(() => {
    document.title = place ? 'WeatherGPT — ' + place.label : 'WeatherGPT — no place to show';
  }, [place]);

  /* The surfaces the blocks offer stay reachable from here rather than being dead ends on a destination. */
  const openSurface = useCallback((viewId: string) => {
    window.location.hash = '#/' + viewId;
  }, []);

  if (!place) {
    return (
      <PageFrame hour={hour}>
        <section className="g-side-block" aria-label="The address was refused">
          <p className="g-side-label">Refused</p>
          <h1 className="g-hero">No place to show</h1>
          <p className="g-hero-sub">{found.refused}</p>
          <p className="g-side-note">
            A place is a name and a pair of coordinates that parse as numbers and fall inside the world. A
            half-written address is refused rather than half-applied, and no read is made for it: nothing on this
            page is filled in from a guess.
          </p>
          <div className="g-chips">
            <a className="g-chip" href="#/assistant">
              <ArrowLeft size={13} aria-hidden="true" /> Back to the conversation
            </a>
          </div>
        </section>
      </PageFrame>
    );
  }

  return (
    <PageFrame hour={hour}>
      <section className="g-side-block" aria-label="The place this page is about">
        <p className="g-side-label">Place</p>
        <h1 className="g-hero">{place.label}</h1>
        {/* The entity, the point and where each came from. The label and the coordinates are the address's
            own — this is the one place on the page that is not a source's statement, and it says so rather
            than passing the link's words off as a resolved place. */}
        <p className="g-hero-sub">
          Latitude {place.latitude}, longitude {place.longitude} — the coordinates this address names, in
          degrees. Every block below is a read for that point; the place was not resolved from the wording of a
          question.
        </p>
        <div className="g-chips">
          <a className="g-chip" href={conversationHref(place)}>Ask about this place</a>
          <a className="g-chip" href="#/assistant">
            <ArrowLeft size={13} aria-hidden="true" /> Back to the conversation
          </a>
        </div>
        <p className="g-side-note">
          The address names the place, so this page can be bookmarked, reloaded and sent, and a reader arriving
          from somebody else’s link holds the place that link names.
        </p>
      </section>

      <StationBlock />
      <DistrictBlock place={place} onOpen={openSurface} />
      <HoursBlock place={place} onOpen={openSurface} />

      <ConversationsAboutPlace place={place} />

      <section className="g-side-block" aria-label="This place in this browser">
        <p className="g-side-label">In this browser</p>
        <PinPlaceButton place={place} />
        <p className="g-side-note">
          A pin is this browser's own shortcut to a place name. It is kept in local storage, sent nowhere, and
          states nothing about the place — the reads above are what a source said.
        </p>
      </section>
    </PageFrame>
  );
}

/* The conversations this machine holds about this place.
   ============================================================================
   The place is the second entity (docs/114): a conversation carries the point its OWN answers resolved, read
   from the engine's stored resolved_points and never from the wording of its question. This lists the stored
   conversations whose recorded place is this one — the store's own fact, matched by the label the engine
   recorded. A store that answers with nothing is said in words, and a store that did not answer is the
   server's own failure sentence, the same one every other surface prints. */
function ConversationsAboutPlace({ place }: { place: PlaceAddress }) {
  const read = useQuery({ queryKey: ['place-conversations', place.label], queryFn: () => ledger(), retry: false });
  const rows = (read.data?.conversations || []).filter(row => row.place?.label === place.label);

  return (
    <section className="g-side-block" aria-label={'Stored conversations about ' + place.label}>
      <p className="g-side-label">This machine’s conversations about this place</p>
      {read.isPending ? <p className="g-side-note">Reading this machine’s stored conversations…</p> : null}
      {read.isError ? <p className="g-side-note">{failureSentence(read.error)}</p> : null}
      {!read.isPending && !read.isError && !rows.length ? (
        <p className="g-side-note">
          The store was read and holds no conversation whose own answers resolved “{place.label}”. A conversation
          that resolved no point carries no place, and none is read out of its question.
        </p>
      ) : null}
      {rows.length ? (
        <>
          <ul className="g-side-sources">
            {rows.map(row => (
              <li key={row.id}>
                <a className="g-row-text g-row-plain" href={storedConversationHref(row.id)}>
                  {row.opening_question || 'Untitled conversation'}
                </a>
                <span className="g-side-source-meta">
                  <span className="g-place-count">{typeof row.turns === 'number' ? row.turns + (row.turns === 1 ? ' turn' : ' turns') : 'turn count not recorded'}</span>
                  {row.updated ? <time dateTime={row.updated}> · stored {istStamp(row.updated)}</time> : ' · stored time not recorded'}
                </span>
              </li>
            ))}
          </ul>
          <p className="g-side-note">The place is the one each conversation’s own answers resolved, as this machine recorded it.</p>
        </>
      ) : null}
    </section>
  );
}
