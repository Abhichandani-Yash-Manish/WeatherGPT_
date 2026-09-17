/* The map-interaction gaps the port ledger could not claim when the React map was written, held here
   against the payloads tests/test_suite_ui.js recorded for vanilla check 19 and vanilla check 20 in part:

   - check 19a a pointer readout: moving the pointer over a drawn feature, or focusing it, states in words
              what the read returned for it — the district, its state, the colour the payload stated and
              its hazard wording — and states the absence of either rather than filling it in;
   - check 19b a city that states its own name and coordinates is made the working place by clicking it,
              the readout says it was set, and the place is what GET /api/now answers for: the route is
              read with exactly the coordinates the vendored geometry carries. A feature that states no
              name is refused, because a working place is never inferred from a coordinate;
   - check 20  the districts are one tab stop, the arrow keys move the cursor between them, Home and End
              jump to the first and last, and each stop announces its own district and colour.

   The district polygons, the place features and the ledger the /api/now check answers with are built from
   the constants tests/test_suite_ui.js records; the recorded vendored district geometry states no colour
   of its own, so the warning day that suite recorded for PATNA (green, "No warning in this product") is
   carried on the feature properties, which is the payload this layer read returns. The React map draws
   only the colours a feature states; the warning-row join is a separate vanilla rule and is not claimed
   here. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as MapSurface } from './MapSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const HEAD = {
  schema_version: 'product-view-v1',
  generated_at_utc: '2026-09-14T18:00:00+00:00',
  status: 'ok',
};

const layersPayload = {
  ...HEAD,
  view: 'map.layers',
  data: {
    build_id: 'basemap-v1-test',
    layers: [
      { name: 'districts', file: 'districts.geojson', kind: 'districts', bytes: 10, budget_bytes: 20 },
      { name: 'places', file: 'places.geojson', kind: 'places', bytes: 10, budget_bytes: 20 },
    ],
    district_polygons: 756,
    skipped_without_a_name: 1,
    attribution: 'IMD',
  },
  sources: [],
  coverage: { layers: 2 },
  limitations: ['A stated limit of this view.'],
  not_established: ['Something not established here.'],
};

const districtsLayer = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { k: 'PATNA', n: 'PATNA', s: 'BIHAR', colour: 'green', hazards: ['No warning in this product'] },
      geometry: { type: 'Polygon', coordinates: [[[85, 25], [86, 25], [86, 26], [85, 26], [85, 25]]] },
    },
    {
      type: 'Feature',
      properties: { k: 'LAKSHADWEEP', n: 'LAKSHADWEEP', s: null, p: 1 },
      geometry: { type: 'Polygon', coordinates: [[[71, 7], [74, 7], [74, 12], [71, 12], [71, 7]]] },
    },
  ],
};

const placesLayer = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { n: 'Patna', t: 'PPLA', a: 'Bihar' },
      geometry: { type: 'Point', coordinates: [85.1, 25.6] },
    },
    {
      type: 'Feature',
      properties: { t: 'PPL' },
      geometry: { type: 'Point', coordinates: [86.2, 26.1] },
    },
  ],
};

/* The recorded now.composed envelope, answering for the point the chosen city states. */
const nowPayload = {
  ...HEAD,
  view: 'now.composed',
  data: {
    schema_version: 'now-v1',
    generated_at_utc: '2026-09-14T18:00:00+00:00',
    point: { latitude: 25.6, longitude: 85.1, label: null },
    observed: {
      status: 'ok',
      rows_in_radius: 1,
      stations: [
        {
          kind: 'metar', network: 'metar', name: 'PATNA', station_code: 'VEPT', distance_km: 6.9,
          observed_at_utc: '2026-09-14T17:00:00+00:00', age_minutes: 25.8, stale: false,
          parameters: [{ field: 'temp', value: 26, unit: null, unit_stated_by_source: false }],
          source_id: 'S63',
        },
      ],
    },
    in_force: {
      status: 'ok', district: 'PATNA', state: 'BIHAR', day: 1, day_label: '14 Sep 2026',
      starts_utc: '2026-09-13T18:30:00+00:00', ends_utc: '2026-09-14T18:30:00+00:00',
      colour: 'green', hazards: ['No warning in this product'], quiet: true,
      status_line: 'Official district warning: green - No warning in this product',
      issued_at_utc: '2026-09-14T06:00:00+00:00', source_id: 'S63', source_locator: '$.features[112]',
    },
    summary: 'Freshest station report here: PATNA, 6.9 km away.',
    not_connected: ['radar and satellite imagery'],
    limitations: ['A quiet day is not an all-clear.'],
    not_established: [],
  },
  sources: [{ source_id: 'S63', product: 'IMD district warning product' }],
  coverage: { stations_in_radius: 1 },
  limitations: ['The right-now view is composed from the products it names.'],
  not_established: ['It is not a forecast.'],
};

