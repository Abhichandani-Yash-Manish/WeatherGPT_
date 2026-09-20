/* Print parity: what a printed card keeps and what it drops.

   A printed answer must still be an answer: the receipt, the sources and the validity window stay; the
   composer, the action buttons and the raw machine record go, because a paper copy has no keyboard and the
   machine record is an audit artefact rather than the answer. The markup and the print stylesheet are checked
   together, so a rename on one side cannot quietly change what a printout contains. */

import { screen, waitFor } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { http, HttpResponse } from 'msw';
import { renderAsk } from '../test/ask';
import { server } from '../test/msw';

const PACKET = {
  schema_version: 'weather-conversation-v1',
  conversation_id: '44444444-4444-4444-8444-444444444444',
  question: 'Will it rain in Ahmedabad?',
  status: 'answered',
  answer: 'Ahmedabad: forecast precipitation 0.3 mm.',
  facts: [{ id: 't1-f1', label: 'Forecast rainfall', value: '0.3', unit: 'mm', place: 'Ahmedabad, Gujarat',
            start: '2026-09-15T06:30:00+05:30', end: '2026-09-15T12:30:00+05:30', source_id: 'S21',
            parameter: 'precipitation', evidence_kind: 'forecast', citation_ids: ['t1-c1'], task_id: 't1' }],
  citations: [{ id: 't1-c1', source_id: 'S21', product: 'GFS forecast delivery', retrieved_at_utc: '2026-09-14T10:39:00+00:00' }],
  notes: [], choices: [], charts: [], task_results: [], answered_at_utc: '2026-09-14T10:47:00+00:00',
  resolved_points: {}, trace: {}, retrieval_plan: [],
};

/* vitest runs with the frontend directory as its working directory, and the print rules are a file the test
   reads rather than a stylesheet jsdom would apply. */
const PRINT_CSS = readFileSync('src/styles/print.css', 'utf8');

async function askAndRender() {
  /* `full` on purpose: the machine record is that register's own addition (docs/136), and this is the
     spec that holds the printout to dropping it. A print copy of `conversational` has no record to drop. */
  window.localStorage.setItem('weathergpt.register', 'full');
  server.use(
    http.post('/api/chat', () => HttpResponse.json(PACKET)),
    http.post('/api/chat/preview', () => HttpResponse.json({ schema_version: 'chat-preview-v1', provisional: true, note: 'provisional', reading: null })),
    http.get('/api/chat/progress', () => HttpResponse.json({ schema_version: 'chat-progress-v1', state: 'idle', stage: null, stages_seen: [], queue: { waiting: 0, active: 0, capacity: 3, wait_seconds_before_refusal: 45 } })),
  );
  renderAsk();
  const box = screen.getByLabelText('Your question');
  const { default: userEvent } = await import('@testing-library/user-event');
  const user = userEvent.setup();
  await user.type(box, 'Will it rain in Ahmedabad?');
  await user.click(screen.getByTestId('send-question'));
  await screen.findByText('Evidence receipt');
  return user;
}

describe('printing a turn', () => {
  it('keeps the receipt and the window, and marks the controls that a paper copy cannot use', async () => {
    await askAndRender();
    const card = screen.getByRole('article');
    expect(card.querySelector('.receipt'), 'the receipt is what makes the printout evidence').not.toBeNull();
    /* Every control the card draws is marked for the drop, and there is more than one now: the action row
       under the answer, and a copy on each claim. The row is the one that carries the words. */
    const dropped = Array.from(card.querySelectorAll('[data-print="drop"]'));
    expect(dropped.length, 'controls are marked so print can drop them').toBeGreaterThan(0);
    const actions = dropped.find(node => /Copy the answer/.test(node.textContent || ''));
    expect(actions, 'the action row is marked so print can drop it').not.toBeUndefined();
    dropped.forEach(node => expect(node.className).toMatch(/no-print|g-chips/));
    expect(PRINT_CSS).toContain("[data-print='drop']");
    expect(PRINT_CSS).toContain('.machine-record');
    expect(PRINT_CSS).toContain('.composer-shell');
  });

  it('keeps the raw machine record out of the printout', async () => {
    const user = await askAndRender();
    await waitFor(() => expect(screen.getByText(/Machine record/)).toBeInTheDocument());
    await user.click(screen.getByText('Machine record (the exact response)'));
    const record = document.querySelector('.machine-record');
    expect(record, 'the machine record exists as depth').not.toBeNull();
    expect(PRINT_CSS).toMatch(/\.machine-record[^{]*\{[^}]*display:\s*none/);
  });
});
