/* The Workspace surface: the vanilla field-builder check ported, and the right-now reading for the point
   it names. The builder's control writes the editable question box and never submits; the reading is GET
   /api/now, whose station rows carry their own distance, age and staleness. */
import axe from 'axe-core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as WorkspaceSurface, intents } from './WorkspaceSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const QUESTION = 'What is the forecast for AHMADABAD from 09:30 to 12:30 IST?';
const PLACE_LABEL = 'AHMADABAD';

const placeRow = { label: PLACE_LABEL, latitude: 23.02579, longitude: 72.58727, admin1: 'Gujarat', admin2: 'Ahmadabad', selection_id: 'geonames:1279233' };

function placesPayload() {
  return { schema_version: 'product-view-v1', view: 'places.search', status: 'ok', data: { matches: [placeRow] },
           sources: [], limitations: [], not_established: [] };
}

const nowPayload = {
  schema_version: 'product-view-v1', generated_at_utc: '2026-09-15T06:05:00Z', view: 'now.composed', status: 'ok',
  data: {
    schema_version: 'now-v1',
    point: { latitude: 23.02579, longitude: 72.58727, label: null },
    observed: { status: 'ok', rows_in_radius: 6, stations: [
      { kind: 'metar', network: 'metar', name: 'AHMEDABAD', station_code: 'VAAH', distance_km: 5.76, age_minutes: 35.0,
        observed_at_utc: '2026-09-15T05:30:00+00:00', stale: false, source_id: 'S63' },
      { kind: 'aws', network: 'aws', name: 'AHMEDABAD', station_code: '99935', distance_km: 9.4, age_minutes: 379.4,
        observed_at_utc: '2026-09-15T00:00:00+00:00', stale: true, source_id: 'S63' },
    ] },
    in_force: { district: 'AHMADABAD', state: 'GUJARAT', day: 1, day_label: '15 Sep 2026', colour: 'yellow', quiet: false,
                status_line: 'Official district warning: yellow - Thunderstorm/lightning/squall',
                issued_at_utc: '2026-09-15T06:00:00+00:00', status: 'ok' },
    next_hours: { status: 'ok', source_id: 'S62', unit: { temperature_2m: '°C', precipitation_probability: '%', precipitation: 'mm', wind_speed_10m: 'km/h' },
      rows: [
        { at: '2026-09-15T06:00:00+00:00', temperature_2m: 29.3, precipitation_probability: 82, precipitation: 0.1, wind_speed_10m: 13.6 },
        { at: '2026-09-15T07:00:00+00:00', temperature_2m: 29.0, precipitation_probability: 86, precipitation: 0.1, wind_speed_10m: 12.3 },
      ] },
  },
  sources: [
    { source_id: 'S63', product: 'IMD district warning product', retrieved_at_utc: '2026-09-15T05:12:00Z', sha256_prefix: 'a1b2c3d4e5f6' },
    { source_id: 'S62', product: 'extended_weather_forecast', retrieved_at_utc: '2026-09-15T05:20:00Z', sha256_prefix: 'bb11cc22dd33' },
  ],
  coverage: { stations: 2, day: 1, hours: 2 },
  limitations: ['A station observation describes its station, not the surrounding district or city.'],
  not_established: ['A station report is one station at one instant: it is not a district average, not a field reading and not a forecast.'],
};

async function nameAPlace(name = PLACE_LABEL) {
  await userEvent.type(screen.getByLabelText('Name a place'), name);
  await userEvent.click(await screen.findByRole('button', { name: new RegExp(name + ' · Ahmadabad, Gujarat') }));
}

