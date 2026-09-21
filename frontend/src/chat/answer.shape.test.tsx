/* The answer as a page.
   ============================================================================
   docs/136. Held against the packets the running engine actually returned on 21 September 2026, recorded in
   research/reviews/final-overhaul-20260921/chat/ by tmp/probe-answers.py — the real Ahmedabad forecast, its
   follow-up, and the Surat station turn. Where a check needs a packet the engine did not return in that run,
   the spec says so and writes the smallest one that exercises the rule.

   What these checks hold, in one sentence each: the finding is printed as the answer and everything else
   unfolds beneath it; the engine's own held clause is printed once and not twice; a publisher's words are
   never folded; a turn with no evidence prints whole; a value says which kind of thing it is; an ambiguous
   place is a control beside the claim rather than three lines of the answer; the packet says who wrote the
   sentence; and the register a reader chooses changes the evidence, never a value. */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { AnswerPacket } from '../api/types';
import { AnswerTurn } from './AnswerTurn';
import { alternativeAsk, answerShape, authorshipNote, splitSentences } from './answer';
import { REGISTER_KEY } from './model';
import ahmedabadJson from '../../../research/reviews/final-overhaul-20260921/chat/ahmedabad-forecast.packet.json';
import followUpJson from '../../../research/reviews/final-overhaul-20260921/chat/ahmedabad-followup.packet.json';
import suratJson from '../../../research/reviews/final-overhaul-20260921/chat/surat-observation.packet.json';

const AHMEDABAD = ahmedabadJson as unknown as AnswerPacket;
const FOLLOW_UP = followUpJson as unknown as AnswerPacket;
const SURAT = suratJson as unknown as AnswerPacket;

const FINDING = 'No rain is forecast for Ahmedabad tomorrow: rainfall of 0.0 mm is expected over the whole day, 22 Sep 2026 00:30 to 23 Sep 2026 00:30 IST.';
const HELD = 'These are model forecasts for the selected points, not observed conditions or district averages.';

function mount(packet: AnswerPacket, onFollowUp: (text: string) => void = () => {}, register?: 'brief' | 'conversational' | 'full') {
  return render(<AnswerTurn packet={packet} onFollowUp={onFollowUp} register={register} />);
}

afterEach(() => {
  window.localStorage.clear();
});

