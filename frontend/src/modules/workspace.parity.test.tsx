/* Parity checks for the workspace surface, ported from the vanilla component suite tests/test_workspace_ui.js
   (6 printed checks; four of those rules are already held by src/modules/workspace.test.tsx and the shell
   specs: the published/quiet warning states, the station rows with their distances and freshness, one failed
   read leaving the rest of the surface standing, and the guided question builder).

   Held here:
   - check 3  a late response from an earlier task cannot overwrite a new task. The vanilla check opened a new
              drawer over an old one and wrote into the old drawer's body late; the React workspace reads its
              point through a query keyed by the coordinates the reader chose, so the late answer for the first
              point cannot replace the reading for the second. The vanilla check recorded no payload (it was a
              drawer/DOM rule): the two bodies below are minimal now.composed reads shaped like the recorded one
              the existing React workspace spec uses.

   Not portable, reported rather than asserted:
   - check 4  a timed-out source read explains that server work may continue. The React client states a stopped
              read ("That request was stopped before the workspace answered it.") and no surface says the server
              may still be working, so the vanilla sentence has no React equivalent. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as WorkspaceSurface } from './WorkspaceSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const AHMEDABAD = { label: 'AHMEDABAD', latitude: 23.02579, longitude: 72.58727, admin1: 'Gujarat', admin2: 'Ahmadabad', selection_id: 'geonames:1279233' };
const SURAT = { label: 'Surat', latitude: 21.1959, longitude: 72.8302, admin1: 'Gujarat', admin2: 'Surat', selection_id: 'geonames:1255364' };

function placesMatches(term: string) {
  return {
    schema_version: 'product-view-v1',
    view: 'places.search',
    status: 'ok',
    data: { query: term, matches: [term.toLowerCase().startsWith('ah') ? AHMEDABAD : SURAT] },
    sources: [],
    limitations: [],
    not_established: [],
  };
}

/* The smallest now.composed body the surface renders: one observed station, no district-day row and no model
   hour. The station name is the marker each read is identified by. */
function nowFor(name: string, point: { latitude: number; longitude: number }) {
  return {
    schema_version: 'product-view-v1',
    generated_at_utc: '2026-09-15T06:05:00Z',
    view: 'now.composed',
    status: 'ok',
    data: {
      schema_version: 'now-v1',
      point: { latitude: point.latitude, longitude: point.longitude, label: null },
      observed: {
        status: 'ok',
        rows_in_radius: 1,
        stations: [
          {
            kind: 'metar',
            network: 'metar',
            name: name,
            station_code: 'X',
            distance_km: 5.0,
            age_minutes: 20,
            observed_at_utc: '2026-09-15T05:45:00+00:00',
            stale: false,
            source_id: 'S63',
          },
        ],
      },
      in_force: { status: 'ok' },
      next_hours: { status: 'ok', source_id: 'S62', unit: {}, rows: [] },
    },
    sources: [],
    coverage: {},
    limitations: [],
    not_established: [],
  };
}

describe('the workspace surface', () => {
  it('keeps a late read for an earlier point from overwriting the reading for the point chosen after it', async () => {
    let lateArrived = false;
    server.use(
      http.get('/api/places/search', ({ request }) =>
        HttpResponse.json(placesMatches(new URL(request.url).searchParams.get('q') || ''))),
      http.get('/api/now', async ({ request }) => {
        const latitude = Number(new URL(request.url).searchParams.get('lat'));
        if (latitude === AHMEDABAD.latitude) {
          await new Promise(resolve => setTimeout(resolve, 300));
          lateArrived = true;
          return HttpResponse.json(nowFor('OLD STATION', AHMEDABAD));
        }
        return HttpResponse.json(nowFor('NEW STATION', SURAT));
      }),
    );
    mount(<WorkspaceSurface />);

    const input = await screen.findByLabelText('Name a place');
    await userEvent.type(input, 'Ahmedabad');
    await userEvent.click(await screen.findByRole('button', { name: /AHMEDABAD/ }));
    await userEvent.clear(input);
    await userEvent.type(input, 'Surat');
    await userEvent.click(await screen.findByRole('button', { name: /Surat ·/ }));

    expect(await screen.findByText(/NEW STATION/)).toBeInTheDocument();
    await waitFor(() => expect(lateArrived).toBe(true));
    await new Promise(resolve => setTimeout(resolve, 50));

    // The earlier point's answer arrived after the new task was on screen, and it is nowhere on it.
    expect(screen.getByText(/NEW STATION/)).toBeInTheDocument();
    expect(screen.queryByText(/OLD STATION/)).toBeNull();
  });
});
