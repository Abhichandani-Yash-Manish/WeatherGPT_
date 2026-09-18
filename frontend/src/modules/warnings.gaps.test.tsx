/* The warnings-surface gaps the port ledger names from tests/test_suite_ui.js: a chosen district-day
   opens its own detail (the hazard wording, its validity window, the source id and the bulletin it came
   from), the CAP relay is assessed in its own block and never merged with the district product, and the
   alert brief is composed for a named point only when asked. Each check reads the payload the route
   returns; the district detail reads the national payload the surface already holds. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as WarningsSurface } from './WarningsSurface';

function envelope(view: string, status: string, data: unknown, extra: Record<string, unknown> = {}) {
  return Object.assign(
    {
      schema_version: 'product-view-v1',
      generated_at_utc: '2026-09-14T18:00:00+00:00',
      view: view,
      status: status,
      data: data,
      sources: [],
      coverage: {},
      limitations: ['A stated limit of this view.'],
      not_established: ['Something not established here.'],
    },
    extra,
  );
}

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <WarningsSurface />
    </QueryClientProvider>,
  );
}

const DAYS = [
  {
    day: 1,
    label: '14 Sep 2026',
    date_utc: '2026-09-14',
    date_local: '2026-09-14',
    starts_utc: '2026-09-13T18:30:00+00:00',
    ends_utc: '2026-09-14T18:30:00+00:00',
    colour: 'green',
    colour_code: 1,
    hazard_codes: [1],
    hazards: ['No warning in this product'],
    source_text: null,
    unknown_hazard_codes: [],
    quiet: true,
  },
  {
    day: 2,
    label: '15 Sep 2026',
    date_utc: '2026-09-15',
    date_local: '2026-09-15',
    starts_utc: '2026-09-14T18:30:00+00:00',
    ends_utc: '2026-09-15T18:30:00+00:00',
    colour: 'yellow',
    colour_code: 3,
    hazard_codes: [4],
    hazards: ['Thunderstorm/lightning/squall'],
    source_text: null,
    unknown_hazard_codes: [],
    quiet: false,
  },
];

const NATIONAL = envelope(
  'warnings.national',
  'ok',
  {
    districts: [
      {
        key: 'PATNA',
        district: 'PATNA',
        state: 'BIHAR',
        bulletin_date: '2026-09-14',
        issued_at_utc: '2026-09-14T06:00:00+00:00',
        updated_at: '2026-09-14T12:35:18Z',
        days: DAYS,
      },
    ],
    tally: { yellow: 1 },
    skipped: [{ obj_id: 9, reason: 'no district name' }],
    basemap_build: 'basemap-v1-test',
  },
  {
    sources: [
      {
        source_id: 'S63',
        product: 'IMD district warning product',
        layer: 'imd:district_warnings_india',
        retrieved_at_utc: '2026-09-14T12:40:00+00:00',
        sha256_prefix: 'abc123',
      },
    ],
    coverage: { features_returned: 764, districts_listed: 1, skipped_without_a_name: 1, basemap_districts: 756 },
  },
);

const CAP = envelope(
  'warnings.cap',
  'ok',
  {
    messages: 9,
    eligible_by_lifecycle: 0,
    latest_sent: '2026-09-09T07:24:34+00:00',
    delivery: 'reference_only_no_delivery',
    records: [
      {
        identifier: 'cap-1',
        sender: 'imd-nwfc',
        sent: '2026-09-09T07:24:34+00:00',
        status: 'Actual',
        msg_type: 'Alert',
        event: 'Rainfall',
        severity: 'Moderate',
        certainty: 'Likely',
        urgency: 'Expected',
        onset: '2026-09-09T08:00:00+00:00',
        expires: '2026-09-10T08:00:00+00:00',
      },
    ],
  },
  {
    sources: [{ source_id: 'S06', product: 'IMD CAP relay', retrieved_at_utc: '2026-09-14T18:00:00+00:00' }],
    coverage: { messages: 9 },
    limitations: [
      'The relay reports rainfall alerts produced by the National Weather Forecasting Centre; it is not the whole national warning picture.',
      'CAP geographic applicability to a place is not computed here and is not established.',
      'An empty eligible set is not an all-clear: a reachable feed is not evidence that nothing is in force.',
    ],
    not_established: ['Origin authentication of the relay is not established, so this is a source assessment and not an alert.'],
  },
);

const PLACES = envelope('places.search', 'ok', {
  matches: [
    {
      label: 'Patna, BIHAR',
      name: 'Patna',
      source_id: 'geonames',
      kind: 'city',
      admin2: 'Patna',
      admin1: 'BIHAR',
      coordinates: { latitude: 25.5941, longitude: 85.1376 },
    },
  ],
});

const BRIEF = envelope(
  'warnings.alert_brief',
  'ok',
  {
    status: 'ok',
    place: { district: 'PATNA', state: 'BIHAR' },
    day: { day: 2, label: '15 Sep 2026', starts_utc: '2026-09-14T18:30:00+00:00', ends_utc: '2026-09-15T18:30:00+00:00' },
    status_line: 'Official district warning: yellow - Thunderstorm/lightning/squall',
    day_status: {
      colour: 'yellow',
      colour_code: 3,
      hazards: ['Thunderstorm/lightning/squall'],
      quiet: false,
      official_wording: null,
      wording_note: 'the product states a colour and hazard codes for this district-day and no free-text wording is recorded',
    },
    issuer: {
      source_id: 'S63',
      product: 'IMD district warning product',
      layer: 'imd:district_warnings_india',
      issued_at_utc: '2026-09-15T00:00:00+00:00',
      retrieved_at_utc: '2026-09-15T04:11:36+00:00',
      source_locator: '$.features[605]',
    },
    relay: {
      source_id: 'S06',
      messages: 9,
      eligible_by_lifecycle: 0,
      latest_sent: '2026-09-09T07:24:34+00:00',
      note: 'reported separately and never merged with the district guidance; a reachable relay is not evidence that nothing is in force',
    },
    what_would_change_this: ['A newer bulletin of the same product replaces these day rows.'],
    not_established: [
      'This is district-level guidance from one published product. It is not point-level, not a flood or cyclone warning, and not an all-clear.',
    ],
    brief_id: '34b32c8d335658f0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718',
  },
  { limitations: ['Day windows are derived from the bulletin date.'] },
);

async function openPatna() {
  const table = within(await screen.findByTestId('warnings-table'));
  await userEvent.click(table.getAllByRole('button', { name: 'PATNA' })[0]);
  return screen.getByTestId('warnings-district');
}

/* The point step both brief checks share: name a place and choose the row the search returned. */
async function namePoint() {
  await screen.findByTestId('warnings-table');
  await userEvent.type(screen.getByLabelText('Name a place'), 'Patna');
  await userEvent.click(await screen.findByRole('button', { name: /25\.5941, 85\.1376/ }));
}

