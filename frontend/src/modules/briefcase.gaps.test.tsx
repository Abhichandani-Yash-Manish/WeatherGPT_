/* The two briefcase sub-rules the port ledger records as unclaimed (tests/test_briefcase_ui.js, one PASS
   bundling ten sub-rules): an export control over GET /api/briefs/export?id=, and the briefing series read
   from GET /api/briefing/latest with its own status and limits. The payload constants are copied from that
   vanilla suite (the entry factory, the kept-briefs view and the briefing record) so both suites read the
   same recorded shapes.

   Held here:
   - export reads the file route for that entry and hands the browser a Markdown file the reader keeps,
     and the surface states that nothing is delivered;
   - the briefing series renders its own status, run facts, identity, latencies, series rows, Markdown and
     the not-established lines written with it;
   - with no briefing written, the surface says the machine holds no briefing yet and names how one is
     written, rather than omitting the section;
   - a failed briefing read is stated as that failure, with a retry that re-reads it. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as BriefcaseSurface } from './BriefcaseSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const KEPT_ID = '11111111-2222-3333-4444-555555555555';

function entry(id: string, title: string) {
  return {
    id: id, saved_at: '2026-09-15T06:30:00+00:00', kind: 'alert_brief', title: title,
    place: { district: 'PATNA', state: 'BIHAR', label: 'Patna, Bihar' },
    window: { label: '15 Sep 2026', starts_utc: '2026-09-15T18:30:00+00:00', ends_utc: '2026-09-16T18:30:00+00:00' },
    content_sha256: 'ab'.repeat(32), sources: ['S63'], status: 'ok',
    evidence: { sources: ['S63'], not_established: ['No all-clear is implied.'], notes: [] },
    delivery: 'local_only_no_delivery',
  };
}

const view = {
  schema_version: 'briefcase-v1', delivery: 'local_only_no_delivery',
  note: 'Kept in the local store. Nothing is delivered, pushed or published from here.',
  briefs: [entry(KEPT_ID, 'Alert brief — PATNA, BIHAR')],
};

const MARKDOWN = '# Alert brief — PATNA, BIHAR\n\nKept body.\n';

/* Copied from the vanilla suite's recorded /api/briefing/latest payload. */
const briefingRecord = {
  schema_version: 'briefing-latest-v1', present: true, directory: '/tmp/briefings',
  note: 'This is a foreground run of a local prototype.',
  run: {
    generated_at_utc: '2026-09-15T05:00:28+00:00', briefing_id: 'f'.repeat(64), place_count: 2, day_number: 1, forecast_days: 3,
    sources: ['S06', 'S62', 'S63'], change: 'same', latency_seconds: 1.301, interval_seconds: 20,
    record_path: '/tmp/briefings/record-20260915T050028Z.json', markdown_path: '/tmp/briefings/briefing-20260915T050028Z.md',
  },
  briefing: { not_established: ['A quiet day in the district warning product is not an all-clear.'] },
  markdown: '# Briefing — Ahmedabad\n',
  series: [
    { run: 1, generated_at_utc: '2026-09-15T05:00:08+00:00', place_count: 2, latency_seconds: 1.4, change: 'no_previous_run' },
    { run: 2, generated_at_utc: '2026-09-15T05:00:28+00:00', place_count: 2, latency_seconds: 1.301, change: 'same' },
  ],
};

const absentBriefing = {
  schema_version: 'briefing-latest-v1', present: false, directory: '/tmp/briefings',
  note: 'This is a foreground run of a local prototype.',
  detail: 'Nothing is delivered, pushed or scheduled by the workspace itself. No briefing has been written to this series '
        + 'directory yet: write one with python3 scripts/briefing.py --place "<place>" --out /tmp/briefings.',
  run: null, briefing: null, markdown: null, series: [],
};

/* The export is a browser download, so the object URL and the anchor click are what the page did; both
   are held here and the Blob the page handed over is read back. */
function captureDownloads() {
  const blobs: Blob[] = [];
  const names: string[] = [];
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, writable: true, value: (blob: Blob) => {
    blobs.push(blob);
    return 'blob:recorded-export';
  } });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, writable: true, value: () => {} });
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
    names.push(this.download);
  });
  return {
    blobs: blobs,
    names: names,
    restore: () => {
      click.mockRestore();
      delete (URL as { createObjectURL?: unknown }).createObjectURL;
      delete (URL as { revokeObjectURL?: unknown }).revokeObjectURL;
    },
  };
}

/* The Blob the page handed to the browser is read back through the reader the browser itself has. */
function blobText(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}

