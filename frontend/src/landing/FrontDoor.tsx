import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson } from '../api/client';
import type { Envelope } from '../api/types';
import './frontdoor.css';

/* The front door.
   ============================================================================
   The page this replaces led with the product's name, a paragraph of method, and a panel titled "the
   shape of an answer" — a table of words where values would go, captioned to say it printed no
   measurement. A weather product's first screen showed no weather.

   This one opens on the country's weather as this machine read it, and then offers the question box.
   Two rules it keeps from the page it replaces, because they were the good part:
   1. Every number here comes from a live read, with the read time beside it. A failed read says so; a
      placeholder number is never rendered.
   2. Nothing is claimed that the read does not state.

   What it adds is a third: the reading comes first, and the method is available rather than compulsory.

   The hero is a sentence, not a stat tile, and it interleaves the two voices deliberately — prose in the
   human face, every value in the machine face — so the architecture the product actually has (a model
   writes the sentence, a governed tool owns the value) is visible in the first thing a reader sees. */

type TodayBlock = {
  counts?: Record<string, number>;
  districts_with_no_day_covering_today?: number;
};

type OverviewData = {
  national?: {
    districts?: number;
    today?: TodayBlock;
    bulletin_date?: string | null;
    newest_bulletin_date_in_this_read?: string | null;
    districts_behind_the_newest_edition?: number | null;
  };
};

/* The four IMD colours in severity order. Severity is the product's own, not this page's invention:
   red and orange are the two that mean act, which is why they are the ones the hero leads with. */
const SEVERE = ['red', 'orange'] as const;

function editionLabel(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const parts = String(iso).split('-');
  if (parts.length !== 3) return String(iso);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = months[Number(parts[1]) - 1];
  if (!month) return String(iso);
  return Number(parts[2]) + ' ' + month;
}

function readClock(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return null;
  return when.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' }) + ' IST';
}

/** A number in the machine voice, inline in a human sentence. */
function Value({ children }: { children: React.ReactNode }) {
  return <span className="machine value">{children}</span>;
}

export type FrontDoorProps = {
  onAsk: (question: string) => void;
  onEnter: () => void;
};

export function FrontDoor({ onAsk, onEnter }: FrontDoorProps) {
  const [question, setQuestion] = useState('');

  const overview = useQuery({
    queryKey: ['front-door', 'overview'],
    queryFn: () => getJson<Envelope<OverviewData>>('/api/overview'),
    staleTime: 60_000,
  });

  const national = overview.data?.data?.national;
  const counts = national?.today?.counts || {};
  /* An absent today block is not a quiet day. A server that has not been restarted since this field was
     added returns an overview without it, and printing 0 there would state that no district carries a
     caution — a number no read produced. So the block's presence is tested, never its truthiness, and a
     read that does not state today says so. */
  const statedToday = Boolean(national?.today && Object.keys(counts).length > 0);
  const severe = SEVERE.reduce((total, colour) => total + (counts[colour] || 0), 0);
  const yellow = counts.yellow || 0;
  const green = counts.green || 0;
  const districts = national?.districts ?? null;
  const edition = editionLabel(national?.newest_bulletin_date_in_this_read || national?.bulletin_date);
  const readAt = readClock(overview.data?.generated_at_utc);
  const behind = national?.districts_behind_the_newest_edition ?? 0;

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const asked = question.trim();
    if (!asked) return;
    onAsk(asked);
  };

  return (
    <div className="v3 front-door">
      <header className="fd-mark">
        <span className="fd-mark-name">WeatherGPT</span>
        <span className="label">India · this machine</span>
      </header>

      <main className="fd-main">
        {/* The hero: what the country's published warnings say about today. */}
        <section className="fd-reading" aria-live="polite">
          {overview.isPending ? (
            <h1 className="human fd-lede fd-lede-waiting">Reading the national district bulletin…</h1>
          ) : overview.isError || overview.data?.status === 'unavailable' ? (
            <h1 className="human fd-lede">
              The national bulletin did not answer this read, so this page states nothing about today rather
              than guessing. Ask a question below and the answer will name what it could and could not read.
            </h1>
          ) : !statedToday ? (
            <h1 className="human fd-lede">
              This read did not state the day covering today, so the national picture is not shown. Ask a
              question below and the answer will name the edition it read.
            </h1>
          ) : severe > 0 ? (
            <>
              <h1 className="human fd-lede">
                <Value>{severe}</Value> {severe === 1 ? 'district is' : 'districts are'} under an orange or
                red warning today.
              </h1>
              <p className="human fd-detail">
                <Value>{yellow}</Value> more carry a yellow caution, and <Value>{green}</Value> have nothing
                flagged.
              </p>
            </>
          ) : (
            <>
              <h1 className="human fd-lede">No district is under an orange or red warning today.</h1>
              <p className="human fd-detail">
                <Value>{yellow}</Value> carry a yellow caution, and <Value>{green}</Value> have nothing
                flagged.
              </p>
            </>
          )}

          {!overview.isPending && !overview.isError && statedToday && edition ? (
            <p className="machine fd-provenance">
              IMD district warning bulletin, {edition} edition
              {districts !== null ? ', ' + districts + ' districts' : ''}
              {readAt ? ' · read ' + readAt : ''}
            </p>
          ) : null}

          {statedToday && behind > 0 ? (
            <p className="fd-caveat">
              <Value>{behind}</Value> of those districts are still publishing an older edition than the newest
              this read returned, so their day above is what that older edition printed.
            </p>
          ) : null}
        </section>

        {/* The one way in. */}
        <form className="fd-ask" onSubmit={submit}>
          <label className="fd-ask-label human" htmlFor="front-question">
            Ask about a place and a time.
          </label>
          <div className="fd-ask-row">
            <input
              id="front-question"
              className="fd-input"
              value={question}
              onChange={event => setQuestion(event.target.value)}
              placeholder="Will it rain in Surat tomorrow morning?"
              autoComplete="off"
              enterKeyHint="go"
            />
            <button type="submit" className="fd-go" disabled={!question.trim()}>
              Ask
            </button>
          </div>
          <p className="fd-ask-note">
            Ask in English, हिंदी, ગુજરાતી or தமிழ். When an answer cannot be written in the language you
            asked for, it says so instead of quietly answering in another one.
          </p>
        </form>

        <p className="fd-enter">
          <button type="button" className="fd-link" onClick={onEnter}>
            Open the workspace
          </button>
          <span className="fd-enter-note">
            the guided surfaces: warnings, forecasts, published documents, farm advisories and the rest
          </span>
        </p>
      </main>

      <footer className="fd-foot">
        Answers are built from published sources and keep their source, window and retrieval time. Nothing here
        is an official warning service: this machine reads what IMD and the model products publish, and it will
        not invent a warning, an observation, a water level or a forecast.
      </footer>
    </div>
  );
}