describe('the answer as a page', () => {
  it('prints the finding as the answer and unfolds the rest of the reply underneath it', () => {
    const { container } = mount(AHMEDABAD);
    const lead = container.querySelector('.answer-lead');
    expect(lead?.textContent).toBe(FINDING);
    /* The three sentences that are not the finding are on the card, behind the fold, in the reply's own
       words. Before this the finding was the first of five lines inside one block of prose. */
    const fold = container.querySelector('.answer-rest')!;
    expect(fold.tagName).toBe('DETAILS');
    expect(fold.hasAttribute('open'), 'the fold is depth, so it starts closed').toBe(false);
    const summary = fold.querySelector('summary')!.textContent || '';
    expect(summary).toContain('The rest of the answer');
    expect(summary).toContain('(3 sentences)');
    const rest = Array.from(fold.querySelectorAll('.g-prose')).map(node => node.textContent || '');
    expect(rest).toHaveLength(3);
    expect(rest[0]).toContain('That figure is a model forecast for the selected place point');
    expect(rest[2]).toBe('Source: GFS forecast; conditions can change.');
    /* And nothing is lost: every sentence of the reply is on the card, the held clause included. */
    const shown = [lead?.textContent, ...Array.from(container.querySelectorAll('.g-prose')).map(node => node.textContent)]
      .filter(Boolean).join(' ');
    answerShape(AHMEDABAD.answer, AHMEDABAD.held_clauses as string[]).rest.forEach(sentence => {
      expect(shown, 'the sentence "' + sentence.slice(0, 40) + '…" is not on the card').toContain(sentence);
    });
  });

  it('prints the engine\'s held clause once, instead of the twice the reply carried it', () => {
    const { container } = mount(AHMEDABAD);
    const text = container.textContent || '';
    const occurrences = text.split(HELD).length - 1;
    expect(occurrences, 'the caveat is said twice again').toBe(1);
    /* It is printed outside the fold, above the depth: a clause the engine holds is not something a reader
       should have to open a drawer to read. */
    const caveat = container.querySelector('.answer-caveat');
    expect(caveat?.textContent).toBe(HELD);
    expect(caveat?.closest('.answer-rest')).toBeNull();
    expect(container.querySelector('.answer-rest')?.textContent).not.toContain(HELD);
  });

  it('keeps a publisher\'s own words out of the fold, because a quotation behind a click is not read', () => {
    const packet = { ...AHMEDABAD, answer: 'The cotton advisory for Rajkot is below.\n\n“Spray acephate 75 % SP on the crop.”', held_clauses: null } as AnswerPacket;
    const { container } = mount(packet);
    const quote = container.querySelector('.answer-quote');
    expect(quote?.textContent).toBe('“Spray acephate 75 % SP on the crop.”');
    expect(quote?.closest('.answer-rest')).toBeNull();
  });

  it('prints a turn with nothing for the answer to stand on whole, with no fold', () => {
    /* The Surat turn has a claim, so it folds; a turn with no claim does not. Both shapes are here so the
       rule is the presence of evidence and not the length of the text. */
    const { container } = mount(SURAT);
    expect(container.querySelector('.answer-rest')).not.toBeNull();

    const refusal = { ...AHMEDABAD, status: 'unavailable', facts: [], held_clauses: null, answer: 'The live district bulletin could not be verified for this district-day. The publisher issued nothing for the window, which is not the same as a quiet day.' } as AnswerPacket;
    const { container: held } = mount(refusal);
    expect(held.querySelector('.answer-rest')).toBeNull();
    expect(held.textContent).toContain('The publisher issued nothing for the window, which is not the same as a quiet day.');
    expect(held.querySelector('.answer-lead')?.textContent).toBe('The live district bulletin could not be verified for this district-day.');
  });

  it('ends a sentence where a sentence starts, and not inside a number, a title or an abbreviation', () => {
    expect(splitSentences('Rainfall of 0.0 mm. Wind 12 kt.')).toEqual(['Rainfall of 0.0 mm.', 'Wind 12 kt.']);
    expect(splitSentences('See e.g. the GFS run. It is unverified.')).toEqual(['See e.g. the GFS run.', 'It is unverified.']);
    expect(splitSentences('Dr. Rao wrote it. The value stands.')).toEqual(['Dr. Rao wrote it.', 'The value stands.']);
    expect(splitSentences('The window is 22 Sep 2026 00:30 to 23 Sep 2026 00:30 IST. That figure is a model forecast.'))
      .toEqual(['The window is 22 Sep 2026 00:30 to 23 Sep 2026 00:30 IST.', 'That figure is a model forecast.']);
    expect(splitSentences('कल बारिश होगी। एक चुनें, या लिखें।')).toEqual(['कल बारिश होगी।', 'एक चुनें, या लिखें।']);
    /* A sentence does not begin in lower case, so a decimal and a Latin abbreviation cannot split one. */
    expect(splitSentences('The value is 1.02 m across the cell. it is unverified.')).toHaveLength(1);
  });

  it('says which kind of thing the leading value is, from the citation that owns it', () => {
    /* The live packet carries no evidence_kind on the fact and states `model_forecast` on the citation, so
       measured before this the claim read only "Ahmedabad, Ahmadābād, State of Gujarāt" - a model forecast
       with nothing on the first screen saying it was not an observation. */
    const fact = (AHMEDABAD.facts || [])[0];
    expect(fact.evidence_kind, 'the recorded packet no longer misses this field, so the check is stale').toBeUndefined();
    const claim = screen.queryByTestId('lead-claim');
    mount(AHMEDABAD);
    expect(screen.getByTestId('lead-claim').querySelector('.g-claim-note')?.textContent).toContain('Model forecast');
    expect(claim).toBeNull();
  });

  it('names the place the answer was read at, and the other places that share the name', () => {
    const { container } = mount(AHMEDABAD);
    const place = container.querySelector('.place-read')!;
    expect(place.textContent).toContain('Read at Ahmedabad, Ahmadābād, State of Gujarāt.');
    expect(place.textContent).toContain('Another place shares this name: Ahmedābād, District Rampur, Uttar Pradesh.');
    /* The reply spent 189 of its 667 characters saying this. It is a control beside the claim now. */
    const chip = within(place as HTMLElement).getByRole('button', { name: 'Read it at Ahmedābād, District Rampur, Uttar Pradesh' });
    expect(chip.getAttribute('title')).toContain('“Will it rain in Ahmedābād, District Rampur, Uttar Pradesh tomorrow?”');
  });

  it('offers that control only when the reader\'s own sentence names the place, and sends that sentence', async () => {
    const asked = vi.fn();
    const { container } = mount(AHMEDABAD, asked);
    await userEvent.click(within(container as HTMLElement).getByRole('button', { name: /Read it at Ahmedābād/ }));
    expect(asked).toHaveBeenCalledTimes(1);
    expect(asked.mock.calls[0][0]).toBe('Will it rain in Ahmedābād, District Rampur, Uttar Pradesh tomorrow?');

    /* "and tomorrow?" names no place, so a substitution would change the question rather than the place:
       the alternative is still named and no chip pretends to be missing. */
    const follow = mount(FOLLOW_UP);
    expect(follow.container.querySelector('.place-read')?.textContent).toContain('Ahmedābād, District Rampur, Uttar Pradesh');
    /* A resolution with nothing to say about other places draws no line at all: an empty region is a defect. */
    expect(mount(SURAT).container.querySelector('.place-read')).toBeNull();
    expect(within(follow.container as HTMLElement).queryByRole('button', { name: /Read it at/ })).toBeNull();
    expect(alternativeAsk('and tomorrow?', 'Ahmedabad', 'Ahmedābād, District Rampur, Uttar Pradesh')).toBeNull();
  });

  it('says which voice wrote the reply when the packet records one, and says nothing when it does not', () => {
    const { container } = mount(AHMEDABAD);
    expect(container.querySelector('.answer-by')?.textContent).toMatch(/^Written by a model from the retrieved facts/);

    /* The engine names the other voice itself: a draft the checks refused leaves the tools' own wording
       standing as the answer, and the card must not present that as model prose. */
    const refused = { ...AHMEDABAD, trace: { generation: { provider: 'verified_fact_renderer', status: 'narrative_refused' } } } as AnswerPacket;
    const { container: floor } = mount(refused);
    expect(authorshipNote(refused)).toMatch(/the checks refused it, so the tools' own wording stands/);
    expect(floor.querySelector('.answer-by')?.textContent).toMatch(/the tools' own wording stands as the answer/);

    /* A packet that records neither says neither. The eight recorded packets carry `trace: {}`, and a
       marker invented for them would be a claim about how they were written that nothing in them supports. */
    const silent = { ...AHMEDABAD, trace: {} } as AnswerPacket;
    const { container: bare } = mount(silent);
    expect(bare.querySelector('.answer-by')).toBeNull();
  });
});

describe('the register a reader chooses', () => {
  const has = (container: HTMLElement, selector: string) => container.querySelector(selector) !== null;

  it('brief keeps the answer and its leading value, and nothing else', () => {
    const { container } = mount(AHMEDABAD, () => {}, 'brief');
    expect(container.querySelector('.answer-lead')?.textContent).toBe(FINDING);
    expect(has(container, '[data-testid="lead-claim"]'), 'the leading value is the register\'s floor').toBe(true);
    expect(has(container, '.answer-rest'), 'the rest of the answer is the answer, not evidence').toBe(true);
    expect(container.querySelector('.place-read'), 'the place line is evidence depth').toBeNull();
    /* Three folds are left and every one of them belongs to the READER rather than to the evidence: the
       rest of the answer itself, the line that changes the register, and the ways to take the answer
       away with you. None of them holds a value, a source, a kind or a warning, which is the rule this
       assertion exists to enforce - brief hides evidence depth, not the reader's own controls. */
    const folds = Array.from(container.querySelectorAll('details.g-fold')).map(node => node.className);
    expect(folds.every(name => /answer-rest|answer-depth|answer-more/.test(name)), 'brief has folds it should not: ' + folds.join(', ')).toBe(true);
    expect(container.textContent).not.toContain('where this came from');
    expect(container.textContent).not.toContain('Machine record');
  });

  it('conversational adds the window, the receipt, the notes and the work, and still no raw record', () => {
    const { container } = mount(AHMEDABAD, () => {}, 'conversational');
    expect(container.textContent).toContain('where this came from');
    expect(container.textContent).toContain('how much of the window this covers');
    expect(container.textContent).toContain('What this answer does not cover');
    expect(container.textContent).toContain('How this was answered');
    expect(container.textContent).not.toContain('Machine record');
    expect(container.textContent).not.toContain('Requested tasks');
  });

  it('full adds the requested tasks, the retrieval choices and the machine record', () => {
    const { container } = mount(AHMEDABAD, () => {}, 'full');
    expect(container.textContent).toContain('Requested tasks');
    expect(container.textContent).toContain('Which tool read it, and why');
    expect(container.textContent).toContain('Machine record');
    /* The engine's own retrieval choice, in the engine's own words, which no register reached before. */
    expect(container.textContent).toContain('Exact-window GFS model summary');
  });

  it('changes the register for every card on screen, from the card\'s own depth line', async () => {
    const first = mount(AHMEDABAD);
    const second = mount(AHMEDABAD);
    expect(first.container.textContent).toContain('where this came from');
    await userEvent.click(within(first.container as HTMLElement).getByRole('button', { name: 'Brief' }));
    expect(window.localStorage.getItem(REGISTER_KEY)).toBe('brief');
    /* The preference is the transcript's, not the card's: a card changed here changes every answer that is
       already on screen, which is what "the register is carried on every turn" has to mean to be usable. */
    expect(second.container.textContent).not.toContain('where this came from');
    expect(first.container.textContent).toContain('How much this card unfolds: Brief');
  });

  it('never changes a value, its kind, its window or its source when the register changes', () => {
    const values = (container: HTMLElement) => [
      container.querySelector('.g-claim-number')?.textContent,
      container.querySelector('.g-claim-unit')?.textContent,
      container.querySelector('.g-claim-note')?.textContent,
      container.querySelector('.g-claim-source')?.textContent,
    ];
    const brief = mount(AHMEDABAD, () => {}, 'brief');
    const full = mount(AHMEDABAD, () => {}, 'full');
    expect(values(full.container as HTMLElement)).toEqual(values(brief.container as HTMLElement));
    expect(values(brief.container as HTMLElement)[0]).toBe('0.0');
  });
});