describe('the district-day detail', () => {
  it('opens a chosen district-day detail with the published hazard wording, its validity window, the source id and the bulletin it came from', async () => {
    server.use(http.get('/api/warnings/national', () => HttpResponse.json(NATIONAL)));
    const seen: string[] = [];
    const passthrough = globalThis.fetch;
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      seen.push(String(input));
      return passthrough(input, init);
    });
    try {
      mount();
      const detail = await openPatna();

      expect(detail).toHaveTextContent('District detail · PATNA, BIHAR');
      expect(detail).toHaveTextContent('Opened from 14 Sep 2026 · 2026-09-14');
      // The wording the product published for that district-day.
      expect(detail).toHaveTextContent('Thunderstorm/lightning/squall');
      // The validity window as the row returned it, in IST.
      expect(detail).toHaveTextContent('15 Sep 2026, 00:00-16 Sep 2026, 00:00 IST');
      // The source id and the bulletin the rows came from.
      expect(detail).toHaveTextContent('S63');
      expect(detail).toHaveTextContent('IMD district warning product');
      expect(detail).toHaveTextContent('2026-09-14');
      expect(detail).toHaveTextContent('IST calendar day');
      // The detail reads the national payload already held: one product read, and no place lookup.
      expect(seen.filter(path => path.includes('/api/warnings/place'))).toHaveLength(0);
      expect(seen.filter(path => path.includes('/api/warnings/national'))).toHaveLength(1);
    } finally {
      spy.mockRestore();
    }
  });
});

