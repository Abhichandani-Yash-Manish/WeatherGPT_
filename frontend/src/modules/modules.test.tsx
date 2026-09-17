/* R3 module surfaces, checked against payloads shaped like the recorded ones.

   Each check asserts what the surface may not lose: the counts the payload stated, an absence rendered
   as an absence, the envelope's limitations and not-established lines in the surface's own voice, a
   failed read stated as a failure with a retry, and a warning colour drawn only where the product
   printed one. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as DocumentsSurface } from './DocumentsSurface';
import { Surface as ForecastSurface } from './ForecastSurface';
import { Surface as ObservationsSurface } from './ObservationsSurface';
import { Surface as SettingsSurface } from './SettingsSurface';
import { Surface as TodaySurface } from './TodaySurface';
import { Surface as WarningsSurface } from './WarningsSurface';

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
  product: 'IMD district warning product',
  layer: 'imd:district_warnings_india',
  retrieved_at_utc: '2026-09-17T05:12:00Z',
  sha256_prefix: 'a1b2c3d4e5f6',
};

const overviewPayload = {
  ...HEAD,
  view: 'overview',
  data: {
    national: {
      districts: 36,
      skipped: 1,
      tally: { red: 2, orange: 5, yellow: 9, green: 20 },
      bulletin_dates: { '2026-09-17': 35, '2026-09-16': 1 },
    },
    radar: { stations: 31, reported: 28 },
    places: [],
  },
  sources: [SOURCE_S63],
  coverage: { features_returned: 37, districts_listed: 36, skipped_without_a_name: 1 },
  limitations: ['Day fields are official hazard code lists, not severity stages.'],
  not_established: ['Origin authentication of the service is not established.'],
};

/* The dashboard's two further reads. The Today surface joins the warning rows to the served geometry by the
   district key, so a suite that mounts it declares both. */
const todayWarningsPayload = {
  ...HEAD,
  view: 'warnings.national',
  status: 'ok',
  data: {
    districts: [
      {
        key: 'PATNA', district: 'PATNA', state: 'BIHAR', bulletin_date: '2026-09-15', bulletin_age_days: 2,
        bulletin_behind_the_newest_read_days: 0, bulletin_is_older_than_this_read: false,
        days: [
          { day: 3, label: '17 Sep 2026', date_local: '2026-09-17', colour: 'yellow', hazard_codes: [5],
            hazards: ['Heavy rain'], quiet: false, is_today: true },
          { day: 4, label: '18 Sep 2026', date_local: '2026-09-18', colour: 'green', hazard_codes: [1],
            hazards: ['No warning in this product'], quiet: true, is_today: false },
        ],
      },
      {
        key: 'SAITUAL', district: 'SAITUAL', state: 'MIZORAM', bulletin_date: '2026-09-11', bulletin_age_days: 6,
        bulletin_behind_the_newest_read_days: 4, bulletin_is_older_than_this_read: true,
        days: [
          { day: 3, label: '17 Sep 2026', date_local: '2026-09-17', colour: null, hazard_codes: [], hazards: [],
            quiet: false, is_today: true },
        ],
      },
      {
        key: 'QUIET', district: 'QUIETVILLE', state: 'BIHAR', bulletin_date: '2026-09-15', bulletin_age_days: 2,
        days: [
          { day: 3, label: '17 Sep 2026', date_local: '2026-09-17', colour: 'green', hazard_codes: [1],
            hazards: ['No warning in this product'], quiet: true, is_today: true },
        ],
      },
    ],
    /* 'orange' is deliberately absent: a colour the tally did not state must read as 'not recorded', not 0. */
    tally: { red: 1, yellow: 1, green: 5, unset: 1 },
    newest_bulletin_date_in_this_read: '2026-09-15',
    districts_behind_the_newest_edition: 1,
    oldest_bulletin_age_days: 6,
  },
  sources: [SOURCE_S63],
  limitations: ['A quiet day means the source published no hazard for that district-day in this product. It is not an all-clear.'],
  not_established: ['Origin authentication of the service is not established.'],
};

function square(west: number, south: number, side: number) {
  return { type: 'Polygon', coordinates: [[[west, south], [west + side, south], [west + side, south + side], [west, south + side], [west, south]]] };
}

