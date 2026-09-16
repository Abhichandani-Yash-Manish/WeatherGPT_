/* Aviation, checked against payloads shaped like the ones the route actually answers. The fixtures are
   the real records this machine retrieved from the NOAA Aviation Weather Center capture
   (research/discovery/evidence/source-audit-20260914T173947Z/S18-*.response and S19-*.response) pushed
   through weathergpt_data.adapters.aviation and the product route's own wrapper.

   What the checks may not lose: the station rows and decoded values the payload gave, the report kind
   exactly as the payload states it for both kinds the route answers, the observation-versus-forecast and
   not-operational-advice sentences in the surface's own voice, a report the read marks stale read as
   stale rather than as current weather, a requested station with no report stated as missing, and a
   failed read stated as a failure with a retry. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as AviationSurface } from './AviationSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const HEAD = { schema_version: 'product-view-v1', generated_at_utc: '2026-09-14T17:45:00Z', status: 'ok' };

const SOURCE_S18 = {
  source_id: 'S18',
  product: 'aviation_metar',
  url: 'https://aviationweather.gov/api/data/metar?ids=VAAH&format=json&hours=3',
  retrieved_at_utc: '2026-09-14T17:41:06.407000+00:00',
  sha256_prefix: 'ecc64eb51ed5',
  integration_status: 'prototype_adapter_tested',
  user_review: 'approved_local_prototype',
};

const SOURCE_S19 = {
  source_id: 'S19',
  product: 'aviation_taf',
  url: 'https://aviationweather.gov/api/data/taf?ids=VAAH&format=json',
  retrieved_at_utc: '2026-09-14T17:41:06.407000+00:00',
  sha256_prefix: 'c7416585fca3',
  integration_status: 'prototype_adapter_tested',
  user_review: 'approved_local_prototype',
};

const FIELDS = { name: 'Ahmadabad/Patel Intl, GJ, IN', lat: 23.077, lon: 72.635, elev: 52, metarType: 'METAR', fltCat: 'IFR' };

function metar(overrides: Record<string, unknown>) {
  return {
    station_id: 'VAAH', observed_at_utc: '2026-09-14T17:30:00+00:00', age_seconds: 900.0,
    freshness: 'within_prototype_age_limit',
    raw_report: 'METAR VAAH 141730Z 14006KT 3000 -DZ BR FEW015 SCT020 OVC080 25/23 Q1008 NOSIG',
    temperature_c: 25, dewpoint_c: 23, wind_speed_kt: 6, wind_direction_native: 140,
    source_locator: '$[0]', raw_fields: FIELDS, ...overrides,
  };
}

/* Three of the six rows the capture held: one inside the read's own prototype age limit, two the read marks stale. */
const metarPayload = {
  ...HEAD,
  view: 'aviation.station',
  data: {
    kind: 'metar',
    missing: [],
    stations: [
      metar({}),
      metar({ observed_at_utc: '2026-09-14T15:30:00+00:00', age_seconds: 8100.0, freshness: 'stale',
        raw_report: 'METAR VAAH 141530Z 14005KT 3000 -DZ BR FEW015 SCT020 BKN080 25/24 Q1007 NOSIG',
        dewpoint_c: 24, wind_speed_kt: 5, source_locator: '$[4]' }),
      metar({ observed_at_utc: '2026-09-14T15:00:00+00:00', age_seconds: 9900.0, freshness: 'stale',
        raw_report: 'METAR VAAH 141500Z 14005KT 3000 -DZ BR FEW015 SCT020 OVC080 25/23 Q1007 NOSIG',
        wind_speed_kt: 5, source_locator: '$[5]' }),
    ],
  },
  sources: [SOURCE_S18],
  coverage: { requested_stations: ['VAAH'], missing_stations: [] },
  limitations: ['Reports concern their airports; not a complete operational aviation briefing.'],
  not_established: ['A station report is not a flight status, a route briefing or a clearance.'],
};

const tafPayload = {
  ...HEAD,
  view: 'aviation.station',
  status: 'outside_validity',
  data: {
    kind: 'taf',
    missing: [],
    stations: [{
      station_id: 'VAAH', issued_at_raw: '2026-09-14T17:00:00.000Z',
      valid_start_utc: '2026-09-14T18:00:00+00:00', valid_end_utc: '2026-09-15T03:00:00+00:00',
      active_by_time: false,
      raw_report: 'TAF VAAH 141700Z 1418/1503 20005KT 3000 -TSRA -SHRA SCT015 SCT020 FEW030CB OVC080 BECMG 1419/1421 18006KT BECMG 1422/1424 21008KT',
      interpretation: 'Original TAF and native change groups preserved; no flight-safety decision generated.',
      source_locator: '$[0]',
      raw_fields: { name: 'Ahmadabad/Patel Intl', lat: 23.077, lon: 72.635, elev: 52, mostRecent: 1 },
    }],
  },
  sources: [SOURCE_S19],
  coverage: { requested_stations: ['VAAH'], missing_stations: [] },
  limitations: ['Reports concern their airports; not a complete operational aviation briefing.'],
  not_established: ['A station report is not a flight status, a route briefing or a clearance.'],
};

