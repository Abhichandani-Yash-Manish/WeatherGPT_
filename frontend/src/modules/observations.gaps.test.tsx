/* The two workspace-surface checks the port ledger names from tests/test_workspace_ui.js, held against
   payloads shaped like the recorded ones:

   - check 1  the district-day rows keep published hazards, missing dates, expired days and explicit quiet
              distinct: the product's own quiet sentence belongs to a day the payload marked quiet, and it
              is never printed for a day whose quiet flag was not returned or whose window has closed;
   - check 2  a network-shaped station read keeps each station's own identity, instant, distance and
              freshness, a reported zero as 0 (the payload carries value 0, not an absent field), and a
              unit the read did not state as 'unit not stated', never borrowed from the row beside it.

   Both rules were genuinely not rendered before this batch: the station table printed no reported values
   at all, so a zero and an unstated unit had nowhere to appear, and the warning table printed no state for
   a day, so a past day, a quiet day and a day whose quiet flag was absent read alike. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as ObservationsSurface } from './ObservationsSurface';
import { Surface as WarningsSurface } from './WarningsSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

function envelope(view: string, status: string, data: unknown, extra: Record<string, unknown> = {}) {
  return Object.assign(
    {
      schema_version: 'product-view-v1',
      generated_at_utc: '2026-09-15T12:00:00+00:00',
      view: view,
      status: status,
      data: data,
      sources: [],
      coverage: {},
      limitations: [],
      not_established: [],
    },
    extra,
  );
}

const WARNINGS = envelope('warnings.national', 'ok', {
  districts: [
    {
      key: 'patna',
      district: 'PATNA',
      state: 'BIHAR',
      bulletin_date: '2026-09-15',
      issued_at_utc: '2026-09-15T06:00:00+00:00',
      updated_at: '2026-09-15T09:00:00+00:00',
      days: [
        /* A published hazard, dated. */
        { day: 1, label: '15 Sep 2026', date_local: '2026-09-15', is_today: true, is_past: false, quiet: false,
          colour: 'yellow', colour_code: 3, hazard_codes: [4], hazards: ['Thunderstorm/lightning/squall'] },
        /* No date fields and no quiet flag at all: the date is absent and the quiet state is unstated. */
        { day: 2, colour: null, colour_code: null, hazard_codes: [], hazards: [] },
        /* An expired day the product marked quiet: the published window has closed. */
        { day: 3, label: '13 Sep 2026', date_local: '2026-09-13', is_today: false, is_past: true, quiet: true,
          colour: null, colour_code: null, hazard_codes: [], hazards: [] },
        /* An explicitly quiet day. */
        { day: 4, label: '16 Sep 2026', date_local: '2026-09-16', is_today: false, is_past: false, quiet: true,
          colour: 'green', colour_code: 1, hazard_codes: [1], hazards: ['No warning in this product'] },
      ],
    },
    /* A district row with no day row stays listed and is never read as a quiet day. */
    { key: 'kolkata', district: 'KOLKATA', state: 'WEST BENGAL', bulletin_date: '2026-09-15',
      issued_at_utc: '2026-09-15T06:00:00+00:00', updated_at: null, days: [] },
  ],
  tally: { yellow: 1, green: 1 },
  skipped: [],
});

const PLACES = envelope('places.search', 'ok', {
  matches: [
    { label: 'Patna, BIHAR', name: 'Patna', admin2: 'Patna', admin1: 'BIHAR',
      coordinates: { latitude: 25.5941, longitude: 85.1376 } },
  ],
});

/* The recorded network-shaped read the vanilla check used, carrying the reported parameters the route's
   station rows carry: the metar row states a zero and no unit, the row beside it states a unit. */
