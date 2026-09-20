/* The wait.
   ============================================================================
   Quiet while it works.

   This printed five paragraphs while a reader waited to learn whether it would rain: an explanation of the
   pipeline, the stage list, the planner's provisional first reading, the queue depth, and the server-work
   figure. All of it true; none of it the question. Evidence proves an answer, and it cannot prove a wait —
   imposing it during one is how a careful product comes to read as an unfinished one.

   So the wait states the two things a reader wants, the stage and how long, and the rest moves one fold
   away where it stays reachable and stops competing. The first reading in particular is a transparency
   feature and is not removed: available, not imposed, and the chat spec pins that so the fold cannot
   quietly become a deletion. */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ThinkingOrb } from 'thinking-orbs';
import { elapsedWords } from '../lib/time';
import { stageLabel } from '../chat/model';
import type { Working } from '../chat/model';
import { currentGroundTheme, orbStateFor } from './orb';

export type WorkingTurnProps = {
  working: Working;
  /** The stage the engine is in now, and every stage it has been through. */
  current: string | null;
  stages: string[];
  /** The planner's provisional reading of the question. Not evidence, and it says so. */
  firstReading: string | null;
  queueLine: string;
};

export function WorkingTurn({ working, current, stages, firstReading, queueLine }: WorkingTurnProps) {
  const { t } = useTranslation();
  const progress = working.progress;

  /* The clock under a working turn: it answers "is this still going?", which is the only question a reader
     has while it runs. It ticks once a second and stops when the turn does. */
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [working.key]);

  return (
    <div className="g-turn g-working" data-testid="working-turn">
      <p className="g-working-head">
        {/* The orb and the stage word are one statement, drawn and said. The canvas is aria-hidden because the
            stage word beside it is a live region: a reader using a screen reader hears the stage once, not twice.
            It freezes when the reader has asked to stop, because a stopped turn is not a turn at work. */}
        <span className="g-orb" aria-hidden="true">
          <ThinkingOrb
            state={orbStateFor(current)}
            size={20}
            theme={currentGroundTheme()}
            paused={working.stopRequested}
          />
        </span>
        <span className="g-working-stage" role="status" aria-live="polite">
          {current ? stageLabel(current) : t('working.default')}
        </span>
        {/* Outside the live region: a clock that ticks once a second would be announced once a second,
            which is unusable with a screen reader. The DELTA, not the clock — this once read the Unix
            epoch in seconds, so a four-second-old turn reported "497172 h 14 min since you asked". */}
        <span className="g-working-clock" aria-hidden="true">
          {elapsedWords(Math.max(0, now - working.startedAt) / 1000)} {t('working.sinceYouAsked')}
        </span>
      </p>

      {/* A reader asked for this one, so it answers where it was asked. */}
      {working.stopRequested ? (
        <p className="g-working-note">{working.stopDetail || t('working.stopRequested')}</p>
      ) : null}

      <details className="g-fold g-working-more">
        <summary>{t('working.whatItsDoing')}</summary>
        <div className="g-fold-body">
          <p className="g-working-note">
            Resolving the place and window, then retrieving evidence. A local model is interpreting your
            question, so this can take up to about a minute.
          </p>
          <ol className="g-stages">
            {stages.map(entry => (
              <li key={entry} data-state={entry === current ? 'now' : 'done'}>
                {stageLabel(entry)}{entry === current ? ' — now' : ''}
              </li>
            ))}
          </ol>
          {firstReading ? (
            <p className="g-reading-line" data-testid="reading-line">
              <span>First reading: </span>{firstReading}
            </p>
          ) : null}
          {working.preview?.note ? <p className="g-working-note">{working.preview.note}</p> : null}
          {working.previewFailed ? <p className="g-working-note">{working.previewFailed}</p> : null}
          {queueLine ? <p className="g-working-note">{queueLine}</p> : null}
          {progress?.turn_seconds ? (
            <p className="g-working-note">{elapsedWords(progress.turn_seconds)} of server work recorded</p>
          ) : null}
        </div>
      </details>
    </div>
  );
}