const todayGeometryPayload = {
  type: 'FeatureCollection',
  features: [
    { type: 'Feature', properties: { k: 'PATNA', n: 'PATNA', s: 'BIHAR' }, geometry: square(85.0, 25.4, 0.4) },
    { type: 'Feature', properties: { k: 'SAITUAL', n: 'SAITUAL', s: 'MIZORAM' }, geometry: square(92.6, 23.3, 0.4) },
    { type: 'Feature', properties: { k: 'QUIET', n: 'QUIETVILLE', s: 'BIHAR' }, geometry: square(85.6, 25.4, 0.4) },
    /* A geometry the warning read returned no row for: drawn as an outline, never filled. */
    { type: 'Feature', properties: { k: 'NOROW', n: 'NOROW', s: 'BIHAR' }, geometry: square(86.2, 25.4, 0.4) },
  ],
};

const nowPayload = {
  ...HEAD,
  view: 'now.composed',
  status: 'ok',
  data: {
    schema_version: 'now-v1',
    point: { latitude: 25.5941, longitude: 85.1376, label: 'Patna, Patna, Bihar' },
    observed: {
      status: 'ok',
      rows_in_radius: 2,
      stations: [
        {
          name: 'Patna Airport',
          station_code: 'VEPT',
          distance_km: 3.2,
          age_minutes: 415.0,
          observed_at_utc: '2026-09-16T22:35:00Z',
          stale: true,
          source_id: 'S63',
          parameters: [{ field: 'temp_c', value: 27.0, unit: null }],
        },
      ],
    },
    in_force: {
      district: 'Patna',
      state: 'Bihar',
      day: 2,
      day_label: 'Day 2',
      colour: 'orange',
      quiet: false,
      status_line: 'Official district warning: orange - Heavy rain',
      issued_at_utc: '2026-09-16T12:00:00Z',
    },
    next_hours: {
      status: 'ok',
      rows: [
        { at: '2026-09-17T06:00:00Z', temperature_2m: 27.1, precipitation_probability: 40, precipitation: 0.4, wind_speed_10m: 11.2 },
        { at: '2026-09-17T07:00:00Z', temperature_2m: 27.8, precipitation_probability: 55, precipitation: 1.2, wind_speed_10m: 12.0 },
      ],
      source_id: 'S62',
      unit: { temperature_2m: '°C', precipitation_probability: '%', precipitation: 'mm', wind_speed_10m: 'km/h' },
    },
    not_connected: ['radar and satellite imagery'],
  },
  sources: [SOURCE_S63, { source_id: 'S62', product: 'extended_weather_forecast', retrieved_at_utc: '2026-09-17T05:20:00Z', sha256_prefix: 'bb11cc22dd33' }],
  coverage: { stations: 1, day: 2, hours: 2 },
  limitations: ['A station observation describes its station, not the surrounding district or city.'],
  not_established: ['A quiet day in the official district product is not an all-clear.'],
};

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

async function nameAPlace(name = 'Patna') {
  const input = screen.getByLabelText('Name a place');
  await userEvent.type(input, name);
  const choice = await screen.findByRole('button', { name: new RegExp(name + ', ' + name + ', Bihar') });
  await userEvent.click(choice);
}

