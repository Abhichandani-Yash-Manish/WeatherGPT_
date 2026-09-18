/* The Map and What-changed surfaces, checked against payloads shaped like the recorded ones.

   What the checks may not lose: a figure that fills a shape only with a colour the feature itself
   stated, a feature that stated none drawn as an outline and named as such, the schematic-versus-basemap
   sentence, both printed editions with their vintages, no delta where the payload stated none, the
   payload's own statements verbatim, and a failed read stated as a failure with a retry. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as ChangesSurface } from './ChangesSurface';
import { Surface as MapSurface } from './MapSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const HEAD = {
  schema_version: 'product-view-v1',
  generated_at_utc: '2026-09-17T05:30:00Z',
  status: 'ok',
};

const SOURCE_S63 = {
  source_id: 'S63',
  product: 'Vendored basemap geometry',
  retrieved_at_utc: '2026-09-14T16:23:00Z',
  sha256_prefix: 'c8cdc1e82baf',
};

const layersPayload = {
  ...HEAD,
  view: 'map.layers',
  data: {
    build_id: 'basemap-v1-testbuild',
    layers: [
      { name: 'districts', file: 'districts.geojson', kind: 'districts', bytes: 1529712, budget_bytes: 3500000 },
      { name: 'places', file: 'places.geojson', bytes: 26744 },
    ],
    join_file: 'district-join.json',
    attribution: 'Geometry: India Meteorological Department GeoServer, terms unresolved, local prototype use.',
    district_polygons: 2,
    skipped_without_a_name: 1,
  },
  sources: [SOURCE_S63],
  coverage: { layers: 2 },
  limitations: ['Simplified for display; not a survey boundary and not an LGD crosswalk.'],
  not_established: ['The basemap is display geometry, not a survey boundary and not an LGD crosswalk.'],
};

const districtsLayer = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { k: 'PATNA', n: 'Patna', s: 'Bihar', colour: 'orange', hazards: ['Heavy rain'] },
      geometry: { type: 'Polygon', coordinates: [[[85.0, 25.4], [85.3, 25.4], [85.3, 25.7], [85.0, 25.7], [85.0, 25.4]]] },
    },
    {
      type: 'Feature',
      properties: { k: 'SURAT', n: 'Surat', s: 'Gujarat', color: 'yellow', wording: 'Thunderstorm likely.' },
      geometry: {
        type: 'MultiPolygon',
        coordinates: [[[[72.6, 21.0], [72.9, 21.0], [72.9, 21.3], [72.6, 21.3], [72.6, 21.0]]]],
      },
    },
    {
      type: 'Feature',
      properties: { k: 'GAYA', n: 'Gaya', s: 'Bihar' },
      geometry: { type: 'Polygon', coordinates: [[[84.8, 24.7], [85.1, 24.7], [85.1, 24.9], [84.8, 24.9], [84.8, 24.7]]] },
    },
  ],
};

const placesLayer = {
  type: 'FeatureCollection',
  features: [
    { type: 'Feature', properties: { n: 'Agartala', t: 'PPLA', a: 'Tripura' }, geometry: { type: 'Point', coordinates: [91.2794, 23.8361] } },
    { type: 'Feature', properties: { n: 'Kochi', t: 'PPLA2', a: 'Kerala' }, geometry: { type: 'Point', coordinates: [76.2673, 9.9312] } },
  ],
};

describe('the Map surface', () => {
  it('draws only the colours the features stated, and lists the same features in the table', async () => {
    server.use(
      http.get('/api/map/layers', () => HttpResponse.json(layersPayload)),
      http.get('/api/map/static/districts', () => HttpResponse.json(districtsLayer)),
    );
    mount(<MapSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Map' })).toBeInTheDocument();
    const figure = await screen.findByTestId('map-figure');
    // Three features were returned and two stated a hazard colour: exactly two shapes are filled with one.
    expect(figure.querySelectorAll('path[data-colour]')).toHaveLength(2);
    expect(figure.querySelector('path[data-colour="orange"]')).toHaveAttribute('fill', 'currentColor');
    expect(figure.querySelector('path[data-colour="yellow"]')).not.toBeNull();
    // Gaya stated no colour: it is drawn as an outline and is not given a colour attribute.
    expect(figure.querySelectorAll('path[fill="none"]')).toHaveLength(1);
    expect(figure.querySelector('path[fill="none"]')?.hasAttribute('data-colour')).toBe(false);
    expect(figure.getAttribute('aria-label')).toContain('Schematic of the districts layer');
    expect(figure.getAttribute('aria-label')).toContain('3 features');

    const tableElement = screen.getByTestId('map-features');
    const table = within(tableElement);
    ['Patna', 'Surat', 'Gaya'].forEach(name => expect(table.getByText(name)).toBeInTheDocument());
    expect(table.getByText('Heavy rain')).toBeInTheDocument();
    expect(table.getByText('Thunderstorm likely.')).toBeInTheDocument();
    expect(table.getByText('colour not stated')).toBeInTheDocument();
    expect(table.getByText('outline only: no colour stated in these properties')).toBeInTheDocument();
    // The table draws a colour only where the feature stated one, exactly as the figure does.
    expect(tableElement.querySelectorAll('[data-colour]')).toHaveLength(2);
    expect(tableElement.querySelectorAll('[data-colour="orange"]')).toHaveLength(1);
    expect(tableElement.querySelectorAll('[data-colour="yellow"]')).toHaveLength(1);

    // The surface says what kind of drawing this is, and how many features it drew.
    expect(screen.getByText(/not a cartographic basemap, not a location map and not a warning service/)).toBeInTheDocument();
    const count = screen.getByTestId('map-count');
    expect(count).toHaveAttribute('role', 'status');
    expect(count).toHaveTextContent('This figure drew 3 features from the chosen layer');
    // A layer field the manifest did not state is shown as not recorded, never filled in.
    const layerTable = within(screen.getByTestId('map-layers'));
    const placesRow = layerTable.getByRole('rowheader', { name: 'places' }).closest('tr') as HTMLTableRowElement;
    expect(placesRow).toHaveTextContent('places.geojson');
    expect(within(placesRow).getAllByText('not recorded')).toHaveLength(2);
    expect(screen.getByTestId('map-manifest')).toHaveTextContent('basemap-v1-testbuild');
    expect(screen.getByText('Simplified for display; not a survey boundary and not an LGD crosswalk.')).toBeInTheDocument();
    expect(screen.getByText('The basemap is display geometry, not a survey boundary and not an LGD crosswalk.')).toBeInTheDocument();
    expect(screen.getByText('S63')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  });


  it('opens on the district layer and fills a district from the warning row it is joined to', async () => {
    /* The live districts layer states a key, a name and a state and no colour at all, so before this join the
       one layer that carries the warning colours could only ever be drawn as outlines. The row below states a
       colour for the same key, and the join is what puts it on the figure. */
    const warnings = {
      ...HEAD,
      view: 'warnings.national',
      data: {
        districts: [
          { key: 'PATNA', district: 'Patna', state: 'Bihar', bulletin_date: '2026-09-15', bulletin_age_days: 2,
            days: [{ day: 3, label: '17 Sep 2026', date_local: '2026-09-17', colour: 'red', hazards: ['Heavy rain at isolated places'],
              quiet: false, is_today: true }] },
        ],
        newest_bulletin_date_in_this_read: '2026-09-15',
      },
    };
    server.use(
      http.get('/api/warnings/national', () => HttpResponse.json(warnings)),
      http.get('/api/map/layers', () => HttpResponse.json(layersPayload)),
      http.get('/api/map/static/districts', () => HttpResponse.json(districtsLayer)),
      http.get('/api/map/static/places', () => HttpResponse.json(placesLayer)),
    );
    const { container } = mount(<MapSurface />);

    expect(await screen.findByTestId('map-figure')).toBeInTheDocument();
    expect(screen.getByLabelText('Layer to draw')).toHaveValue('districts');
    /* The row's red replaces the orange the feature states on its own: the joined read is the newer one. */
    await waitFor(() => expect(container.querySelector('path[data-colour="red"]')).not.toBeNull());
    expect(screen.getByText(/joined to the warning row for this key/)).toBeInTheDocument();

    await userEvent.click(container.querySelector('path[data-colour="red"]') as Element);
    const inspector = await screen.findByTestId('today-inspector-district');
    expect(within(inspector).getByText('Patna')).toBeInTheDocument();
    expect(within(inspector).getByText(/Heavy rain at isolated places/)).toBeInTheDocument();
    expect(within(inspector).getByRole('link', { name: /Open in Warnings/ })).toHaveAttribute('href', '#/warnings?district=Patna');

    /* The day selector moves the join off the day that covers today, and the figure follows it. */
    await userEvent.selectOptions(screen.getByLabelText('Day to inspect'), '2');
    await waitFor(() => expect(container.querySelector('path[data-colour="red"]')).toBeNull());
  });

  it('draws the layer the reader chooses, and states when no feature carried a colour', async () => {
    server.use(
      http.get('/api/map/layers', () => HttpResponse.json(layersPayload)),
      http.get('/api/map/static/districts', () => HttpResponse.json(districtsLayer)),
      http.get('/api/map/static/places', () => HttpResponse.json(placesLayer)),
    );
    mount(<MapSurface />);
    expect(await screen.findByTestId('map-figure')).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText('Layer to draw'), 'places');

    /* Scoped to the figure: the shell's own icons are SVGs too, and a decorative circle in a header
       is not a drawn feature. */
    const figure = screen.getByTestId('map-figure');
    await waitFor(() => expect(figure.querySelectorAll('circle')).toHaveLength(2));
    expect(figure.querySelectorAll('circle[data-colour]')).toHaveLength(0);
    const count = screen.getByTestId('map-count');
    expect(count).toHaveTextContent('No feature carried a colour');
    const table = within(screen.getByTestId('map-features'));
    expect(table.getByText('Agartala')).toBeInTheDocument();
    expect(table.getByText('Tripura')).toBeInTheDocument();
    expect(table.queryByText('Patna')).toBeNull();
  });

  it('states a failed layer read as that failure, with a retry, and keeps the manifest standing', async () => {
    server.use(
      http.get('/api/map/layers', () => HttpResponse.json(layersPayload)),
      http.get('/api/map/static/districts', () =>
        HttpResponse.json({ error: 'the basemap build could not be read' }, { status: 503 })),
    );
    mount(<MapSurface />);

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the basemap build could not be read');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
    expect(screen.getByTestId('map-layers')).toBeInTheDocument();
    expect(screen.queryByTestId('map-figure')).toBeNull();
  });

  it('states a failed manifest read as the store being unavailable, with a retry', async () => {
    server.use(http.get('/api/map/layers', () => HttpResponse.json({ error: 'the store is unavailable' }, { status: 503 })));
    mount(<MapSurface />);

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
  });
});

