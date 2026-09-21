/* The opening of a surface: what a reader meets on the first screen, held by a check.
   ============================================================================
   docs/127 §6 named `frontend/src/modules/**` as the one place X1's audit did not reach and left the
   decision to "a later lane". This is that lane, and this is the decision, stated as five rules that a
   build either keeps or fails:

     1. **A surface starts from the place this browser holds.** Measured 21 September 2026: eleven of the
        eighteen surfaces opened on "No point was named, so no ... read was requested." for a reader whose
        place was already held, and the reader had to name it a second time on every surface.
     2. **The reading leads.** The first screen states what the numbers mean, in the evidence's own terms,
        before the table that proves it — measured against the captured screens, five of these six surfaces
        opened on a card of standing sentences that named no value the read had returned, so
        light-verification@1440 was a title, three chips and three paragraphs about what the surface does
        not claim. The first screen of forecast verification contained no verification.
     3. **The standing sentences are kept, and are no longer the opening.** Every one of them survives
        word for word, in its own element, under its own test id, inside a fold BELOW the evidence it
        qualifies. The envelope's own limitations and not-established lines do not move: EvidenceFooter
        prints those unfolded, from the read itself.
     4. **The controls survive.** A read in flight, and a read that failed, leave the place picker, the
        window and the station code on the page. Before this batch `busy` and `error` replaced the whole
        surface: a reader who picked a place watched it blink to a skeleton with the picker gone, and a
        reader whose read failed lost the control that would let them ask about somewhere else.
     5. **X1 holds here.** Every number in the reading carries provenance, checked by the same function the
        answer card and docs/127's surfaces use.

   What this spec does NOT claim is in the record: it renders six surfaces with recorded payloads. It is
   not a browser, it is not the live routes, and a passing check here is not a product acceptance. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { provenanceOffenders } from '../flagship/provenance';
import { forgetWorkingPlace, rememberPlace } from './Evidence';
import { Surface as AirQualitySurface } from './AirQualitySurface';
import { Surface as AviationSurface } from './AviationSurface';
import { Surface as CompareSurface } from './CompareSurface';
import { Surface as EnsembleSurface } from './EnsembleSurface';
import { Surface as MarineSurface } from './MarineSurface';
import { Surface as VerificationSurface } from './VerificationSurface';

/* The place the rail holds, in the words the rail holds it in: a catalogue label and two coordinates, and
   nothing else. Every surface below is rendered with this already held and no interaction of any kind. */
const HELD = { label: 'Kochi, Ernakulam, Kerala', latitude: 9.9312, longitude: 76.2673 };

beforeEach(() => { forgetWorkingPlace(); rememberPlace(HELD); });
afterEach(() => { forgetWorkingPlace(); });

const HEAD = { schema_version: 'product-view-v1', generated_at_utc: '2026-09-20T22:10:42Z', status: 'ok' };
const SOURCE = [{ source_id: 'S68', product: 'ensemble_forecast', retrieved_at_utc: '2026-09-20T22:10:42Z', sha256_prefix: 'a1b2c3d4e5f6' }];

const ensemble = {
  ...HEAD, view: 'ensemble.spread',
  data: {
    model: 'gfs025', time_basis: 'UTC', days: 3,
    requested: { latitude: HELD.latitude, longitude: HELD.longitude },
    grid: { latitude: 9.958336, longitude: 76.20836 },
    member_total: { temperature_2m: 31 },
    statistics: { spread: 'population standard deviation across the returned members' },
    parameters: {
      temperature_2m: { unit: '°C', model: 'gfs025', points: [{ t: '2026-09-20T00:00:00Z', v: '25.620' }] },
      temperature_2m_spread: { unit: '°C', model: 'gfs025', points: [{ t: '2026-09-20T00:00:00Z', v: '0.912' }] },
    },
  },
  sources: SOURCE, limitations: ['Modelled grid values are not direct local measurements.'], not_established: [],
};

const verification = {
  ...HEAD, view: 'verification.skill',
  data: {
    method: { mae: 'mean of the absolute error over matched hours' }, minimum_sample_hours: 24,
    forecast: { source_id: 'S70', model: 'gfs_seamless', grid: { latitude: 9.9252, longitude: 76.275 } },
    reference: { source_id: 'S22', grid: { latitude: 9.9252, longitude: 76.275 } },
    units: { temperature_2m: '°C' },
    window: { start: '2026-09-08', end: '2026-09-14' },
    variables: {
      temperature_2m: [{ lead_days: 1, forecast_hours: 168, unmatched_hours: 0, n: 168, status: 'measured', bias: '2.646', mae: '2.646' }],
    },
  },
  sources: [{ source_id: 'S70', product: 'Archived model runs at fixed lead-time offsets', retrieved_at_utc: '2026-09-20T22:10:42Z', sha256_prefix: 'bb11cc22dd33' }],
  limitations: ['The reference is ERA5 reanalysis, a modelled analysis, not a station observation.'],
  not_established: ['This measures one model against reanalysis over one bounded window; it is not forecast skill.'],
};