/* One requested station answered, one did not: the route reports the second as missing and the status as partial. */
const partialPayload = {
  ...metarPayload,
  status: 'partial',
  data: { kind: 'metar', missing: ['VOBL'], stations: [metar({})] },
  coverage: { requested_stations: ['VOBL', 'VAAH'], missing_stations: ['VOBL'] },
};

const okMetar = http.get('/api/aviation', () => HttpResponse.json(metarPayload));
const ICAO_LABEL = 'ICAO codes to read, comma separated';

/* The station block: the facts list carries the testid, and the raw report and decoded table are its siblings. */
function stationBlock(index: number): HTMLElement {
  const article = screen.getByTestId('aviation-station-' + index).closest('article');
  if (!article) throw new Error('the station facts are not inside a station article');
  return article;
}

async function requestReports(codes = 'VAAH', kind?: string) {
  await userEvent.type(screen.getByLabelText(ICAO_LABEL), codes);
  if (kind) await userEvent.selectOptions(screen.getByLabelText('Report kind to read'), kind);
  await userEvent.click(screen.getByRole('button', { name: 'Read these reports' }));
}

describe('the Aviation surface', () => {
  it('renders the station rows and decoded values the METAR read returned, with each own instant, age and freshness', async () => {
    server.use(okMetar);
    mount(<AviationSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Aviation' })).toBeInTheDocument();
    // The read is asked for, never fired from a half-typed code.
    expect(screen.getByRole('button', { name: 'Read these reports' })).toBeDisabled();
    const kinds = within(screen.getByLabelText('Report kind to read'));
    expect(kinds.getAllByRole('option')).toHaveLength(2);
    expect(kinds.queryByRole('option', { name: /stationinfo/ })).toBeNull();

    await requestReports();

    const read = within(await screen.findByTestId('aviation-read'));
    expect(read.getByText('metar')).toBeInTheDocument();
    expect(read.getByText('3 station reports')).toBeInTheDocument();
    expect(read.getByText('VAAH')).toBeInTheDocument();
    expect(read.getByText('every station this read was asked for answered')).toBeInTheDocument();

    const station = within(screen.getByTestId('aviation-station-0'));
    expect(within(stationBlock(0)).getByRole('heading', { level: 3, name: 'VAAH · Ahmadabad/Patel Intl, GJ, IN' })).toBeInTheDocument();
    expect(station.getByText('23.077, 72.635')).toBeInTheDocument();
    expect(station.getByText('52')).toBeInTheDocument();
    expect(station.getByText('$[0]')).toBeInTheDocument();
    expect(station.getByText('METAR')).toBeInTheDocument();
    expect(station.getByText(/900 s as returned/)).toBeInTheDocument();
    expect(station.getByText('14 Sep 2026, 23:00 IST')).toBeInTheDocument();
    expect(within(stationBlock(0)).getByText(/METAR VAAH 141730Z 14006KT 3000 -DZ BR FEW015 SCT020 OVC080 25\/23 Q1008 NOSIG/)).toBeInTheDocument();

    const decoded = within(screen.getByTestId('aviation-decoded-0'));
    expect(within(decoded.getByText('temperature_c').closest('tr') as HTMLElement).getByText('25')).toBeInTheDocument();
    const wind = decoded.getByText('wind_speed_kt').closest('tr') as HTMLElement;
    expect(within(wind).getByText('6')).toBeInTheDocument();
    expect(within(wind).getByText('kt')).toBeInTheDocument();
    const direction = decoded.getByText('wind_direction_native').closest('tr') as HTMLElement;
    expect(within(direction).getByText('140')).toBeInTheDocument();
    expect(within(direction).getByText('unit not stated by this read')).toBeInTheDocument();
    // The unit is the product's own for these fields, and the time basis is the report's own instant.
    expect(decoded.getAllByText('°C')).toHaveLength(2);
    expect(decoded.getAllByText('14 Sep 2026, 23:00 IST')).toHaveLength(4);

    // The envelope's own lines and its source row stay visible, in the read's own words.
    expect(screen.getByText('Reports concern their airports; not a complete operational aviation briefing.')).toBeInTheDocument();
    expect(screen.getByText('A station report is not a flight status, a route briefing or a clearance.')).toBeInTheDocument();
    const sources = within(screen.getByRole('table', { name: /Every source row this read attached/ }));
    expect(sources.getByText('S18')).toBeInTheDocument();
    expect(sources.getByText('aviation_metar')).toBeInTheDocument();
    expect(sources.getByText('ecc64eb51ed5')).toBeInTheDocument();
  });

  it('renders the report kind exactly as the payload states it, and a TAF as a forecast with its own window', async () => {
    const asked: string[] = [];
    server.use(http.get('/api/aviation', ({ request }) => {
      asked.push(request.url);
      const kind = new URL(request.url).searchParams.get('kind');
      return HttpResponse.json(kind === 'taf' ? tafPayload : metarPayload);
    }));
    mount(<AviationSurface />);
    await screen.findByLabelText(ICAO_LABEL);
    await requestReports('VAAH', 'metar');

    const read = within(await screen.findByTestId('aviation-read'));
    expect(read.getByText('metar')).toBeInTheDocument();
    expect(read.queryByText('taf')).toBeNull();

    // The same route, asked for the other kind it answers.
    await userEvent.selectOptions(screen.getByLabelText('Report kind to read'), 'taf');
    await userEvent.click(screen.getByRole('button', { name: 'Read these reports' }));

    expect(await within(await screen.findByTestId('aviation-read')).findByText('taf')).toBeInTheDocument();
    const station = within(screen.getByTestId('aviation-station-0'));
    expect(station.getByText('2026-09-14T17:00:00.000Z')).toBeInTheDocument();
    expect(station.getByText(/23:30-15 Sep 2026, 08:30 IST/)).toBeInTheDocument();
    expect(station.getByText('false')).toBeInTheDocument();
    expect(station.getByText('Original TAF and native change groups preserved; no flight-safety decision generated.')).toBeInTheDocument();
    // A forecast is not decoded into point values, and the surface says why rather than inventing a table.
    expect(screen.queryByTestId('aviation-decoded-0')).toBeNull();
    expect(screen.getByText(/a forecast is not an observation from the station/)).toBeInTheDocument();
  });

  it('says in its own voice what a METAR and a TAF are, and what neither of them is', async () => {
    server.use(okMetar);
    mount(<AviationSurface />);

    const standing = await screen.findByTestId('aviation-standing');
    expect(standing).toHaveTextContent(/A METAR is an observation from that station and not a forecast/);
    expect(standing).toHaveTextContent(/a TAF is a forecast and not an observation/);
    expect(standing).toHaveTextContent(/Neither is a flight-safety clearance, a runway state, a turbulence or icing determination or any other operational advice/);
    expect(standing).toHaveTextContent(/stale rather than current weather/);
  });

  it('reads a report the source marks stale as stale, and never restyles another word as current', async () => {
    server.use(okMetar);
    mount(<AviationSurface />);
    await screen.findByLabelText(ICAO_LABEL);
    await requestReports();

    await screen.findByTestId('aviation-station-0');
    // Each row carries the word the read returned for it: no chip is drawn for a state the read did not state.
    expect(within(screen.getByTestId('aviation-station-1')).getByText('stale')).toHaveClass('chip', 'is-stale');
    expect(within(screen.getByTestId('aviation-station-2')).getByText('stale')).toHaveClass('chip', 'is-stale');
    const countLine = screen.getByTestId('aviation-count');
    expect(countLine).toHaveAttribute('aria-live', 'polite');
    expect(countLine).toHaveTextContent('3 station reports returned for metar; 2 rows carry the read’s own stale word and must not be read as current weather');
    // The payload's own word for a report it does not mark stale is printed as that word, not as "current".
    expect(within(screen.getByTestId('aviation-station-0')).getByText('within_prototype_age_limit')).toHaveClass('chip', 'is-unknown');
    expect(screen.queryByText('current')).toBeNull();
  });

  it('states a requested station the read did not answer rather than dropping it', async () => {
    server.use(http.get('/api/aviation', () => HttpResponse.json(partialPayload)));
    mount(<AviationSurface />);
    await screen.findByLabelText(ICAO_LABEL);
    await requestReports('VOBL,VAAH');

    const read = within(await screen.findByTestId('aviation-read'));
    expect(read.getByText('VOBL, VAAH')).toBeInTheDocument();
    expect(read.getByText('VOBL')).toBeInTheDocument(); // the station the read reports as missing
    expect(read.getByText('1 station report')).toBeInTheDocument();
    expect(screen.getByTestId('aviation-station-0')).toHaveTextContent('VAAH');
  });

  it('renders a failed read as the local evidence store being unavailable, and retries it', async () => {
    let failing = true;
    server.use(http.get('/api/aviation', () =>
      failing ? HttpResponse.json({ error: 'the airport cache is not on disk' }, { status: 503 }) : HttpResponse.json(metarPayload)));
    mount(<AviationSurface />);
    await screen.findByLabelText(ICAO_LABEL);
    await requestReports();

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable: the airport cache is not on disk');
    expect(failure).toHaveTextContent('The airport reports read failed.');
    const retry = within(failure).getByRole('button', { name: 'Retry this read' });

    failing = false;
    await userEvent.click(retry);
    expect(await screen.findByTestId('aviation-station-0')).toHaveTextContent('VAAH');
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('shows the route’s own refusal sentence when the codes are not four letters', async () => {
    server.use(http.get('/api/aviation', () =>
      HttpResponse.json({ error: 'Provide 1–20 four-letter ICAO station codes' }, { status: 400 })));
    mount(<AviationSurface />);
    await screen.findByLabelText(ICAO_LABEL);
    await requestReports('VOBL123');

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('This read did not answer: Provide 1–20 four-letter ICAO station codes');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
  });
});
