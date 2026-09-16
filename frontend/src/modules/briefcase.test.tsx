/* The Briefcase surface, checked against payloads shaped like the recorded ones in
   research/implementation/personas-briefcase-20260915/. The checks assert what the surface may not lose: the
   payload's entries and counts, its own delivery sentence, an absence rendered as an absence, the surface's
   local-only statement, a keep request that asks the server to compose, a removal confirmed in words, and a
   failed read stated as that failure. */
import axe from 'axe-core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { istStamp, istWindow } from '../lib/time';
import { Surface as BriefcaseSurface, intents } from './BriefcaseSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const ALERT_ID = 'af94cba1-4bae-4301-b6c6-ecde8fed8e4d';
const ADVISORY_ID = '236e9faa-06ee-4bba-b12b-8069996d9003';
const NOTE = 'Kept in the local store. Nothing is delivered, pushed or published from here; an export is a file you keep.';
const LIMIT = 'This is district-level guidance from one published product. It is not point-level, not a flood or cyclone warning, and not an all-clear.';

const alertEntry = {
  id: ALERT_ID,
  saved_at: '2026-09-15T04:47:02+00:00',
  kind: 'alert_brief',
  title: 'Alert brief — AHMADABAD, GUJARAT',
  place: { district: 'AHMADABAD', state: 'GUJARAT', label: 'AHMADABAD', latitude: null, longitude: null },
  window: { starts_utc: '2026-09-13T18:30:00+00:00', ends_utc: '2026-09-14T18:30:00+00:00', label: '14 Sep 2026', day: 1 },
  content_sha256: 'a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90',
  sources: ['S63', 'S06'],
  status: 'ok',
  delivery: 'local_only_no_delivery',
  evidence: { sources: ['S63', 'S06'], not_established: [LIMIT], why: null, notes: [] },
};

const advisoryEntry = {
  id: ADVISORY_ID,
  saved_at: '2026-09-15T04:47:06+00:00',
  kind: 'advisory_brief',
  title: 'Advisory brief — cotton · squaring · Ahmedabad',
  place: { district: 'Ahmedabad', state: 'Gujarat', label: 'Ahmedabad' },
  window: { label: { days: 1, first_valid: '2026-09-15T00:00:00+00:00', last_valid: '2026-09-15T23:00:00+00:00' },
            day: null, starts_utc: null, ends_utc: null },
  content_sha256: '64ff118087298b81cbb0755675736258836dcd4925ecf05f60c63ea99a38b136',
  sources: ['S57'],
  status: 'ok',
  delivery: 'local_only_no_delivery',
  evidence: { sources: ['S57'], not_established: ['This is published district-level advice for the printed issue date shown, not a prescription for a field.'],
              why: null, notes: [] },
};

const briefsPayload = {
  schema_version: 'briefcase-v1',
  delivery: 'local_only_no_delivery',
  note: NOTE,
  briefs: [alertEntry, advisoryEntry],
};

/* /api/briefs/get returns the stored entry without the list's status field: its absence is rendered. */
const storedAlertEntry = { ...alertEntry, status: undefined };

const MARKDOWN = '# Alert brief - AHMADABAD, GUJARAT\n\n- Day: Day 1 (day 1 of the published product)\n';

const placeRow = {
  label: 'AHMADABAD',
  latitude: 23.02579,
  longitude: 72.58727,
  admin1: 'Gujarat',
  admin2: 'Ahmadabad',
  selection_id: 'geonames:1279233',
};

function placesPayload() {
  return { schema_version: 'product-view-v1', view: 'places.search', status: 'ok', data: { matches: [placeRow] },
           sources: [], limitations: [], not_established: [] };
}

async function nameAHMADABAD() {
  await userEvent.type(screen.getByLabelText('Name a place'), 'AHMADABAD');
  await userEvent.click(await screen.findByRole('button', { name: /AHMADABAD · Ahmadabad, Gujarat/ }));
}

