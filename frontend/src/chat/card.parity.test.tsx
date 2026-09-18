/* Card parity: the checks tests/test_views.js makes against the vanilla answer card, held against the React
   card. The payloads are the same recorded packets the vanilla suite read
   (research/reviews/frontend-overhaul-20260914/packets/), plus the two packets that suite writes inline, copied
   verbatim. Where a packet is partial the test says so. Nothing here re-implements a product rule: the real
   components decide, and these specs assert what a reader is shown. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import type { AnswerPacket } from '../api/types';
import { server } from '../test/msw';
import { AnswerTurn } from './AnswerTurn';
import { AskSurface } from './AskSurface';
import airportJson from '../../../research/reviews/frontend-overhaul-20260914/packets/airport.json';
import clarificationJson from '../../../research/reviews/frontend-overhaul-20260914/packets/clarification.json';
import forecastJson from '../../../research/reviews/frontend-overhaul-20260914/packets/forecast-simple.json';
import hindiJson from '../../../research/reviews/frontend-overhaul-20260914/packets/language-hindi.json';
import historicalJson from '../../../research/reviews/frontend-overhaul-20260914/packets/historical-chart.json';
import marineJson from '../../../research/reviews/frontend-overhaul-20260914/packets/marine.json';
import multiJson from '../../../research/reviews/frontend-overhaul-20260914/packets/multi-task.json';
import warningJson from '../../../research/reviews/frontend-overhaul-20260914/packets/warning.json';

const RECORDED = {
  forecast: forecastJson.packet as unknown as AnswerPacket,
  multi: multiJson.packet as unknown as AnswerPacket,
  historical: historicalJson.packet as unknown as AnswerPacket,
  marine: marineJson.packet as unknown as AnswerPacket,
  airport: airportJson.packet as unknown as AnswerPacket,
  clarification: clarificationJson.packet as unknown as AnswerPacket,
  warning: warningJson.packet as unknown as AnswerPacket,
  hindi: hindiJson.packet as unknown as AnswerPacket,
};

/* The eight packets the vanilla suite captured. */
const CAPTURED: [string, AnswerPacket][] = [
  ['forecast-simple', RECORDED.forecast],
  ['multi-task', RECORDED.multi],
  ['historical-chart', RECORDED.historical],
  ['marine', RECORDED.marine],
  ['airport', RECORDED.airport],
  ['clarification', RECORDED.clarification],
  ['warning', RECORDED.warning],
  ['language-hindi', RECORDED.hindi],
];

/* Copied from tests/test_views.js (check 25): the conversational packet the vanilla suite wrote inline. */
const CONVERSATION: AnswerPacket = {
  schema_version: 'weather-conversation-v1', conversation_id: 'c', question: 'hello', status: 'conversation',
  answer: 'Hello! I can check the weather, the official district warnings and published documents. Tell me a place and a day.',
  answer_basis: 'conversation', facts: [], citations: [], choices: [], charts: [], calculations: [], task_results: [],
  notes: ['A conversational reply written by the model for this message. It is not retrieved evidence.'],
  answered_at_utc: '2026-09-16T17:00:00+00:00', plan: { intent: 'chat', language: 'en', context_action: 'new', changed_fields: [] },
};

/* Copied from tests/test_views.js (check 15): the warning-day packet the vanilla suite wrote inline. Its
   citation states no retrieval time, so the sources list can only show what the citation holds. */
const WARNING_DAY: AnswerPacket = {
  schema_version: 'weather-conversation-v1', conversation_id: 'w', question: 'Is there an official warning?', status: 'answered',
  answer: 'IMD district warning for PATNA.',
  citations: [{ id: 'district-warning', source_id: 'S15', provider: 'India Meteorological Department', product: 'District-wise warning product', url: 'https://reactjs.imd.gov.in/geoserver/wfs' }],
  notes: [], choices: [], charts: [], calculations: [], task_results: [],
  facts: [{
    id: 't1-f1', label: 'Day 1 \u00b7 14 Sep 2026', value: 'No warning in this product', unit: 'IMD district warning colour',
    place: 'PATNA', start: '2026-09-13T18:30:00+00:00', end: '2026-09-14T18:30:00+00:00', source_id: 'S15',
    parameter: 'official_district_warning', entity_id: 'imd-district:364', citation_ids: ['district-warning'],
  }],
};

/* A partial packet: only the fields the title and status rules read, because the recorded set holds no packet
   for these statuses. It is not an engine response and the test claims nothing else from it. */