describe('the Today surface', () => {
  it('renders the national counts, the stated tally, the evidence and its own limits', async () => {
    server.use(
      http.get('/api/overview', () => HttpResponse.json(overviewPayload)),
      http.get('/api/warnings/national', () => HttpResponse.json(todayWarningsPayload)),
      http.get('/api/map/static/districts', () => HttpResponse.json(todayGeometryPayload)),
    );
    const { container } = mount(<TodaySurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Today' })).toBeInTheDocument();
    /* The KPI row states the same numbers the old fact list did, each in its own card: the district count
       with its unit, the radar counts in words, and an absent field as 'not recorded'. */
    const national = await screen.findByTestId('today-national');
    const districts = within(await screen.findByTestId('today-kpi-districts'));
    expect(districts.getByText('36')).toBeInTheDocument();
    expect(districts.getByText('districts')).toBeInTheDocument();
    expect(national).toHaveTextContent('31 stations');
    expect(national).toHaveTextContent('28');
    // The payload stated no bulletin_date and no tally for 'unset': both are stated as absent.
    expect(national).toHaveTextContent('not recorded');
    const tally = within(screen.getByTestId('today-tally'));
    expect(tally.getByText('red').closest('[data-colour]')).toHaveAttribute('data-colour', 'red');
    /* The tally this read returned stated no orange count, so the row says so; the unset count it did state is shown. */
    expect(tally.getByRole('rowheader', { name: /orange/ })).toBeInTheDocument();
    expect(tally.getByRole('rowheader', { name: /orange/ }).nextSibling).toHaveTextContent('not recorded');
    expect(tally.getByRole('rowheader', { name: /unset/ })).toBeInTheDocument();
    expect(tally.getByRole('rowheader', { name: /unset/ }).nextSibling).toHaveTextContent('1');

    expect(screen.getByText('Day fields are official hazard code lists, not severity stages.')).toBeInTheDocument();
    expect(screen.getByText('Origin authentication of the service is not established.')).toBeInTheDocument();
    expect(screen.getByText('S63')).toBeInTheDocument();
    expect(screen.getByText('IMD district warning product')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(container.querySelectorAll('table').length).toBeGreaterThan(0);
  });

  it('reads the right-now view only once a place is named, and keeps the three products apart', async () => {
    server.use(
      http.get('/api/overview', () => HttpResponse.json(overviewPayload)),
      http.get('/api/warnings/national', () => HttpResponse.json(todayWarningsPayload)),
      http.get('/api/map/static/districts', () => HttpResponse.json(todayGeometryPayload)),
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/now', () => HttpResponse.json(nowPayload)),
    );
    mount(<TodaySurface />);
    await screen.findByTestId('today-national');
    expect(screen.getByText('No point was requested, so no observation, warning day or model hour is shown here.')).toBeInTheDocument();

    await nameAPlace();

    expect(await screen.findByText('Patna Airport')).toBeInTheDocument();
    expect(screen.getByText('3.2 km')).toBeInTheDocument();
    expect(screen.getByText('415 minutes before retrieval')).toBeInTheDocument();
    expect(screen.getByText(/older than the layer’s freshness window/)).toBeInTheDocument();
    const statusLine = screen.getByText('Official district warning: orange - Heavy rain');
    expect(statusLine.closest('p')?.querySelector('[data-colour]')).toHaveAttribute('data-colour', 'orange');
    const hours = within(screen.getByTestId('today-hours'));
    expect(hours.getByText('temperature_2m (°C)')).toBeInTheDocument();
    expect(hours.getByText('0.4')).toBeInTheDocument();
    expect(screen.getByText('A station observation describes its station, not the surrounding district or city.')).toBeInTheDocument();
  });

  it('states a failed read as that failure, with a retry control', async () => {
    server.use(http.get('/api/overview', () => HttpResponse.json({ error: 'the store could not be opened' }, { status: 503 })));
    mount(<TodaySurface />);

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the store could not be opened');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
  });
});

const warningsPayload = {
  ...HEAD,
  view: 'warnings.national',
  data: {
    districts: [
      {
        key: 'PATNA',
        district: 'Patna',
        state: 'Bihar',
        bulletin_date: '2026-09-17',
        issued_at_utc: '2026-09-17T04:00:00Z',
        updated_at: '2026-09-17T05:00:00Z',
        days: [
          { day: 1, day_label: 'Day 1', date: '2026-09-17', colour: 'red', colour_code: 4, hazards: ['Heavy rain'], wording: 'Heavy rain at a few places.' },
          { day: 2, day_label: 'Day 2', date: '2026-09-18', colour: null, colour_code: null, hazards: [], wording: null },
        ],
      },
      {
        key: 'SURAT',
        district: 'Surat',
        state: 'Gujarat',
        bulletin_date: '2026-09-17',
        issued_at_utc: '2026-09-17T04:00:00Z',
        updated_at: null,
        days: [{ day: 1, day_label: 'Day 1', date: '2026-09-17', colour: 'yellow', colour_code: 2, hazards: [], wording: 'Thunderstorm likely.' }],
      },
    ],
    tally: { red: 1, yellow: 1 },
    skipped: [{ obj_id: 'obj-77', reason: 'the source feature carries no district name' }],
  },
  sources: [SOURCE_S63],
  coverage: { features_returned: 3, districts_listed: 2, skipped_without_a_name: 1 },
  limitations: ['A quiet day means the source published no hazard for that district-day in this product. It is not an all-clear.'],
  not_established: ['No live update, cancel or supersede edition has been observed for this layer.'],
};

describe('the Warnings surface', () => {
  it('renders only the colours the payload stated, beside the product wording, and says what it filters', async () => {
    server.use(http.get('/api/warnings/national', () => HttpResponse.json(warningsPayload)));
    const { container } = mount(<WarningsSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Warnings' })).toBeInTheDocument();
    const table = within(await screen.findByTestId('warnings-table'));

    // Three district-days were returned and two state a colour: exactly two colour chips are drawn.
    expect(container.querySelectorAll('[data-colour]')).toHaveLength(2);
    expect(container.querySelector('[data-colour="red"]')).not.toBeNull();
    expect(container.querySelector('[data-colour="yellow"]')).not.toBeNull();
    expect(container.querySelector('[data-colour=""]')).toBeNull();
    expect(table.getByText('Heavy rain at a few places.')).toBeInTheDocument();
    expect(table.getAllByText('colour not stated')).toHaveLength(1);
    expect(table.getByText('no hazard wording published for this district-day')).toBeInTheDocument();
    // With no filter set the summary says what the read returned; it only speaks of "this filter"
    // when one is entered (repaired 17 September 2026: it claimed a filter that was not set).
    expect(screen.getByText('Showing all 3 district-day rows this read returned.')).toBeInTheDocument();
    expect(screen.getByText(/This filter runs in this browser over the 2 district rows this read returned/)).toBeInTheDocument();
    expect(screen.getByText('A quiet day means the source published no hazard for that district-day in this product. It is not an all-clear.')).toBeInTheDocument();
    expect(screen.getByText('No live update, cancel or supersede edition has been observed for this layer.')).toBeInTheDocument();
    expect(within(screen.getByTestId('warnings-skipped')).getByText('the source feature carries no district name')).toBeInTheDocument();
    // Surat's row states no updated_at, and the bulletin table states that absence rather than a blank.
    expect(within(screen.getByTestId('warnings-bulletins')).getAllByText('not recorded').length).toBeGreaterThan(0);
  });

  it('filters the rows it already has and says the product was not asked again', async () => {
    server.use(http.get('/api/warnings/national', () => HttpResponse.json(warningsPayload)));
    mount(<WarningsSurface />);
    const filter = await screen.findByLabelText('District name contains');
    await userEvent.type(filter, 'Surat');

    const count = screen.getByTestId('warnings-count');
    expect(count).toHaveAttribute('role', 'status');
    expect(count).toHaveTextContent('Showing 1 of 1 district-day row matching this filter.');
    const table = within(screen.getByTestId('warnings-table'));
    expect(table.getByText('Surat')).toBeInTheDocument();
    expect(table.queryByText('Patna')).toBeNull();
    expect(table.queryByText('Heavy rain at a few places.')).toBeNull();
  });
});

const forecastPayload = {
  ...HEAD,
  view: 'forecast.point',
  data: {
    requested: { latitude: 25.5941, longitude: 85.1376 },
    parameters: {
      temperature_2m: {
        unit: '°C',
        points: [
          { t: '2026-09-17T06:00:00Z', v: 29.4 },
          { t: '2026-09-17T07:00:00Z', v: null },
          { t: '2026-09-17T08:00:00Z', v: 30.1 },
        ],
      },
    },
    days: 3,
    source_family: 'hourly_forecast',
    time_basis: 'UTC',
  },
  sources: [{ source_id: 'S62', product: 'extended_weather_forecast', retrieved_at_utc: '2026-09-17T05:20:00Z', sha256_prefix: 'bb11cc22dd33' }],
  coverage: { requested_point: { latitude: 25.59, longitude: 85.14 }, returned_grid: { latitude: 25.5, longitude: 85.25 } },
  limitations: ['Model run lineage is unspecified for this delivery, so run-to-run comparison is not established.'],
  not_established: ['No forecast skill or probability calibration is validated here.'],
};

const changesPayload = {
  ...HEAD,
  view: 'forecast.changes',
  status: 'partial',
  data: {
    retrievals: [{ retrieved_at_utc: '2026-09-17T05:00:00Z', product: 'forecast', request_date: '2026-09-17', response_sha256_prefix: '1234abcd' }],
    retrieval_count: 1,
    parameters: { temperature_2m: { unit: '°C', valid_hours: 3, mean_abs_change: 0.4, max_abs_change: 0.9 } },
    overlapping_valid_hours: 3,
    interpretation: 'vintage_variance_not_skill',
  },
  sources: [{ source_id: 'S21', product: 'weather_forecast', retrieved_at_utc: '2026-09-17T05:00:00Z', sha256_prefix: '1234abcd' }],
  coverage: { requested_point: { latitude: 25.59, longitude: 85.14 }, retrievals: 1, overlapping_valid_hours: 3 },
  limitations: ['This compares stored retrievals of the same valid hour; it conflates model updates with shorter horizons because run identity is not exposed.'],
  not_established: ['Forecast skill, calibration and accuracy: no observation or verified analysis is matched here.'],
};

describe('the Forecast surface', () => {
  it('renders each parameter as a table, states a gap as a gap, and keeps the changed-edition view separate', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/forecast', () => HttpResponse.json(forecastPayload)),
      http.get('/api/forecast/changes', () => HttpResponse.json(changesPayload)),
    );
    mount(<ForecastSurface />);
    await screen.findByLabelText('Name a place');
    expect(screen.getByText('No point was named, so no forecast series was requested.')).toBeInTheDocument();

    await nameAPlace();

    expect(await screen.findByRole('heading', { level: 3, name: 'temperature_2m (°C)' })).toBeInTheDocument();
    const gaps = screen.getByTestId('forecast-gaps-temperature_2m');
    expect(gaps).toHaveTextContent('3 points returned, 1 point holding no value');
    expect(gaps).toHaveTextContent('A missing point is a gap, never a zero.');
    expect(screen.getByText('no value returned for this point')).toBeInTheDocument();
    // The payload's requested block states no label: the surface says so rather than inventing one.
    const requested = screen.getByTestId('forecast-requested');
    expect(requested).toHaveTextContent('Label as the reading returned it');
    expect(requested).toHaveTextContent('not recorded');
    expect(screen.getByText('Model run lineage is unspecified for this delivery, so run-to-run comparison is not established.')).toBeInTheDocument();
    const changes = within(screen.getByTestId('forecast-changes'));
    expect(changes.getByText('vintage_variance_not_skill')).toBeInTheDocument();
    expect(changes.getByText('Valid hours retrieved more than once')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  });

  it('states a failed forecast read as a failure with a retry', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/forecast', () => HttpResponse.json({ error: 'the store is busy longer than the queue' }, { status: 429 })),
      http.get('/api/forecast/changes', () => HttpResponse.json(changesPayload)),
    );
    mount(<ForecastSurface />);
    await screen.findByLabelText('Name a place');
    await nameAPlace();

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('This read did not answer: the store is busy longer than the queue');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
  });
});