describe('the briefcase export and briefing series', () => {
  it('offers a download control that reads the export file route for the entry and says the file is kept, not delivered', async () => {
    const requested: string[] = [];
    server.use(
      http.get('/api/briefs', () => HttpResponse.json(view)),
      http.get('/api/briefs/export', ({ request }) => {
        requested.push(request.url);
        return HttpResponse.text(MARKDOWN, { headers: { 'Content-Type': 'text/markdown; charset=utf-8' } });
      }),
      http.get('/api/briefing/latest', () => HttpResponse.json(absentBriefing)),
    );
    const downloads = captureDownloads();
    mount(<BriefcaseSurface />);
    await screen.findByTestId('briefcase-table');

    await userEvent.click(screen.getByRole('button', { name: 'Export Alert brief — PATNA, BIHAR' }));

    const status = await screen.findByTestId('briefcase-export');
    expect(requested).toHaveLength(1);
    expect(new URL(requested[0]).pathname).toBe('/api/briefs/export');
    expect(new URL(requested[0]).searchParams.get('id')).toBe(KEPT_ID);
    expect(downloads.names).toEqual(['alert-brief-patna-bihar-11111111.md']);
    expect(downloads.blobs[0].type).toContain('text/markdown');
    expect(await blobText(downloads.blobs[0])).toBe(MARKDOWN);
    expect(status).toHaveTextContent('a Markdown file you keep on this machine');
    expect(status).toHaveTextContent('Nothing was delivered, pushed or published');
    expect(screen.getByTestId('briefcase-export-note')).toHaveTextContent('nothing is delivered, pushed or published by it');
    downloads.restore();
  });

  it('renders the briefing series from the latest-briefing read with its own status, run facts, series, limits and Markdown', async () => {
    server.use(
      http.get('/api/briefs', () => HttpResponse.json(view)),
      http.get('/api/briefing/latest', () => HttpResponse.json(briefingRecord)),
    );
    mount(<BriefcaseSurface />);

    const section = within(await screen.findByTestId('briefing-latest'));
    expect(section.getByRole('heading', { level: 2, name: 'Latest briefing on this machine' })).toBeInTheDocument();
    expect(section.getByTestId('briefing-status')).toHaveTextContent('present: yes');
    expect(section.getByTestId('briefing-status')).toHaveTextContent('/tmp/briefings');
    expect(section.getByText(/This is a foreground run of a local prototype/)).toBeInTheDocument();

    const run = within(section.getByTestId('briefing-run'));
    expect(run.getByText('2 place(s)')).toBeInTheDocument();
    expect(run.getByText('1.301 s')).toBeInTheDocument();
    expect(run.getByText('sha256 ffffffffffffffff')).toBeInTheDocument();
    expect(run.getByText('day 1 of the published product')).toBeInTheDocument();
    expect(run.getByText('S06, S62, S63')).toBeInTheDocument();

    const series = within(section.getByTestId('briefing-series'));
    expect(series.getByText('run 1')).toBeInTheDocument();
    expect(series.getByText('run 2')).toBeInTheDocument();
    expect(series.getByText('no_previous_run')).toBeInTheDocument();

    expect(section.getByTestId('briefing-markdown')).toHaveTextContent('# Briefing — Ahmedabad');
    expect(section.getByText('A quiet day in the district warning product is not an all-clear.')).toBeInTheDocument();
  });

  it('states that this machine holds no briefing yet, and names how one is written, rather than omitting the section', async () => {
    server.use(
      http.get('/api/briefs', () => HttpResponse.json(view)),
      http.get('/api/briefing/latest', () => HttpResponse.json(absentBriefing)),
    );
    mount(<BriefcaseSurface />);

    const section = within(await screen.findByTestId('briefing-latest'));
    const absent = section.getByTestId('briefing-absent');
    expect(section.getByTestId('briefing-status')).toHaveTextContent('present: no');
    expect(absent).toHaveTextContent('This machine holds no briefing yet');
    expect(absent).toHaveTextContent('Nothing has been scheduled or delivered.');
    expect(absent).toHaveTextContent('scripts/briefing.py');
    expect(section.queryByTestId('briefing-run')).toBeNull();
    expect(section.queryByTestId('briefing-markdown')).toBeNull();
  });

  it('states a failed briefing read as that failure, with a retry that re-reads it', async () => {
    let reads = 0;
    server.use(
      http.get('/api/briefs', () => HttpResponse.json(view)),
      http.get('/api/briefing/latest', () => {
        reads += 1;
        if (reads === 1) return HttpResponse.json({ error: 'the briefing series directory could not be read' }, { status: 503 });
        return HttpResponse.json(absentBriefing);
      }),
    );
    mount(<BriefcaseSurface />);

    const section = await screen.findByTestId('briefing-latest');
    const failure = await within(section).findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the briefing series directory could not be read');
    await userEvent.click(within(failure).getByRole('button', { name: 'Retry this read' }));

    expect(await within(section).findByTestId('briefing-absent')).toBeInTheDocument();
    expect(reads).toBe(2);
  });
});