describe('the CAP relay block', () => {
  it('keeps the CAP relay assessment in its own block, separate from the printed product, and says CAP reference resolution alone never authorises dissemination', async () => {
    server.use(
      http.get('/api/warnings/national', () => HttpResponse.json(NATIONAL)),
      http.get('/api/warnings/cap', () => HttpResponse.json(CAP)),
    );
    mount();
    const detail = await openPatna();
    const cap = screen.getByTestId('warnings-cap');

    // The standing rule and the separation from the district product are stated before any read.
    expect(cap).toHaveTextContent('never merged with the district guidance');
    expect(cap).toHaveTextContent('CAP reference resolution alone never authorises dissemination.');
    expect(cap).not.toHaveTextContent('Thunderstorm/lightning/squall');
    expect(detail).not.toHaveTextContent('CAP relay');

    await userEvent.click(within(cap).getByRole('button', { name: 'Read the CAP relay assessment' }));
    const records = await within(cap).findByTestId('warnings-cap-records');
    expect(records).toHaveTextContent('Rainfall');
    expect(records).toHaveTextContent('Actual');
    expect(within(cap).getByTestId('warnings-cap-facts')).toHaveTextContent('9');
    expect(cap).toHaveTextContent('An empty eligible set is not an all-clear');
    // Reading the relay added nothing to the district product's block.
    expect(detail).not.toHaveTextContent('Rainfall');
  });
});