describe('the Workspace surface', () => {
  it('writes the fields into the editable question box, moves focus there, and sends nothing', async () => {
    const seen: string[] = [];
    const passthrough = globalThis.fetch;
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      seen.push((init?.method || 'GET') + ' ' + String(input));
      return passthrough(input, init);
    });
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/now', () => HttpResponse.json(nowPayload)),
    );
    const box = mount(<WorkspaceSurface />).container;
    const question = await screen.findByLabelText('Your question');
    expect(question).toHaveValue('');
    expect(screen.getByText(/writes the question box and nothing else/)).toBeInTheDocument();
    expect(screen.getByText(/no value is filled in for you/)).toBeInTheDocument();
    expect(screen.getByText(/a district is never inferred from a coordinate/)).toBeInTheDocument();
    expect(screen.getByText(/No point has been chosen, so no right-now reading was requested/)).toBeInTheDocument();
    expect(intents).toContain('What is it like right now in Ahmedabad?');

    await userEvent.click(screen.getByRole('button', { name: 'Write this into the question' }));
    expect(screen.getByTestId('workspace-written')).toHaveTextContent('Name a place first');
    expect(question).toHaveValue('');
    expect(seen).toHaveLength(0);

    await nameAPlace();
    fireEvent.change(screen.getByLabelText('From (IST)'), { target: { value: '09:30' } });
    fireEvent.change(screen.getByLabelText('Until (IST)'), { target: { value: '12:30' } });
    const before = seen.length;
    await userEvent.click(screen.getByRole('button', { name: 'Write this into the question' }));
    await waitFor(() => expect(question).toHaveValue(QUESTION));
    expect(question).toHaveFocus();
    expect(screen.getByTestId('workspace-written')).toHaveTextContent('Wrote this into the editable question box');
    expect(screen.getByTestId('workspace-written')).toHaveTextContent('The box stays editable');
    expect(seen).toHaveLength(before);
    expect(seen.every(call => call.startsWith('GET '))).toBe(true);
    expect(await screen.findByTestId('workspace-stations')).toBeInTheDocument();
    expect(box.querySelectorAll('form')).toHaveLength(0);
    spy.mockRestore();
  });

  it('renders the station rows with their distances, ages and staleness, the district line and the hour units', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/now', ({ request }) => {
        expect(new URL(request.url).searchParams.get('lat')).toBe('23.02579');
        return HttpResponse.json(nowPayload);
      }),
    );
    const { container } = mount(<WorkspaceSurface />);
    /* The surface is labelled Dashboard since the design migration; its route stays #/workspace. */
    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument();
    await nameAPlace();

    const stations = within(await screen.findByTestId('workspace-stations'));
    expect(stations.getByText('AHMEDABAD · VAAH')).toBeInTheDocument();
    expect(stations.getByText('5.76 km')).toBeInTheDocument();
    expect(stations.getByText('35 minutes before retrieval')).toBeInTheDocument();
    expect(stations.getByText('379.4 minutes before retrieval')).toBeInTheDocument();
    expect(stations.getByText('current')).toBeInTheDocument();
    expect(stations.getByText(/stale: the report is older than the layer’s freshness window/)).toBeInTheDocument();

    const point = within(screen.getByTestId('workspace-point'));
    expect(point.getByText('label not recorded in this read')).toBeInTheDocument();
    expect(point.getByText('AHMADABAD')).toBeInTheDocument();
    const line = screen.getByText('Official district warning: yellow - Thunderstorm/lightning/squall');
    expect(line.closest('p')?.querySelector('[data-colour]')).toHaveAttribute('data-colour', 'yellow');
    expect(container.querySelector('[data-colour="green"]')).toBeNull();

    const hours = within(await screen.findByTestId('workspace-hours'));
    expect(hours.getByText('temperature_2m (°C)')).toBeInTheDocument();
    expect(hours.getByText('precipitation_probability (%)')).toBeInTheDocument();
    expect(hours.getByText('precipitation (mm)')).toBeInTheDocument();
    expect(hours.getByText('wind_speed_10m (km/h)')).toBeInTheDocument();
    expect(hours.getByText('29.3')).toBeInTheDocument();
    expect(hours.getByText('13.6')).toBeInTheDocument();

    expect(screen.getByText('A station observation describes its station, not the surrounding district or city.')).toBeInTheDocument();
    expect(screen.getByText('A station report is one station at one instant: it is not a district average, not a field reading and not a forecast.')).toBeInTheDocument();
    expect(screen.getByText('S63')).toBeInTheDocument();
    expect(screen.getByText('IMD district warning product')).toBeInTheDocument();
    expect(container.querySelectorAll('h1')).toHaveLength(1);
    const scan = await axe.run(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(scan.violations.map(violation => violation.id).join(', ')).toBe('');
  });

  it('states a failed right-now read, and the retry re-reads it', async () => {
    let calls = 0;
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/now', () => {
        calls += 1;
        if (calls === 1) return HttpResponse.json({ error: 'the local store could not be opened' }, { status: 503 });
        return HttpResponse.json(nowPayload);
      }),
    );
    mount(<WorkspaceSurface />);
    await nameAPlace();

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the local store could not be opened');
    await userEvent.click(within(failure).getByRole('button', { name: 'Retry this read' }));
    expect(await screen.findByTestId('workspace-stations')).toBeInTheDocument();
  });
});