const placeMatch = {
  label: 'Patna, Patna, Bihar',
  latitude: 25.5941,
  longitude: 85.1376,
  admin1: 'Bihar',
  admin2: 'Patna',
  selection_id: 'geonames:1260086',
};

function placesPayload() {
  return {
    ...HEAD,
    view: 'places.search',
    data: { query: 'Patna', matches: [placeMatch] },
    sources: [{ source_id: 'S61', product: 'GeoNames India place catalogue', retrieved_at_utc: '2026-09-14T00:00:00Z' }],
    limitations: ['Place records are GeoNames source labels, not authoritative LGD entities.'],
    not_established: ['No reviewed dated administrative crosswalk is applied here.'],
  };
}

async function nameAPlace() {
  const input = screen.getByLabelText('Name a place');
  await userEvent.type(input, 'Patna');
  const choice = await screen.findByRole('button', { name: /Patna, Patna, Bihar/ });
  await userEvent.click(choice);
}

const changesPayload = {
  ...HEAD,
  view: 'forecast.changes',
  status: 'partial',
  data: {
    point: { latitude: 25.5941, longitude: 85.1376 },
    requested_point: { latitude: 25.5941, longitude: 85.1376 },
    retrievals: [
      { retrieved_at_utc: '2026-09-16T18:00:00Z', product: 'forecast', request_date: '2026-09-16', response_sha256_prefix: 'aaaa1111bbbb' },
      { retrieved_at_utc: '2026-09-17T05:00:00Z', product: 'forecast', request_date: '2026-09-17', response_sha256_prefix: 'cccc2222dddd' },
    ],
    retrieval_count: 2,
    parameters: {
      temperature_2m: {
        unit: '°C',
        valid_hours: 4,
        example: {
          valid_time_utc: '2026-09-17T09:00:00Z',
          first_value: 29.4,
          last_value: 30.1,
          first_retrieved_utc: '2026-09-16T18:00:00Z',
          last_retrieved_utc: '2026-09-17T05:00:00Z',
        },
      },
      wind_speed_10m: {
        unit: 'km/h',
        valid_hours: 4,
        max_abs_change: 3.4,
        example: {
          valid_time_utc: '2026-09-17T09:00:00Z',
          first_value: 11.2,
          last_value: 14.6,
          first_retrieved_utc: '2026-09-16T18:00:00Z',
          last_retrieved_utc: '2026-09-17T05:00:00Z',
        },
      },
    },
    overlapping_valid_hours: 8,
    interpretation: 'vintage_variance_not_skill',
  },
  sources: [{ source_id: 'S21', product: 'weather_forecast', retrieved_at_utc: '2026-09-17T05:00:00Z', sha256_prefix: 'cccc2222dddd' }],
  coverage: {
    requested_point: { latitude: 25.59, longitude: 85.14 },
    stored_point: { latitude: 25.59, longitude: 85.14 },
    retrievals: 2,
    overlapping_valid_hours: 8,
  },
  limitations: [
    'This compares stored retrievals of the same valid hour; it conflates model updates with shorter horizons because run identity is not exposed.',
  ],
  not_established: ['Forecast skill, calibration and accuracy: no observation or verified analysis is matched here.'],
};

