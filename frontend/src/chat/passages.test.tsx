/* The passages an answer carries: the locator, the quotation, the context label, and the rule that only a
   local saved document becomes a link. The rules are the ones the vanilla passage card was checked
   against; the checks below are the React port of them. */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { AnswerPacket } from '../api/types';
import { AnswerTurn } from './AnswerTurn';

const SHA = 'a'.repeat(64);

function packet(overrides: Partial<AnswerPacket> = {}): AnswerPacket {
  return {
    conversation_id: '44444444-4444-4444-8444-444444444444',
    question: 'What does the latest national bulletin say about heavy rain?',
    status: 'answered',
    answer: 'The edition carries a heavy-rain section.',
    facts: [],
    citations: [],
    notes: [],
    choices: [],
    charts: [],
    task_results: [],
    answered_at_utc: '2026-09-17T10:47:00+00:00',
    resolved_points: {},
    trace: {},
    retrieval_plan: [],
    ...overrides,
  };
}

function mount(p: AnswerPacket) {
  return render(<AnswerTurn packet={p} register="conversational" onFollowUp={() => {}} />);
}

describe('the passages an answer carries', () => {
  it('quotes the source with its printed page and offers the saved edition as a page-anchored link', async () => {
    mount(packet({
      passages: [
        {
          id: 'p1',
          text: 'Heavy rain likely over Konkan and Goa during the next 24 hours.',
          crop: 'Cotton',
          stage: 'Squaring',
          district: 'AHMEDABAD',
          page: 3,
          issue_date: '2026-09-15',
          family: 'district_agromet',
          evidence_kind: 'published_advisory',
          source_id: 'S57',
          document_sha256: SHA,
        },
      ],
    }));
    const section = screen.getByTestId('passages');
    expect(within(section).getByText(/Cotton/)).toBeInTheDocument();
    expect(within(section).getByText(/page 3/)).toBeInTheDocument();
    await userEvent.click(within(section).getByText(/Cotton/));
    expect(within(section).getByText('Heavy rain likely over Konkan and Goa during the next 24 hours.')).toBeInTheDocument();
    expect(within(section).getByText(/Published 2026-09-15/)).toBeInTheDocument();
    expect(within(section).getByRole('link', { name: 'Open the saved source PDF' })).toHaveAttribute('href', '/api/documents/' + SHA + '#page=3');
    expect(within(section).getByRole('link', { name: 'Download the saved PDF' })).toHaveAttribute('download', 'bulletin-' + SHA + '.pdf');
  });

  it('labels a bulletin-context section apart from a crop row, and says what stays unverified', async () => {
    mount(packet({
      passages: [
        { id: 'c1', evidence_kind: 'published_bulletin_context', section: 'Warning', text: 'Fishermen are advised not to venture into the sea.', page: 1, district: 'KOCHI' },
      ],
    }));
    const section = screen.getByTestId('passages');
    expect(within(section).getByText(/Bulletin context: Warning/)).toBeInTheDocument();
    await userEvent.click(within(section).getByText(/Bulletin context: Warning/));
    expect(within(section).getByText(/current warning and individual field applicability remain unverified/)).toBeInTheDocument();
  });

  it('refuses to make a remote or javascript address clickable', async () => {
    mount(packet({
      citations: [{ id: 'c-remote', source_id: 'S99', url: 'javascript:alert(1)' } as never],
      passages: [{ id: 'p2', text: 'A passage whose citation carries a script address.', page: 2, citation_ids: ['c-remote'], source_id: 'S99' }],
    }));
    const section = screen.getByTestId('passages');
    await userEvent.click(within(section).getByText(/page 2/));
    expect(within(section).queryByRole('link')).toBeNull();
    expect(within(section).getByText(/No saved copy of this edition is reachable/)).toBeInTheDocument();
  });

  it('renders nothing at all when the answer carries no passage', () => {
    mount(packet());
    expect(screen.queryByTestId('passages')).toBeNull();
  });
});
