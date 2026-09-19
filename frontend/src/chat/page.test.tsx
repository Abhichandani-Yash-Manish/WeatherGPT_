/* Two rules the vanilla suite held that are about the page rather than a value: an empty question is refused
   without a request, and no stylesheet class name leaks into the visible text of an answer.

   The leak rule matters here because the card is assembled from class names; a renderer that pushed a class
   name into a text node would show the reader chrome instead of a measure. */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { readdirSync, readFileSync } from 'node:fs';
import { http, HttpResponse } from 'msw';
import type { AnswerPacket } from '../api/types';
import { AnswerTurn } from './AnswerTurn';
import { server } from '../test/msw';
import { renderAsk } from '../test/ask';

const PACKET: AnswerPacket = {
  conversation_id: '44444444-4444-4444-8444-444444444444',
  question: 'Will it rain in Ahmedabad?',
  status: 'answered',
  answer: 'Ahmedabad: forecast precipitation 0.3 mm.',
  facts: [{ id: 't1-f1', label: 'Forecast rainfall', value: '0.3', unit: 'mm', place: 'Ahmedabad, Gujarat',
            start: '2026-09-18T06:30:00+05:30', end: '2026-09-18T12:30:00+05:30', source_id: 'S21',
            parameter: 'precipitation', evidence_kind: 'forecast', citation_ids: ['t1-c1'], task_id: 't1' }],
  citations: [{ id: 't1-c1', source_id: 'S21', product: 'GFS forecast delivery', retrieved_at_utc: '2026-09-17T10:39:00+00:00' }],
  notes: ['A note the card may show.'],
  choices: [],
  charts: [],
  task_results: [],
  answered_at_utc: '2026-09-17T10:47:00+00:00',
  resolved_points: {},
  trace: {},
  retrieval_plan: [],
};

describe('the page rules', () => {
  it('refuses an empty question without sending anything', async () => {
    const asked: string[] = [];
    server.use(http.post('/api/chat', ({ request }) => { asked.push(request.url); return HttpResponse.json(PACKET); }));
    renderAsk();
    const box = screen.getByLabelText('Your question');
    expect(screen.getByTestId('send-question')).toBeDisabled();
    await userEvent.click(box);
    await userEvent.keyboard('{Control>}{Enter}{/Control}');
    await userEvent.click(screen.getByTestId('send-question'), { pointerEventsCheck: 0 }).catch(() => undefined);
    expect(asked).toEqual([]);
    expect(screen.queryByText(/precipitation 0.3 mm/)).toBeNull();
  });


  it('names the state a failed read left the reader in, not only the server sentence', async () => {
    /* An expired token and an unavailable store must read differently: they call for different actions, and a
       generic failure sentence would leave the reader guessing which one happened. */
    server.use(
      http.post('/api/chat', () => HttpResponse.json({ error: 'The workspace token is no longer accepted.' }, { status: 403 })),
    );
    renderAsk();
    const box = screen.getByLabelText('Your question');
    await userEvent.type(box, 'Will it rain?');
    await userEvent.click(screen.getByTestId('send-question'));
    expect(await screen.findByText(/The workspace token is no longer accepted/)).toBeInTheDocument();
    expect(screen.getByText(/If the server was restarted, reload the page/)).toBeInTheDocument();
    expect(screen.queryByText(/The local evidence store did not answer/)).toBeNull();
  });

  it('names an unavailable store as its own state', async () => {
    server.use(
      http.post('/api/chat', () => HttpResponse.json({ error: 'The local evidence store is unavailable.' }, { status: 503 })),
    );
    renderAsk();
    const box = screen.getByLabelText('Your question');
    await userEvent.type(box, 'Will it rain?');
    await userEvent.click(screen.getByTestId('send-question'));
    expect(await screen.findByText(/The local evidence store is unavailable/)).toBeInTheDocument();
    expect(screen.getByText(/Nothing was read, so this is not an empty result/)).toBeInTheDocument();
  });

  it('never renders a stylesheet class name as visible text', () => {
    /* Every class name the stylesheets declare, collected from the sources the built page uses. A text node
       that matched one would be chrome shown as a measure. */
    const classes = new Set<string>();
    const collect = (directory: string) => {
      for (const entry of readdirSync(directory, { withFileTypes: true })) {
        const path = directory + '/' + entry.name;
        if (entry.isDirectory()) {
          collect(path);
          continue;
        }
        if (!entry.name.endsWith('.css')) continue;
        /* Only hyphenated class names: a plain word may legitimately appear as a label ('source', 'place'),
           and asserting against those would fail on the product's own vocabulary. A hyphenated token in a text
           node is chrome, never a measure. */
        for (const match of readFileSync(path, 'utf8').matchAll(/\.[a-z][a-z0-9]*-[a-z0-9-]+/g)) classes.add(match[0].slice(1));
      }
    };
    collect('src/styles');
    collect('../web');
    expect(classes.size).toBeGreaterThan(20);

    const { container } = render(<AnswerTurn packet={PACKET} onFollowUp={() => {}} />);
    const words = (container.textContent || '').split(/[^A-Za-z0-9-]+/).filter(Boolean);
    const leaked = words.filter(word => classes.has(word));
    expect(leaked, 'class names reached the visible text: ' + leaked.join(', ')).toEqual([]);
  });
});
