/* The palette gaps the port ledger could not claim when the React palette was written, held here
   against the payloads tests/test_suite_ui.js recorded for vanilla check 25:

   - the surface commands stay in the list, a typed term filters them, and the arrow keys move the active
     item while Enter runs it and closes the palette (the keyboard contract the vanilla check held);
   - a typed term reaches GET /api/places/search, the match is listed with its own source and kind, and
     running it fills the question with exactly the place the payload named, through the control the
     shell supplies — a place the payload did not return is never invented;
   - GET /api/conversations supplies the stored conversations, each with its own asked count, and running
     one opens exactly that stored conversation through the shell.

   The Surat place match, the stored conversation and the conversation-ledger envelope below are copied
   from tests/test_suite_ui.js. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { vi } from 'vitest';
import { server } from '../test/msw';
import { Palette } from './Palette';
import { VIEWS } from './views';

const HEAD = {
  schema_version: 'product-view-v1',
  generated_at_utc: '2026-09-14T18:00:00+00:00',
  status: 'ok',
};

const placesPayload = {
  ...HEAD,
  view: 'places.search',
  data: {
    matches: [
      {
        label: 'Surat, S\u016brat, State of Gujar\u0101t',
        name: 'Surat',
        source_id: 'geonames',
        kind: 'city',
        coordinates: { latitude: 21.1959, longitude: 72.8302 },
      },
    ],
  },
  sources: [],
  limitations: ['Place records are GeoNames source labels, not authoritative LGD entities.'],
  not_established: ['No reviewed dated administrative crosswalk is applied here.'],
};

const emptyPlacesPayload = { ...placesPayload, data: { matches: [] } };

const conversationLedger = {
  schema_version: 'conversation-ledger-v1',
  total: 1,
  limit: 6,
  conversations: [
    { id: 'c1', opening_question: 'Will it rain in Surat tomorrow?', asked: 2, turns: 4, updated: '2026-09-14T18:00:00+00:00' },
  ],
};

function mountPalette(overrides: { onAsk?: ((question: string) => void) | undefined } = {}) {
  const props = {
    open: true,
    onClose: vi.fn(),
    onOpenView: vi.fn(),
    onNewConversation: vi.fn(),
    onAsk: vi.fn() as ((question: string) => void) | undefined,
    onOpenConversation: vi.fn(),
    ...overrides,
  };
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(
    <QueryClientProvider client={client}>
      <Palette {...props} />
    </QueryClientProvider>,
  );
  return props;
}

const input = () => document.getElementById('palette-search') as HTMLInputElement;

describe('the command palette gaps', () => {
  it('keeps every surface as a command, filters them by what is typed, and runs the active item with the keyboard', async () => {
    /* A term of two characters or more may also be a place search; an empty match set is served here so
       the surface-filter rule is checked on its own. */
    server.use(http.get('/api/places/search', () => HttpResponse.json(emptyPlacesPayload)));
    const props = mountPalette();

    const palette = await screen.findByRole('dialog', { name: 'Command palette' });
    const options = within(palette).getAllByRole('option');
    expect(options.length).toBeGreaterThanOrEqual(12);
    const text = options.map(option => option.textContent || '');
    VIEWS.forEach(view => expect(text.some(line => line.startsWith('Open ' + view.label))).toBe(true));
    expect(within(palette).getByRole('option', { name: /Open What changed/ })).toBeInTheDocument();
    expect(within(palette).getByRole('option', { name: /Start a new conversation/ })).toBeInTheDocument();

    await userEvent.type(input(), 'Warnings');
    expect(within(palette).getByRole('option', { name: /Open Warnings/ })).toBeInTheDocument();
    expect(within(palette).queryByRole('option', { name: /Open What changed/ })).toBeNull();

    await userEvent.clear(input());
    await waitFor(() => expect(within(palette).getAllByRole('option').length).toBeGreaterThanOrEqual(12));
    await userEvent.keyboard('{ArrowDown}');
    expect(within(palette).getAllByRole('option')[1]).toHaveAttribute('aria-selected', 'true');
    await userEvent.keyboard('{Enter}');
    expect(props.onOpenView).toHaveBeenCalledWith(VIEWS[0].id);
    expect(props.onClose).toHaveBeenCalled();
  });

  it('searches the place catalogue for a typed term and asks about the place the payload named', async () => {
    server.use(http.get('/api/places/search', () => HttpResponse.json(placesPayload)));
    const props = mountPalette();

    const palette = await screen.findByRole('dialog', { name: 'Command palette' });
    await userEvent.type(input(), 'surat');

    const place = await screen.findByRole('option', { name: /Surat, S\u016brat, State of Gujar\u0101t/ });
    expect(place).toHaveTextContent('geonames');
    expect(place).toHaveTextContent('city');
    expect(place).toHaveTextContent('21.1959, 72.8302');
    expect(place).toHaveTextContent('asks the conversation about this place');
    /* The typed term filters the surface commands out of the list rather than being ignored. */
    expect(within(palette).queryByRole('option', { name: /Open What changed/ })).toBeNull();

    await userEvent.click(within(place).getByRole('button'));
    expect(props.onAsk).toHaveBeenCalledWith('What is it like right now in Surat, S\u016brat, State of Gujar\u0101t?');
    expect(props.onClose).toHaveBeenCalled();
  });

  it('lists the stored conversations with their asked counts and opens the one the reader chooses', async () => {
    server.use(http.get('/api/conversations', () => HttpResponse.json(conversationLedger)));
    const props = mountPalette();

    await screen.findByRole('dialog', { name: 'Command palette' });
    const group = await screen.findByRole('group', { name: 'Recent conversations' });
    const conversation = within(group).getByRole('option', { name: /Will it rain in Surat tomorrow\?/ });
    expect(conversation).toHaveTextContent('2 asked');
    expect(conversation).toHaveTextContent('opens this stored conversation');

    await userEvent.click(within(conversation).getByRole('button'));
    expect(props.onOpenConversation).toHaveBeenCalledWith('c1');
    expect(props.onClose).toHaveBeenCalled();
  });

  it('states what a place entry did when the shell supplies no question control, rather than passing as filled', async () => {
    server.use(http.get('/api/places/search', () => HttpResponse.json(placesPayload)));
    mountPalette({ onAsk: undefined });

    await screen.findByRole('dialog', { name: 'Command palette' });
    await userEvent.type(input(), 'surat');
    const place = await screen.findByRole('option', { name: /Surat, S\u016brat, State of Gujar\u0101t/ });
    expect(place).toHaveTextContent('no question was filled');

    await userEvent.click(within(place).getByRole('button'));
    expect(window.location.hash).toBe('#/assistant');
  });
});