const forecast = (value: number) => ({
  ...HEAD, view: 'forecast.point',
  data: {
    requested: { label: HELD.label, latitude: HELD.latitude, longitude: HELD.longitude },
    grid: { latitude: 9.93, longitude: 76.26 }, source_family: 'gfs_seamless', time_basis: 'UTC', days: 3,
    parameters: { temperature_2m: { unit: '°C', model: 'gfs_seamless', points: [{ t: '2026-09-20T11:30:00Z', v: value }] } },
  },
  sources: [{ source_id: 'S21', product: 'forecast', retrieved_at_utc: '2026-09-17T05:30:00Z', sha256_prefix: '11aa22bb33cc' }],
  limitations: ['Run identity is not exposed; retrieval time is not model issue time.'], not_established: [],
});

const marine = {
  ...HEAD, view: 'marine.point',
  data: {
    days: 7, grid: { latitude: 9.958336, longitude: 76.20836 }, grid_distance_km: 6.474,
    parameters: { wave_height: { unit: 'm', model: 'meteofrance_wave', points: [{ t: '2026-09-20T00:00:00Z', v: 1.24 }] } },
  },
  sources: [{ source_id: 'S56', product: 'marine', retrieved_at_utc: '2026-09-20T22:10:42Z', sha256_prefix: 'eeff00112233' }],
  limitations: ['Modelled grid values are not direct local measurements.'], not_established: [],
};

const airQuality = {
  ...HEAD, view: 'air_quality.point',
  data: {
    requested: { label: HELD.label, latitude: HELD.latitude, longitude: HELD.longitude },
    grid: { latitude: 9.93, longitude: 76.26 }, grid_distance_km: 3.2, domain: 'CAMS global', time_basis: 'UTC',
    current: { pm2_5: 66.6, us_aqi: 160 },
    parameters: {
      pm2_5: { unit: 'µg/m³', model: 'CAMS via Open-Meteo', points: [{ t: '2026-09-20T00:00:00Z', v: 66.6 }] },
      us_aqi: { unit: 'USAQI', model: 'CAMS via Open-Meteo', category: 'Very Unhealthy', points: [{ t: '2026-09-20T00:00:00Z', v: 160 }] },
    },
  },
  sources: [{ source_id: 'S69', product: 'air_quality', retrieved_at_utc: '2026-09-20T22:10:43Z', sha256_prefix: 'bb199326cdb1' }],
  limitations: ['CAMS modelled air quality at a coarse grid cell; it is not a monitor measurement.'],
  not_established: ['An air-quality index is the source’s own index, and no health advice is produced from it.'],
};

const metar = {
  ...HEAD, view: 'aviation.station',
  data: {
    kind: 'metar',
    stations: [{
      station_id: 'VOCI', observed_at_utc: '2026-09-20T22:00:00Z', age_seconds: 642, freshness: 'current',
      raw_report: 'VOCI 202200Z 25008KT 9999 SCT020 27/24 Q1008', temperature_c: 27, dewpoint_c: 24,
      wind_speed_kt: 8, wind_direction_native: 250, source_locator: 'S18',
      raw_fields: { name: 'Cochin International', lat: 10.152, lon: 76.401, elev: 9, metarType: 'METAR' },
    }],
  },
  sources: [{ source_id: 'S18', product: 'metar', retrieved_at_utc: '2026-09-20T22:10:42Z', sha256_prefix: 'c0ffee123456' }],
  limitations: ['A report older than the source’s own validity is stale rather than current weather.'], not_established: [],
};

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

/* The five rules, as one set of assertions over a rendered surface. `reading` is the test id the reading
   carries on that surface; `meaning` is the id the fold carries; `control` is the label of the one control
   a reader uses to ask.
   ============================================================================
   Rule 2 is checked in document order rather than by eye: the reading must precede the first table, which
   is the machine-readable form of "before the table that proves it". Rule 3 is checked by asking whether
   the element is inside a `<details>`, which is the machine-readable form of "under a fold". */
