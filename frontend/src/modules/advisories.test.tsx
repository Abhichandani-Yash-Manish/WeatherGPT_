/* The farm-advisory and air-quality surfaces, checked against payloads shaped like the recorded ones
   (research/implementation/air-quality-20260915, research/implementation/personas-briefcase-20260915).

   Each check asserts what these surfaces may not lose: the directory rows the payload stated, a filter
   that only re-reads rows already in the browser, the brief's own sections and every not-established
   line, a named district that is never inferred from a coordinate, the unit and the cell of a modelled
   value, a missing value read as missing rather than as zero, and a failed read stated with a retry. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as AdvisoriesSurface } from './AdvisoriesSurface';
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

const SOURCE_S57 = {
  source_id: 'S57',
  product: 'IMD district agromet advisory service',
  retrieved_at_utc: '2026-09-15T04:40:00Z',
  sha256_prefix: '653f005c5eb6',
};

const statesPayload = {
  ...HEAD,
  view: 'advisories.states',
  data: { states: [{ id: 'gujarat', label: 'Gujarat' }, { id: 'bihar', label: 'Bihar' }] },
  sources: [SOURCE_S57],
  coverage: { state: null },
  limitations: ['Listed entries do not prove a currently issued bulletin.'],
  not_established: ['A listed state is a directory entry, not proof that a bulletin was issued today.'],
};

const districtsPayload = {
  ...HEAD,
  view: 'advisories.districts',
  data: { state: 'gujarat', districts: [{ id: 'ahmedabad', label: 'Ahmedabad' }, { id: 'surat', label: 'Surat' }] },
  sources: [SOURCE_S57],
  coverage: { state: 'gujarat' },
  limitations: ['Source names and identifiers are not an official administrative crosswalk.'],
  not_established: ['A listed district is a directory entry, not proof of a current bulletin.'],
};

const biharPayload = {
  ...districtsPayload,
  data: { state: 'bihar', districts: [{ id: 'patna', label: 'Patna' }] },
  coverage: { state: 'bihar' },
};

/* The recorded brief: published passages with page and printed issue date, the source's own
   conditions, a model forecast kept apart, and the non-prescription lines the workspace attaches. */
const briefPayload = {
  status: 'ok',
  schema_version: 'advisory-brief-v1',
  generated_at_utc: '2026-09-15T04:47:06+00:00',
  brief_id: '64ff118087298b81cbb0755675736258836dcd4925ecf05f60c63ea99a38b136',
  forecast_status: 'ok',
  request: {
    crop: 'cotton',
    growth_stage: 'squaring',
    topic: 'irrigation',
    mode: 'source_lookup',
    region: 'Ahmedabad',
    state: 'Gujarat',
    point: { latitude: 23.02579, longitude: 72.58727 },
    window: { days: 1, first_valid: '2026-09-15T00:00:00+00:00', last_valid: '2026-09-15T23:00:00+00:00' },
  },
  published_advice: {
    family: 'district_agromet',
    scope: 'district',
    region: 'Ahmedabad',
    matched: 1,
    passages: [
      {
        source_id: 'S57',
        family: 'district_agromet',
        region: 'Ahmedabad',
        page: 3,
        issue_date: '2026-09-11',
        section: null,
        crop: 'cotton',
        growth_stage: 'squaring',
        quote: 'If irrigation facilities are available then apply need based irrigation through drip irrigation …',
        conditions: ['If the infestation is severe, spray'],
        source_locator: 'physical PDF page 3',
        document_sha256_prefix: '653f005c5eb6',
      },
    ],
  },
  forecast: {
    status: 'retrieved',
    window: { days: 1, first_valid: '2026-09-15T00:00:00+00:00', last_valid: '2026-09-15T23:00:00+00:00' },
    values: [
      {
        parameter: 'temperature_2m',
        label: 'temperature_2m',
        first_value: 25.2,
        last_value: 24.9,
        unit: '°C',
        samples: 24,
        series_start: '2026-09-15T00:00:00+00:00',
        series_end: '2026-09-15T23:00:00+00:00',
        source_id: 'S62',
        place: null,
      },
    ],
    note: 'model forecast for a grid cell, not an observation of the field, and not an instruction',
  },
  conditions_named_by_the_source: ['If the infestation is severe, spray'],
  not_established: [
    'This is published district-level advice for the printed issue date shown, not a prescription for a field.',
    'The workspace does not diagnose crop symptoms, does not choose a pesticide or a dose, and does not decide whether an operation is safe.',
    'Passages that name another crop (chilli, gram, groundnut, rice) were left out of this brief rather than served for cotton.',
  ],
  sources: ['S57'],
};

