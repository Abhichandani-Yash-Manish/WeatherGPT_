/* An answer arriving at reading pace.
   ============================================================================
   The engine composes an answer, checks it against the evidence it was given, and only then sends it, so
   the text is final before any of this runs. What is paced is the REVEAL. These checks hold the three
   things that could turn a presentation choice into a lie or a nuisance:

     - it never shows a word the engine did not send, and never withholds one at the end;
     - a restored conversation is shown, not performed;
     - a reader who asked for reduced motion gets the answer whole, at once.

   Measured 21 September 2026 against the running engine, at frame rate: before the decision moved into
   the render pass, the lead painted its full 96 characters and then dropped to 3 and typed back up. The
   both-sides pair for that is `starts from nothing` and `is shown whole when it is not being performed`.
*/
import { render, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { AnswerPacket } from '../api/types';
import { AnswerTurn } from './AnswerTurn';
import { MAX_MS, MIN_MS, revealDuration, revealedLength } from './reveal';
import ahmedabadJson from '../../../research/reviews/final-overhaul-20260921/chat/ahmedabad-forecast.packet.json';

const AHMEDABAD = ahmedabadJson as unknown as AnswerPacket;
const WHOLE = String(AHMEDABAD.answer);

function mount(reveal: boolean) {
  return render(<AnswerTurn packet={AHMEDABAD} onFollowUp={() => {}} register="conversational" reveal={reveal} />);
}

function leadOf(container: HTMLElement): string {
  return container.querySelector('.answer-lead')?.textContent || '';
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('how much of the answer has arrived', () => {
  it('stops on a word boundary rather than inside a word', () => {
    /* A cursor that lands inside "thunderstorm" prints "thunders", which is a different word for as long
       as the next frame takes to arrive. */
    const text = 'A thunderstorm warning is in force';
    for (let elapsed = 0; elapsed <= 100; elapsed += 7) {
      const shown = text.slice(0, revealedLength(text, elapsed, 100));
      expect(shown === '' || text.startsWith(shown), 'the prefix is always the real text').toBe(true);
      const tail = shown.split(' ').pop() || '';
      expect(text.split(' ').includes(tail) || tail === '', 'cut inside a word: "' + tail + '"').toBe(true);
    }
  });

  it('ends on the whole text, never one character short', () => {
    expect(revealedLength(WHOLE, 10_000, 500)).toBe(WHOLE.length);
    expect(revealedLength(WHOLE, 500, 500)).toBe(WHOLE.length);
  });

  it('paces a long answer faster rather than making the reader wait for it', () => {
    /* A one-line reply must not finish so fast that the effect is a flicker, and a long marine briefing
       must not take twenty seconds to become readable. */
    expect(revealDuration(40)).toBe(MIN_MS);
    expect(revealDuration(100_000)).toBe(MAX_MS);
    expect(revealDuration(1800)).toBeGreaterThan(MIN_MS);
    expect(revealDuration(1800)).toBeLessThan(MAX_MS);
    expect(revealDuration(0)).toBe(0);
  });
});

describe('the answer on the page', () => {
  it('is shown whole when it is not being performed', () => {
    /* Every restored, reloaded and older turn takes this path: a conversation opened from the rail shows
       what it said rather than acting it out again. */
    const { container } = mount(false);
    expect(leadOf(container).length).toBeGreaterThan(20);
    expect(WHOLE.startsWith(leadOf(container))).toBe(true);
  });

  it('starts from nothing and finishes on the whole answer', async () => {
    const { container } = mount(true);
    /* The FIRST render, before any frame has run. This is the assertion that the decision is made while
       rendering rather than in an effect: an effect would let the finished answer paint once first. */
    expect(leadOf(container), 'the finished answer flashed before the reveal started').toBe('');
    await waitFor(() => expect(leadOf(container).length).toBeGreaterThan(20));
    await waitFor(() => expect(container.querySelector('.g-answer')?.hasAttribute('data-revealing')).toBe(false));
    /* And nothing the engine sent is left off the end. */
    expect(WHOLE.startsWith(leadOf(container))).toBe(true);
    /* The value is on the finished card, in the sentence that answers - the reveal delivered the answer,
       not a truncation of it. (The same figure is also on the tool-owned claim below; this names the one
       it means.) */
    expect(leadOf(container)).toContain('0.0 mm');
  });

  it('gives a reader who asked for reduced motion the answer at once', () => {
    /* Text arriving in pieces is motion, and it is exactly the kind a vestibular reader asks to be
       spared. The request is honoured even though this turn is the one being performed. */
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query.includes('prefers-reduced-motion'),
      media: query, onchange: null, addListener: () => {}, removeListener: () => {},
      addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
    }));
    const { container } = mount(true);
    expect(leadOf(container).length).toBeGreaterThan(20);
    expect(container.querySelector('.g-answer')?.hasAttribute('data-revealing')).toBe(false);
  });
});
