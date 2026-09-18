import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as TodaySurface } from './TodaySurface';

const HEAD = {
  schema_version: 'product-view-v1',
  generated_at_utc: '2026-09-17T06:00:00+00:00',
  status: 'ok',
  coverage: {},
  limitations: ['A stated limit.'],
  not_established: ['Something not established here.'],
};

const SOURCE = { source_id: 'S63', product: 'IMD district warning product', retrieved_at_utc: '2026-09-17T05:55:00+00:00', sha256_prefix: 'abc123' };

const OVERVIEW = {
  ...HEAD,
  view: 'overview',
  data: {
    national: { districts: 756, skipped: 8, tally: { red: 1, orange: 26, yellow: 9, green: 19 },
      bulletin_dates: { '2026-09-15': 742, '2026-09-11': 2 }, bulletin_date: '2026-09-15' },
    radar: { stations: 39, reported: 39 },
    places: [],
  },
  sources: [SOURCE],
};

const WARNINGS = {
  ...HEAD,
  view: 'warnings.national',
  data: {
    districts: [
      { key: 'PATNA', district: 'PATNA', state: 'BIHAR', bulletin_date: '2026-09-15', bulletin_age_days: 2,
        bulletin_behind_the_newest_read_days: 0, bulletin_is_older_than_this_read: false,
        days: [
          { day: 3, label: '17 Sep 2026', date_local: '2026-09-17', colour: 'yellow', hazard_codes: [5],
            hazards: ['Thunderstorm/lightning/squall'], quiet: false, is_today: true },
          { day: 4, label: '18 Sep 2026', date_local: '2026-09-18', colour: 'green', hazard_codes: [1],
            hazards: ['No warning in this product'], quiet: true, is_today: false },
        ] },
      { key: 'SAITUAL', district: 'SAITUAL', state: 'MIZORAM', bulletin_date: '2026-09-11', bulletin_age_days: 6,
        bulletin_behind_the_newest_read_days: 4, bulletin_is_older_than_this_read: true,
        days: [{ day: 3, label: '17 Sep 2026', date_local: '2026-09-17', colour: null, hazard_codes: [], hazards: [], quiet: false, is_today: true }] },
      { key: 'QUIET', district: 'QUIETVILLE', state: 'BIHAR', bulletin_date: '2026-09-15', bulletin_age_days: 2,
        days: [{ day: 3, label: '17 Sep 2026', date_local: '2026-09-17', colour: 'green', hazard_codes: [1], hazards: ['No warning in this product'], quiet: true, is_today: true }] },
    ],
    tally: { red: 1, orange: 26, yellow: 9, green: 19, unset: 5 },
    newest_bulletin_date_in_this_read: '2026-09-15',
    districts_behind_the_newest_edition: 14,
    oldest_bulletin_age_days: 1047,
  },
  sources: [SOURCE],
};

function square(west: number, south: number, side: number) {
  return { type: 'Polygon', coordinates: [[[west, south], [west + side, south], [west + side, south + side], [west, south + side], [west, south]]] };
}

const GEOMETRY = {
  type: 'FeatureCollection',
  features: [
    { type: 'Feature', properties: { k: 'PATNA', n: 'PATNA', s: 'BIHAR' }, geometry: square(85.0, 25.4, 0.4) },
    { type: 'Feature', properties: { k: 'SAITUAL', n: 'SAITUAL', s: 'MIZORAM' }, geometry: square(92.6, 23.3, 0.4) },
    { type: 'Feature', properties: { k: 'QUIET', n: 'QUIETVILLE', s: 'BIHAR' }, geometry: square(85.6, 25.4, 0.4) },
    { type: 'Feature', properties: { k: 'NOROW', n: 'NOROW', s: 'BIHAR' }, geometry: square(86.2, 25.4, 0.4) },
  ],
};

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}><TodaySurface /></QueryClientProvider>);
}

async function mounted(extra: ReturnType<typeof http.get>[] = []) {
  /* A test's own handler goes first in the batch: MSW answers a request from the first matching handler,
     so an override must be registered before the default this helper supplies. */
  server.use(
    ...extra,
    http.get('/api/overview', () => HttpResponse.json(OVERVIEW)),
    http.get('/api/warnings/national', () => HttpResponse.json(WARNINGS)),
    http.get('/api/map/static/districts', () => HttpResponse.json(GEOMETRY)),
  );
  mount();
  await screen.findByTestId('today-national');
  await screen.findByTestId('risk-map');
}

