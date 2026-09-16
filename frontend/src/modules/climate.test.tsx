/* Climate records, checked against payloads shaped like the ones the two routes actually answered
   (captured from data/processed/districts/district-v1-c8b978172b77182e/districts.sqlite through
   weathergpt_data/product_api.py — the source's own annual figures arrive as strings, and a year the
   source does not hold simply has no row).

   What the checks may not lose: the counts and district rows the index stated, the year rows the series
   returned with the source's own text, a year inside the stated span with no row stated as missing
   rather than drawn as a zero, a row that holds no value stated as absent, the surface's own statement
   about what the record is, and a failed read stated as a failure with a retry control. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Surface as ClimateSurface } from './ClimateSurface';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const HEAD = {
  schema_version: 'product-view-v1',
  generated_at_utc: '2026-09-17T05:30:00Z',
  status: 'ok',
};

const SOURCE_S27 = {
  source_id: 'S27',
  product: 'Supplied district historical rainfall collection',
  url: 'https://imdpune.gov.in/library/public/e-book110.pdf',
  retrieved_at_utc: null,
  sha256_prefix: '',
};

const indexPayload = {
  ...HEAD,
  view: 'climate.index',
  data: {
    states: [
      {
        state: 'Andhra Pradesh',
        districts: [
          { district: 'Anantapur', years: 110, first_year: 1901, last_year: 2010 },
          { district: 'Vizianagaram', years: 108, first_year: 1901, last_year: 2010 },
        ],
      },
      { state: 'Gujarat', districts: [{ district: 'Ahmedabad', years: 110, first_year: 1901, last_year: 2010 }] },
    ],
    districts: 3,
  },
  sources: [SOURCE_S27],
  coverage: { states: 2, districts: 3 },
  limitations: ['Published district tables as transcribed, not a boundary-harmonised series.'],
  not_established: ['No attribution, homogenisation or climate projection is performed on this record.'],
};

function point(year: number, value: string | null) {
  return {
    year, value, unit: 'mm', series_id: 'IMD110-P342', source_page: '342', source_row: 1212,
    source_file: 'data/raw/imports/2026-09-11/states/andhra_pradesh.csv',
    asset_sha256_prefix: '94e005182700', quality_flags: '', label: 'VIZIANAGARAM',
  };
}

/* The whole span the read states, with 1902-1904 held by no row and 1905's row holding no value. */
const seriesPayload = {
  ...HEAD,
  view: 'climate.series',
  data: {
    district: 'Vizianagaram',
    state: 'Andhra Pradesh',
    parameter: 'rainfall',
    series_id: 'IMD110-P342',
    points: [point(1901, '1071.5'), point(1905, null), point(1906, '1041.0')],
    first_year: 1901,
    last_year: 1906,
  },
  sources: [SOURCE_S27],
  coverage: { years: 3 },
  limitations: ['Values are the published annual totals as transcribed, in millimetres, and missing years are gaps rather than zeros.'],
  not_established: ['No trend, anomaly or attribution is asserted by this view; a descriptive slope would still not be a projection.'],
};

const okIndex = http.get('/api/climate/index', () => HttpResponse.json(indexPayload));
const okSeries = http.get('/api/climate/series', () => HttpResponse.json(seriesPayload));
const DISTRICT_LABEL = /District to read the rainfall series for/;

async function chooseVizianagaram() {
  await userEvent.selectOptions(screen.getByLabelText(DISTRICT_LABEL), 'Andhra Pradesh|Vizianagaram');
}

