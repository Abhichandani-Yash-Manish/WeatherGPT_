/* Loading shapes. The vanilla component check (tests/test_suite_ui.js, check 30) held that a read in
   progress reserves the shape of the answer it will occupy — three bars and a chart frame — that the
   skeleton carries no number, and that it never reads as a value. This spec holds the React rule for
   the Briefcase surface: while /api/briefs is unanswered the skeleton is on screen beside the sentence
   that says a read is in progress, and it is replaced by the payload when the read answers. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as BriefcaseSurface } from './BriefcaseSurface';

const briefsPayload = {
  schema_version: 'briefcase-v1',
  delivery: 'local_only_no_delivery',
  note: 'Kept in the local store. Nothing is delivered, pushed or published from here.',
  briefs: [{
    id: '11111111-2222-3333-4444-555555555555',
    saved_at: '2026-09-15T06:30:00+00:00',
    kind: 'alert_brief',
    title: 'Alert brief — PATNA, BIHAR',
    place: { district: 'PATNA', state: 'BIHAR', label: 'Patna, Bihar' },
    window: { label: '15 Sep 2026', starts_utc: '2026-09-15T18:30:00+00:00', ends_utc: '2026-09-16T18:30:00+00:00' },
    content_sha256: 'ab'.repeat(32),
    sources: ['S63'],
    status: 'ok',
    evidence: { sources: ['S63'], not_established: ['No all-clear is implied.'], notes: [] },
    delivery: 'local_only_no_delivery',
  }],
};

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

/* The route answers only when the test releases it, so the reading state is the state under test. */
function heldRead() {
  let open: () => void = () => {};
  const gate = new Promise<void>(resolve => {
    open = resolve;
  });
  server.use(http.get('/api/briefs', async () => {
    await gate;
    return HttpResponse.json(briefsPayload);
  }));
  return () => open();
}

describe('loading shapes', () => {
  /* The briefing section is a second read on this surface; it is not the one under test and it answers at once. */
  beforeEach(() => {
    server.use(http.get('/api/briefing/latest', () => HttpResponse.json({
      schema_version: 'briefing-latest-v1', present: false, directory: '/tmp/briefings',
      detail: 'No briefing has been written to this series directory yet.',
    })));
  });

  it('reserves the shape of a read in progress with an aria-hidden skeleton beside the sentence that says so', async () => {
    const release = heldRead();
    mount(<BriefcaseSurface />);

    expect(await screen.findByText('Reading kept-brief list from the local store…')).toBeInTheDocument();
    const skeleton = screen.getByTestId('skeleton');
    expect(skeleton).toHaveAttribute('aria-hidden', 'true');
    expect(skeleton.querySelectorAll('[data-skeleton="bar"]')).toHaveLength(3);
    expect(skeleton.querySelectorAll('[data-skeleton="frame"]')).toHaveLength(1);

    release();
    expect(await screen.findByTestId('briefcase-table')).toBeInTheDocument();
    expect(screen.queryByTestId('skeleton')).toBeNull();
  });

  it('carries no number, no label and no progress control, so nothing in it can be read as data or progress', async () => {
    const release = heldRead();
    mount(<BriefcaseSurface />);

    const skeleton = await screen.findByTestId('skeleton');
    expect(skeleton.textContent).toBe('');
    expect(skeleton.querySelector('[role="progressbar"]')).toBeNull();
    expect(skeleton.querySelector('progress')).toBeNull();
    expect(skeleton.querySelector('[aria-valuenow], [aria-valuemin], [aria-valuemax]')).toBeNull();
    expect(skeleton.querySelector('[class*="animate-"]')).toBeNull();

    release();
    await screen.findByTestId('briefcase-table');
  });
});