describe('the Today dashboard', () => {
  it('states the counted KPIs from the payload, and an absent field as not recorded', async () => {
    await mounted();
    const districts = within(await screen.findByTestId('today-kpi-districts'));
    expect(districts.getByText('756')).toBeInTheDocument();
    expect(districts.getByText('districts')).toBeInTheDocument();
    const days = within(screen.getByTestId('today-kpi-district-days'));
    expect(days.getByText('55')).toBeInTheDocument();
    expect(days.getByText('district-days')).toBeInTheDocument();
    expect(days.getByText(/Unrecognised colour codes counted separately: 5/)).toBeInTheDocument();
    const editions = within(screen.getByTestId('today-kpi-editions'));
    expect(editions.getByText('14')).toBeInTheDocument();
    expect(editions.getByText(/1047 days before this read/)).toBeInTheDocument();
    const radar = within(screen.getByTestId('today-kpi-radar'));
    expect(radar.getByText('39')).toBeInTheDocument();
    expect(radar.getByText('of 39 returned')).toBeInTheDocument();
  });

  it('fills a district only with the colour its own row published, and leaves the rest as outlines', async () => {
    await mounted();
    const figure = await screen.findByTestId('risk-map');
    expect(figure.querySelector('[data-key="PATNA"]')).toHaveAttribute('data-colour', 'yellow');
    expect(figure.querySelector('[data-key="SAITUAL"]')).not.toHaveAttribute('data-colour');
    expect(figure.querySelector('[data-key="NOROW"]')).not.toHaveAttribute('data-colour');
    expect(figure.getAttribute('aria-label')).toMatch(/4 districts drawn/);
    expect(figure.getAttribute('aria-label')).toMatch(/2 filled with the colour its own returned row published/);
  });

  it('inspects a district with the keyboard and states an absent row in the readout', async () => {
    await mounted();
    const figure = await screen.findByTestId('risk-map');
    fireEvent.keyDown(figure, { key: 'ArrowRight' });
    fireEvent.keyDown(figure, { key: 'ArrowRight' });
    fireEvent.keyDown(figure, { key: 'ArrowRight' });
    fireEvent.keyDown(figure, { key: 'Enter' });
    const readout = screen.getByTestId('risk-map-readout');
    expect(readout).toHaveTextContent('NOROW');
    expect(readout).toHaveTextContent('no warning row in this read');
  });

  it('filters in the browser and says the product was not asked again', async () => {
    await mounted();
    fireEvent.change(screen.getByLabelText('Search district'), { target: { value: 'patna' } });
    expect(await screen.findByTestId('today-filter-note')).toHaveTextContent('1 district match');
    expect(screen.getByTestId('today-filter-note')).toHaveTextContent('The product is not asked again');
    const figure = screen.getByTestId('risk-map');
    expect(figure.querySelector('[data-key="SAITUAL"]')?.getAttribute('class')).toMatch(/district-muted/);
    const table = within(screen.getByTestId('today-map-table'));
    expect(table.getByText('PATNA')).toBeInTheDocument();
    expect(table.queryByText('SAITUAL')).toBeNull();
  });

  it('colours by the day the reader asked to inspect, and stops colouring when told to', async () => {
    await mounted();
    fireEvent.change(screen.getByLabelText('Day to inspect'), { target: { value: '4' } });
    const figure = screen.getByTestId('risk-map');
    expect(figure.querySelector('[data-key="PATNA"]')).toHaveAttribute('data-colour', 'green');
    fireEvent.click(screen.getByLabelText('Colour only where published'));
    expect(figure.querySelector('[data-key="PATNA"]')).not.toHaveAttribute('data-colour');
  });

  it('draws a bubble per returned cell and leaves an empty cell as a gap', async () => {
    await mounted();
    const matrix = await screen.findByTestId('today-matrix');
    expect(matrix.querySelectorAll('circle[data-colour]').length).toBeGreaterThan(0);
    const table = within(screen.getByTestId('today-matrix-table'));
    const yellow = table.getByRole('row', { name: /yellow/ });
    expect(within(yellow).getByText('1')).toBeInTheDocument();
    expect(within(yellow).getAllByText('not recorded').length).toBeGreaterThan(0);
  });

  it('lists only the districts that published a hazard covering today', async () => {
    await mounted();
    const list = await screen.findByTestId('today-warned');
    expect(within(list).getByText(/PATNA/)).toBeInTheDocument();
    expect(within(list).getByText(/colour not stated/)).toBeInTheDocument();
    expect(within(list).queryByText(/QUIETVILLE/)).toBeNull();
  });

  it('keeps the rest of the page standing when the warning read fails, and says why the list is empty', async () => {
    await mounted([http.get('/api/warnings/national', () => HttpResponse.json({ error: 'the store could not be opened' }, { status: 503 }))]);
    expect(await screen.findByTestId('today-warned-error')).toHaveTextContent('not because nothing was published');
    expect(screen.getByTestId('today-national')).toBeInTheDocument();
    expect(screen.getByTestId('risk-map')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('draws no number before the read answers', async () => {
    server.use(
      http.get('/api/overview', () => new Promise(() => {})),
      http.get('/api/warnings/national', () => HttpResponse.json(WARNINGS)),
      http.get('/api/map/static/districts', () => HttpResponse.json(GEOMETRY)),
    );
    mount();
    /* While the overview read is unanswered the shell reserves the shape of an answer and renders no card at
       all: the loading state carries the placeholder and no number, which is the rule this pins. */
    expect(await screen.findByText(/Reading national overview from the local store/)).toBeInTheDocument();
    expect(screen.queryByTestId('today-national')).toBeNull();
    expect(screen.queryByTestId('today-filters')).toBeNull();
    expect(screen.queryByText('756')).toBeNull();
  });

  it('keeps one alert for a failed surface read and one heading', async () => {
    server.use(http.get('/api/overview', () => HttpResponse.json({ error: 'the store could not be opened' }, { status: 503 })));
    mount();
    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('the store could not be opened');
    expect(screen.getAllByRole('alert')).toHaveLength(1);
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  });

  it('carries the table behind the figure with the same rows the figure draws', async () => {
    await mounted();
    const table = within(await screen.findByTestId('today-map-table'));
    expect(table.getByText('PATNA')).toBeInTheDocument();
    expect(table.getByText('Thunderstorm/lightning/squall')).toBeInTheDocument();
    expect(table.getByText('NOROW')).toBeInTheDocument();
    expect(table.getByText('this district has no warning row in this read')).toBeInTheDocument();
  });

  it('takes the editions count from whichever read stated it first, and says when the rows are still being read', async () => {
    /* The overview read answers in milliseconds and carries the same national fields as the 1.65 MB row read.
       Before this check the card said 'not recorded' whenever the row read was still in flight, which is a
       false absence: the page already had the number. */
    const overviewWithEditions = {
      ...OVERVIEW,
      data: {
        ...OVERVIEW.data,
        national: {
          ...OVERVIEW.data.national,
          newest_bulletin_date_in_this_read: '2026-09-15',
          districts_behind_the_newest_edition: 14,
          oldest_bulletin_age_days: 1047,
        },
      },
    };
    await mounted([
      http.get('/api/overview', () => HttpResponse.json(overviewWithEditions)),
      http.get('/api/warnings/national', () => new Promise(() => undefined)),
    ]);
    const editions = within(await screen.findByTestId('today-kpi-editions'));
    expect(editions.getByText('14')).toBeInTheDocument();
    expect(editions.queryByText('not recorded')).toBeNull();
    expect(editions.getByText(/The district rows are still being read/)).toBeInTheDocument();
    /* The profile is drawn from the overview's own printed dates, which this read returned. */
    expect(editions.getByTestId('today-edition-profile')).toBeInTheDocument();
  });

  it('sets a word value at the word size and a numeral at the numeral size', async () => {
    const overviewWithoutDistricts = {
      ...OVERVIEW,
      data: { ...OVERVIEW.data, national: { ...OVERVIEW.data.national, districts: null } },
    };
    await mounted([http.get('/api/overview', () => HttpResponse.json(overviewWithoutDistricts))]);
    const districts = within(await screen.findByTestId('today-kpi-districts'));
    const card = screen.getByTestId('today-kpi-districts');
    expect(card).toHaveAttribute('data-value-kind', 'word');
    expect(districts.getByText('not recorded')).toBeInTheDocument();
    const word = card.querySelector('.dash-kpi-number');
    expect(word).not.toBeNull();
    expect(word?.className).toContain('dash-kpi-number-word');
    expect(screen.getByTestId('today-kpi-radar')).toHaveAttribute('data-value-kind', 'number');
  });

  it('opens the district inspector from the figure with the district days and two working links', async () => {
    await mounted();
    const figure = await screen.findByTestId('risk-map');
    const patna = figure.querySelector('[data-key="PATNA"]');
    expect(patna).not.toBeNull();
    await userEvent.click(patna as Element);

    const inspector = await screen.findByTestId('today-inspector-district');
    expect(within(inspector).getByText('PATNA')).toBeInTheDocument();
    expect(within(inspector).getByText('BIHAR')).toBeInTheDocument();
    /* Every published day-row the district row carries, with the colour and the wording as printed. */
    expect(within(inspector).getByText(/Thunderstorm\/lightning\/squall/)).toBeInTheDocument();
    expect(within(inspector).getByText(/No warning in this product/)).toBeInTheDocument();
    expect(inspector.querySelector('[data-colour="yellow"]')).not.toBeNull();
    expect(within(inspector).getByText(/covers the day inspected/)).toBeInTheDocument();

    const warningsLink = within(inspector).getByRole('link', { name: /Open in Warnings/ });
    expect(warningsLink).toHaveAttribute('href', '#/warnings?district=PATNA');
    const askLink = within(inspector).getByRole('link', { name: /Ask about this district/ });
    expect(askLink.getAttribute('href')).toContain('#/assistant?ask=');
    expect(decodeURIComponent(askLink.getAttribute('href') || '')).toContain('PATNA');
  });

  it('lists the states in the read before a district is chosen, and filters the figure from one', async () => {
    await mounted();
    const states = await screen.findByTestId('today-inspector-states');
    expect(within(states).getByText('BIHAR')).toBeInTheDocument();
    await userEvent.click(within(states).getByRole('button', { name: /BIHAR/ }));
    const filtered = await screen.findByTestId('today-inspector-state');
    expect(within(filtered).getByText('PATNA')).toBeInTheDocument();
    expect(within(filtered).getByText('QUIETVILLE')).toBeInTheDocument();
  });
});