describe('the Climate records surface', () => {
  it('renders the counts and rows the index stated, offers only those districts, and reads the series for one', async () => {
    server.use(okIndex, okSeries);
    mount(<ClimateSurface />);

    expect(await screen.findByRole('heading', { level: 1, name: 'Climate records' })).toBeInTheDocument();
    const facts = await screen.findByTestId('climate-index');
    expect(facts).toHaveTextContent('2 states');
    // The coverage counts the index stated, restated by the index and by the picker it feeds.
    expect(within(facts).getAllByText('3 districts')).toHaveLength(3);

    const table = within(screen.getByTestId('climate-index-table'));
    expect(table.getByText('Vizianagaram')).toBeInTheDocument();
    expect(table.getAllByText('Andhra Pradesh')).toHaveLength(2); // one row per district the index listed under it
    expect(table.getByText('108')).toBeInTheDocument();

    const select = screen.getByLabelText(DISTRICT_LABEL);
    expect(within(select).getAllByRole('option')).toHaveLength(4); // the no-choice row plus the three the index listed
    expect(within(select).getByRole('option', { name: /Vizianagaram \(Andhra Pradesh\) · 108 years as the index counted them · 1901 to 2010/ })).toBeInTheDocument();
    expect(within(select).queryByRole('option', { name: /Kochi/ })).toBeNull();
    expect(screen.getByText('No district was chosen, so no series was read.')).toBeInTheDocument();

    await chooseVizianagaram();

    const seriesFacts = await screen.findByTestId('climate-series');
    expect(seriesFacts).toHaveTextContent('Vizianagaram');
    expect(seriesFacts).toHaveTextContent('IMD110-P342');
    expect(seriesFacts).toHaveTextContent('rainfall');
    expect(seriesFacts).toHaveTextContent('mm');
    const yearsTable = within(await screen.findByTestId('climate-years'));
    // The value, its unit column and its own source page and row sit in one row, as the payload returned them.
    const firstRow = includingRowOf(yearsTable.getByText('1071.5'));
    expect(firstRow).toHaveTextContent('342');
    expect(firstRow).toHaveTextContent('1212');
    expect(yearsTable.getByText('1041.0')).toBeInTheDocument();
    expect(screen.getByTestId('climate-series-count')).toHaveAttribute('aria-live', 'polite');
    expect(screen.getByTestId('climate-series-count')).toHaveTextContent('3 year rows returned for this district');
    // The series read's own limitation line, in its own words.
    expect(screen.getByText('Values are the published annual totals as transcribed, in millimetres, and missing years are gaps rather than zeros.')).toBeInTheDocument();
  });

  it('states a year with no row, and a row holding no value, as absent rather than as a zero', async () => {
    server.use(okIndex, okSeries);
    mount(<ClimateSurface />);
    await screen.findByTestId('climate-index');
    await chooseVizianagaram();

    const table = within(await screen.findByTestId('climate-years'));
    // 1902 lies inside the span the read stated, and the record holds no row for it.
    const heldByNoRow = includingRowOf(table.getByText('1902'));
    expect(heldByNoRow).toHaveTextContent('no row returned for this year');
    // 1905's row exists and holds no value: that is not the same state as no row at all.
    const holdsNoValue = includingRowOf(table.getByText('1905'));
    expect(holdsNoValue).toHaveTextContent('not recorded in this row');
    expect(table.getByText('1906')).toBeInTheDocument();
    // No zero stands in for either absence, and the drawing breaks at the gaps.
    expect(table.queryByText('0')).toBeNull();
    expect(screen.getByTestId('chart-block').querySelectorAll('circle')).toHaveLength(2);
  });

  it('keeps the surface’s own statement about what the stored record is and is not', async () => {
    server.use(okIndex, okSeries);
    mount(<ClimateSurface />);

    const standing = await screen.findByTestId('climate-standing');
    expect(standing).toHaveTextContent(/stored historical record as this machine holds it/);
    expect(standing).toHaveTextContent(/The years returned are the years the source published/);
    expect(standing).toHaveTextContent(/never a zero, and no value is interpolated across a missing year/);
    expect(standing).toHaveTextContent(/not a climate projection, not an attribution and not a forecast/);
  });

  it('states the envelope’s limits verbatim, and says when a read attached no source row', async () => {
    server.use(
      okIndex,
      http.get('/api/climate/series', () =>
        HttpResponse.json({ ...seriesPayload, sources: [], limitations: [], not_established: [] })),
    );
    mount(<ClimateSurface />);
    await screen.findByTestId('climate-index');

    // The index read's own lines are visible before any district is chosen.
    expect(screen.getByText('Published district tables as transcribed, not a boundary-harmonised series.')).toBeInTheDocument();
    expect(screen.getByText('No attribution, homogenisation or climate projection is performed on this record.')).toBeInTheDocument();

    await chooseVizianagaram();

    await screen.findByTestId('climate-series-count');
    expect(screen.getByText('No source row came back with this read.')).toBeInTheDocument();
    expect(screen.getByText('This read returned no limitation line.')).toBeInTheDocument();
  });

  it('renders a failed index read as the local evidence store being unavailable, and retries it', async () => {
    let failing = true;
    server.use(
      http.get('/api/climate/index', () =>
        failing
          ? HttpResponse.json({ error: 'the climate database is not on disk' }, { status: 503 })
          : HttpResponse.json(indexPayload)),
      okSeries,
    );
    mount(<ClimateSurface />);

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable: the climate database is not on disk');
    expect(failure).toHaveTextContent('The climate record index read failed.');
    const retry = within(failure).getByRole('button', { name: 'Retry this read' });

    failing = false;
    await userEvent.click(retry);
    expect(await screen.findByTestId('climate-index')).toHaveTextContent('2 states');
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('renders a failed series read the same way, with its own retry', async () => {
    let failing = true;
    server.use(
      okIndex,
      http.get('/api/climate/series', () =>
        failing
          ? HttpResponse.json({ error: 'the series could not be read' }, { status: 503 })
          : HttpResponse.json(seriesPayload)),
    );
    mount(<ClimateSurface />);
    await screen.findByTestId('climate-index');
    await chooseVizianagaram();

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable: the series could not be read');
    expect(failure).toHaveTextContent('The stored rainfall series read failed.');

    failing = false;
    await userEvent.click(within(failure).getByRole('button', { name: 'Retry this read' }));
    expect(await screen.findByTestId('climate-years')).toHaveTextContent('1071.5');
  });
});

function includingRowOf(cell: HTMLElement): HTMLElement {
  const row = cell.closest('tr');
  if (!row) throw new Error('the year cell is not inside a table row');
  return row;
}
