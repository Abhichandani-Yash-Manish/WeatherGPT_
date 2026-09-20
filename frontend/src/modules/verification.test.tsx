/* The Forecast verification surface, checked against a payload shaped like the route's own product view.

   What the checks may not lose: the window, model and both source sides the read returned; the per-lead
   counts (matched hours n, forecast hours, unmatched hours); the metric values it stated and the
   correlation note it returned instead of a number; an unmeasured lead printed as unmeasured with its
   reason and no metric invented; an absent field read as absent; the mandatory statement that this is
   not validated skill, not a nationwide accuracy claim and not an operational clearance; every limit and
   not-established line; and a failed read stated with a retry. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { provenanceOffenders } from '../flagship/provenance';
import { Surface as VerificationSurface } from './VerificationSurface';

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
    sources: [],
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

function pickWindow(start = '2026-09-01', end = '2026-09-07') {
  fireEvent.change(screen.getByLabelText('Window start (completed date)'), { target: { value: start } });
  fireEvent.change(screen.getByLabelText('Window end (completed date)'), { target: { value: end } });
}

const LIMITS = [
  'The reference is ERA5 reanalysis, a modelled analysis, not a station observation.',
  'The statistics describe this sample for this model, variable and window; they are not operational skill, a confidence or a risk.',
  'A lead with fewer than 24 matched hours is reported as unmeasured, not given a number.',
  'A model is never ranked against another and no single skill score is produced.',
];

const verificationPayload = {
  ...HEAD,
  view: 'verification.skill',
  data: {
    schema_version: 'verification-result-v1',
    method: {
      bias: 'mean of (forecast minus reference) over matched hours',
      mae: 'mean of the absolute error over matched hours',
      rmse: 'square root of the mean squared error over matched hours',
      correlation: 'Pearson product-moment correlation over matched hours',
    },
    minimum_sample_hours: 24,
    forecast: { source_id: 'S70', model: 'gfs_seamless', grid: { latitude: 25.5, longitude: 85.25 }, retrieved_at_utc: '2026-09-17T05:40:00Z', sha256: 'abcdef0123456789abcdef' },
    reference: { source_id: 'S22', grid: { latitude: 25.5, longitude: 85.5 }, retrieved_at_utc: '2026-09-17T05:45:00Z', sha256: 'fedcba9876543210fedcba' },
    variables: {
      temperature_2m: [
        { lead_days: 1, forecast_hours: 120, unmatched_hours: 0, n: 120, status: 'measured', bias: '-1.204', mae: '1.870', rmse: '2.310', correlation: '0.741' },
        { lead_days: 7, forecast_hours: 120, unmatched_hours: 98, n: 22, status: 'unmeasured', reason: 'fewer than 24 matched hours' },
      ],
      precipitation: [
        { lead_days: 1, forecast_hours: 120, unmatched_hours: 4, n: 116, status: 'measured', bias: '0.310', mae: '0.880', rmse: '1.240', correlation: null, correlation_note: 'undefined: one series has no variation in this sample' },
      ],
    },
    units: { temperature_2m: '°C', precipitation: 'mm' },
    limits: LIMITS,
    window: { start: '2026-09-01', end: '2026-09-07' },
  },
  sources: [
    { source_id: 'S70', product: 'Archived model runs at fixed lead-time offsets', retrieved_at_utc: '2026-09-17T05:40:00Z', sha256_prefix: 'abcdef012345' },
    { source_id: 'S22', product: 'ERA5 hourly reanalysis, used as the reference', retrieved_at_utc: '2026-09-17T05:45:00Z', sha256_prefix: 'fedcba987654' },
  ],
  coverage: { window: { start: '2026-09-01', end: '2026-09-07' }, model: 'gfs_seamless', grid: { latitude: 25.5, longitude: 85.25 } },
  limitations: LIMITS,
  not_established: ['This measures one model against reanalysis over one bounded window; it is not forecast skill, an observation-based verification or a model ranking.'],
};

describe('the Forecast verification surface', () => {
  it('renders the window, sources, per-lead counts and metrics, and leaves an unmeasured lead unmeasured', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/verification', () => HttpResponse.json(verificationPayload)),
    );
    const { container } = mount(<VerificationSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Forecast verification' })).toBeInTheDocument();
    await screen.findByLabelText('Name a place');
    expect(screen.getByText('No point was named, so no verification read was requested.')).toBeInTheDocument();
    await nameAPlace();
    expect(screen.getByText('Give both completed dates to read the comparison for this point; the read is not requested before then.')).toBeInTheDocument();
    pickWindow();

    const windowFacts = within(await screen.findByTestId('verification-window'));
    expect(windowFacts.getByText('Window requested').nextSibling).toHaveTextContent('2026-09-01 to 2026-09-07');
    expect(windowFacts.getByText('Window as the reading returned it').nextSibling).toHaveTextContent('2026-09-01 to 2026-09-07');
    expect(windowFacts.getByText('Model as returned').nextSibling).toHaveTextContent('gfs_seamless');
    expect(windowFacts.getByText('Forecast side as returned').nextSibling).toHaveTextContent('S70');
    expect(windowFacts.getByText('Reference side as returned').nextSibling).toHaveTextContent('S22');
    expect(windowFacts.getByText('Minimum matched hours for a measured lead').nextSibling).toHaveTextContent('24');

    // The first-screen reading: the shortest measured lead's own mean absolute error, stated before the
    // per-lead tables that prove it, and carrying the same provenance shape as a conversation claim.
    const headline = screen.getByTestId('verification-headline');
    expect(headline).toHaveTextContent(
      'At a 1-day lead, this read’s temperature_2m forecast differed from the reference by a mean absolute error of 1.870 °C over 120 matched hours.',
    );
    expect(headline.querySelector('.g-claim-source')).toHaveTextContent('S70');
    expect(headline.querySelector('.g-claim-source')).toHaveTextContent('S22');
    expect(provenanceOffenders(headline)).toEqual([]);

    expect(screen.getByRole('heading', { level: 3, name: 'temperature_2m (°C)' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: 'precipitation (mm)' })).toBeInTheDocument();

    const temperature = within(screen.getByTestId('verification-temperature_2m'));
    const measured = within(temperature.getByRole('rowheader', { name: '1' }).closest('tr') as HTMLElement);
    expect(measured.getAllByText('120')).toHaveLength(2);
    expect(measured.getByText('-1.204')).toBeInTheDocument();
    expect(measured.getByText('1.870')).toBeInTheDocument();
    expect(measured.getByText('2.310')).toBeInTheDocument();
    expect(measured.getByText('0.741')).toBeInTheDocument();

    const unmeasured = within(temperature.getByRole('rowheader', { name: '7' }).closest('tr') as HTMLElement);
    expect(unmeasured.getByText('unmeasured')).toBeInTheDocument();
    expect(unmeasured.getByText('22')).toBeInTheDocument();
    expect(unmeasured.getByText('98')).toBeInTheDocument();
    expect(unmeasured.getByText('fewer than 24 matched hours')).toBeInTheDocument();
    expect(unmeasured.getAllByText('this read did not answer for this lead')).toHaveLength(4);

    // A correlation the read did not state is the read's own note, never a number derived here.
    expect(
      within(screen.getByTestId('verification-precipitation')).getAllByText('undefined: one series has no variation in this sample'),
    ).toHaveLength(2);

    const countLine = screen.getByTestId('verification-count');
    expect(countLine).toHaveAttribute('aria-live', 'polite');
    expect(countLine).toHaveTextContent('3 lead rows returned across 2 parameters');

    const statement = screen.getByTestId('verification-not-skill');
    expect(statement).toHaveTextContent('not validated forecast skill');
    expect(statement).toHaveTextContent('not a nationwide accuracy claim');
    expect(statement).toHaveTextContent('not an operational clearance');
    expect(screen.getByTestId('verification-what-was-compared')).toHaveTextContent('at the same valid hour');
    expect(within(screen.getByTestId('verification-method')).getByText('mean of the absolute error over matched hours')).toBeInTheDocument();
    expect(screen.getByText('The reference is ERA5 reanalysis, a modelled analysis, not a station observation.')).toBeInTheDocument();
    expect(screen.getByText('A lead with fewer than 24 matched hours is reported as unmeasured, not given a number.')).toBeInTheDocument();
    expect(screen.getByText('This measures one model against reanalysis over one bounded window; it is not forecast skill, an observation-based verification or a model ranking.')).toBeInTheDocument();
    expect(screen.getByText('Archived model runs at fixed lead-time offsets')).toBeInTheDocument();
    expect(screen.getByText('ERA5 hourly reanalysis, used as the reference')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(container.querySelectorAll('table').length).toBeGreaterThan(0);
  });

  it('states an absent window, model, cell and metric as not recorded rather than as a zero', async () => {
    const absentPayload = {
      ...verificationPayload,
      data: {
        ...verificationPayload.data,
        forecast: { source_id: 'S70', model: null, grid: null },
        reference: { source_id: 'S22', grid: null },
        variables: {
          temperature_2m: [{ lead_days: 2, forecast_hours: 48, unmatched_hours: 0, n: 48, status: 'measured', bias: '0.500' }],
        },
        units: {},
        window: null,
      },
    };
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/verification', () => HttpResponse.json(absentPayload)),
    );
    mount(<VerificationSurface />);
    await screen.findByLabelText('Name a place');
    await nameAPlace();
    pickWindow();

    const windowFacts = within(await screen.findByTestId('verification-window'));
    expect(windowFacts.getByText('Window as the reading returned it').nextSibling).toHaveTextContent('not recorded');
    expect(windowFacts.getByText('Model as returned').nextSibling).toHaveTextContent('not recorded');
    expect(windowFacts.getByText('Forecast cell as returned').nextSibling).toHaveTextContent('not recorded');
    expect(windowFacts.getByText('Reference cell as returned').nextSibling).toHaveTextContent('not recorded');

    // No lead in this fixture states a mae value, so the headline says that plainly rather than reporting
    // a metric from a lead that has none.
    expect(screen.getByTestId('verification-headline')).toHaveTextContent(
      'This read measured no lead with a stated mean absolute error for this window',
    );

    const table = within(screen.getByTestId('verification-temperature_2m'));
    expect(table.getAllByText('not recorded')).toHaveLength(3);
    expect(screen.getByRole('heading', { level: 3, name: 'temperature_2m (unit not stated)' })).toBeInTheDocument();
  });

  it('states a failed read as that failure, with a retry control', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/verification', () => HttpResponse.json({ error: 'the store could not be opened' }, { status: 503 })),
    );
    mount(<VerificationSurface />);
    await screen.findByLabelText('Name a place');
    await nameAPlace();
    pickWindow();

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the store could not be opened');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
    expect(screen.queryByTestId('verification-count')).toBeNull();
  });
});