const placeMatch = {
  label: 'Delhi, Delhi, India',
  latitude: 28.6139,
  longitude: 77.209,
  admin1: 'Delhi',
  admin2: 'Delhi',
  selection_id: 'geonames:1273294',
};

function placesPayload() {
  return {
    ...HEAD,
    view: 'places.search',
    data: { query: 'Delhi', matches: [placeMatch] },
    sources: [{ source_id: 'S61', product: 'GeoNames India place catalogue', retrieved_at_utc: '2026-09-14T00:00:00Z' }],
    limitations: ['Place records are GeoNames source labels, not authoritative LGD entities.'],
    not_established: ['No reviewed dated administrative crosswalk is applied here.'],
  };
}

/* The recorded air-quality coverage: requested point, returned grid, the source's own current instant.
   The cell distance is a payload value where the payload carries one. */
function airQualityPayload(): Record<string, unknown> {
  return {
    ...HEAD,
    generated_at_utc: '2026-09-15T12:12:36Z',
    view: 'air_quality.point',
    data: {
      parameters: {
        pm2_5: {
          unit: 'μg/m³',
          points: [{ t: '2026-09-15T00:00:00+00:00', v: 40.2 }, { t: '2026-09-15T01:00:00+00:00', v: null }],
          aggregation: 'instant',
          model: 'CAMS via Open-Meteo',
          quality_flags: ['source_value_missing'],
        },
        us_aqi: { unit: 'USAQI', points: [{ t: '2026-09-15T00:00:00+00:00', v: 185 }], aggregation: 'instant', quality_flags: [] },
      },
      current: { pm2_5: 40.2, us_aqi: 185, pm10: null },
      domain: 'CAMS global (Open-Meteo automatic domain)',
      grid: { latitude: 28.599998, longitude: 77.20001 },
      requested: { label: null, latitude: 28.6139, longitude: 77.209 },
      time_basis: 'UTC',
    },
    sources: [{ source_id: 'S69', product: 'CAMS air quality via Open-Meteo', retrieved_at_utc: '2026-09-15T12:12:36Z', sha256_prefix: 'd1e2f3a4b5c6' }],
    coverage: {
      requested_point: { latitude: 28.6139, longitude: 77.209 },
      returned_grid: { latitude: 28.599998, longitude: 77.20001 },
      time_basis: 'UTC',
      domain: 'CAMS global (Open-Meteo automatic domain)',
      current: { pm2_5: 40.2, us_aqi: 185 },
      grid_distance_km: 3.962,
    },
    limitations: ['CAMS modelled air quality at a coarse grid cell; it is not a monitor measurement and no ground monitor is connected.'],
    not_established: ["An air-quality index is the source's own index, and no health advice, risk score or official warning is produced from it."],
  };
}

async function nameAPlace(name = 'Delhi') {
  const input = screen.getByLabelText('Name a place');
  await userEvent.type(input, name);
  const choice = await screen.findByRole('button', { name: new RegExp(name + ', ' + name) });
  await userEvent.click(choice);
}

async function nameADistrict(region = 'Ahmedabad', extra: Record<string, string> = {}) {
  await userEvent.type(screen.getByLabelText('District or region (required)'), region);
  await userEvent.type(screen.getByLabelText('State as published'), extra.state || 'Gujarat');
  await userEvent.type(screen.getByLabelText('Crop'), extra.crop || 'cotton');
  await userEvent.type(screen.getByLabelText('Growth stage'), extra.stage || 'squaring');
  await userEvent.click(screen.getByRole('button', { name: 'Read the published brief' }));
}

