/* The transcript: one column, newest at the bottom, with a jump control that appears only when there is
   something below the fold. The log announces additions; it does not re-read the whole conversation. */

import { useEffect, useRef, useState } from 'react';
import type { AnswerPacket } from '../api/types';
import { istStamp } from '../lib/time';
import { AnswerTurn } from './AnswerTurn';
import { noticeHint, type Turn } from './model';
import { WorkingTurn } from './WorkingTurn';
import type { Working } from './model';

export type TranscriptProps = {
  turns: Turn[];
  working: Working | null;
  onFollowUp: (text: string) => void;
  onStop: () => void;
  onRefresh: (packet: AnswerPacket) => void;
};

export function Transcript({ turns, working, onFollowUp, onStop, onRefresh }: TranscriptProps) {
  const box = useRef<HTMLDivElement | null>(null);
  const [showJump, setShowJump] = useState(false);

  /* Scrolling the log to its end: smooth where the browser offers it, a plain assignment where it does
     not, and never an error either way. */
  const toEnd = (smooth = true) => {
    const node = box.current;
    if (!node) return;
    if (typeof node.scrollTo === 'function') node.scrollTo({ top: node.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
    else node.scrollTop = node.scrollHeight;
  };

  useEffect(() => {
    toEnd(false);
  }, [turns.length, working ? working.key : '']);

  useEffect(() => {
    const node = box.current;
    if (!node) return;
    const sync = () => setShowJump(node.scrollHeight - node.scrollTop - node.clientHeight > 240);
    sync();
    node.addEventListener('scroll', sync, { passive: true });
    return () => node.removeEventListener('scroll', sync);
  }, [turns.length]);

  return (
    <div className="relative min-h-0 flex-1">
      {/* The log scrolls, so it is focusable: a keyboard reader can then scroll it with the arrow keys. */}
      <div
        ref={box}
        className="flex h-full flex-col overflow-y-auto"
        role="log"
        aria-relevant="additions"
        tabIndex={0}
        aria-label="Conversation transcript"
      >
        {turns.map(turn => {
          if (turn.role === 'user') {
            return (
              <div key={turn.key} className="b-turn" style={{ paddingBottom: 4, borderBottom: 0 }}>
                <p className="b-you">{turn.text}</p>
                {turn.at ? <p className="b-stamp">{istStamp(turn.at)}</p> : null}
              </div>
            );
          }
          if (turn.role === 'notice') {
            return (
              <div key={turn.key} className="b-notice" data-tone={turn.tone}>
                <p style={{ margin: 0 }}>{turn.text}</p>
                {noticeHint(turn.kind) ? <p className="b-claim-note" style={{ marginTop: 4 }}>{noticeHint(turn.kind)}</p> : null}
                <p className="b-claim-source" style={{ marginTop: 4 }}>Your question is back in the box so it stays editable.</p>
              </div>
            );
          }
          if (turn.role === 'restored') {
            return (
              <article key={turn.key} className="b-turn" data-restored="true">
                <p className="b-label">Restored from the local store</p>
                <p className="b-sentence">{turn.text}</p>
                <p className="b-claim-note">
                  The stored sentence, kept as it was written. It is a receipt from the moment it was retrieved, not a
                  standing fact, and it carries no fresh values: ask again before relying on it.
                </p>
              </article>
            );
          }
          return <AnswerTurn key={turn.key} packet={turn.packet} onFollowUp={onFollowUp} onRefresh={onRefresh} />;
        })}
        {working ? <WorkingTurn working={working} onStop={onStop} /> : null}
      </div>
      {showJump ? (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center pb-3">
          <button type="button" className="b-chip b-chip-accent pointer-events-auto" onClick={() => toEnd()}>
            Jump to the latest
          </button>
        </div>
      ) : null}
    </div>
  );
}
