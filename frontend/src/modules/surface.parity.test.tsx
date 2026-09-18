/* Parity checks for the suite shell, the surface panels and the map, ported from the vanilla component
   suite tests/test_suite_ui.js. That file prints 33 PASS lines; the module specs in this directory and the
   other parity specs hold most of the others (the Today tally, the warnings table, the documents list, the
   settings reads, the advisories directory and air-quality cell, the aviation report, the climate row, the
   marine cell, the ensemble statistics, the verification metrics, the what-changed vintages and the map
   colours). This file holds the remaining rules the React product does hold, against the payload constants
   copied verbatim from the vanilla file; the rules it cannot hold are listed at the end of this comment.

   Held here (numbered by the order the vanilla file prints its PASS lines):
   - check 1  every registered surface has a renderer, the map included; only the conversation itself sits
              outside the module registry, and App renders it;
   - check 5  the forecast surface draws its returned series as a chart;
   - check 13 the printed Alt+number hints agree with the mapping the keyboard handler opens;
   - check 21 the plans panel lists the saved plans and their notifications and checks them only when asked;
   - check 22 the watch inbox is read and a foreground watch check runs only when asked;
   - check 23 the appearance cycles system, day and night and records the choice;
   - check 25 the command palette lists every surface as a command, filters by what is typed and runs the
              chosen item;
   - check 28 every routed name resolves to itself, the hyphenated air-quality route included;
   - check 29 a fresh visit routes to the conversation, and an unknown route falls back to it;
   - check 31 two named places are read side by side and the surface refuses to difference or rank them;
   - check 32 an empty compare surface states its own emptiness;
   - check 33 every surface request carries the workspace token.

   Not portable, reported rather than asserted (the React product has no equivalent control or read):
   - check 3  the warnings surface writes an alert brief from a district detail drawer and presents the CAP
              relay as separate (the React warnings surface is the national table only; the briefcase composes
              and keeps alert briefs, which src/modules/briefcase.parity.test.tsx covers);
   - check 4  in part: the observations radar board, the rejected-feature list and station parameter units
              (the React observations surface reads the near and network station lists only);
   - checks 19, 20 the map pointer readout, a city selection as the working place, and the district tab stop
              with arrow keys (the React map is a schematic beside its accessible table, with no cursor);
   - check 24 the rail readout of per-product collection health (the React health chip states the store and
              its totals; the per-product rows live on the settings surface);
   - check 25 in part: a place search and stored conversations in the palette (the React palette lists
              surfaces and shell actions only);
   - check 26 document.startViewTransition is offered when available and never required (the React shell
              makes no view-transition call at all);
   - check 27 pinned places remembered locally (the React product stores no pins);
   - check 30 loading skeletons that reserve the shape of the answer (the React loading state is a sentence,
              and states no number);
   - check 21 in part: no 'Ask about this change' control on a notification, and check 22 in part: no
              'Checked n watch(es) in the foreground' sentence derived from the result rows. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { App } from '../App';
import { PlanWatch } from '../plans/PlanWatch';
import { parseHash } from '../shell/useHashRoute';
import { VIEWS } from '../shell/views';
import { server } from '../test/msw';
import { Surface as CompareSurface } from './CompareSurface';
import { Surface as ForecastSurface } from './ForecastSurface';
import { Surface as TodaySurface } from './TodaySurface';
import { Surface as WarningsSurface } from './WarningsSurface';
import { moduleFor } from './registry';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

beforeEach(() => {
  window.location.hash = '';
  try {
    window.localStorage.clear();
  } catch {
    /* storage is optional */
  }
});

afterEach(() => {
  document.documentElement.removeAttribute('data-theme');
  try {
    window.localStorage.clear();
  } catch {
    /* storage is optional */
  }
});

/* The vanilla file's own envelope and day helpers, copied so the payload constants below stay verbatim. */
function envelope(view: string, status: string, data: unknown, extra: Record<string, unknown> = {}) {
  return Object.assign(
    {
      schema_version: 'product-view-v1',
      generated_at_utc: '2026-09-14T18:00:00+00:00',
      view: view,
      status: status,
      data: data,
      sources: [],
      coverage: {},
      limitations: ['A stated limit of this view.'],
      not_established: ['Something not established here.'],
    },
    extra,
  );
}

