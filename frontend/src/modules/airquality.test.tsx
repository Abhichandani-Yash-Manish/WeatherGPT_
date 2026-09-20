/* The Air quality surface, checked against a payload shaped like the route's own product view.

   What the checks may not lose: the cell identity and its distance from the requested point, exactly as
   the payload states them; the parameter rows with their own unit, current-hour value and gap counts; a
   value the payload did not return read as 'not recorded for this cell', never a zero and never clean
   air; the provider's own AQI category printed only where the payload states one, and never turned into
   health advice or a protective action; the mandatory model-not-monitor statement; and a failed read
   stated as that failure with a retry.

   docs/127 records that nothing under src/modules is audited by X1 yet ("A later batch extends there").
   This file extends it to the one region this batch added here: the first-screen headline, which is held
   to flagship/provenance.ts's own provenanceOffenders — the same function the answer card and the other
   product surfaces are held to — rather than a second copy of the rule. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { provenanceOffenders } from '../flagship/provenance';
import { Surface as AirQualitySurface } from './AirQualitySurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const HEAD = {
  schema_version: 'product-view-v1',
  generated_at_utc: '2026-09-17T05:30:00Z',
  status: 'ok',
};

const placeMatch = {
  label: 'Kanpur Nagar, Kanpur Nagar, Uttar Pradesh',
  latitude: 26.4499,
  longitude: 80.3319,
  admin1: 'Uttar Pradesh',
  admin2: 'Kanpur Nagar',
  selection_id: 'geonames:1273865',
};

function placesPayload() {
  return {
    ...HEAD,
    view: 'places.search',
    data: { query: 'Kanpur Nagar', matches: [placeMatch] },
    sources: [],
    limitations: ['Place records are GeoNames source labels, not authoritative LGD entities.'],
    not_established: ['No reviewed dated administrative crosswalk is applied here.'],
  };
}

async function nameAPlace(name = 'Kanpur Nagar') {
  const input = screen.getByLabelText('Name a place');
  await userEvent.type(input, name);
  const choice = await screen.findByRole('button', { name: new RegExp(name + ', ' + name + ', Uttar Pradesh') });
  await userEvent.click(choice);
}

const MODEL = 'CAMS European air quality forecast';

/* us_aqi is named before pm2_5 deliberately: it is the fixture's only parameter carrying a stated
   category, and the surface's headline reads the first-named parameter, so this is what proves the
   category is printed without being turned into advice. */
const airQualityPayload = {
  ...HEAD,
  view: 'air-quality.point',
  data: {
    requested: { label: 'Kanpur Nagar, Uttar Pradesh', latitude: 26.4499, longitude: 80.3319 },
    grid: { latitude: 26.5, longitude: 80.25 },
    grid_distance_km: 6.2,
    domain: 'india',
    time_basis: 'UTC',
    current: { us_aqi: 168, pm2_5: 118 },
    parameters: {
      us_aqi: {
        unit: 'AQI', aggregation: 'instant', model: MODEL, category: 'Unhealthy', quality_flags: [],
        points: [{ t: '2026-09-17T06:00:00Z', v: 168 }, { t: '2026-09-17T07:00:00Z', v: null }],
      },
      pm2_5: {
        unit: 'µg/m³', aggregation: 'instant', model: MODEL, quality_flags: ['source_value_missing'],
        points: [{ t: '2026-09-17T06:00:00Z', v: 118 }],
      },
    },
  },
  sources: [{ source_id: 'S66', product: 'cams_air_quality', retrieved_at_utc: '2026-09-17T05:20:00Z', sha256_prefix: 'a1b2c3d4e5f6' }],
  coverage: { requested_point: { latitude: 26.4499, longitude: 80.3319 }, returned_grid: { latitude: 26.5, longitude: 80.25 }, grid_distance_km: 6.2 },
  limitations: ['Modelled grid values are not direct local measurements.', 'This is a model value, not a monitor measurement or an observation.'],
  not_established: ['An air-quality index is the source’s own index, and no health advice, risk score or official warning is produced from it.'],
};

