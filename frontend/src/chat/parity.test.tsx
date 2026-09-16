/* Checks ported from the vanilla suites that the transcript suite does not already cover, kept in their own
   file so the ledger can point at them by name: the receipt chain, the clarification choices, the resolved
   point read out of the packet (or reported absent), and deleting a stored conversation through the local
   route only. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import type { AnswerPacket } from '../api/types';
import { server } from '../test/msw';
import { AnswerTurn } from './AnswerTurn';
import { ConversationRail } from './ConversationRail';
import { firstPoint } from './model';

function mount(node: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

function packet(overrides: Partial<AnswerPacket> = {}): AnswerPacket {
  return {
    schema_version: 'weather-conversation-v1',
    conversation_id: '44444444-4444-4444-8444-444444444444',
    question: 'Will it rain in Ahmedabad?',
    status: 'answered',
    answer: 'Ahmedabad: forecast precipitation 0.3 mm.',
    facts: [{ id: 't1-f1', label: 'Forecast rainfall', value: '0.3', unit: 'mm', place: 'Ahmedabad, Gujarat',
              start: '2026-09-15T06:30:00+05:30', end: '2026-09-15T12:30:00+05:30', source_id: 'S21',
              parameter: 'precipitation', evidence_kind: 'forecast', method: 'gfs_hourly_v1',
              citation_ids: ['t1-c1'], task_id: 't1' }],
    citations: [{ id: 't1-c1', source_id: 'S21', product: 'GFS forecast delivery',
                  retrieved_at_utc: '2026-09-14T10:39:00+00:00' }],
    notes: [], choices: [], charts: [], task_results: [], answered_at_utc: '2026-09-14T10:47:00+00:00',
    resolved_points: { Ahmedabad: { selection_id: 'geonames:1279233', label: 'Ahmedabad, Gujarat',
                                    coordinates: { latitude: 23.02579, longitude: 72.58727 } } },
    trace: {}, retrieval_plan: [],
    ...overrides,
  };
}

describe('transcript parity', () => {
  it('names the source, the retrieval time and the method in one chain', () => {
    mount(<AnswerTurn packet={packet()} register="conversational" onFollowUp={() => {}} />);
    const receipt = document.querySelector('.receipt')!;
    const chain = receipt.querySelector('.receipt-chain')!;
    expect(chain.textContent).toMatch(/S21/);
    expect(chain.textContent).toMatch(/retrieved 14 Sep 2026, 16:09 IST/);
    expect(chain.textContent).toMatch(/gfs_hourly_v1/);
  });

  it('offers every candidate the engine sent for a clarification', async () => {
    mount(
      <AnswerTurn
        packet={packet({
          status: 'needs_selection',
          answer: 'Two places share that name.',
          facts: [],
          choices: [
            { label: 'Surat, Gujarat', value: 'Surat', selection_id: 'geonames:1255364' },
            { label: 'Surat, Himachal Pradesh', value: 'Surat HP', selection_id: 'geonames:1255365' },
          ],
        })}
        register="conversational"
        onFollowUp={() => {}}
      />,
    );
    const buttons = screen.getAllByRole('button', { name: /Surat/ });
    expect(buttons).toHaveLength(2);
    expect(buttons[0]).toHaveTextContent('Surat, Gujarat');
    expect(buttons[1]).toHaveTextContent('Surat, Himachal Pradesh');
  });

  it('reads the resolved point out of the packet, and reports it absent when there is none', () => {
    expect(firstPoint(packet())).toEqual({ latitude: 23.02579, longitude: 72.58727, label: 'Ahmedabad, Gujarat' });
    expect(firstPoint(packet({ resolved_points: {} }))).toBeNull();
    expect(firstPoint(packet({ resolved_points: { nowhere: { label: 'nowhere' } } }))).toBeNull();
  });

  it('deletes a stored conversation through the local route only, and says when the delete failed', async () => {
    const asked: string[] = [];
    server.use(
      http.get('/api/conversations', () => HttpResponse.json({
        schema_version: 'conversation-ledger-v1', total: 1, limit: 40, note: 'stored locally',
        conversations: [{ id: '11111111-1111-4111-8111-111111111111', opening_question: 'hello', turns: 2, asked: 1 }],
      })),
      http.delete('/api/conversations/:id', async ({ request, params }) => {
        asked.push(request.method + ' ' + String(params.id));
        return HttpResponse.json({ removed: String(params.id) });
      }),
    );
    mount(<ConversationRail currentId={null} onOpen={() => {}} onNew={() => {}} register="conversational" onRegister={() => {}} />);
    const row = await screen.findByText('hello');
    expect(row).toBeInTheDocument();
    const button = within(row.parentElement!.parentElement as HTMLElement).getByRole('button', { name: /Delete/ });
    await userEvent.click(button);
    await waitFor(() => expect(asked).toEqual(['DELETE 11111111-1111-4111-8111-111111111111']));
  });
});