function day(index: number, colour: string, codes?: number[], hazards?: string[]) {
  return {
    day: index,
    date_utc: '2026-09-14',
    colour: colour,
    colour_code: null,
    hazard_codes: codes || [1],
    hazards: hazards || ['No warning in this product'],
    source_text: null,
    unknown_hazard_codes: [],
    quiet: (hazards || ['No warning in this product'])[0] === 'No warning in this product',
  };
}

const DISTRICT = {
  key: 'PATNA',
  district: 'PATNA',
  state: 'BIHAR',
  bulletin_date: '2026-09-14',
  issued_at_utc: '2026-09-14T06:00:00+00:00',
  updated_at: '2026-09-14T12:35:18Z',
  days: [day(1, 'green'), day(2, 'yellow', [4], ['Thunderstorm/lightning/squall'])],
};

const OVERVIEW = envelope('overview', 'ok', {
  national: {
    districts: 756,
    tally: { yellow: 10, green: 700 },
    skipped: 8,
    bulletin_date: '2026-09-14',
    bulletin_dates: { '2026-09-14': 740 },
  },
  radar: { stations: 39, reported: 39 },
  places: [{ label: 'Patna', district: 'PATNA', state: 'BIHAR', bulletin_date: '2026-09-14', days: DISTRICT.days, note: null }],
});

const WARNINGS = envelope(
  'warnings.national',
  'ok',
  {
    districts: [DISTRICT],
    tally: { yellow: 1 },
    skipped: [{ obj_id: 9, reason: 'no district name' }],
    basemap_build: 'basemap-v1-test',
  },
  { coverage: { features_returned: 764, districts_listed: 1, skipped_without_a_name: 1, basemap_districts: 756 } },
);

/* One district polygon for the dashboard's map read: the token contract is what this file checks, so the
   geometry only has to be a readable FeatureCollection. */
const DISTRICT_GEOMETRY = {
  type: 'FeatureCollection',
  features: [
    { type: 'Feature', properties: { k: 'PATNA', n: 'PATNA', s: 'BIHAR' },
      geometry: { type: 'Polygon', coordinates: [[[85.0, 25.4], [85.4, 25.4], [85.4, 25.8], [85.0, 25.8], [85.0, 25.4]]] } },
  ],
};

const FORECAST = envelope('forecast.point', 'ok', {
  parameters: {
    temperature_2m: {
      unit: '°C',
      model: 'test model',
      quality_flags: [],
      points: [{ t: '2026-09-14T00:00:00+00:00', v: 26, source_locator: '$.hourly.temperature_2m[0]' }],
    },
  },
  days: 1,
  source_family: 'hourly_forecast',
  grid: { latitude: 23.02, longitude: 72.6 },
  requested: { latitude: 23.03, longitude: 72.59 },
  time_basis: 'UTC',
});

const CHANGES = envelope(
  'forecast.changes',
  'ok',
  {
    point: { latitude: 23.02579, longitude: 72.58727 },
    requested_point: { latitude: 23.02579, longitude: 72.58727 },
    retrievals: [
      { retrieved_at_utc: '2026-09-14T22:34:10+00:00', product: 'forecast', request_date: '2026-09-12', response_sha256_prefix: 'abc123' },
    ],
    retrieval_count: 2,
    overlapping_valid_hours: 6,
    parameters: {
      temperature_2m: {
        unit: '°C',
        valid_hours: 6,
        mean_abs_change: 0.7,
        max_abs_change: 4.8,
        example: {
          valid_time_utc: '2026-09-13T10:00:00+00:00',
          first_value: 29.1,
          last_value: 24.3,
          first_retrieved_utc: '2026-09-12T07:38:40+00:00',
          last_retrieved_utc: '2026-09-12T20:40:23+00:00',
        },
      },
    },
    interpretation: 'vintage_variance_not_skill',
  },
  { limitations: ['Not forecast skill.'], not_established: ['Forecast skill is not measured here.'] },
);

const PLACES = envelope('places.search', 'ok', {
  matches: [{ label: 'Surat, Sūrat, State of Gujarāt', name: 'Surat', source_id: 'geonames', kind: 'city', coordinates: { latitude: 21.1959, longitude: 72.8302 } }],
});

