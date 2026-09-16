/* The working turn: what the server is doing now, the engine's provisional first reading, the elapsed
   clock and the stop control. Nothing here is a percentage, an ETA or a claim that an answer is near. */

import { useEffect, useState } from 'react';
import { elapsedWords } from '../lib/time';
import { readingLine, stageLabel, type Working } from './model';

export function WorkingTurn({ working, onStop }: { working: Working; onStop: () => void }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const progress = working.progress;
  const seen = progress?.stages_seen?.length ? progress.stages_seen : [];
  const current = progress?.stage || null;
  const stages = seen.length ? seen : current ? [current] : ['started'];
  const line = readingLine(working.preview);
  const queue = progress?.queue;
  const elapsed = (now - working.startedAt) / 1000;

  return (
    <div className="card flex gap-3 px-4 py-3" data-testid="working-turn">
      <span className="working-dot" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">Working on it</p>
        <p className="mt-1 text-xs text-ink-soft">
          Resolving the place and window, then retrieving evidence. A local model is interpreting your question,
          so this can take up to about a minute.
        </p>

        <div className="stage-list mt-2" role="status" aria-live="polite">
          {stages.map(stage => {
            const state = stage === current ? 'now' : 'done';
            return (
              <span key={stage} className="stage-step" data-state={state} data-stage={stage}>
                <span className="stage-mark" aria-hidden="true" />
                {stageLabel(stage)}
                {state === 'now' ? <span className="quiet"> \u2014 now</span> : null}
              </span>
            );
          })}
        </div>
        {progress?.stage_note ? <p className="mt-1 text-[11px] quiet">{progress.stage_note}</p> : null}

        {line ? (
          <p className="reading-line mt-2" data-testid="reading-line">
            <span className="font-semibold">First reading: </span>
            {line}
          </p>
        ) : null}
        {working.preview?.note ? <p className="mt-1 text-[11px] quiet">{working.preview.note}</p> : null}
        {working.previewFailed ? <p className="mt-1 text-[11px] quiet">{working.previewFailed}</p> : null}

        {queue && (queue.waiting > 0 || queue.capacity) ? (
          <p className="mt-1 text-[11px] quiet">
            {queue.active ? 'One turn is running on this workspace. ' : ''}
            {queue.waiting > 0 ? queue.waiting + ' question' + (queue.waiting === 1 ? '' : 's') + ' waiting' : 'No question is waiting'}
            {queue.capacity ? ' \u00b7 the queue holds ' + queue.capacity + ' waiting' : ''}
            {queue.wait_seconds_before_refusal ? ' \u00b7 a wait longer than ' + queue.wait_seconds_before_refusal + ' s is refused rather than queued' : ''}.
          </p>
        ) : null}

        <div className="mt-2 flex flex-wrap items-center gap-3">
          <p className="working-clock" aria-hidden="true">
            {elapsedWords(elapsed)} since you asked \u00b7 {elapsedWords(progress?.turn_seconds ?? null)} of server work recorded
          </p>
          {working.stopRequested ? (
            <p className="text-[11px] text-ink-soft">{working.stopDetail || 'Stop requested.'}</p>
          ) : (
            <button type="button" className="btn" onClick={onStop} data-testid="stop-turn">
              Stop this turn
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
