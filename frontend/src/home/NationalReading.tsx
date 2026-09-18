/* The opening line of the conversation: the country's published picture, as the machine's first turn.
   A sentence in the human face with every value in the machine face, one source line, nothing else.
   No count without a read; an absent today block is not a quiet day. */

import type { ReactNode } from 'react';
import { describeNational, useOverview } from './overview';

function V({ children }: { children: ReactNode }) {
  return <span className="b-machine">{children}</span>;
}

export function NationalReading() {
  const overview = useOverview();
  const picture = describeNational(overview);

  if (overview.isPending) {
    return (
      <p className="b-sentence" data-testid="reading">
        Reading the district warning bulletin on this machine…
      </p>
    );
  }
  if (overview.isError) {
    return (
      <div data-testid="reading">
        <h1 className="b-sentence b-sentence-lead">The district warning bulletin could not be read from this machine.</h1>
        <p className="b-claim-note" style={{ marginTop: 10 }}>
          No count is printed, because no read produced one. {String((overview.error as Error)?.message || '').slice(0, 160)}
        </p>
      </div>
    );
  }
  if (!picture.statedToday) {
    return (
      <div data-testid="reading">
        <h1 className="b-sentence b-sentence-lead">This read does not state today.</h1>
        <p className="b-claim-note" style={{ marginTop: 10 }}>
          The overview came back without a today block, so no count is printed. An absent block is not a quiet day.
        </p>
      </div>
    );
  }
  return (
    <div data-testid="reading">
      <h1 className="b-sentence b-sentence-lead">
        {picture.severe > 0 ? (
          <>
            <V>{picture.severe}</V> districts are under an orange or red warning today.
          </>
        ) : (
          <>No district is under an orange or red warning today.</>
        )}
      </h1>
      <p className="b-sentence" style={{ marginTop: 10 }}>
        <V>{picture.yellow}</V> carry a yellow caution, and <V>{picture.green}</V> have nothing flagged.
      </p>
      {picture.sourceLine ? (
        <p className="b-claim-source" style={{ marginTop: 10 }}>
          {picture.sourceLine}
          {picture.behind !== null && picture.behind > 0 ? (
            <>
              {' · '}
              {picture.behind} districts still publish an older edition
            </>
          ) : null}
        </p>
      ) : null}
    </div>
  );
}