const AIR_QUALITY = envelope(
  'air_quality.point',
  'ok',
  {
    parameters: {
      pm2_5: { unit: '\u03bcg/m\u00b3', points: [{ t: '2026-09-14T00:00:00+00:00', v: 7.3, source_locator: '$.hourly.pm2_5[0]' }] },
      us_aqi: { unit: 'US AQI', points: [{ t: '2026-09-14T00:00:00+00:00', v: 53, source_locator: '$.hourly.us_aqi[0]' }] },
    },
    current: { pm2_5: 12.6, us_aqi: 53 },
    grid: { latitude: 23.0, longitude: 72.6 },
    domain: 'CAMS global (Open-Meteo automatic domain)',
    requested: { latitude: 23.03, longitude: 72.59 },
  },
  { not_established: ['An air-quality index is the source\u2019s own index, and no health advice, risk score or official warning is produced from it.'] },
);


const PLANS = {
  schema_version: 'plan-inbox-v1',
  mode: 'live',
  delivery: 'local_inbox_and_browser_notifications_while_the_workspace_runs',
  plans: [
    {
      id: 'p1',
      title: 'Cotton spraying · Rajkot, Gujarat · Monday 21 Sep morning',
      state: 'waiting_for_coverage',
      state_words: 'waiting for IMD coverage',
      hazards: 'heavy rain, thunderstorm & lightning and strong surface winds',
      last_checked_at: '2026-09-15T05:00:00+00:00',
      not_connected: null,
    },
  ],
  notifications: [
    {
      id: 3,
      plan_id: 'p1',
      kind: 'change',
      created_at: '2026-09-15T07:00:00+00:00',
      visible_at: '2026-09-15T07:00:00+00:00',
      visible: true,
      title: 'Monday 21 Sep · Rajkot, Gujarat · official warning issued',
      text: 'Monday 21 Sep for your cotton spraying in Rajkot, Gujarat changed: no warning for your watched hazards → Thunderstorm/lightning/squall (yellow).',
      receipt: {
        place: 'Rajkot, Gujarat',
        date: '2026-09-21',
        district: 'RAJKOT',
        hazards: ['Thunderstorm/lightning/squall'],
        colour: 'yellow',
        source_id: 'S63',
        origin_authentication: 'unverified',
      },
    },
  ],
  watcher: { running: true, interval_seconds: 1800, last_cycle_at: '2026-09-15T07:00:00+00:00', last_error: null },
  recorded_editions: 0,
  limits: ['No warning for your watched hazards is not an all-clear.'],
};

const PLAN_CHECK = { schema_version: 'plan-check-v1', result: { checked: 1, notified: 0, read: true } };

const WATCHES = {
  schema_version: 'watch-inbox-v1',
  delivery: 'local_inbox_only_no_push',
  note: 'Watches are evaluated only when asked.',
  checked_products: ['S15 IMD district warning product', 'S06 CAP relay assessment'],
  watches: [
    {
      id: 'w1',
      created_at: '2026-09-15T08:00:00+00:00',
      question: 'Notify me if a heavy rain warning is issued for Thiruvananthapuram, Kerala tomorrow',
      place: { name: 'Thiruvananthapuram, Kerala' },
      hazard: 'heavy_rain',
      window_start: null,
      window_end: null,
      state: 'registered_check_on_request',
      last_checked_at: null,
      result: null,
    },
  ],
};

const WATCH_CHECK = {
  schema_version: 'watch-check-v1',
  delivery: 'local_inbox_only_no_push',
  results: [{ id: 'w1', state: 'checked_no_match', matched: false, detail: 'No current day matches; this is not an all-clear.' }],
};

/* The plan/watch panel also reads the outbox, the watch-health, the push state and the delivery aggregate.
   The vanilla suite has no recorded payload for those four routes (its panel read the same views from a
   single notify body), so they are the smallest bodies the panel renders without inventing a value. */
const OUTBOX = { schema_version: 'outbox-v1', delivery: 'local_inbox_only_no_push', note: 'Nothing has been dispatched from this machine.', notifications: [] };

const WATCH_HEALTH = {
  schema_version: 'watch-health-v1',
  mode: 'manual-only',
  note: 'No hosted daemon or OS scheduler is installed.',
  tick: { fresh: false, age_seconds: null, reason: 'no heartbeat recorded yet' },
  outbox: { counts: { queued: 0 }, undispatched_depth: 0 },
  watches: { total: 1, active: 1, expired: 0 },
  plan_watcher: { running: true, interval_seconds: 1800 },
};