const publishedPayload = {
  ...HEAD,
  view: 'warnings.place',
  data: {
    district: 'Patna',
    state: 'Bihar',
    issued_at_utc: '2026-09-16T12:00:00Z',
    headline: 'A yellow warning is published for this district',
    severity: 'yellow',
    overlap: 1.0,
    days: [
      {
        day: 2,
        day_label: 'Day 2',
        date_utc: '2026-09-17',
        colour: 'yellow',
        hazards: ['Thunderstorm'],
        wording: 'Thunderstorm/lightning/squall',
      },
    ],
  },
  sources: [SOURCE_S63],
  coverage: { district: 'Patna', days: 1 },
  limitations: ['The headline severity is derived from the published day colours and hazards, not a new IMD field.'],
  not_established: ['This is district-level warning guidance, not a flood warning, not a CAP alert and not an all-clear.'],
};

describe('the What changed surface', () => {
  it('prints both printed editions with their vintages, invents no delta, and reads the district product', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/forecast/changes', () => HttpResponse.json(changesPayload)),
      http.get('/api/warnings/place', () => HttpResponse.json(publishedPayload)),
    );
    mount(<ChangesSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'What changed' })).toBeInTheDocument();
    expect(
      screen.getByText('No point was named, so no stored retrieval was compared and no district product was read.'),
    ).toBeInTheDocument();

    await nameAPlace();

    const table = within(await screen.findByTestId('changes-parameters'));
    // What each edition printed, and the two vintages, one row per changed parameter.
    expect(table.getByText('29.4')).toBeInTheDocument();
    expect(table.getByText('30.1')).toBeInTheDocument();
    expect(table.getByText('11.2')).toBeInTheDocument();
    expect(table.getByText('14.6')).toBeInTheDocument();
    expect(table.getAllByText('17 Sep 2026, 14:30 IST').length).toBeGreaterThan(0);
    expect(table.getAllByText('16 Sep 2026, 23:30 IST').length).toBeGreaterThan(0);
    expect(table.getAllByText('17 Sep 2026, 10:30 IST').length).toBeGreaterThan(0);
    // temperature_2m stated no delta: both values stand and no difference is computed here.
    expect(table.getByText('no delta stated by this entry; both printed values stand beside each other')).toBeInTheDocument();
    expect(screen.queryByText('0.7')).toBeNull();
    // wind_speed_10m stated a largest absolute change, which is printed as returned.
    expect(table.getByText(/largest absolute change as returned: 3.4/)).toBeInTheDocument();
    expect(screen.getByText(/is not a skill or accuracy claim/)).toBeInTheDocument();
    const count = screen.getByTestId('changes-count');
    expect(count).toHaveAttribute('role', 'status');
    expect(count).toHaveTextContent('2 parameters with a comparison this read returned, across 2 stored retrievals.');
    // The payload's own statements are rendered verbatim, not summarised away.
    const statements = within(screen.getByTestId('changes-statements'));
    expect(statements.getByText('interpretation')).toBeInTheDocument();
    expect(statements.getByText('vintage_variance_not_skill')).toBeInTheDocument();
    expect(
      screen.getByText(
        'This compares stored retrievals of the same valid hour; it conflates model updates with shorter horizons because run identity is not exposed.',
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Forecast skill, calibration and accuracy: no observation or verified analysis is matched here.'),
    ).toBeInTheDocument();
    expect(within(screen.getByTestId('changes-retrievals')).getByText('aaaa1111bbbb')).toBeInTheDocument();
    // The published district product this change is about is read on its own route.
    const district = within(await screen.findByTestId('changes-district'));
    expect(district.getByText('A yellow warning is published for this district')).toBeInTheDocument();
    expect(district.getByText('16 Sep 2026, 17:30 IST')).toBeInTheDocument();
    expect(within(screen.getByTestId('changes-days')).getByText('Thunderstorm/lightning/squall')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  });

  it('states a failed comparison as the store being unavailable, with a retry', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/forecast/changes', () => HttpResponse.json({ error: 'the store is unavailable' }, { status: 503 })),
      http.get('/api/warnings/place', () => HttpResponse.json(publishedPayload)),
    );
    mount(<ChangesSurface />);
    await screen.findByLabelText('Name a place');
    await nameAPlace();

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
  });
});
