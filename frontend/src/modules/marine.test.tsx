/* The Sea and rivers surface, checked against payloads shaped like the marine and river routes': two
   independent reads, each naming its own answering cell and the distance the payload states; the wave
   and discharge rows with the model and unit they carry; the surface's own boundary sentences; an
   unstated distance reading as not recorded; and a failed read as that failure with a retry. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as MarineSurface } from './MarineSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const HEAD = { schema_version: 'product-view-v1', generated_at_utc: '2026-09-17T05:00:00Z', status: 'ok' };

const KOCHI = { label: 'Kochi, Ernakulam, Kerala', latitude: 9.9312, longitude: 76.2673, admin1: 'Kerala', admin2: 'Ernakulam', selection_id: 'geonames:1273874' };
const SURAT = { label: 'Surat, Surat, Gujarat', latitude: 21.1702, longitude: 72.8311, admin1: 'Gujarat', admin2: 'Surat', selection_id: 'geonames:1255364' };

function placesPayload(term: string) {
  return {
    ...HEAD,
    view: 'places.search',
    data: { query: term, matches: [term.toLowerCase().startsWith('ko') ? KOCHI : SURAT] },
    sources: [{ source_id: 'S61', product: 'GeoNames India place catalogue', retrieved_at_utc: '2026-09-14T00:00:00Z' }],
    limitations: ['Place records are GeoNames source labels, not authoritative LGD entities.'],
    not_established: ['No reviewed dated administrative crosswalk is applied here.'],
  };
}

const MARINE_MODEL = 'Open-Meteo default marine model selection; run unspecified';
const wavePayload = {
  ...HEAD,
  generated_at_utc: '2026-09-17T05:30:00Z',
  view: 'marine.point',
  status: 'ok',
  data: {
    requested: { latitude: 9.93, longitude: 76.27 },
    grid: { latitude: 9.75, longitude: 76.0 },
    grid_distance_km: null,
    days: 3,
    parameters: {
      wave_height: {
        unit: 'm',
        model: MARINE_MODEL,
        aggregation: 'instant',
        quality_flags: ['source_value_missing'],
        points: [
          { t: '2026-09-17T06:00:00Z', v: 1.2 },
          { t: '2026-09-17T07:00:00Z', v: null },
        ],
      },
      wave_direction: { unit: '°', model: MARINE_MODEL, aggregation: 'instant', points: [{ t: '2026-09-17T06:00:00Z', v: 240.0 }] },
      wave_period: { unit: 's', model: MARINE_MODEL, aggregation: 'instant', points: [{ t: '2026-09-17T06:00:00Z', v: 6.4 }] },
    },
  },
  sources: [{ source_id: 'S56', product: 'marine_forecast', retrieved_at_utc: '2026-09-17T05:20:00Z', sha256_prefix: 'aa11bb22cc33' }],
  coverage: { requested_point: { latitude: 9.93, longitude: 76.27 }, returned_grid: { latitude: 9.75, longitude: 76.0 }, time_basis: 'UTC' },
  limitations: ['Modelled grid values are not direct local measurements.', 'Wave information is not an official marine warning or navigation clearance.'],
  not_established: ['No official sea-area bulletin, observed buoy value, tide, current or sea-surface temperature is retrieved here.'],
};

const RIVER_MODEL = 'GloFAS default selection via Open-Meteo';
const dischargePayload = {
  ...HEAD,
  generated_at_utc: '2026-09-17T05:35:00Z',
  view: 'river.point',
  status: 'ok',
  data: {
    grid: { latitude: 21.25, longitude: 72.75 },
    grid_distance_km: 12.5,
    days: 3,
    parameters: {
      river_discharge: {
        unit: 'm³/s',
        model: RIVER_MODEL,
        points: [
          { t: '2026-09-18T00:00:00Z', v: 210.0 },
          { t: '2026-09-19T00:00:00Z', v: null },
        ],
      },
    },
  },
  sources: [{ source_id: 'S37', product: 'river_discharge', retrieved_at_utc: '2026-09-17T05:25:00Z', sha256_prefix: 'dd44ee55ff66' }],
  coverage: { requested_point: { latitude: 21.17, longitude: 72.83 }, returned_grid: { latitude: 21.25, longitude: 72.75 }, time_basis: 'UTC' },
  limitations: ['Model-derived daily data; not direct gauge measurements.', 'River-cell identity has not been matched to a local gauge.'],
  not_established: ['No observed gauge level, danger level, inundation extent or official flood warning is established by a discharge value.'],
};

const placesRoute = () =>
  http.get('/api/places/search', ({ request }) =>
    HttpResponse.json(placesPayload(new URL(request.url).searchParams.get('q') || '')));

const waveRoute = (fail = false) =>
  http.get('/api/marine', () =>
    fail ? HttpResponse.json({ error: 'the marine store could not be opened' }, { status: 503 }) : HttpResponse.json(wavePayload));

const riverRoute = (fail = false) =>
  http.get('/api/river', () =>
    fail ? HttpResponse.json({ error: 'the river store could not be opened' }, { status: 503 }) : HttpResponse.json(dischargePayload));

async function chooseSeaAndRiver() {
  const inputs = await screen.findAllByLabelText('Name a place');
  await userEvent.type(inputs[0], 'Kochi');
  await userEvent.click(await screen.findByRole('button', { name: /Kochi, Ernakulam, Kerala/ }));
  await userEvent.type(inputs[1], 'Surat');
  await userEvent.click(await screen.findByRole('button', { name: /Surat, Surat, Gujarat/ }));
}

describe('the Sea and rivers surface', () => {
  it('renders each read with its own cell, the distance the payload states, model and unit, and states the boundary', async () => {
    server.use(placesRoute(), waveRoute(), riverRoute());
    mount(<MarineSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Sea and rivers' })).toBeInTheDocument();
    const boundary = screen.getByTestId('marine-boundary');
    expect(boundary).toHaveTextContent('A wave height is a modelled sea-state value for a grid cell.');
    expect(boundary).toHaveTextContent('It is not an observation, not a sea-area bulletin and not a coastal or marine safety warning.');
    expect(boundary).toHaveTextContent('A discharge is modelled volume flow.');
    expect(boundary).toHaveTextContent('not an observed water level, not a gauge reading, not a danger level, not an inundation extent or a flood warning');
    expect(boundary).toHaveTextContent('S58 and S59 are not connected here');
    expect(boundary).toHaveTextContent('this surface never computes one');
    expect(screen.getByText('No point has been chosen for the wave read, so no sea cell was requested.')).toBeInTheDocument();
    expect(screen.getByText('No point has been chosen for the river read, so no river cell was requested.')).toBeInTheDocument();

    await chooseSeaAndRiver();

    // The wave read: its own answering cell, an unstated distance, the model and the unit per parameter.
    await screen.findByTestId('marine-wave-series-wave_height');
    const waveFacts = within(screen.getByTestId('marine-wave-facts'));
    expect(waveFacts.getByText('Answering cell as returned').nextElementSibling).toHaveTextContent('latitude 9.75, longitude 76');
    expect(waveFacts.getByText('Distance as returned for that cell').nextElementSibling).toHaveTextContent('not recorded');
    expect(screen.getByTestId('marine-wave-model-wave_height')).toHaveTextContent('Model as returned: ' + MARINE_MODEL);
    expect(screen.getByRole('heading', { level: 3, name: 'wave_height (m)' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: 'wave_direction (°)' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: 'wave_period (s)' })).toBeInTheDocument();
    const height = within(screen.getByTestId('marine-wave-series-wave_height'));
    expect(height.getByText('1.2')).toBeInTheDocument();
    expect(height.getByText('no value returned for this point')).toBeInTheDocument();
    const waveSection = within(screen.getByTestId('marine-wave'));
    expect(waveSection.getByText('S56')).toBeInTheDocument();
    expect(waveSection.getByText('Wave information is not an official marine warning or navigation clearance.')).toBeInTheDocument();

    // The river read: its own cell, the distance the payload states, the model, the unit and the time basis.
    await screen.findByTestId('marine-river-series-river_discharge');
    const riverFacts = within(screen.getByTestId('marine-river-facts'));
    expect(riverFacts.getByText('Answering cell as returned').nextElementSibling).toHaveTextContent('latitude 21.25, longitude 72.75');
    expect(riverFacts.getByText('Distance as returned for that cell').nextElementSibling).toHaveTextContent('12.5 km');
    expect(riverFacts.getByText('Time basis as returned').nextElementSibling).toHaveTextContent('UTC');
    expect(screen.getByTestId('marine-river-model-river_discharge')).toHaveTextContent('Model as returned: ' + RIVER_MODEL);
    expect(screen.getByRole('heading', { level: 3, name: 'river_discharge (m³/s)' })).toBeInTheDocument();
    const discharge = within(screen.getByTestId('marine-river-series-river_discharge'));
    expect(discharge.getByText('210')).toBeInTheDocument();
    expect(discharge.getByText('no value returned for this point')).toBeInTheDocument();
    const riverSection = within(screen.getByTestId('marine-river'));
    expect(riverSection.getByText('S37')).toBeInTheDocument();
    expect(riverSection.getByText('No observed gauge level, danger level, inundation extent or official flood warning is established by a discharge value.')).toBeInTheDocument();

    // Two cells answered and the surface says plainly that they differ.
    const cells = screen.getByTestId('marine-cells');
    expect(cells).toHaveTextContent('The wave read answered for cell latitude 9.75, longitude 76');
    expect(cells).toHaveTextContent('The river read answered for cell latitude 21.25, longitude 72.75');
    expect(cells).toHaveTextContent('They are two different cells');

    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('reads a failed river read as the local evidence store being unavailable, with a retry, while the wave read stands', async () => {
    server.use(placesRoute(), waveRoute(), riverRoute(true));
    mount(<MarineSurface />);
    await chooseSeaAndRiver();

    const river = within(await screen.findByTestId('marine-river'));
    const failure = await river.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the river store could not be opened');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();

    // The failed read is not an empty river: the wave read keeps its values, and no cell comparison is drawn.
    expect(await screen.findByTestId('marine-wave-series-wave_height')).toHaveTextContent('1.2');
    expect(screen.queryByTestId('marine-cells')).toBeNull();
  });
});