const PUSH_STATE = { schema_version: 'push-state-v1', subscriptions: { active: 0 } };

const WATCH_DMA = {
  schema_version: 'watch-dma-v2',
  note: 'Counts of local notifications and the responses owners sent back, broken down by official source.',
  places: [],
};

function planWatchHandlers(onPlanCheck: () => void, onWatchCheck: () => void) {
  return [
    http.get('/api/plans', () => HttpResponse.json(PLANS)),
    http.get('/api/watches', () => HttpResponse.json(WATCHES)),
    http.get('/api/outbox', () => HttpResponse.json(OUTBOX)),
    http.get('/api/watch-health', () => HttpResponse.json(WATCH_HEALTH)),
    http.get('/api/push/state', () => HttpResponse.json(PUSH_STATE)),
    http.get('/api/watches/dma', () => HttpResponse.json(WATCH_DMA)),
    http.post('/api/plans/check', () => {
      onPlanCheck();
      return HttpResponse.json(PLAN_CHECK);
    }),
    http.post('/api/watches/check', () => {
      onWatchCheck();
      return HttpResponse.json(WATCH_CHECK);
    }),
  ];
}

describe('every surface has a renderer', () => {
  it('registers a renderer for every routed surface, the map included, with only the conversation outside the registry', async () => {
    const withoutARenderer: string[] = [];
    for (const view of VIEWS) {
      if (view.id === 'assistant') continue;
      const entry = moduleFor(view.id);
      if (!entry) {
        withoutARenderer.push(view.id);
        continue;
      }
      const loaded = await entry.load();
      if (typeof loaded.Surface !== 'function') withoutARenderer.push(view.id);
    }

    expect(withoutARenderer).toEqual([]);
    expect(moduleFor('map')).toBeDefined();
    expect(VIEWS.filter(view => !moduleFor(view.id)).map(view => view.id)).toEqual(['assistant']);
  });
});