describe('the alert brief', () => {
  it("composes the brief for the point that was named, with the payload's own status and wording, and says it is not a warning anyone else receives", async () => {
    let askedUrl = '';
    server.use(
      http.get('/api/warnings/national', () => HttpResponse.json(NATIONAL)),
      http.get('/api/places/search', () => HttpResponse.json(PLACES)),
      http.get('/api/warnings/alert-brief', ({ request }) => {
        askedUrl = new URL(request.url).search;
        return HttpResponse.json(BRIEF);
      }),
    );
    mount();
    await namePoint();
    await userEvent.selectOptions(screen.getByLabelText('Published day to compose'), '2');
    await userEvent.click(screen.getByRole('button', { name: 'Write the alert brief' }));

    const block = await screen.findByTestId('warnings-brief');
    // The route is asked for the point that was resolved, with the day the reader chose.
    expect(askedUrl).toBe('?lat=25.5941&lon=85.1376&day=2');
    expect(block).toHaveTextContent('Official district warning: yellow - Thunderstorm/lightning/squall');
    expect(block).toHaveTextContent('Composed for the point that was resolved to PATNA, BIHAR');
    expect(block).toHaveTextContent('It is not a warning anyone else receives');
    expect(block).toHaveTextContent('S63');
    expect(block).toHaveTextContent('S06');
    expect(block).toHaveTextContent('reported separately and never merged with the district guidance');
    expect(block).toHaveTextContent('This is district-level guidance from one published product.');
    expect(block).toHaveTextContent('34b32c8d3356');
  });

  it('leaves the day out of the brief request when the first published day is left to the product', async () => {
    let askedUrl = '';
    server.use(
      http.get('/api/warnings/national', () => HttpResponse.json(NATIONAL)),
      http.get('/api/places/search', () => HttpResponse.json(PLACES)),
      http.get('/api/warnings/alert-brief', ({ request }) => {
        askedUrl = new URL(request.url).search;
        return HttpResponse.json(BRIEF);
      }),
    );
    mount();
    await namePoint();
    await userEvent.click(screen.getByRole('button', { name: 'Write the alert brief' }));

    await screen.findByTestId('warnings-brief');
    expect(askedUrl).toBe('?lat=25.5941&lon=85.1376');
  });

  it("states a failed alert-brief read as the server's sentence, with a retry", async () => {
    server.use(
      http.get('/api/warnings/national', () => HttpResponse.json(NATIONAL)),
      http.get('/api/places/search', () => HttpResponse.json(PLACES)),
      http.get('/api/warnings/alert-brief', () =>
        HttpResponse.json({ error: 'the warning store is unavailable' }, { status: 503 }),
      ),
    );
    mount();
    await namePoint();
    await userEvent.click(screen.getByRole('button', { name: 'Write the alert brief' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('the warning store is unavailable');
    expect(within(alert).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
  });

  /* The two wording defects the audit of 17 September 2026 found in this surface: the summary
     described rows as "matching this filter" when no filter was set, and a printed ISO date wrapped
     inside its column ('2026-' / '09-11'). */
  it('describes the row count honestly with no filter set, and keeps a printed date on one line', async () => {
    server.use(http.get('/api/warnings/national', () => HttpResponse.json(NATIONAL)));
    mount();

    const summary = await screen.findByTestId('warnings-count');
    expect(summary).toHaveTextContent('2 district-day rows this read returned');
    expect(summary).not.toHaveTextContent('matching this filter');

    const table = await screen.findByTestId('warnings-bulletins');
    const date = within(table).getByText('2026-09-14');
    expect(date.className).toMatch(/whitespace-nowrap/);

    await userEvent.type(screen.getByLabelText('District name contains'), 'Patna');
    expect(screen.getByTestId('warnings-count')).toHaveTextContent('matching this filter');
  });

  it('states which districts are behind the newest edition this read held', async () => {
    const aged = envelope('warnings.national', 'ok', {
      districts: [
        {
          key: 'YANAM', district: 'YANAM', state: 'PUDUCHERRY',
          bulletin_date: '2023-11-05', issued_at_utc: '2023-11-05T06:00:00+00:00',
          bulletin_age_days: 1047, bulletin_behind_the_newest_read_days: 1040,
          bulletin_is_older_than_this_read: true, days: DAYS,
        },
      ],
      tally: { yellow: 1 },
      skipped: [],
      newest_bulletin_date_in_this_read: '2026-09-15',
      districts_behind_the_newest_edition: 1,
      oldest_bulletin_age_days: 1047,
      oldest_edition_examples: [{ district: 'YANAM', state: 'PUDUCHERRY', bulletin_date: '2023-11-05', bulletin_age_days: 1047, days_behind_the_newest_edition: 1040 }],
    });
    server.use(http.get('/api/warnings/national', () => HttpResponse.json(aged)));
    mount();

    const note = await screen.findByTestId('warnings-bulletin-age');
    expect(note).toHaveTextContent('carry an edition older than the newest edition of this read');
    expect(note).toHaveTextContent('2026-09-15');
    expect(note).toHaveTextContent('the oldest 1047 days before this read');
    expect(note).toHaveTextContent('still the official product for the days it covers');

    const table = await screen.findByTestId('warnings-bulletins');
    expect(within(table).getByText(/1047 days/)).toHaveTextContent('1040 days behind the newest edition in this read');
  });

  it('does not call a recent edition stale when it is the newest this read held', async () => {
    // 17 September 2026 measured 755 of 756 districts on the 15 September edition, which is this
    // product's current read: its own Day fields cover today.
    server.use(http.get('/api/warnings/national', () => HttpResponse.json(NATIONAL)));
    mount();
    const note = await screen.findByTestId('warnings-bulletin-age');
    expect(note).not.toHaveTextContent('older than the newest');
    expect(note).not.toHaveTextContent('days before this read');
  });
});