const observationsNear = {
  ...HEAD,
  view: 'observations.both',
  data: {
    networks: {
      metar: [
        { kind: 'metar', name: 'Patna Airport', station_code: 'VEPT', distance_km: 3.2, observed_at_utc: '2026-09-16T22:35:00Z', age_minutes: 415, stale: true, source_id: 'S63' },
      ],
      aws: [{ kind: 'aws', name: 'Patna AWS', station_code: '', distance_km: null, observed_at_utc: null, age_minutes: null, source_id: 'S63' }],
    },
  },
  sources: [SOURCE_S63],
  coverage: { metar: 1, aws: 1 },
  limitations: ['A station observation describes its station, not the surrounding district or city.'],
  not_established: ['A station observation is not a district average and not a forecast.'],
};

const observationsNetwork = {
  ...HEAD,
  view: 'observations.near',
  data: {
    kind: 'metar',
    stations: [
      { kind: 'metar', name: 'Gaya Airport', station_code: 'VEGY', distance_km: 88.4, observed_at_utc: '2026-09-17T05:00:00Z', age_minutes: 30, stale: false, source_id: 'S63' },
    ],
  },
  sources: [SOURCE_S63],
  coverage: { stations_in_layer: 214, stations_within_radius: 1 },
  limitations: ['No unit is asserted for any value: this layer does not state units, so values are reported verbatim.'],
  not_established: ['Nothing here establishes whether a warning applies.'],
};