describe('the Briefcase surface', () => {
  it('renders the kept entries, the count, the payload delivery sentence and its own local-only limits', async () => {
    server.use(http.get('/api/briefs', () => HttpResponse.json(briefsPayload)));
    const { container } = mount(<BriefcaseSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Briefcase' })).toBeInTheDocument();
    expect(await screen.findByTestId('briefcase-count')).toHaveTextContent('2 kept briefs in this read');
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByTestId('briefcase-count')).toHaveTextContent('local_only_no_delivery');
    expect(screen.getByTestId('briefcase-delivery-note')).toHaveTextContent(NOTE);

    const table = within(screen.getByTestId('briefcase-table'));
    expect(table.getByText('Alert brief — AHMADABAD, GUJARAT')).toBeInTheDocument();
    expect(table.getByText('AHMADABAD, GUJARAT')).toBeInTheDocument();
    expect(table.getByText('14 Sep 2026 · day 1')).toBeInTheDocument();
    // Both entries were kept in the same IST minute: the saved instant is rendered for each row.
    expect(table.getAllByText(istStamp(alertEntry.saved_at))).toHaveLength(2);
    expect(table.getByText('S63, S06')).toBeInTheDocument();
    expect(table.getByText('Advisory brief — cotton · squaring · Ahmedabad')).toBeInTheDocument();
    expect(table.getByText(istWindow('2026-09-15T00:00:00+00:00', '2026-09-15T23:00:00+00:00'))).toBeInTheDocument();
    expect(table.getByText('S57')).toBeInTheDocument();

    // The read's own envelope attached no coverage count and no source row: both are stated as absent.
    expect(screen.getByText('This read returned no coverage count.')).toBeInTheDocument();
    expect(screen.getByText('No source row came back with this read.')).toBeInTheDocument();
    expect(screen.getByText(/The briefcase is not a warning service and is not an all-clear/)).toBeInTheDocument();
    expect(intents).toContain('Save this answer to the briefcase.');
    // The rendered surface carries no axe violation (colour contrast needs a layout engine and is not measurable here).
    const scan = await axe.run(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(scan.violations.map(violation => violation.id).join(', ')).toBe('');
  });

  it('opens one kept brief in full and states the fields the entry did not record', async () => {
    server.use(
      http.get('/api/briefs', () => HttpResponse.json(briefsPayload)),
      http.get('/api/briefs/get', ({ request }) => {
        expect(new URL(request.url).searchParams.get('id')).toBe(ALERT_ID);
        return HttpResponse.json({ schema_version: 'briefcase-entry-v1', delivery: 'local_only_no_delivery',
                                   entry: storedAlertEntry, markdown: MARKDOWN });
      }),
    );
    mount(<BriefcaseSurface />);
    await screen.findByTestId('briefcase-table');

    await userEvent.click(screen.getByRole('button', { name: 'Open Alert brief — AHMADABAD, GUJARAT' }));
    const opened = await screen.findByTestId('briefcase-entry');

    expect(within(opened).getByRole('heading', { level: 3, name: 'Alert brief — AHMADABAD, GUJARAT' })).toBeInTheDocument();
    const facts = within(within(opened).getByTestId('briefcase-entry-facts'));
    expect(facts.getByText('status not recorded in this entry')).toBeInTheDocument();
    expect(facts.getByText('coordinates not recorded in this entry')).toBeInTheDocument();
    expect(facts.getByText('sha256 a1b2c3d4e5f60718')).toBeInTheDocument();

    const sources = within(within(opened).getByTestId('briefcase-entry-sources'));
    expect(sources.getByRole('rowheader', { name: 'S63' })).toBeInTheDocument();
    expect(sources.getByRole('rowheader', { name: 'S06' })).toBeInTheDocument();
    expect(sources.getAllByText('not recorded')).toHaveLength(6);
    expect(within(opened).getByText(LIMIT)).toBeInTheDocument();
    expect(within(opened).getByText('This entry carries no note line.')).toBeInTheDocument();
    expect(within(opened).getByTestId('briefcase-markdown')).toHaveTextContent('# Alert brief - AHMADABAD, GUJARAT');
    expect(within(opened).getByText(/The export route returns this same Markdown as a file you keep/)).toBeInTheDocument();
  });

  it('asks the server to compose an alert brief for a resolved point, and cannot post a brief itself', async () => {
    let kept: unknown;
    server.use(
      http.get('/api/briefs', () => HttpResponse.json(briefsPayload)),
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.post('/api/briefs/save', async ({ request }) => {
        kept = await request.json();
        return HttpResponse.json({ schema_version: 'briefcase-entry-v1', delivery: 'local_only_no_delivery',
                                   entry: alertEntry, saved: true,
                                   detail: 'The brief was composed from its sources and kept in the local store; nothing was delivered.' });
      }),
    );
    mount(<BriefcaseSurface />);
    await screen.findByTestId('briefcase-table');
    expect(screen.getByText(/No point is resolved yet, so no compose control is offered/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Compose and keep an alert brief for this point' })).toBeNull();

    await nameAHMADABAD();
    expect(screen.getByTestId('briefcase-point')).toHaveTextContent('23.02579, 72.58727');
    await userEvent.click(screen.getByRole('button', { name: 'Compose and keep an alert brief for this point' }));

    expect(kept).toEqual({ kind: 'alert_brief', lat: 23.02579, lon: 72.58727 });
    const result = await screen.findByTestId('briefcase-kept');
    expect(result).toHaveTextContent('The brief was composed from its sources and kept in the local store; nothing was delivered.');
    expect(result).toHaveTextContent('Alert brief — AHMADABAD, GUJARAT');
  });

  it('confirms a removal in words and then states what was removed', async () => {
    let deleted: unknown;
    server.use(
      http.get('/api/briefs', () => HttpResponse.json(briefsPayload)),
      http.post('/api/briefs/delete', async ({ request }) => {
        deleted = await request.json();
        return HttpResponse.json({ deleted: ALERT_ID, briefs: [advisoryEntry],
                                   detail: 'The kept brief was removed from the local store. Nothing was delivered from it.' });
      }),
    );
    mount(<BriefcaseSurface />);
    await screen.findByTestId('briefcase-table');

    await userEvent.click(screen.getByRole('button', { name: 'Delete Alert brief — AHMADABAD, GUJARAT' }));
    const confirm = await screen.findByTestId('briefcase-confirm');
    expect(confirm).toHaveTextContent('Remove “Alert brief — AHMADABAD, GUJARAT” from this machine\'s local store?');
    await userEvent.click(within(confirm).getByRole('button', { name: 'Keep it' }));
    expect(screen.queryByTestId('briefcase-confirm')).toBeNull();
    expect(deleted).toBeUndefined();

    await userEvent.click(screen.getByRole('button', { name: 'Delete Alert brief — AHMADABAD, GUJARAT' }));
    await userEvent.click(screen.getByRole('button', { name: 'Yes, remove it from the local store' }));

    expect(deleted).toEqual({ id: ALERT_ID });
    const removed = await screen.findByTestId('briefcase-removed');
    expect(removed).toHaveTextContent('Removed “Alert brief — AHMADABAD, GUJARAT”');
    expect(removed).toHaveTextContent('The kept brief was removed from the local store. Nothing was delivered from it.');
  });

  it('states a failed read as that failure, and the retry re-reads it', async () => {
    let calls = 0;
    server.use(http.get('/api/briefs', () => {
      calls += 1;
      if (calls === 1) return HttpResponse.json({ error: 'the briefcase store could not be opened' }, { status: 503 });
      return HttpResponse.json(briefsPayload);
    }));
    mount(<BriefcaseSurface />);

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the briefcase store could not be opened');
    await userEvent.click(within(failure).getByRole('button', { name: 'Retry this read' }));

    expect(await screen.findByTestId('briefcase-table')).toBeInTheDocument();
    expect(screen.getByTestId('briefcase-count')).toHaveTextContent('2 kept briefs in this read');
  });
});