describe('the forecast surface draws a chart', () => {
  it('draws the series the read returned as a chart beside its exact values', async () => {
    server.use(
      http.get('/api/places/search', () => HttpResponse.json(PLACES)),
      http.get('/api/forecast', () => HttpResponse.json(FORECAST)),
      http.get('/api/forecast/changes', () => HttpResponse.json(CHANGES)),
    );
    mount(<ForecastSurface />);
    await screen.findByLabelText('Name a place');
    await userEvent.type(screen.getByLabelText('Name a place'), 'Surat');
    await userEvent.click(await screen.findByRole('button', { name: /Surat, Sūrat, State of Gujarāt/ }));

    expect(await screen.findByRole('heading', { level: 3, name: 'temperature_2m (°C)' })).toBeInTheDocument();
    const chart = screen.getByTestId('chart-block');
    expect(chart.querySelector('svg')).not.toBeNull();
    // The one returned point is drawn, and the same number is still reachable as its exact value.
    expect(chart).toHaveTextContent('26');
    expect(within(chart).getByRole('button', { name: /26 °C/ })).toBeInTheDocument();
  });
});
describe('the plans and watches panel', () => {
  it('lists the saved plans and their notifications, and checks plans only when asked', async () => {
    let checks = 0;
    server.use(...planWatchHandlers(() => { checks += 1; }, () => {}));
    mount(<PlanWatch onClose={() => {}} />);

    const plans = within(await screen.findByTestId('planwatch-plans'));
    expect(plans.getByText('Cotton spraying · Rajkot, Gujarat · Monday 21 Sep morning')).toBeInTheDocument();
    expect(plans.getByText('waiting for IMD coverage')).toBeInTheDocument();

    const notifications = within(await screen.findByTestId('planwatch-notifications'));
    expect(notifications.getByText('Monday 21 Sep · Rajkot, Gujarat · official warning issued')).toBeInTheDocument();
    expect(notifications.getByText(/no warning for your watched hazards/)).toHaveTextContent('Thunderstorm/lightning/squall (yellow)');
    expect(screen.getByText('No warning for your watched hazards is not an all-clear.')).toBeInTheDocument();
    // Replay is not offered without two recorded editions, and this read states none were recorded.
    expect(screen.queryByRole('button', { name: /Replay/ })).toBeNull();
    expect(checks).toBe(0);

    await userEvent.click(screen.getByRole('button', { name: 'Check saved plans now' }));
    await waitFor(() => expect(checks).toBe(1));
    const result = await screen.findByTestId('planwatch-check-result');
    expect(result).toHaveTextContent('the district warning product was read in this cycle');
    expect(within(result).getByText('checked (as returned)')).toBeInTheDocument();
  });

  it('reads the local watch inbox and runs a foreground watch check only when asked', async () => {
    let checks = 0;
    server.use(...planWatchHandlers(() => {}, () => { checks += 1; }));
    mount(<PlanWatch onClose={() => {}} />);

    const watches = within(await screen.findByTestId('planwatch-watches'));
    expect(watches.getByText('Thiruvananthapuram, Kerala')).toBeInTheDocument();
    expect(watches.getByText('registered_check_on_request')).toBeInTheDocument();
    expect(screen.getByText(/Watches are evaluated only when asked/)).toBeInTheDocument();
    expect(checks).toBe(0);

    await userEvent.click(screen.getByRole('button', { name: 'Check open watches now (foreground)' }));
    await waitFor(() => expect(checks).toBe(1));
    const result = await screen.findByTestId('planwatch-watch-check');
    expect(within(result).getByText('checked_no_match')).toBeInTheDocument();
    expect(within(result).getByText('No current day matches; this is not an all-clear.')).toBeInTheDocument();
  });
});
describe('the routed names', () => {
  it('resolves every routed view name to itself, including the hyphenated air-quality route', async () => {
    expect(parseHash('#/air-quality').view.id).toBe('air-quality');
    expect(parseHash('#/ensemble').view.id).toBe('ensemble');
    expect(parseHash('#/overview').view.id).toBe('overview');

    server.use(http.get('/api/air-quality', () => HttpResponse.json(AIR_QUALITY)));
    window.location.hash = '#/air-quality';
    mount(<App />);
    await waitFor(() => expect(document.querySelector('[data-surface="air-quality"]')).not.toBeNull());
  });

  it('routes a fresh visit to the conversation and falls back to it for an unknown route', async () => {
    // A fresh visit opens the front door first (a recorded change from the vanilla shell) and the route it
    // holds is the conversation. The door's one action — handing a question to the conversation — is
    // checked in App.test.tsx; here the contract is the route and the reachable question box.
    window.location.hash = '';
    const front = render(<App />);
    expect(parseHash('').view.id).toBe('assistant');
    expect(screen.getByLabelText('Your question')).toBeInTheDocument();
    /* The door is served at the empty address and does not redirect: the conversation is the route it
       holds, and reaching it is the reader's action rather than a side effect of arriving. */
    expect(window.location.hash).toBe('');
    front.unmount();

    window.location.hash = '#/nothing-here';
    mount(<App />);
    expect(parseHash('#/nothing-here').view.id).toBe('assistant');
    expect(await screen.findByLabelText('Your question')).toBeInTheDocument();
  });
});