describe('the Observations surface', () => {
  it('states each station row with its own distance, instant, age and source, and reads a stale row as stale', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/observations/near', () => HttpResponse.json(observationsNear)),
      http.get('/api/observations/network', () => HttpResponse.json(observationsNetwork)),
    );
    mount(<ObservationsSurface />);
    await screen.findByLabelText('Name a place');
    expect(screen.getByText('No point was named, so no station layer was searched.')).toBeInTheDocument();

    await nameAPlace();

    const near = within(await screen.findByTestId('observations-near'));
    expect(near.getByText('Patna Airport')).toBeInTheDocument();
    expect(near.getByText('3.2 km')).toBeInTheDocument();
    expect(near.getByText('415 minutes before retrieval')).toBeInTheDocument();
    expect(near.getAllByText('S63').length).toBe(2);
    expect(near.getByText('stale')).toBeInTheDocument();
    // The AWS row states no distance, no instant, no age and no staleness flag: each is stated as absent.
    expect(near.getAllByText('not recorded').length).toBeGreaterThanOrEqual(3);
    expect(near.getByText('staleness not recorded')).toBeInTheDocument();
    expect(screen.getByText('2 station rows returned by the near read across 2 networks.')).toBeInTheDocument();
    expect(screen.getByText('A station observation describes its station, not the surrounding district or city.')).toBeInTheDocument();
  });

  it('reads the wider network on its own and shows its own coverage', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/observations/near', () => HttpResponse.json(observationsNear)),
      http.get('/api/observations/network', () => HttpResponse.json(observationsNetwork)),
    );
    mount(<ObservationsSurface />);
    await screen.findByLabelText('Name a place');
    await nameAPlace();

    const network = within(await screen.findByTestId('observations-network'));
    expect(network.getByText('Gaya Airport')).toBeInTheDocument();
    expect(network.getByText('88.4 km')).toBeInTheDocument();
    expect(network.getByText('current')).toBeInTheDocument();
    expect(screen.getByText('1 station row returned by the network read.')).toBeInTheDocument();
    expect(screen.getByText('Stations In Layer')).toBeInTheDocument();
    expect(screen.getByText('No unit is asserted for any value: this layer does not state units, so values are reported verbatim.')).toBeInTheDocument();
    expect(screen.getByText('Nothing here establishes whether a warning applies.')).toBeInTheDocument();
  });
});