describe('the Farm advisories surface', () => {
  it('renders the directory rows it was given, reads the selected state, and filters only the rows already read', async () => {
    const askedStates: (string | null)[] = [];
    server.use(
      http.get('/api/advisories/states', () => HttpResponse.json(statesPayload)),
      http.get('/api/advisories/districts', ({ request }) => {
        const state = new URL(request.url).searchParams.get('state');
        askedStates.push(state);
        return HttpResponse.json(state === 'bihar' ? biharPayload : districtsPayload);
      }),
    );
    const { container } = mount(<AdvisoriesSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Farm advisories' })).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);

    const states = within(await screen.findByTestId('advisories-states'));
    expect(states.getByRole('rowheader', { name: 'Gujarat' })).toBeInTheDocument();
    expect(states.getByRole('rowheader', { name: 'Bihar' })).toBeInTheDocument();

    // The first state row the payload returned selects the state, and its districts are read for it.
    const districts = within(await screen.findByTestId('advisories-districts'));
    expect(districts.getByRole('rowheader', { name: 'Ahmedabad' })).toBeInTheDocument();
    expect(districts.getByRole('rowheader', { name: 'Surat' })).toBeInTheDocument();
    expect(askedStates).toEqual(['gujarat']);
    expect(container.querySelectorAll('table').length).toBeGreaterThan(1);

    // The filter runs in this browser: the publisher is not asked again, and the count says so.
    const count = screen.getByTestId('advisories-count');
    expect(count).toHaveAttribute('role', 'status');
    expect(count).toHaveTextContent('Showing 2 district rows of 2 district rows read for this state.');
    await userEvent.type(screen.getByLabelText('District name contains'), 'Surat');
    expect(count).toHaveTextContent('Showing 1 district row of 2 district rows read for this state.');
    expect(screen.getByText(/This filter runs in this browser over the 2 district rows this read returned for Gujarat/)).toBeInTheDocument();
    expect(askedStates).toEqual(['gujarat']);
    const filtered = within(screen.getByTestId('advisories-districts'));
    expect(filtered.getByRole('rowheader', { name: 'Surat' })).toBeInTheDocument();
    expect(filtered.queryByRole('rowheader', { name: 'Ahmedabad' })).toBeNull();

    // A different state is the only thing that re-reads the district directory.
    await userEvent.clear(screen.getByLabelText('District name contains'));
    await userEvent.selectOptions(screen.getByLabelText('State to read districts for'), 'bihar');
    expect(within(await screen.findByTestId('advisories-districts')).getByRole('rowheader', { name: 'Patna' })).toBeInTheDocument();
    expect(askedStates).toEqual(['gujarat', 'bihar']);

    expect(screen.getByText('Listed entries do not prove a currently issued bulletin.')).toBeInTheDocument();
    expect(screen.getByText('A listed state is a directory entry, not proof that a bulletin was issued today.')).toBeInTheDocument();
    expect(screen.getByTestId('advisories-standing')).toHaveTextContent('not a field recommendation');
    expect(screen.getByTestId('advisories-standing')).toHaveTextContent('not issued');
  });

  it('asks for a district and does not read a brief from a coordinate when none is named', async () => {
    const briefRequests: string[] = [];
    server.use(
      http.get('/api/advisories/states', () => HttpResponse.json(statesPayload)),
      http.get('/api/advisories/districts', () => HttpResponse.json(districtsPayload)),
      http.get('/api/advisories/brief', ({ request }) => {
        briefRequests.push(request.url);
        return HttpResponse.json(briefPayload);
      }),
    );
    mount(<AdvisoriesSurface />);
    await screen.findByTestId('advisories-districts');

    expect(screen.getByTestId('advisories-brief-idle')).toHaveTextContent('No district has been named yet');
    expect(screen.getByTestId('advisories-standing')).toHaveTextContent('no pesticide dosage and no irrigation decision is made here');
    // The surface carries the engine's own refusal, and it refuses rather than guessing.
    expect(screen.getByText(/the workspace will not guess one from a coordinate/)).toBeInTheDocument();

    // A coordinate alone is named, and the district field is empty: the brief is refused, not inferred.
    await userEvent.click(screen.getByRole('button', { name: 'Read the published brief' }));
    expect(await screen.findByTestId('advisories-refusal')).toHaveTextContent('the workspace will not guess one from a coordinate');
    expect(briefRequests).toEqual([]);
    expect(screen.queryByTestId('advisories-passages')).toBeNull();
  });

  it('renders the brief’s own sections, its forecast context and every line it does not establish', async () => {
    const briefRequests: string[] = [];
    server.use(
      http.get('/api/advisories/states', () => HttpResponse.json(statesPayload)),
      http.get('/api/advisories/districts', () => HttpResponse.json(districtsPayload)),
      http.get('/api/advisories/brief', ({ request }) => {
        briefRequests.push(request.url);
        return HttpResponse.json(briefPayload);
      }),
    );
    mount(<AdvisoriesSurface />);
    await screen.findByTestId('advisories-districts');
    await nameADistrict();

    const identity = within(await screen.findByTestId('advisories-brief-identity'));
    expect(identity.getByText('district_agromet (district) for Ahmedabad')).toBeInTheDocument();
    expect(identity.getByText('1')).toBeInTheDocument();
    expect(identity.getByText('23.02579, 72.58727')).toBeInTheDocument();
    // The district was named by the reader, so the brief route was asked for exactly that district.
    expect(briefRequests).toHaveLength(1);
    expect(new URL(briefRequests[0]).searchParams.get('region')).toBe('Ahmedabad');
    expect(new URL(briefRequests[0]).searchParams.get('crop')).toBe('cotton');

    const passages = within(screen.getByTestId('advisories-passages'));
    expect(passages.getByText(/page 3 · printed 2026-09-11/)).toBeInTheDocument();
    expect(passages.getByText('cotton / squaring')).toBeInTheDocument();
    expect(passages.getByText(/If irrigation facilities are available then apply need based irrigation/)).toBeInTheDocument();

    expect(screen.getByText('If the infestation is severe, spray')).toBeInTheDocument();
    const forecast = within(screen.getByTestId('advisories-forecast'));
    expect(forecast.getByRole('rowheader', { name: 'temperature_2m' })).toBeInTheDocument();
    expect(forecast.getByText('°C')).toBeInTheDocument();
    expect(forecast.getByText('24')).toBeInTheDocument();
    expect(screen.getByText(/model forecast for a grid cell, not an observation of the field, and not an instruction/)).toBeInTheDocument();
    expect(screen.getByText(/Status as returned: retrieved/)).toBeInTheDocument();

    // Every not-established line the brief carries is visible, not folded into a tooltip.
    expect(screen.getByText('This is published district-level advice for the printed issue date shown, not a prescription for a field.')).toBeInTheDocument();
    expect(screen.getByText(/The workspace does not diagnose crop symptoms, does not choose a pesticide or a dose/)).toBeInTheDocument();
    expect(screen.getByText(/were left out of this brief rather than served for cotton/)).toBeInTheDocument();
    // The brief names its source identifiers, and they are shown as source rows.
    expect(screen.getAllByText('S57').length).toBeGreaterThan(0);
    expect(screen.getByText(/no limitation line/)).toBeInTheDocument();
  });

  it('states a failed directory read as that failure, with a retry control', async () => {
    server.use(http.get('/api/advisories/states', () => HttpResponse.json({ error: 'the store could not be opened' }, { status: 503 })));
    mount(<AdvisoriesSurface />);

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the store could not be opened');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
  });
});

describe('the Air quality surface', () => {
  it('renders the modelled parameters with their units, the cell and its distance, and says it is a model', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/air-quality', () => HttpResponse.json(airQualityPayload())),
    );
    const { container } = mount(<AirQualitySurface />);
    await screen.findByLabelText('Name a place');
    expect(screen.getByText('No point was named, so no air-quality read was requested.')).toBeInTheDocument();

    await nameAPlace();

    expect(await screen.findByRole('heading', { level: 1, name: 'Air quality' })).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);

    const cell = within(await screen.findByTestId('air-quality-cell'));
    // Both coordinate pairs are rendered as the payload stated them, never recomputed or rounded here.
    expect(cell.getByText(/Requested coordinates/).nextSibling).toHaveTextContent('28.6139, 77.209');
    expect(cell.getByText(/Cell identity as returned/).nextSibling).toHaveTextContent('28.599998, 77.20001');
    expect(cell.getByText(/Requested point as the reading returned it/).nextSibling).toHaveTextContent('28.6139, 77.209');
    expect(cell.getByText('3.962 km')).toBeInTheDocument();
    expect(cell.getByText('CAMS global (Open-Meteo automatic domain)')).toBeInTheDocument();

    // The model-not-monitor statement, with the no-advice and no-invented-category clauses it must keep.
    const statement = screen.getByTestId('air-quality-model-not-monitor');
    expect(statement).toHaveTextContent('This is a model, not a monitor, and not an observation');
    expect(statement).toHaveTextContent('The cell is a grid cell, not the point you named, and its distance from the requested point is stated above');
    expect(statement).toHaveTextContent('No health or exposure advice is produced here');
    expect(statement).toHaveTextContent('An AQI category is shown only where the payload itself states one');

    const table = screen.getByTestId('air-quality-table');
    expect(table).toHaveTextContent('Unit as returned');
    const pm = within(table).getByRole('rowheader', { name: 'pm2_5' }).closest('tr') as HTMLElement;
    expect(pm).toHaveTextContent('μg/m³');
    expect(pm).toHaveTextContent('40.2');
    const index = within(table).getByRole('rowheader', { name: 'us_aqi' }).closest('tr') as HTMLElement;
    expect(index).toHaveTextContent('USAQI');
    expect(index).toHaveTextContent('185');

    // pm10 is in the payload's own current block with no value: that is a missing reading, not a zero.
    const missing = within(table).getByRole('rowheader', { name: 'pm10' }).closest('tr') as HTMLElement;
    expect(within(missing).getByText('not recorded for this cell')).toBeInTheDocument();
    expect(missing).toHaveTextContent('unit not stated by the source');
    expect(screen.getByTestId('air-quality-count')).toHaveAttribute('role', 'status');
    expect(screen.getByTestId('air-quality-count')).toHaveTextContent('3 parameter rows returned for this cell');
    expect(container.querySelectorAll('table').length).toBeGreaterThan(0);

    expect(screen.getByText('CAMS modelled air quality at a coarse grid cell; it is not a monitor measurement and no ground monitor is connected.')).toBeInTheDocument();
    expect(screen.getByText(/An air-quality index is the source's own index, and no health advice, risk score or official warning is produced from it./)).toBeInTheDocument();
    expect(screen.getByText('S69')).toBeInTheDocument();
  });

  it('records a cell distance the payload does not state as absent, never as a number computed here', async () => {
    const payload = airQualityPayload();
    const { grid_distance_km: _omitted, ...coverage } = payload.coverage as Record<string, unknown>;
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/air-quality', () => HttpResponse.json({ ...payload, coverage })),
    );
    mount(<AirQualitySurface />);
    await nameAPlace();

    const cell = within(await screen.findByTestId('air-quality-cell'));
    expect(cell.getByText(/Cell distance from the requested point/).nextSibling).toHaveTextContent('not recorded');
    expect(screen.getByText(/A distance this read does not state is recorded as absent here; it is never computed from the two coordinate pairs./)).toBeInTheDocument();
  });

  it('states a failed model read as that failure, with a retry control', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/air-quality', () => HttpResponse.json({ error: 'the store could not be opened' }, { status: 503 })),
    );
    mount(<AirQualitySurface />);
    await nameAPlace();

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the store could not be opened');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
  });
});
