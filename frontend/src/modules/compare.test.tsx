/* Compare places, checked against payloads shaped like the route's own: two independent reads, each
   with its own retrieved instant, coverage, limits and source rows; the union of parameters and
   instants, where a point or parameter one read did not return is stated as absent for that read; and
   a failed read rendered as that failure with a retry while the other read stands. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { provenanceOffenders } from '../flagship/provenance';
import { Surface as CompareSurface } from './CompareSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const HEAD = { schema_version: 'product-view-v1', generated_at_utc: '2026-09-17T05:00:00Z', status: 'ok' };

const SURAT = { label: 'Surat, Surat, Gujarat', latitude: 21.1702, longitude: 72.8311, admin1: 'Gujarat', admin2: 'Surat', selection_id: 'geonames:1255364' };
const VADODARA = { label: 'Vadodara, Vadodara, Gujarat', latitude: 22.3072, longitude: 73.1812, admin1: 'Gujarat', admin2: 'Vadodara', selection_id: 'geonames:1253573' };

function placesPayload(term: string) {
  return {
    ...HEAD,
    view: 'places.search',
    data: { query: term, matches: [term.toLowerCase().startsWith('sur') ? SURAT : VADODARA] },
    sources: [{ source_id: 'S61', product: 'GeoNames India place catalogue', retrieved_at_utc: '2026-09-14T00:00:00Z' }],
    limitations: ['Place records are GeoNames source labels, not authoritative LGD entities.'],
    not_established: ['No reviewed dated administrative crosswalk is applied here.'],
  };
}

const suratForecast = {
  ...HEAD,
  generated_at_utc: '2026-09-17T05:30:00Z',
  view: 'forecast.point',
  status: 'ok',
  data: {
    requested: { latitude: 21.17, longitude: 72.83 },
    grid: { latitude: 21.25, longitude: 72.75 },
    days: 3,
    source_family: 'hourly_forecast',
    time_basis: 'UTC',
    parameters: {
      temperature_2m: {
        unit: '°C',
        model: 'Open-Meteo best match',
        aggregation: 'instant',
        points: [
          { t: '2026-09-17T06:00:00Z', v: 29.4 },
          { t: '2026-09-17T07:00:00Z', v: null },
        ],
      },
      precipitation: { unit: 'mm', points: [{ t: '2026-09-17T06:00:00Z', v: 0.4 }] },
    },
  },
  sources: [{ source_id: 'S62', product: 'extended_weather_forecast', retrieved_at_utc: '2026-09-17T05:20:00Z', sha256_prefix: 'bb11cc22dd33' }],
  coverage: { requested_point: { latitude: 21.17, longitude: 72.83 }, returned_grid: { latitude: 21.25, longitude: 72.75 }, time_basis: 'UTC' },
  limitations: ['Run identity is not exposed; retrieval time is not model issue time.'],
  not_established: ['No forecast skill or probability calibration is validated here.'],
};

const vadodaraForecast = {
  ...HEAD,
  generated_at_utc: '2026-09-17T05:45:00Z',
  view: 'forecast.point',
  status: 'partial',
  data: {
    requested: { latitude: 22.31, longitude: 73.18 },
    grid: { latitude: 22.25, longitude: 73.25 },
    days: 3,
    source_family: 'hourly_forecast',
    time_basis: 'UTC',
    parameters: {
      temperature_2m: {
        unit: '°C',
        points: [
          { t: '2026-09-17T06:00:00Z', v: 30.1 },
          { t: '2026-09-17T08:00:00Z', v: 31.0 },
        ],
      },
      wind_speed_10m: { unit: 'km/h', points: [{ t: '2026-09-17T06:00:00Z', v: 14.0 }] },
    },
  },
  sources: [{ source_id: 'S21', product: 'weather_forecast', retrieved_at_utc: '2026-09-17T05:40:00Z', sha256_prefix: 'd4e5f6a7b8c9' }],
  coverage: { requested_point: { latitude: 22.31, longitude: 73.18 }, returned_grid: { latitude: 22.25, longitude: 73.25 }, time_basis: 'UTC' },
  limitations: ['Modelled grid values are not direct local measurements.'],
  not_established: ['Upstream model run identity is not exposed.'],
};

const placesRoute = () =>
  http.get('/api/places/search', ({ request }) =>
    HttpResponse.json(placesPayload(new URL(request.url).searchParams.get('q') || '')));

const forecastRoute = (failFirst = false) =>
  http.get('/api/forecast', ({ request }) => {
    const lat = new URL(request.url).searchParams.get('lat');
    if (lat === String(SURAT.latitude)) {
      return failFirst
        ? HttpResponse.json({ error: 'the store could not be opened' }, { status: 503 })
        : HttpResponse.json(suratForecast);
    }
    return HttpResponse.json(vadodaraForecast);
  });

async function chooseTwoPlaces() {
  const inputs = await screen.findAllByLabelText('Name a place');
  await userEvent.type(inputs[0], 'Surat');
  await userEvent.click(await screen.findByRole('button', { name: /Surat, Surat, Gujarat/ }));
  await userEvent.type(inputs[1], 'Vadodara');
  await userEvent.click(await screen.findByRole('button', { name: /Vadodara, Vadodara, Gujarat/ }));
}

describe('the Compare places surface', () => {
  it("fetches each place separately, keeps each read's instant and source, and states a missing point or parameter for the read that lacks it", async () => {
    server.use(placesRoute(), forecastRoute());
    mount(<CompareSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Compare places' })).toBeInTheDocument();
    const boundary = screen.getByTestId('compare-boundary');
    expect(boundary).toHaveTextContent('two separate reads');
    expect(boundary).toHaveTextContent('may have been retrieved at different times');
    expect(boundary).toHaveTextContent('not a ranking, a recommendation, a better-or-worse judgement or a claim about forecast skill');
    expect(boundary).toHaveTextContent("the point-forecast product's own model output, not an observation");
    expect(screen.getByText('No place has been chosen for the first read, so no forecast was requested for it.')).toBeInTheDocument();

    await chooseTwoPlaces();

    const firstRead = within(await screen.findByTestId('compare-read-first'));
    const secondRead = within(screen.getByTestId('compare-read-second'));
    // Each read states its own generated_at_utc: 05:30Z and 05:45Z are two different retrieved instants.
    expect(await firstRead.findByText('17 Sep 2026, 11:00 IST')).toBeInTheDocument();
    expect(secondRead.getByText('17 Sep 2026, 11:15 IST')).toBeInTheDocument();
    expect(firstRead.getByText('S62')).toBeInTheDocument();
    expect(firstRead.getByText('bb11cc22dd33')).toBeInTheDocument();
    expect(secondRead.getByText('S21')).toBeInTheDocument();
    expect(firstRead.getByText('Run identity is not exposed; retrieval time is not model issue time.')).toBeInTheDocument();
    expect(secondRead.getByText('Modelled grid values are not direct local measurements.')).toBeInTheDocument();

    // The first-screen reading: both reads' own latest value for the first shared parameter, held side by
    // side and never resolved into which one is right, before the table that proves it.
    const headline = screen.getByTestId('compare-headline');
    expect(headline).toHaveTextContent('For temperature_2m: Surat, Surat, Gujarat’s own read reads 29.4 °C');
    expect(headline).toHaveTextContent('Vadodara, Vadodara, Gujarat’s own read reads 30.1 °C');
    expect(headline).toHaveTextContent('not a ranking, an average or a confidence');
    expect(provenanceOffenders(headline)).toEqual([]);

    // The counts the payloads gave, one line per read, kept separate.
    const counts = screen.getByTestId('compare-count-temperature_2m');
    expect(counts).toHaveTextContent('Surat, Surat, Gujarat: 2 points returned · unit °C');
    expect(counts).toHaveTextContent('Vadodara, Vadodara, Gujarat: 2 points returned · unit °C');

    // The union of the instants: the shared hour, then the hour only one read returned.
    const temperature = within(await screen.findByTestId('compare-parameter-temperature_2m'));
    const shared = temperature.getByRole('row', { name: /17 Sep 2026, 11:30 IST/ });
    expect(within(shared).getByText('29.4 °C')).toBeInTheDocument();
    expect(within(shared).getByText('30.1 °C')).toBeInTheDocument();
    const secondHour = temperature.getByRole('row', { name: /17 Sep 2026, 12:30 IST/ });
    expect(within(secondHour).getByText('no value returned for this point')).toBeInTheDocument();
    expect(within(secondHour).getByText('no point returned for this instant')).toBeInTheDocument();
    const thirdHour = temperature.getByRole('row', { name: /17 Sep 2026, 13:30 IST/ });
    expect(within(thirdHour).getByText('no point returned for this instant')).toBeInTheDocument();
    expect(within(thirdHour).getByText('31 °C')).toBeInTheDocument();

    // A parameter only one read returned stays in the union, with the absence stated for the other read.
    expect(within(screen.getByTestId('compare-parameter-precipitation')).getByText('no row returned for this parameter in this read')).toBeInTheDocument();
    expect(within(screen.getByTestId('compare-parameter-wind_speed_10m')).getByText('no row returned for this parameter in this read')).toBeInTheDocument();

    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('reads a 503 on one read as the local evidence store being unavailable, with a retry, and keeps the other read standing', async () => {
    server.use(placesRoute(), forecastRoute(true));
    mount(<CompareSurface />);
    await chooseTwoPlaces();

    const firstRead = within(await screen.findByTestId('compare-read-first'));
    const failure = await firstRead.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the store could not be opened');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();

    // The failed read is not drawn as an empty forecast: its column says the read did not answer.
    const temperature = within(await screen.findByTestId('compare-parameter-temperature_2m'));
    expect(temperature.getAllByText('this read did not answer').length).toBeGreaterThan(0);
    expect(temperature.getAllByText('30.1 °C').length).toBeGreaterThan(0);
    expect(within(screen.getByTestId('compare-read-second')).getByText('S21')).toBeInTheDocument();
  });
});