describe('the Air quality surface', () => {
  it('renders the cell, the parameter rows the read returned and the headline reading, with the provider’s own category', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/air-quality', () => HttpResponse.json(airQualityPayload)),
    );
    const { container } = mount(<AirQualitySurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Air quality' })).toBeInTheDocument();
    await screen.findByLabelText('Name a place');
    expect(screen.getByText('No point was named, so no air-quality read was requested.')).toBeInTheDocument();
    await nameAPlace();

    const cell = within(await screen.findByTestId('air-quality-cell'));
    expect(cell.getByText('Cell identity as returned').nextSibling).toHaveTextContent('26.5, 80.25');
    expect(cell.getByText('Cell distance from the requested point').nextSibling).toHaveTextContent('6.2 km');
    expect(cell.getByText('Domain as returned').nextSibling).toHaveTextContent('india');

    // The first-screen reading: the first-named parameter's own current value and the source's own
    // category word for it, stated before the table that proves it, and never turned into advice.
    const headline = screen.getByTestId('air-quality-headline');
    expect(headline).toHaveTextContent('This read’s current us_aqi for this cell is 168, which the source itself categorises as “Unhealthy”.');
    expect(headline).not.toHaveTextContent(/should|avoid|mask|stay indoors|sensitive group/i);
    expect(headline.querySelector('.g-claim-source')).toHaveTextContent('india');
    expect(headline.querySelector('.g-claim-source')).toHaveTextContent('26.5, 80.25');
    expect(provenanceOffenders(headline)).toEqual([]);

    const table = within(await screen.findByTestId('air-quality-table'));
    const aqiRow = table.getByRole('rowheader', { name: 'us_aqi' }).closest('tr') as HTMLElement;
    expect(within(aqiRow).getByText(/168 · category as stated: Unhealthy/)).toBeInTheDocument();
    expect(within(aqiRow).getByText('AQI')).toBeInTheDocument();
    const pmRow = table.getByRole('rowheader', { name: 'pm2_5' }).closest('tr') as HTMLElement;
    expect(within(pmRow).getByText('118')).toBeInTheDocument();
    expect(within(pmRow).getByText('µg/m³')).toBeInTheDocument();
    expect(within(pmRow).getByText('source_value_missing')).toBeInTheDocument();

    const countLine = screen.getByTestId('air-quality-count');
    expect(countLine).toHaveAttribute('role', 'status');
    expect(countLine).toHaveTextContent('2 parameter rows returned for this cell');

    expect(screen.getByTestId('air-quality-model-not-monitor')).toHaveTextContent('This is a model, not a monitor, and not an observation');
    expect(screen.getByText('This is a model value, not a monitor measurement or an observation.')).toBeInTheDocument();
    expect(screen.getByText('An air-quality index is the source’s own index, and no health advice, risk score or official warning is produced from it.')).toBeInTheDocument();
    expect(screen.getByText('S66')).toBeInTheDocument();
    expect(screen.getByText('cams_air_quality')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(container.querySelectorAll('table').length).toBeGreaterThan(0);
  });

  it('states a parameter with no value and no category as absent rather than as clean air, and a distance the payload omits as not recorded', async () => {
    const noCategoryPayload = {
      ...airQualityPayload,
      data: {
        ...airQualityPayload.data,
        grid_distance_km: null,
        current: { us_aqi: null },
        parameters: { us_aqi: { unit: 'AQI', model: MODEL, points: [] } },
      },
      coverage: { requested_point: { latitude: 26.4499, longitude: 80.3319 } },
    };
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/air-quality', () => HttpResponse.json(noCategoryPayload)),
    );
    mount(<AirQualitySurface />);
    await screen.findByLabelText('Name a place');
    await nameAPlace();

    const cell = within(await screen.findByTestId('air-quality-cell'));
    expect(cell.getByText('Cell distance from the requested point').nextSibling).toHaveTextContent('not recorded');

    const headline = screen.getByTestId('air-quality-headline');
    expect(headline).toHaveTextContent('This read’s current us_aqi for this cell is not recorded for this cell — the source states no category for this reading.');
    expect(provenanceOffenders(headline)).toEqual([]);

    const table = within(screen.getByTestId('air-quality-table'));
    expect(table.getByText('not recorded for this cell')).toBeInTheDocument();
  });

  it('states a failed read as that failure, with a retry control', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/air-quality', () => HttpResponse.json({ error: 'the store could not be opened' }, { status: 503 })),
    );
    mount(<AirQualitySurface />);
    await screen.findByLabelText('Name a place');
    await nameAPlace();

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the store could not be opened');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
    expect(screen.queryByTestId('air-quality-count')).toBeNull();
    expect(screen.queryByTestId('air-quality-headline')).toBeNull();
  });
});
