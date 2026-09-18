/* The opening: the country's published picture, as the machine's first turn.
   A sentence in the human face with every value in the machine face, counting up to the number the read
   returned; one source line; nothing else. No count without a read; an absent today block is not a quiet day. */

import { AnimatedNumber, Reveal } from '../flagship/motion';
import { describeNational, useOverview } from './overview';

function V({ value }: { value: number }) {
  return <AnimatedNumber value={String(value)} className="f-num" />;
}

export function NationalReading() {
  const overview = useOverview();
  const picture = describeNational(overview);

  if (overview.isPending) {
    return (
      <div data-testid="reading" className="f-hero">
        <p className="f-kicker">Reading the district warning bulletin on this machine…</p>
        <div className="f-shimmer" style={{ height: '2.4rem', width: '70%' }} aria-hidden="true" />
        <div className="f-shimmer" style={{ height: '1.2rem', width: '50%' }} aria-hidden="true" />
      </div>
    );
  }
  if (overview.isError) {
    return (
      <div data-testid="reading" className="f-hero">
        <h1 className="f-lead">The district warning bulletin could not be read from this machine.</h1>
        <p className="f-sub">No count is printed, because no read produced one. {String((overview.error as Error)?.message || '').slice(0, 160)}</p>
      </div>
    );
  }
  if (!picture.statedToday) {
    return (
      <div data-testid="reading" className="f-hero">
        <h1 className="f-lead">This read does not state today.</h1>
        <p className="f-sub">The overview came back without a today block, so no count is printed. An absent block is not a quiet day.</p>
      </div>
    );
  }
  return (
    <div data-testid="reading" className="f-hero">
      <p className="f-kicker">India · today · as this machine read it</p>
      {picture.severe > 0 ? (
        <h1 className="f-lead">
          <V value={picture.severe} /> districts are under an orange or red warning today.
        </h1>
      ) : (
        <Reveal as="h1" className="f-lead" text="No district is under an orange or red warning today." />
      )}
      <p className="f-sub">
        <V value={picture.yellow} /> carry a yellow caution, and <V value={picture.green} /> have nothing flagged.
      </p>
      {picture.sourceLine ? (
        <p className="f-source">
          {picture.sourceLine}
          {picture.behind !== null && picture.behind > 0 ? <> · {picture.behind} districts still publish an older edition</> : null}
        </p>
      ) : null}
    </div>
  );
}