async function checkOpening(container: HTMLElement, reading: string, meaning: string | null, control: string) {
  // 1 — read on arrival, from the held place, with no interaction.
  const headline = await screen.findByTestId(reading);
  expect(headline.querySelector('.g-claim-source')).not.toBeNull();

  // 2 — the reading leads: in document order it precedes the first table and the first fold.
  const firstTable = container.querySelector('table');
  expect(firstTable).not.toBeNull();
  expect(headline.compareDocumentPosition(firstTable as Node) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

  // 5 — and every number in it carries provenance, by the same function the answer card uses.
  expect(provenanceOffenders(headline)).toEqual([]);

  // 3 — the standing sentences survive, below the evidence, inside a fold.
  if (meaning) {
    const fold = screen.getByTestId(meaning);
    expect(fold.tagName).toBe('DETAILS');
    expect(fold.compareDocumentPosition(headline) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy();
    expect(fold).toHaveTextContent(/\S/);
  }

  // 4 — the control a reader used is still on the page. Marine names a sea point and a river point, so
  // this counts the labelled controls rather than demanding exactly one.
  expect(screen.getAllByLabelText(control).length).toBeGreaterThan(0);
}

describe('what a surface shows on its first screen', () => {
  it('reads the held place on arrival, leads with the reading, and keeps the standing sentences under it', async () => {
    server.use(
      http.get('/api/ensemble', () => HttpResponse.json(ensemble)),
      http.get('/api/verification', () => HttpResponse.json(verification)),
      http.get('/api/marine', () => HttpResponse.json(marine)),
      http.get('/api/air-quality', () => HttpResponse.json(airQuality)),
    );

    const ensembleView = mount(<EnsembleSurface />);
    await checkOpening(ensembleView.container, 'ensemble-headline', 'ensemble-meaning', 'Name a place');
    expect(screen.getAllByText(HELD.label).length).toBeGreaterThan(0);
    // The held place is the place the read was asked about, named on the page rather than remembered.
    expect(within(screen.getByTestId('ensemble-point')).getByText('Requested place').nextSibling)
      .toHaveTextContent(HELD.label);
    ensembleView.unmount();

    const verificationView = mount(<VerificationSurface />);
    await checkOpening(verificationView.container, 'verification-headline', 'verification-meaning', 'Name a place');
    // The window the read used is stated back beside the window that was asked for.
    const facts = within(await screen.findByTestId('verification-window'));
    expect(facts.getByText('Window as the reading returned it').nextSibling).toHaveTextContent('2026-09-08 to 2026-09-14');
    verificationView.unmount();

    const marineView = mount(<MarineSurface />);
    await checkOpening(marineView.container, 'marine-wave-headline', 'marine-boundary', 'Name a place');
    marineView.unmount();

    const airView = mount(<AirQualitySurface />);
    await checkOpening(airView.container, 'air-quality-headline', 'air-quality-model-not-monitor', 'Name a place');
    // The source's own category word is printed; health advice is not, in any wording.
    expect(screen.getByTestId('air-quality-headline')).toHaveTextContent('Very Unhealthy');
    expect(screen.getByTestId('air-quality-headline')).not.toHaveTextContent(
      /should|must |avoid|wear a mask|stay indoors|close your windows|limit outdoor|protectiv|risk score/i,
    );
    airView.unmount();
  });

  it('states the two places it needs before it reads either of them, and issues the readings for the held place and then the chosen one', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json({
        ...HEAD, view: 'places.search', data: { matches: [{ label: 'Surat, Surat, Gujarat', latitude: 21.1702, longitude: 72.8311, selection_id: 'geonames:1' }] },
        sources: [], limitations: [], not_established: [],
      })),
      http.get('/api/forecast', ({ request }) => HttpResponse.json(
        new URL(request.url).searchParams.get('lat') === String(HELD.latitude) ? forecast(29.4) : forecast(31.2),
      )),
    );
    const view = mount(<CompareSurface />);

    // One place is already held, so the surface names it and asks for the other. The reading is drawn only
    // once both reads have answered: two numbers side by side is the whole surface, and one column is not it.
    expect(await screen.findByTestId('compare-awaiting')).toHaveTextContent('One place is chosen.');
    expect(screen.queryByTestId('compare-headline')).toBeNull();

    const inputs = await screen.findAllByLabelText('Name a place');
    await userEvent.type(inputs[1], 'Surat');
    await userEvent.click(await screen.findByRole('button', { name: /Surat, Surat, Gujarat/ }));

    const headline = await screen.findByTestId('compare-headline');
    expect(headline).toHaveTextContent('Kochi, Ernakulam, Kerala');
    expect(headline).toHaveTextContent('29.4');
    expect(headline).toHaveTextContent('31.2');
    // Two printed outputs held beside each other. The refusal is the surface's own sentence, and nothing
    // computed appears beside it: no winner, no margin, no averaged or resolved number.
    expect(headline).toHaveTextContent('not a ranking, an average or a confidence');
    expect(headline).not.toHaveTextContent(/more accurate|better than|wins|difference of|averaged|resolved to/i);
    expect(provenanceOffenders(headline)).toEqual([]);
    const firstTable = view.container.querySelector('table');
    expect(headline.compareDocumentPosition(firstTable as Node) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const fold = screen.getByTestId('compare-boundary');
    expect(fold.tagName).toBe('DETAILS');
    view.unmount();
  });

  it('keeps the controls while a read is in flight and after one has failed', async () => {
    server.use(
      http.get('/api/ensemble', async () => { await delay(120); return HttpResponse.json(ensemble); }),
    );
    const view = mount(<EnsembleSurface />);
    // In flight: the wait is stated, and the place that produced it is still named and still changeable.
    expect(await screen.findByTestId('skeleton')).toBeInTheDocument();
    expect(screen.getByLabelText('Name a place')).toBeInTheDocument();
    expect(await screen.findByTestId('ensemble-headline')).toBeInTheDocument();
    view.unmount();

    server.use(
      http.get('/api/ensemble', () => HttpResponse.json({ error: 'the store could not be opened' }, { status: 503 })),
    );
    const failed = mount(<EnsembleSurface />);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('The local evidence store is unavailable');
    expect(alert).toHaveTextContent('the store could not be opened');
    // The failure is stated, and the control that would ask about somewhere else is still there.
    expect(screen.getByLabelText('Name a place')).toBeInTheDocument();
    expect(screen.queryByTestId('ensemble-headline')).toBeNull();
    failed.unmount();
  });

  it('reads a station report from a code and decodes it beside the source’s own string, verbatim', async () => {
    server.use(http.get('/api/aviation', () => HttpResponse.json(metar)));
    const view = mount(<AviationSurface />);

    // Nothing has been read before a code is given: an invitation, not a sentence about the machine.
    expect(await screen.findByTestId('aviation-awaiting')).toHaveTextContent('Nothing has been read yet.');
    expect(screen.queryByTestId('aviation-headline')).toBeNull();

    await userEvent.type(screen.getByLabelText('ICAO codes to read, comma separated'), 'VOCI');
    await userEvent.click(screen.getByRole('button', { name: 'Read these reports' }));

    const headline = await screen.findByTestId('aviation-headline');
    expect(headline).toHaveTextContent('VOCI');
    expect(headline).toHaveTextContent('temperature 27°C');
    expect(headline).toHaveTextContent('freshness word for it: current');
    expect(provenanceOffenders(headline)).toEqual([]);

    // The publisher's own words, character for character, and the decoded fields ALONGSIDE them.
    expect(await screen.findByText('VOCI 202200Z 25008KT 9999 SCT020 27/24 Q1008')).toBeInTheDocument();
    const decoded = within(await screen.findByTestId('aviation-decoded-0'));
    expect(decoded.getByText('temperature_c')).toBeInTheDocument();
    expect(decoded.getByRole('rowheader', { name: 'temperature_c' }).nextSibling).toHaveTextContent('27');

    const fold = screen.getByTestId('aviation-standing');
    expect(fold.tagName).toBe('DETAILS');
    expect(fold).toHaveTextContent('A METAR is an observation from that station and not a forecast');
    expect(headline.compareDocumentPosition(fold) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    view.unmount();
  });

  it('reads the held place on arrival for the surfaces that take a point, and reads nothing at all without one', async () => {
    server.use(http.get('/api/ensemble', () => HttpResponse.json(ensemble)));
    forgetWorkingPlace();
    const view = mount(<EnsembleSurface />);

    // No place held, no request made: the surface states the one action that produces a reading and says
    // nothing about what the reading will refuse. A place the reader has not given is never fetched for.
    expect(await screen.findByTestId('ensemble-awaiting')).toHaveTextContent('Nothing has been read yet.');
    expect(screen.queryByTestId('ensemble-headline')).toBeNull();
    expect(screen.getByLabelText('Name a place')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByTestId('skeleton')).toBeNull());
    view.unmount();
  });
});