function serveDistricts() {
  server.use(
    http.get('/api/map/layers', () => HttpResponse.json(layersPayload)),
    http.get('/api/map/static/districts', () => HttpResponse.json(districtsLayer)),
  );
}

describe('the map pointer readout', () => {
  it('reads out the district, its colour and its hazard wording under the pointer and on focus', async () => {
    serveDistricts();
    const { container } = mount(<MapSurface />);

    const readout = await screen.findByTestId('map-readout');
    expect(readout).toHaveTextContent('Hover or focus a drawn feature to read out what the payload states about it.');
    const figure = await screen.findByTestId('map-figure');
    const paths = figure.querySelectorAll('path');
    expect(paths).toHaveLength(2);

    await userEvent.hover(paths[0]);
    expect(readout).toHaveTextContent('PATNA, BIHAR: green');
    expect(readout).toHaveTextContent('No warning in this product');

    await userEvent.hover(paths[1]);
    expect(readout).toHaveTextContent('LAKSHADWEEP: colour not supplied');
    expect(readout).toHaveTextContent('no hazard wording published in these properties');
    expect(readout).toHaveTextContent('(the source supplies a bounding box for this feature, not a coastline)');

    /* The readout is reachable without a pointer: each drawn feature carries the readout as its own label
       and focus moves the line. */
    expect(paths[0]).toHaveAccessibleName(/PATNA, BIHAR: green/);
    act(() => { paths[1].focus(); });
    expect(readout).toHaveTextContent('LAKSHADWEEP: colour not supplied');

    const notes = within(container).getAllByText(/Keyboard: Tab reaches the figure/);
    expect(notes).toHaveLength(1);
  });

  it('moves one district tab stop with the arrow keys, Home and End, announcing every stop', async () => {
    serveDistricts();
    mount(<MapSurface />);

    const figure = await screen.findByTestId('map-figure');
    const readout = await screen.findByTestId('map-readout');
    const paths = figure.querySelectorAll('path');
    expect(figure.querySelectorAll('[tabindex="0"]')).toHaveLength(1);
    expect(paths[0]).toHaveAttribute('tabindex', '0');
    expect(paths[1]).toHaveAttribute('tabindex', '-1');

    await userEvent.tab(); // the layer selector
    await userEvent.tab(); // the figure's one tab stop
    expect(document.activeElement).toBe(paths[0]);
    expect(readout).toHaveTextContent('PATNA, BIHAR: green');

    await userEvent.keyboard('{ArrowRight}');
    expect(document.activeElement).toBe(paths[1]);
    expect(paths[1]).toHaveAttribute('tabindex', '0');
    expect(paths[0]).toHaveAttribute('tabindex', '-1');
    expect(figure.querySelectorAll('[tabindex="0"]')).toHaveLength(1);
    expect(readout).toHaveTextContent('LAKSHADWEEP');
    expect(readout).toHaveTextContent('colour not supplied');

    await userEvent.keyboard('{End}');
    expect(document.activeElement).toBe(paths[1]);
    await userEvent.keyboard('{Home}');
    expect(document.activeElement).toBe(paths[0]);
    expect(paths[0]).toHaveAttribute('tabindex', '0');
    expect(paths[1]).toHaveAttribute('tabindex', '-1');

    /* One tab stop means Tab leaves the figure rather than walking every feature. */
    await userEvent.tab();
    expect(figure.contains(document.activeElement)).toBe(false);
  });

  it('sets the working place from a city the layer states and reads /api/now for exactly those coordinates', async () => {
    const requested: string[] = [];
    serveDistricts();
    server.use(
      http.get('/api/map/static/places', () => HttpResponse.json(placesLayer)),
      http.get('/api/now', ({ request }) => {
        requested.push(new URL(request.url).search);
        return HttpResponse.json(nowPayload);
      }),
    );
    mount(<MapSurface />);

    await screen.findByTestId('map-figure');
    await userEvent.selectOptions(screen.getByLabelText('Layer to draw'), 'places');
    const figure = await screen.findByTestId('map-figure');
    await waitFor(() => expect(figure.querySelectorAll('circle')).toHaveLength(2));
    const circles = figure.querySelectorAll('circle');

    await userEvent.hover(circles[0]);
    expect(screen.getByTestId('map-readout')).toHaveTextContent('Place Patna, Bihar \u00b7 25.6, 85.1');
    expect(screen.getByTestId('map-readout')).toHaveTextContent('select it to make it the working place');

    expect(requested).toHaveLength(0);
    await userEvent.click(circles[0]);
    expect(screen.getByTestId('map-readout')).toHaveTextContent(
      'Working place set to Patna, Bihar at the coordinates the vendored geometry carries (25.6, 85.1).',
    );
    await waitFor(() => expect(requested).toHaveLength(1));
    expect(requested[0]).toContain('lat=25.6');
    expect(requested[0]).toContain('lon=85.1');

    const chosen = await screen.findByTestId('map-chosen-place');
    expect(chosen).toHaveTextContent('Patna, Bihar');
    expect(chosen).toHaveTextContent('25.6, 85.1');
    expect(await screen.findByTestId('map-now-summary')).toHaveTextContent('Freshest station report here: PATNA, 6.9 km away.');
    expect(screen.getByText('Official district warning: green - No warning in this product')).toBeInTheDocument();
    /* The reading keeps its own limit and the limit the envelope carried. */
    expect(screen.getByText('A quiet day is not an all-clear.')).toBeInTheDocument();
    expect(screen.getByText('The right-now view is composed from the products it names.')).toBeInTheDocument();
  });

  it('refuses to name a working place from a coordinate when the feature states no name', async () => {
    const requested: string[] = [];
    serveDistricts();
    server.use(
      http.get('/api/map/static/places', () => HttpResponse.json(placesLayer)),
      http.get('/api/now', ({ request }) => {
        requested.push(new URL(request.url).search);
        return HttpResponse.json(nowPayload);
      }),
    );
    mount(<MapSurface />);

    await screen.findByTestId('map-figure');
    await userEvent.selectOptions(screen.getByLabelText('Layer to draw'), 'places');
    const figure = await screen.findByTestId('map-figure');
    await waitFor(() => expect(figure.querySelectorAll('circle')).toHaveLength(2));
    const unnamed = figure.querySelectorAll('circle')[1];

    expect(unnamed).toHaveAttribute('role', 'img');
    await userEvent.hover(unnamed);
    expect(screen.getByTestId('map-readout')).toHaveTextContent('Point place name not stated in these properties \u00b7 26.1, 86.2');
    expect(screen.getByTestId('map-readout')).toHaveTextContent('this feature states no name of its own, so it cannot be made the working place');

    await userEvent.click(unnamed);
    expect(screen.queryByTestId('map-chosen-place')).toBeNull();
    expect(requested).toHaveLength(0);
  });
});