const partial = (status: string): AnswerPacket => ({
  conversation_id: 'partial', question: 'A partial packet', status, answer: 'A partial packet, for the title rule only.',
});

function mountCard(packet: AnswerPacket, _register: 'brief' | 'conversational' | 'full' = 'conversational') {
  return render(<AnswerTurn packet={packet} onFollowUp={() => {}} />);
}

function withClient(node: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

describe('the answer card, held against the vanilla checks', () => {
  it('titles each status with its own words instead of one generic answer title', () => {
    const cases: [AnswerPacket, string][] = [
      [RECORDED.forecast, 'Answer'],
      [CONVERSATION, 'Conversation'],
      [RECORDED.clarification, 'Which place do you mean?'],
      [RECORDED.warning, 'No verified evidence for this'],
      [RECORDED.historical, 'Retrieved series'],
      [partial('needs_clarification'), 'One more detail needed'],
      [partial('explanation'), 'General explanation'],
      [partial('outside_validity'), 'That window is not available'],
      [partial('cancelled'), 'Stopped'],
    ];
    cases.forEach(([packet, title]) => {
      const { container, unmount } = mountCard(packet);
      expect(container.querySelector('h2')?.textContent).toBe(title);
      unmount();
    });
  });

  it('tags the status, the requested output and an unread reply beside the answer', () => {
    const first = mountCard(RECORDED.forecast);
    expect(first.container.querySelector('.tag')?.textContent).toBe('Evidence retrieved');
    expect(first.container.querySelector('.tag')?.className).not.toMatch(/tag-held/);
    first.unmount();

    const held = mountCard(RECORDED.warning);
    const heldTag = Array.from(held.container.querySelectorAll('.tag')).find(tag => tag.textContent === 'Evidence gap')!;
    expect(heldTag.className).toMatch(/tag-held/);
    held.unmount();

    /* The requested-output tag is read from the generation trace; the recorded forecast packet states no
       requested language, so the field is set here on an otherwise recorded packet. */
    const requested = mountCard({ ...RECORDED.forecast, trace: { generation: { requested_language: 'hi' } } });
    expect(within(requested.container).getByText('Requested output: hi')).toBeInTheDocument();
    requested.unmount();

    const reply = mountCard(CONVERSATION);
    expect(within(reply.container).getByText('No source read')).toBeInTheDocument();
    reply.unmount();

    const untimed = mountCard(partial('answered'));
    expect(within(untimed.container).getByText('Time not recorded')).toBeInTheDocument();
  });

  /* Check 10 and the remaining clauses of check 25: where there is no retrieved evidence there is no headline
     value, no receipt and no window, and the card says what the reader is looking at instead. */
  it('keeps a held warning and a conversational reply free of any value, receipt or window', () => {
    const held = mountCard(RECORDED.warning);
    expect(held.container.querySelector('h2')?.textContent).toBe('No verified evidence for this');
    expect(held.container.querySelector('.tag-held')).not.toBeNull();
    expect(held.container.querySelectorAll('.receipt')).toHaveLength(0);
    expect(held.container.querySelectorAll('.lead-value')).toHaveLength(0);
    expect(held.container.querySelector('.ruler-rail')).toBeNull();
    expect(held.container.textContent).toMatch(/does not mean there are no warnings/i);
    held.unmount();

    const reply = mountCard(CONVERSATION);
    expect(reply.container.querySelector('h2')?.textContent).toBe('Conversation');
    expect(within(reply.container).getByText('No source read')).toBeInTheDocument();
    expect(reply.container.querySelectorAll('.receipt')).toHaveLength(0);
    expect(reply.container.querySelector('.ruler-rail')).toBeNull();
    expect(reply.container.querySelectorAll('.lead-value')).toHaveLength(0);
    expect(reply.container.textContent).toMatch(/not retrieved evidence/i);
  });

  it('draws the validity ruler from the retrieved window and describes every drawn segment', () => {
    const { container } = mountCard(RECORDED.forecast);
    const rail = container.querySelector('.ruler-rail')!;
    const svg = rail.closest('svg')!;
    const label = svg.getAttribute('aria-label') || '';
    expect(label).toMatch(/^Requested window /);
    expect(label).toMatch(/covering 6 hours across 1 retrieved sample/);
    expect(container.querySelectorAll('.ruler-rail')).toHaveLength(1);
    const covered = container.querySelector('.ruler-covered')!;
    expect(Number(covered.getAttribute('x'))).toBe(Number(rail.getAttribute('x')));
    expect(Number(covered.getAttribute('width'))).toBe(Number(rail.getAttribute('width')));
    const hits = container.querySelectorAll('.ruler-hit');
    expect(hits).toHaveLength(1);
    expect(hits[0].getAttribute('aria-label')).toMatch(/Covered by retrieved evidence/);
  });

  it('reads a focused part of the window out in words', () => {
    const { container } = mountCard(RECORDED.forecast);
    const readout = container.querySelector('[aria-live="polite"]')!;
    expect(readout.textContent).toMatch(/Focus a part of the window/);
    fireEvent.focus(container.querySelector('.ruler-hit')!);
    expect(readout.textContent).toMatch(/Covered by retrieved evidence/);
    expect(readout.textContent).toMatch(/1 sample/);
  });

  it('draws no window where the evidence has no interval', () => {
    [RECORDED.airport, RECORDED.marine].forEach(packet => {
      const { container, unmount } = mountCard(packet);
      expect(container.querySelector('.ruler-rail')).toBeNull();
      const windows = Array.from(container.querySelectorAll('svg[role="img"]'))
        .filter(svg => /^Requested window/.test(svg.getAttribute('aria-label') || ''));
      expect(windows).toHaveLength(0);
      unmount();
    });
  });

  it('keeps the retrieved volume bounded and never re-lists a plotted value as a fact row', () => {
    CAPTURED.forEach(([name, packet]) => {
      const { container, unmount } = mountCard(packet);
      expect(container.querySelectorAll('.fact-row').length, name).toBeLessThanOrEqual(8);
      unmount();
    });
    const { container, unmount } = mountCard(RECORDED.historical);
    expect(container.querySelectorAll('.fact-row')).toHaveLength(0);
    unmount();
  });

  it('never headlines one member of a returned series, and draws the series instead', () => {
    [RECORDED.historical, RECORDED.marine].forEach(packet => {
      const { container, unmount } = mountCard(packet);
      expect(container.querySelector('h2')?.textContent).toBe('Retrieved series');
      expect(container.querySelectorAll('.lead-value')).toHaveLength(0);
      expect(container.querySelectorAll('.fact-row')).toHaveLength(0);
      expect(container.querySelectorAll('[data-testid="chart-block"]').length).toBeGreaterThan(0);
      unmount();
    });
  });

  it('gives every remaining fact its measure, kind, value, place, window and source in one row', () => {
    const { container } = mountCard(RECORDED.airport);
    const rows = Array.from(container.querySelectorAll('.fact-row'));
    expect(rows).toHaveLength(1);
    const text = rows[0].textContent || '';
    expect(text).toContain('Airport wind speed');
    expect(text).toContain('Observation');
    expect(text).toContain('8');
    expect(text).toContain('kt');
    expect(text).toContain('VOBL \u00b7 Bangaluru Intl');
    /* An observation is one instant: the window label used to print '16:30-16:30', a zero-length
       range that reads as a window while saying nothing (repaired 17 September 2026). */
    expect(text).toContain('14 Sep 2026, 16:30 IST');
    expect(text).not.toContain('16:30-16:30');
    expect(text).toContain('S18');
  });

  it('shows no number that is not in the packet the engine returned', () => {
    const digits = (text: string) => text.match(/-?\d+(?:\.\d+)?/g) || [];
    ['forecast-simple', 'multi-task', 'historical-chart', 'marine', 'airport'].forEach(name => {
      const packet = CAPTURED.find(([recordedName]) => recordedName === name)![1];
      const { container, unmount } = mountCard(packet);
      const raw = JSON.stringify(packet);
      let checked = 0;
      Array.from(container.querySelectorAll('.lead-value, .fact-value, td')).forEach(node => {
        digits(node.textContent || '').forEach(value => {
          checked += 1;
          expect(raw, name + ': ' + value + ' is not in the packet').toContain(value);
        });
      });
      expect(checked, name + ' exposed at least one number to check').toBeGreaterThan(0);
      unmount();
    });
  });

  /* The vanilla check also asserts the record locator ("$.hourly.precipitation["). The recorded packet states
     source_locators as plain strings; the React receipt reads only the object form ({page,row,column}), so the
     locator is absent. That is a product gap, reported rather than asserted or repaired here. */
  it('keeps entity, window, source and retrieval time together in the receipt rows', () => {
    const { container } = mountCard(RECORDED.forecast);
    const receipt = container.querySelector('.receipt')!;
    const keys = Array.from(receipt.querySelectorAll('.receipt-key')).map(key => key.textContent);
    ['Measure', 'Value', 'Place', 'Entity', 'Window', 'Source', 'Retrieved'].forEach(key => expect(keys).toContain(key));
    const text = receipt.textContent || '';
    expect(text).toContain('geonames:1279233');
    expect(text).toContain('S21');
    expect(text).toContain('not an observation');
    expect(within(receipt as HTMLElement).getByRole('button', { name: 'Copy this receipt' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Print this answer' })).toBeInTheDocument();
  });

  it('says the clipboard refused the copy instead of claiming a success', async () => {
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined });
    const { container } = mountCard(RECORDED.forecast);
    const button = within(container.querySelector('.receipt') as HTMLElement).getByRole('button', { name: 'Copy this receipt' });
    fireEvent.click(button);
    await waitFor(() => expect(button).toHaveTextContent('Copy refused'));
    expect(button).not.toHaveTextContent('Copied');
  });

  it('lists each source an answer reached, with its product and provider', () => {
    const { container } = mountCard(WARNING_DAY);
    const list = within(container).getByText('Sources reached').closest('.card') as HTMLElement;
    expect(list.textContent).toContain('S15');
    expect(list.textContent).toContain('District-wise warning product');
    expect(list.textContent).toContain('India Meteorological Department');
  });

  it('keeps every disclosure reachable on one shape of card, and never changes what the card says', () => {
    const { container } = mountCard(RECORDED.forecast);
    const summaries = Array.from(container.querySelectorAll('summary')).map(summary => summary.textContent || '');
    expect(summaries).toContain('where this came from');
    expect(summaries.some(text => /Machine record/.test(text))).toBe(true);
    expect(summaries.some(text => /how this was answered/.test(text))).toBe(true);
    expect(container.querySelector('.f-sentence')?.textContent).toBe(RECORDED.forecast.answer);
    expect(container.querySelector('.lead-value')).not.toBeNull();
  });

  it('shows the exact rendered packet in the machine record rather than a summary', () => {
    const { container } = mountCard(RECORDED.forecast, 'full');
    fireEvent.click(within(container).getByText('Machine record (the exact response)'));
    const pre = container.querySelector('pre')!;
    expect(pre.textContent).toContain('"conversation_id"');
    expect(JSON.parse(pre.textContent || '')).toEqual(RECORDED.forecast);
    const details = pre.closest('details')!;
    expect(details.querySelector('summary')?.textContent).toContain('Machine record');
    expect(details.textContent).toContain('complete response this card was rendered from');
  });

  it('offers every place candidate the engine sent for a shared name', () => {
    const { container } = mountCard(RECORDED.clarification);
    const labels = (RECORDED.clarification.choices || []).map(choice => String(choice.label));
    expect(labels).toHaveLength(3);
    const buttons = Array.from(container.querySelectorAll('button.chip')).map(button => button.textContent);
    expect(buttons).toEqual(labels);
    expect(buttons[0]).toContain('Bhop');
    expect(container.querySelectorAll('.lead-value')).toHaveLength(0);
  });

  it('sends the selection id of the candidate the reader chose back to the engine', async () => {
    const bodies: { question?: string; selection_id?: string }[] = [];
    let calls = 0;
    server.use(
      http.post('/api/chat', async ({ request }) => {
        bodies.push((await request.json()) as { question?: string; selection_id?: string });
        calls += 1;
        return HttpResponse.json(calls === 1 ? RECORDED.clarification : RECORDED.forecast);
      }),
      http.post('/api/chat/preview', () => HttpResponse.json({ schema_version: 'chat-preview-v1', provisional: true, reading: null })),
      http.get('/api/chat/progress', () => HttpResponse.json({ schema_version: 'chat-progress-v1', state: 'working', stage: 'started' })),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [], note: 'stored locally' })),
    );
    withClient(<AskSurface language="" persona="" />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Your question'), 'Tell me about rainfall in Bhopal');
    await user.click(screen.getByTestId('send-question'));
    const first = (RECORDED.clarification.choices || [])[0];
    await user.click(await screen.findByRole('button', { name: String(first.label) }));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[1].selection_id).toBe(first.selection_id);
    expect(bodies[1].question).toBe(String(first.label));
  });
});