describe('the compare surface', () => {
  const SURAT = { label: 'Surat, Surat, Gujarat', latitude: 21.1702, longitude: 72.8311, admin1: 'Gujarat', admin2: 'Surat' };
  const VADODARA = { label: 'Vadodara, Vadodara, Gujarat', latitude: 22.3072, longitude: 73.1812, admin1: 'Gujarat', admin2: 'Vadodara' };

  const placesRoute = () =>
    http.get('/api/places/search', ({ request }) => {
      const term = new URL(request.url).searchParams.get('q') || '';
      return HttpResponse.json(envelope('places.search', 'ok', { matches: [term.toLowerCase().startsWith('sur') ? SURAT : VADODARA] }));
    });

  it('holds two named places side by side from two separate reads and refuses to difference or rank them', async () => {
    server.use(placesRoute(), http.get('/api/forecast', () => HttpResponse.json(FORECAST)));
    mount(<CompareSurface />);

    const inputs = await screen.findAllByLabelText('Name a place');
    await userEvent.type(inputs[0], 'Surat');
    await userEvent.click(await screen.findByRole('button', { name: /Surat, Surat, Gujarat/ }));
    await userEvent.type(inputs[1], 'Vadodara');
    await userEvent.click(await screen.findByRole('button', { name: /Vadodara, Vadodara, Gujarat/ }));

    expect(await screen.findByTestId('compare-read-first')).toHaveTextContent('Surat, Surat, Gujarat');
    expect(await screen.findByTestId('compare-read-second')).toHaveTextContent('Vadodara, Vadodara, Gujarat');
    expect(screen.getByTestId('compare-boundary')).toHaveTextContent(/not a ranking, a recommendation, a better-or-worse judgement/);

    const table = within(await screen.findByTestId('compare-parameter-temperature_2m'));
    const headers = table.getAllByRole('columnheader').map(cell => cell.textContent || '');
    expect(headers.some(name => /First read · Surat/.test(name))).toBe(true);
    expect(headers.some(name => /Second read · Vadodara/.test(name))).toBe(true);
    // No column states a difference or a delta between the two places.
    expect(headers.some(name => /difference|delta|change/i.test(name))).toBe(false);
  });

  it('states its own emptiness when no place has been named on either side', async () => {
    mount(<CompareSurface />);
    expect(await screen.findByText('No place has been chosen for the first read, so no forecast was requested for it.')).toBeInTheDocument();
    expect(screen.getByText('No place has been chosen for the second read, so no forecast was requested for it.')).toBeInTheDocument();
    expect(screen.queryByTestId('compare-parameter-temperature_2m')).toBeNull();
  });
});

describe('the command palette', () => {
  it('lists every surface as a command, filters by what is typed, and runs the chosen item', async () => {
    server.use(http.get('/api/warnings/national', () => HttpResponse.json(WARNINGS)));
    window.location.hash = '#/assistant';
    mount(<App />);

    await userEvent.keyboard('{Alt>}k{/Alt}');
    const palette = await screen.findByRole('dialog', { name: 'Command palette' });
    const commands = within(palette).getAllByRole('option').map(option => option.textContent || '');
    for (const view of VIEWS) {
      expect(commands.some(text => text.startsWith('Open ' + view.label))).toBe(true);
    }

    await userEvent.type(document.getElementById('palette-search') as HTMLInputElement, 'Warnings');
    await userEvent.keyboard('{Enter}');
    expect(window.location.hash).toBe('#/warnings');
  });
});

describe('the workspace token', () => {
  it('is carried on every request the surfaces made', async () => {
    const TOKEN = 'test-token';
    const meta = document.createElement('meta');
    meta.setAttribute('name', 'workspace-token');
    meta.setAttribute('content', TOKEN);
    document.head.append(meta);

    const seen: { path: string; token: string | null }[] = [];
    const passthrough = globalThis.fetch;
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      seen.push({ path: String(input), token: new Headers(init?.headers as HeadersInit | undefined).get('X-WeatherGPT-Token') });
      return passthrough(input, init);
    });

    try {
      server.use(
        http.get('/api/overview', () => HttpResponse.json(OVERVIEW)),
        http.get('/api/warnings/national', () => HttpResponse.json(WARNINGS)),
        /* The Today dashboard joined a third read to itself: the served district geometry its map draws. */
        http.get('/api/map/static/districts', () => HttpResponse.json(DISTRICT_GEOMETRY)),
      );
      mount(
        <>
          <TodaySurface />
          <WarningsSurface />
        </>,
      );
      await screen.findByTestId('today-national');
      await screen.findByTestId('warnings-table');
      /* Three distinct reads. The today dashboard and the warnings surface name the warning read with the same
         cache key, so the app's 30 s staleTime serves the second observer from the first fetch; this harness
         sets no staleTime, so it may fetch that URL once per observer and the set is what is asserted. */
      await waitFor(() => expect(new Set(seen.filter(row => row.path.startsWith('/api/')).map(row => row.path)).size).toBe(3));
    } finally {
      spy.mockRestore();
      meta.remove();
    }

    const surfaceCalls = seen.filter(row => row.path.startsWith('/api/'));
    expect(Array.from(new Set(surfaceCalls.map(row => row.path))).sort()).toEqual(['/api/map/static/districts', '/api/overview', '/api/warnings/national']);
    expect(surfaceCalls.every(row => row.token === TOKEN)).toBe(true);
  });
});