const corpusPayload = {
  ...HEAD,
  view: 'corpus.documents',
  data: {
    documents: [
      {
        sha256: 'a'.repeat(64),
        sha_prefix: 'aaaaaaaaaaaa',
        family: 'district_agromet',
        family_label: 'District agromet advisory',
        region: 'Patna, Bihar',
        issue_date: '2026-09-16',
        pages: 4,
        passages: 12,
        source_id: 'S57',
        age_days: 1,
        body: 'available',
        extraction_status: 'text_layer',
        quarantined_passages: 0,
      },
      {
        sha256: 'b'.repeat(64),
        sha_prefix: 'bbbbbbbbbbbb',
        family: 'national_bulletin',
        family_label: 'National bulletin',
        region: 'India',
        issue_date: null,
        pages: null,
        passages: 7,
        source_id: 'S27',
        age_days: null,
        body: 'pruned',
        extraction_status: 'ocr_quarantined',
        quarantined_passages: 3,
      },
    ],
    families: [
      { family: 'district_agromet', label: 'District agromet advisory', documents: 1, passages: 12, newest_issue_date: '2026-09-16' },
      { family: 'national_bulletin', label: 'National bulletin', documents: 1, passages: 7, newest_issue_date: null },
    ],
    counts: { documents: 2, passages: 19, regions: 2, families: 2, bodies_available: 1, pruned: 1, documents_without_a_printed_issue_date: 1 },
    index: 'data/runtime/ingestion/bulletins/v3/index.sqlite',
    reason: '',
  },
  sources: [
    { source_id: 'S57', product: 'District agromet advisory', retrieved_at_utc: '2026-09-16T06:00:00Z', sha256_prefix: 'cccccccccccc' },
    { source_id: 'S27', product: 'National bulletin', retrieved_at_utc: '2026-09-15T06:00:00Z' },
  ],
  coverage: { documents: 2, passages: 19, families: 2, bodies_available: 1, bodies_pruned: 1 },
  limitations: ['A stored document is the record of one printed edition: never a current warning, an all-clear or advice.'],
  not_established: ['Nothing here establishes that a document applies to a place, a crop or a decision.'],
};

