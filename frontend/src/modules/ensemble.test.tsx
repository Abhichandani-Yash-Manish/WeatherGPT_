/* The Ensemble spread surface, checked against a payload shaped like the route's own product view.

   What the checks may not lose: the member count the read returned per variable, the spread points it
   stated (a null spread point read as a gap, never a zero), the mandatory statement that a member is one
   model run and the spread is not a probability/confidence/skill score, an absent field read as absent,
   the envelope's own limitations and not-established lines, the source rows, and a failed read stated
   as that failure with a retry. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as EnsembleSurface } from './EnsembleSurface';

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

const SPREAD_STATEMENT =
  'The spread is a property of the returned ensemble members, not a forecast probability, a confidence or a skill measure.';

const ensemblePayload = {
  ...HEAD,
  view: 'ensemble.spread',
  data: {
    requested: { latitude: 25.59, longitude: 85.14 },
    parameters: {
      temperature_2m_mean: {
        unit: '°C',
        aggregation: 'instant',
        model: 'gfs025',
        quality_flags: [],
        points: [{ t: '2026-09-17T06:00:00Z', v: '28.700' }],
      },
      temperature_2m_spread: {
        unit: '°C',
        aggregation: 'instant',
        model: 'gfs025',
        quality_flags: [],
        points: [
          { t: '2026-09-17T06:00:00Z', v: '0.912' },
          { t: '2026-09-17T07:00:00Z', v: null },
        ],
      },
      precipitation_spread: {
        unit: 'mm',
        aggregation: 'preceding_hour_sum',
        model: 'gfs025',
        quality_flags: ['source_value_missing'],
        points: [{ t: '2026-09-17T07:00:00Z', v: null, start: '2026-09-17T06:00:00Z', end: '2026-09-17T07:00:00Z' }],
      },
    },
    days: 3,
    model: 'gfs025',
    member_total: { temperature_2m: 31, precipitation: 31 },
    statistics: {
      mean: 'arithmetic mean of the returned perturbed members',
      spread: 'population standard deviation across the returned members',
      percentile: 'nearest-rank on the sorted member values',
    },
    grid: { latitude: 25.5, longitude: 85.25 },
    time_basis: 'UTC',
  },
  sources: [
    { source_id: 'S68', product: 'ensemble_forecast', retrieved_at_utc: '2026-09-17T05:25:00Z', sha256_prefix: 'ffeeddccbbaa' },
  ],
  coverage: {
    requested_point: { latitude: 25.59, longitude: 85.14 },
    returned_grid: { latitude: 25.5, longitude: 85.25 },
    model: 'gfs025',
    time_basis: 'UTC',
  },
  limitations: [
    'Ensemble spread and percentiles describe the returned members; they are not a probability, confidence, risk or skill measure.',
    SPREAD_STATEMENT,
  ],
  not_established: [SPREAD_STATEMENT],
};

describe('the Ensemble spread surface', () => {
  it('renders the member counts the read returned, the spread it stated, and its own limits', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/ensemble', () => HttpResponse.json(ensemblePayload)),
    );
    const { container } = mount(<EnsembleSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Ensemble spread' })).toBeInTheDocument();
    await screen.findByLabelText('Name a place');
    expect(screen.getByText('No point was named, so no ensemble read was requested.')).toBeInTheDocument();
    await nameAPlace();

    // The member counts the payload stated, per variable, exactly as returned.
    const members = within(await screen.findByTestId('ensemble-member-total'));
    expect(members.getByRole('rowheader', { name: 'temperature_2m' }).nextSibling).toHaveTextContent('31');
    expect(members.getByRole('rowheader', { name: 'precipitation' }).nextSibling).toHaveTextContent('31');

    // The spread the payload stated is drawn with its unit; the point with no value is a gap, never a zero.
    const spread = within(screen.getByTestId('ensemble-spread'));
    expect(spread.getAllByText('temperature_2m_spread')).toHaveLength(2);
    expect(spread.getByText('0.912')).toBeInTheDocument();
    expect(spread.getAllByText('°C').length).toBeGreaterThan(0);
    expect(spread.getAllByText('no value returned for this point')).toHaveLength(2);
    expect(spread.queryByText('0')).toBeNull();

    // The count line is a live count of what arrived, not a completeness measure.
    const countLine = screen.getByTestId('ensemble-count');
    expect(countLine).toHaveAttribute('aria-live', 'polite');
    expect(countLine).toHaveTextContent('3 series returned across 2 variable names');
    expect(countLine).toHaveTextContent('no completeness percentage is computed here');

    // The sentences this surface must say in its own voice.
    const meaning = screen.getByTestId('ensemble-meaning');
    expect(meaning).toHaveTextContent('An ensemble member is one model run.');
    expect(meaning).toHaveTextContent('not a probability of the outcome at your place');
    expect(meaning).toHaveTextContent('not a skill score');
    expect(screen.getByTestId('ensemble-members-stated')).toHaveTextContent('not an observation');

    // The envelope's own limit and not-established lines stay visible, with the source rows.
    expect(screen.getAllByText(SPREAD_STATEMENT)).toHaveLength(2);
    expect(
      screen.getByText('Ensemble spread and percentiles describe the returned members; they are not a probability, confidence, risk or skill measure.'),
    ).toBeInTheDocument();
    expect(screen.getByText('S68')).toBeInTheDocument();
    expect(screen.getByText('ensemble_forecast')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(container.querySelectorAll('table').length).toBeGreaterThan(0);
  });

  it('states an absent member count and an absent timing field as not recorded rather than as a zero', async () => {
    const absentPayload = {
      ...ensemblePayload,
      data: {
        ...ensemblePayload.data,
        member_total: null,
        statistics: null,
        grid: null,
        time_basis: null,
      },
      coverage: { requested_point: { latitude: 25.59, longitude: 85.14 } },
    };
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/ensemble', () => HttpResponse.json(absentPayload)),
    );
    mount(<EnsembleSurface />);
    await screen.findByLabelText('Name a place');
    await nameAPlace();

    expect(await screen.findByText(/The count of returned members is not recorded in this read/)).toBeInTheDocument();
    expect(screen.queryByTestId('ensemble-member-total')).toBeNull();
    const point = within(screen.getByTestId('ensemble-point'));
    expect(point.getByText('Time basis').nextSibling).toHaveTextContent('not recorded');
    expect(point.getByText('Cell identity as returned').nextSibling).toHaveTextContent('not recorded');
    // With no member-total field the series are grouped under their own returned names, never a guessed variable.
    expect(screen.getByTestId('ensemble-series-temperature_2m_spread')).toHaveTextContent('0.912');
  });

  it('states a failed read as that failure, with a retry control', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/ensemble', () => HttpResponse.json({ error: 'the store could not be opened' }, { status: 503 })),
    );
    mount(<EnsembleSurface />);
    await screen.findByLabelText('Name a place');
    await nameAPlace();

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the store could not be opened');
    expect(within(failure).getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
    expect(screen.queryByTestId('ensemble-count')).toBeNull();
  });
});
