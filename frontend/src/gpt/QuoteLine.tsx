/* A line for the hour, on the welcome screen.
   ============================================================================
   One short line of verse, under whatever the sky has said. It is the quietest thing on the screen and the
   only thing on it that a reader can change: the line turns by itself with the hour, and a reader who wants
   another one presses the turn on the caption.

   The attribution is set in the mono face because it is a source line, like every other source line in this
   product — an author, a work and a year, with the edition the wording was checked against in the title. The
   verse itself is in the display face at reading size, because it is the one piece of prose on this screen
   that is not a claim about the weather. */

import { useEffect, useState } from 'react';
import { RotateCw } from 'lucide-react';
import type { Hour } from './fieldPaint';
import { lineFor, nextLine, type Quote } from './quotes';

export function QuoteLine({ at, hour }: { at: Date; hour: Hour }) {
  const [quote, setQuote] = useState<Quote>(() => lineFor(at, hour));

  /* The hour moves, and the pool of lines with it. The minute does not: a line that changed while a reader
     was reading it would be a fault, not a feature. */
  useEffect(() => { setQuote(lineFor(new Date(), hour)); }, [hour]);

  return (
    <figure className="w-quote" data-testid="quote" title={'Wording checked against: ' + quote.basis}>
      <blockquote key={quote.id}>
        <p>{quote.text}</p>
      </blockquote>
      <figcaption>
        <span className="w-quote-author">{quote.author}</span>
        <span className="w-quote-work">{quote.work}, {quote.year}</span>
        <button
          type="button"
          className="w-quote-next"
          aria-label="Another line"
          title="Another line"
          onClick={() => setQuote(current => nextLine(current, at, hour))}
        >
          <RotateCw size={12} aria-hidden="true" />
        </button>
      </figcaption>
    </figure>
  );
}