describe('the Documents surface', () => {
  it('renders the index counts, states an unprinted issue date and a pruned body honestly', async () => {
    server.use(
      http.get('/api/corpus', () => HttpResponse.json(corpusPayload)),
      http.get('/api/documents/:sha', () =>
        HttpResponse.json(
          {
            error: 'The source document body is outside the local retention window.',
            retention_days: 7,
            retained: 'the document hash and its extracted pages remain indexed and citable',
            sha256: 'b'.repeat(64),
          },
          { status: 410 },
        ),
      ),
    );
    mount(<DocumentsSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Published documents' })).toBeInTheDocument();
    const count = await screen.findByTestId('corpus-count');
    expect(count).toHaveAttribute('role', 'status');
    expect(count).toHaveTextContent('2 documents in the index');
    expect(count).toHaveTextContent('19 passages');
    // A family this build does not register is listed, not fatal: measured 17 September 2026, one
    // such family in the index answered the whole read 400 and the surface showed a retry card.
    expect(screen.queryByTestId('corpus-unregistered')).toBeNull();
    expect(count).toHaveTextContent('2 families indexed');
    expect(count).toHaveTextContent('1 with a saved body, 1 pruned');
    expect(count).toHaveTextContent('1 without a printed issue date');

    const table = within(screen.getByTestId('corpus-table'));
    expect(table.getByText('not stated')).toBeInTheDocument();
    expect(table.getAllByText('not recorded').length).toBeGreaterThan(0);
    expect(table.getByText('body pruned')).toBeInTheDocument();
    expect(table.getByText('body held')).toBeInTheDocument();
    expect(table.getByRole('link', { name: 'Open the saved body' })).toHaveAttribute('href', '/api/documents/' + 'a'.repeat(64));
    expect(screen.getByText('A stored document is the record of one printed edition: never a current warning, an all-clear or advice.')).toBeInTheDocument();
    expect(screen.getByText('Nothing here establishes that a document applies to a place, a crop or a decision.')).toBeInTheDocument();
    expect(screen.getByText(/No document has been opened yet/)).toBeInTheDocument();
  });

  it('renders the document route 410 as that edition’s stated state, not as a crash', async () => {
    server.use(
      http.get('/api/corpus', () => HttpResponse.json(corpusPayload)),
      http.get('/api/documents/:sha', () =>
        HttpResponse.json({ error: 'The source document body is outside the local retention window.', retention_days: 7 }, { status: 410 }),
      ),
    );
    mount(<DocumentsSurface />);
    // The row whose body is still held offers the file itself; the pruned row's state is asked of the route.
    expect(await screen.findAllByRole('button', { name: 'Read what the document route answers' })).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: 'Read what the document route answers' }));

    const viewer = await screen.findByTestId('document-viewer');
    const state = within(viewer).getByTestId('document-viewer-410');
    expect(state).toHaveTextContent('410');
    expect(state).toHaveTextContent('The source document body is outside the local retention window.');
    expect(state).toHaveTextContent(/pruned|survives/i);
    expect(screen.queryByRole('alert')).toBeNull();
    /* The viewer is the one component that answers a saved body, so the 410 is the document's state here
       rather than a second implementation somewhere else. */
    expect(within(viewer).getByRole('button', { name: /Close/ })).toBeInTheDocument();
  });

  it('lists a document in a family this build does not register instead of failing the read', async () => {
    const withUnknownFamily = {
      ...corpusPayload,
      data: {
        ...corpusPayload.data,
        counts: { ...corpusPayload.data.counts, documents_in_an_unregistered_family: 1 },
        unregistered_families: ['gkms_grid'],
      },
    };
    server.use(http.get('/api/corpus', () => HttpResponse.json(withUnknownFamily)));
    mount(<DocumentsSurface />);

    const note = await screen.findByTestId('corpus-unregistered');
    expect(note).toHaveTextContent('1 document in this index belong to a family this build does not register');
    expect(note).toHaveTextContent('gkms_grid');
    expect(note).toHaveTextContent('opening one is refused rather than answered from an unregistered product');
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByTestId('corpus-table')).toBeInTheDocument();
  });
});

const capabilitiesPayload = {
  ...HEAD,
  view: 'settings.capabilities',
  data: {
    capabilities: [
      { tool: 'forecast', kind: 'point', operations: ['forecast'], parameters: ['temperature_2m'], purpose: 'model output for a point' },
    ],
    sources: [
      { source_id: 'S62', product: 'extended_weather_forecast', integration_status: 'prototype_adapter_tested', user_review: 'pending', usage_terms: 'unresolved' },
    ],
    registered_sources: 74,
    connected_sources: 12,
    provider: {
      policy: 'deepseek, then openrouter free ids',
      planner_policy: 'model',
      chat_router: false,
      providers: [
        { provider: 'deepseek', model: 'deepseek-chat', available: false, reason: 'no key configured on this machine' },
        { provider: 'openrouter', models: ['vendor/free-model:free'], reason: 'the account probe has not been run' },
      ],
      rules_floor: { model: 'rules', available: true, detail: 'the deterministic rules plan only under WEATHERGPT_PLANNER=rules' },
      deepseek: { configured: false, model: 'deepseek-chat', note: 'No DeepSeek key is configured on this machine.' },
      openrouter: { configured: false, routing_order: [], refused: [], note: 'No OpenRouter key is configured, so the free ids are not part of the order above.' },
      probe_command: 'python3 scripts/models.py --check',
      key_note: 'A key is written to local configuration on this machine with owner-only permissions.',
    },
  },
  sources: [],
  coverage: { capabilities: 1, sources_in_use: 1 },
  limitations: ['A registered source is not a serving approval, and a connected adapter is not operational readiness.'],
  not_established: ['Voice, mobile acceptance and hosted distribution remain incomplete.'],
};