const NEAR = envelope('observations.both', 'ok', {
  networks: {
    aws: [
      { kind: 'aws', name: 'Older AWS', stale: false, observed_at_utc: '2026-09-15T00:00:00Z',
        parameters: [{ field: 'temp', value: 29, unit: '°C', unit_stated_by_source: true }] },
    ],
    metar: [
      { kind: 'metar', name: 'Fresh METAR', stale: false, observed_at_utc: '2026-09-15T10:00:00Z', distance_km: 7.45,
        parameters: [{ field: 'temp', value: 0, unit: null, unit_stated_by_source: false }] },
    ],
  },
});

const NETWORK = envelope('observations.near', 'ok', { kind: 'metar', stations: [] });

describe('the district-day rows', () => {
  it('keeps published hazards, missing dates, expired days and explicit quiet distinct', async () => {
    server.use(http.get('/api/warnings/national', () => HttpResponse.json(WARNINGS)));
    mount(<WarningsSurface />);

    const table = within(await screen.findByTestId('warnings-table'));

    // A published hazard keeps its date, its wording and its own state.
    const hazard = table.getByRole('row', { name: /Thunderstorm\/lightning\/squall/ });
    expect(hazard).toHaveTextContent('15 Sep 2026');
    expect(hazard).toHaveTextContent('not quiet as returned');
    expect(hazard).not.toHaveTextContent(/no warning in this product/i);

    // The day the read dated nowhere states its absent date, and is not read as quiet.
    const unstated = table.getByRole('row', { name: /the quiet flag was not returned/ });
    expect(unstated).toHaveTextContent('not recorded');
    expect(unstated).not.toHaveTextContent(/no warning in this product/i);
    expect(unstated).not.toHaveTextContent(/quiet as returned/);

    // An expired day is its own state: not quiet, and not the product's quiet sentence.
    const expired = table.getByRole('row', { name: /past as returned/ });
    expect(expired).toHaveTextContent('13 Sep 2026');
    expect(expired).not.toHaveTextContent(/no warning in this product/i);
    expect(expired).not.toHaveTextContent(/quiet as returned/);

    // Only the day the payload marked quiet carries the product's quiet sentence.
    const quiet = table.getByRole('row', { name: /quiet as returned: no warning in this product/ });
    expect(quiet).toHaveTextContent('16 Sep 2026');
    expect(quiet).toHaveTextContent(/no warning in this product/i);

    // The district with no day rows is still named, and it contributes no district-day row.
    expect(within(screen.getByTestId('warnings-bulletins')).getByText('KOLKATA')).toBeInTheDocument();
    expect(screen.getByTestId('warnings-count')).toHaveTextContent('Showing 4 district-day rows of 4 district-day rows matching this filter.');
  });
});

describe('the network-shaped station read', () => {
  it('keeps station identity, freshness, a zero value and an unstated unit, and borrows no unit from the next row', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(PLACES)),
      http.get('/api/observations/near', () => HttpResponse.json(NEAR)),
      http.get('/api/observations/network', () => HttpResponse.json(NETWORK)),
    );
    mount(<ObservationsSurface />);
    await screen.findByLabelText('Name a place');
    await userEvent.type(screen.getByLabelText('Name a place'), 'Patna');
    await userEvent.click(await screen.findByRole('button', { name: /25\.5941, 85\.1376/ }));

    const near = within(await screen.findByTestId('observations-near'));

    // The station keeps its own name, instant, distance and freshness state.
    const metar = near.getByRole('row', { name: /Fresh METAR/ });
    expect(metar).toHaveTextContent('15 Sep 2026, 15:30 IST');
    expect(metar).toHaveTextContent('7.45 km');
    expect(metar).toHaveTextContent('current');
    // The payload carried value 0, so the row states 0; the unit the read did not state is stated as unstated.
    expect(metar).toHaveTextContent('temp 0 (unit not stated)');
    // And the unit the neighbouring row stated is never borrowed into this row.
    expect(metar).not.toHaveTextContent('°C');

    const older = near.getByRole('row', { name: /Older AWS/ });
    expect(older).toHaveTextContent('15 Sep 2026, 05:30 IST');
    expect(older).toHaveTextContent('temp 29 (°C)');
    expect(older).not.toHaveTextContent('unit not stated');
  });
});
