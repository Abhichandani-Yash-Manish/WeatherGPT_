/* Parity checks for the Briefcase surface, ported from the vanilla component suite tests/test_briefcase_ui.js.
   That suite prints one PASS line, but the check bundles ten sub-rules. The recorded payload constants below
   (the entry factory, the kept-briefs view, the opened entry and the empty-store view) are copied verbatim from
   the vanilla file.

   Held here (the surface's own sub-rules: keeping, listing, reopening, deleting and the empty store):
   - kept entries render with their own provenance and no invented delivery;
   - opening an entry reads it through the token-authenticated store route and shows the stored limits, the
     content hash and the Markdown that would be exported (the vanilla drawer is the React entry section here);
   - delete posts the identifier and the list is re-read rather than assumed;
   - an empty store says nothing is kept and invents no entry;
   - the compose control asks the server to compose for a point and posts no brief body (the vanilla check was a
     static string check on web/panels.js; the React surface sends kind and coordinates and no day — its own
     note says the first published day is composed).

   Not portable, reported rather than asserted: sub-rule 3 (export over /api/briefs/export and a .md download:
   the React surface carries no export control at all), and sub-rules 9 and 10 (the briefing series read from
   /api/briefing/latest: there is no briefing surface in the React tree). Sub-rules 7 and 8 (the reading position
   and the welcome) belong to Topbar/Welcome in React, not to this surface. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { istStamp } from '../lib/time';
import { server } from '../test/msw';
import { Surface as BriefcaseSurface } from './BriefcaseSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const TOKEN = 'test-token';

function entry(id: string, title: string) {
  return { id: id, saved_at: '2026-09-15T06:30:00+00:00', kind: 'alert_brief', title: title,
           place: { district: 'PATNA', state: 'BIHAR', label: 'Patna, Bihar' },
           window: { label: '15 Sep 2026', starts_utc: '2026-09-15T18:30:00+00:00', ends_utc: '2026-09-16T18:30:00+00:00' },
           content_sha256: 'ab'.repeat(32), sources: ['S63'], status: 'ok',
           evidence: { sources: ['S63'], not_established: ['No all-clear is implied.'], notes: [] },
           delivery: 'local_only_no_delivery' };
}

const KEPT_ID = '11111111-2222-3333-4444-555555555555';
const view = { schema_version: 'briefcase-v1', delivery: 'local_only_no_delivery',
               note: 'Kept in the local store. Nothing is delivered, pushed or published from here.',
               briefs: [entry(KEPT_ID, 'Alert brief — PATNA, BIHAR')] };
const saved = { schema_version: 'briefcase-entry-v1', delivery: 'local_only_no_delivery', entry: view.briefs[0],
                markdown: '# Alert brief - PATNA, BIHAR\n\nKept body.' };

function workspaceToken(): () => void {
  const meta = document.createElement('meta');
  meta.setAttribute('name', 'workspace-token');
  meta.setAttribute('content', TOKEN);
  document.head.append(meta);
  return () => meta.remove();
}

describe('briefcase parity', () => {
  it('renders the kept brief with the time it was kept, the source it named and the no-delivery sentence the store returned', async () => {
    server.use(http.get('/api/briefs', () => HttpResponse.json(view)));
    mount(<BriefcaseSurface />);

    const table = within(await screen.findByTestId('briefcase-table'));
    expect(table.getByText(view.briefs[0].title)).toBeInTheDocument();
    /* The vanilla check printed the raw instant with the word Kept; this surface prints the IST stamp in its
       Saved column from the same recorded instant. */
    expect(table.getByText(istStamp(view.briefs[0].saved_at))).toBeInTheDocument();
    expect(table.getByText('S63')).toBeInTheDocument();

    expect(screen.getByTestId('briefcase-count')).toHaveTextContent('1 kept brief in this read');
    expect(screen.getByTestId('briefcase-count')).toHaveTextContent('local_only_no_delivery');
    expect(screen.getByTestId('briefcase-delivery-note')).toHaveTextContent(view.note);
    expect(screen.getByText(/an export is a file you keep, not a delivery/)).toBeInTheDocument();
    expect(screen.getByText(/is not a warning service and is not an all-clear/)).toBeInTheDocument();
  });

  it('reads an opened brief through the token-authenticated store route and shows the limits and hash stored with it', async () => {
    const cleanup = workspaceToken();
    const reads: { id: string | null; token: string | null }[] = [];
    try {
      server.use(
        http.get('/api/briefs', () => HttpResponse.json(view)),
        http.get('/api/briefs/get', ({ request }) => {
          reads.push({ id: new URL(request.url).searchParams.get('id'), token: request.headers.get('X-WeatherGPT-Token') });
          return HttpResponse.json(saved);
        }),
      );
      mount(<BriefcaseSurface />);
      await screen.findByTestId('briefcase-table');

      await userEvent.click(screen.getByRole('button', { name: 'Open ' + view.briefs[0].title }));
      const opened = await screen.findByTestId('briefcase-entry');

      expect(reads).toEqual([{ id: KEPT_ID, token: TOKEN }]);
      expect(within(opened).getByText('No all-clear is implied.')).toBeInTheDocument();
      expect(within(opened).getByText('sha256 abababababababab')).toBeInTheDocument();
      expect(within(opened).getByTestId('briefcase-markdown')).toHaveTextContent('Kept body.');
    } finally {
      cleanup();
    }
  });

  it('deletes only after a stated confirmation, names the brief, and re-reads the list rather than assuming', async () => {
    const deleted: unknown[] = [];
    let reads = 0;
    server.use(
      http.get('/api/briefs', () => { reads += 1; return HttpResponse.json(view); }),
      http.post('/api/briefs/delete', async ({ request }) => {
        deleted.push(await request.json());
        return HttpResponse.json({ deleted: KEPT_ID, detail: 'The kept brief was removed from the local store.' });
      }),
    );
    mount(<BriefcaseSurface />);
    await screen.findByTestId('briefcase-table');

    await userEvent.click(screen.getByRole('button', { name: 'Delete ' + view.briefs[0].title }));
    const confirm = await screen.findByTestId('briefcase-confirm');
    expect(confirm).toHaveTextContent(view.briefs[0].title);
    expect(confirm).toHaveTextContent('from this machine');

    await userEvent.click(within(confirm).getByRole('button', { name: 'Yes, remove it from the local store' }));
    await screen.findByTestId('briefcase-removed');

    expect(deleted).toEqual([{ id: KEPT_ID }]);
    await waitFor(() => expect(reads).toBe(2));
  });

  it('says nothing is kept when the store is empty, and invents no entry', async () => {
    const empty = { schema_version: 'briefcase-v1', delivery: 'local_only_no_delivery', note: 'Kept in the local store.', briefs: [] };
    server.use(http.get('/api/briefs', () => HttpResponse.json(empty)));
    mount(<BriefcaseSurface />);

    expect(await screen.findByTestId('briefcase-count')).toHaveTextContent('0 kept briefs in this read');
    expect(screen.queryByTestId('briefcase-table')).toBeNull();
    expect(screen.getByText(/no row returned for this table/)).toBeInTheDocument();
    expect(screen.queryByText(view.briefs[0].title)).toBeNull();
  });

  it('asks the server to compose a brief for a resolved point rather than posting a brief body itself', async () => {
    const composed: unknown[] = [];
    /* The vanilla check was a static string check, so it recorded no place-search row. This row is shaped like
       /api/places/search's own answer and states coordinates, which is what the compose control requires. */
    const placeRow = { label: 'Patna', latitude: 25.5941, longitude: 85.1376, admin1: 'Bihar', admin2: 'Patna',
                       selection_id: 'geonames:1260086' };
    server.use(
      http.get('/api/briefs', () => HttpResponse.json(view)),
      http.get('/api/places/search', () => HttpResponse.json({ schema_version: 'product-view-v1', view: 'places.search', status: 'ok',
                                                               data: { matches: [placeRow] }, sources: [], limitations: [], not_established: [] })),
      http.post('/api/briefs/save', async ({ request }) => {
        composed.push(await request.json());
        return HttpResponse.json({ entry: { title: 'Alert brief — PATNA, BIHAR' } });
      }),
    );
    mount(<BriefcaseSurface />);
    await screen.findByTestId('briefcase-table');

    await userEvent.type(screen.getByLabelText('Name a place'), 'Patna');
    await userEvent.click(await screen.findByRole('button', { name: /Patna · Patna, Bihar/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Compose and keep an alert brief for this point' }));
    await screen.findByTestId('briefcase-kept');

    expect(composed).toEqual([{ kind: 'alert_brief', lat: 25.5941, lon: 85.1376 }]);
    expect(Object.keys(composed[0] as Record<string, unknown>)).toEqual(['kind', 'lat', 'lon']);
    expect(screen.getByText(/No day is sent: the first published day is composed/)).toBeInTheDocument();
    expect(screen.getByTestId('briefcase-kept')).toHaveTextContent('Alert brief — PATNA, BIHAR');
  });
});