const healthPayload = {
  schema_version: 'source-health-v1',
  available: true,
  products: [{ product: 'forecast', jobs: 4, states: { committed: 4 }, newest_commit_utc: '2026-09-17T05:00:00Z' }],
  total_jobs: 4,
  streams: 2,
  active_leases: 0,
  note: 'Collected on this machine only.',
};

const watchHealthPayload = {
  schema_version: 'watch-health-v1',
  mode: 'manual-only',
  note: 'No hosted daemon or OS scheduler is installed: checks run while a supervisor loop or a manual trigger fires.',
  tick: { fresh: false, age_seconds: null, reason: 'no heartbeat recorded yet' },
  outbox: { counts: { queued: 0 }, undispatched_depth: 0 },
  watches: { total: 1, active: 1, expired: 0 },
  plan_watcher: { running: false, interval_seconds: 60 },
};

const briefsPayload = {
  schema_version: 'briefcase-v1',
  delivery: 'local_only_no_delivery',
  note: 'A kept brief is a local record: nothing is delivered, pushed or scheduled.',
  briefs: [{ id: 'b1', saved_at: '2026-09-17T05:00:00Z', kind: 'alert_brief', title: 'Patna, Day 2', status: 'ok', delivery: 'local_only_no_delivery' }],
};

describe('the Settings surface', () => {
  it('renders the capability and source counts, each provider’s own availability, and the local state', async () => {
    server.use(
      http.get('/api/settings/capabilities', () => HttpResponse.json(capabilitiesPayload)),
      http.get('/api/health', () => HttpResponse.json(healthPayload)),
      http.get('/api/watch-health', () => HttpResponse.json(watchHealthPayload)),
      http.get('/api/briefs', () => HttpResponse.json(briefsPayload)),
    );
    mount(<SettingsSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Sources and settings' })).toBeInTheDocument();
    const providers = within(await screen.findByTestId('settings-providers'));
    expect(screen.getByText(/1 capability this read returned · 74 registered sources · 12 connected sources/)).toBeInTheDocument();
    expect(providers.getByText('deepseek')).toBeInTheDocument();
    expect(providers.getByText('not available')).toBeInTheDocument();
    expect(providers.getByText(/no key configured on this machine/)).toBeInTheDocument();
    // A provider that is not configured says so in its own words, once per unconfigured provider.
    expect(providers.getAllByText('not configured')).toHaveLength(2);
    expect(providers.getByText(/No OpenRouter key is configured/)).toBeInTheDocument();
    // The payload stated no key_source: the row says so rather than leaving the field out.
    expect(providers.getByText(/key source: not recorded/)).toBeInTheDocument();
    // The second provider's payload states no availability flag: the surface says so instead of guessing.
    expect(providers.getByText('availability not recorded')).toBeInTheDocument();
    expect(providers.getByText(/vendor\/free-model:free/)).toBeInTheDocument();

    const health = within(screen.getByTestId('settings-health'));
    expect(health.getByText('true')).toBeInTheDocument();
    expect(health.getByText('4')).toBeInTheDocument();
    const watches = within(screen.getByTestId('settings-watches'));
    expect(watches.getByText('manual-only')).toBeInTheDocument();
    expect(screen.getByTestId('settings-watches')).toHaveTextContent('no heartbeat recorded yet');
    expect(watches.getByText('1 / 1 / 0')).toBeInTheDocument();
    expect(screen.getByText(/1 kept brief · delivery as returned: local_only_no_delivery/)).toBeInTheDocument();
    expect(within(screen.getByTestId('settings-briefs')).getByText('Patna, Day 2')).toBeInTheDocument();

    expect(screen.getByText('A registered source is not a serving approval, and a connected adapter is not operational readiness.')).toBeInTheDocument();
    expect(screen.getByText('Voice, mobile acceptance and hosted distribution remain incomplete.')).toBeInTheDocument();
    // The capabilities envelope attached no source row, and the surface says exactly that.
    expect(screen.getByText('No source row came back with this read.')).toBeInTheDocument();
  });

  it('states a failed store read as a failure with a retry, and leaves the rest of the surface standing', async () => {
    server.use(
      http.get('/api/settings/capabilities', () => HttpResponse.json(capabilitiesPayload)),
      http.get('/api/health', () => HttpResponse.json({ error: 'the store is unavailable' }, { status: 503 })),
      http.get('/api/watch-health', () => HttpResponse.json(watchHealthPayload)),
      http.get('/api/briefs', () => HttpResponse.json(briefsPayload)),
    );
    mount(<SettingsSurface />);
    await screen.findByTestId('settings-watches');

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
    expect(screen.getByTestId('settings-watches')).toBeInTheDocument();
  });
});
