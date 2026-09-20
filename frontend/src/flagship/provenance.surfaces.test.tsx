/* X1 across the surfaces nobody else is holding: one rule, held against every surface in this lane.
   ============================================================================
   claims.audit.test.tsx holds the rule over the answer card; this file holds the SAME definitions —
   imported from ./provenance.ts, never copied — over the surfaces around it: the welcome, the rail, the
   bar, the field, a turn still working, the plan and watch panel, the owner gate, the component kit and
   the national read.

   Every payload below is copied verbatim from the spec that already carries it, named above each block, so
   each surface is audited against the same recorded read its own spec holds it to and no live server is
   called. A surface whose render needs the shell's providers is mounted through the harness its own spec
   uses, and the audit is given the subtree that surface owns.

   docs/127 records what each offender was and the decision taken on it. The verdict here is the audit's:
   `provenanceOffenders` is the function the answer card is held to, so a surface that passes here passes
   the same rule, not a second one. */

import { render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';
import { server } from '../test/msw';
import { renderAsk } from '../test/ask';
import { Field } from '../gpt/Field';
import { Rail } from '../gpt/Rail';
import { StationBlock } from '../gpt/ReadingPanel';
import { TopBar } from '../gpt/TopBar';
import { Welcome } from '../gpt/Welcome';
import { useSky } from '../gpt/sky';
import { describeNational } from '../home/overview';
import { OwnerGate } from '../landing/OwnerGate';
import { OWNER_KEY } from '../landing/owner';
import { PlanWatch } from '../plans/PlanWatch';
import { Button, Empty, Field as KitField, HazardChip, Panel, Segmented, SkeletonLines, Stat, Switch, ToastHost, useToast } from '../ui/kit';
import { provenanceOffenders } from './provenance';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const clean = (container: HTMLElement) => provenanceOffenders(container);

/* ---- the reading a station reported: home.test.tsx's recorded /api/now answer -------------------------- */

/* home.test.tsx, copied verbatim: the envelope every /api/now answer arrives in, and a station that printed
   its own weather field. */
function envelope(data: Record<string, unknown>, status = 'ok') {
  return {
    schema_version: 'product-view-v1',
    view: 'now.composed',
    status,
    generated_at_utc: '2026-09-19T06:30:00+00:00',
    data,
    sources: [],
  };
}

function station(fields: { field: string; value: unknown; unit?: string | null }[]) {
  return envelope({
    schema_version: 'now-v1',
    point: { latitude: 23.0225, longitude: 72.5714, label: 'Ahmedabad, Gujarat' },
    observed: {
      status: 'ok',
      stations: [{
        kind: 'metar', name: 'AHMEDABAD', station_code: 'VAAH',
        observed_at_utc: '2026-09-19T06:30:00+00:00', distance_km: 8.8, source_id: 'S63', stale: false,
        parameters: fields,
      }],
    },
  });
}

const PLACE_KEY = 'weathergpt.place';

function holdAPlace() {
  window.localStorage.setItem(PLACE_KEY, JSON.stringify({ label: 'Ahmedabad, Gujarat', latitude: 23.0225, longitude: 72.5714 }));
}

const STATION_READING = [
  { field: 'temp', value: 29, unit: '°C' },
  { field: 'weather', value: 'haze', unit: null },
];

const serveTheStation = () => server.use(http.get('/api/now', () => HttpResponse.json(station(STATION_READING))));

/* The bar draws the reading sky.ts derives, so it is mounted over the product's own derivation rather than
   over a hand-written SkyReading: the number on screen is the one the payload produced. TopBar takes that
   reading as a prop, exactly as Workspace passes it. */
function SkyHarness() {
  const sky = useSky();
  return (
    <TopBar
      title="Will it rain in Ahmedabad?"
      chatting
      sky={sky.data}
      panelOpen={false}
      onTogglePanel={() => {}}
      onToggleRail={() => {}}
      onExport={null}
    />
  );
}

/* ---- the rail: shell.test.tsx's recorded conversation ledger ------------------------------------------ */

/* shell.test.tsx, copied verbatim: the ledger the rail reads, including the row that resolved a place. */
const LEDGER = {
  schema_version: 'conversation-ledger-v1',
  total: 2,
  limit: 40,
  conversations: [
    { id: 'p1', updated: new Date().toISOString(), turns: 2, asked: 1,
      opening_question: 'Is any warning in force?', place: { label: 'Patna, Patna, State of Bihar', latitude: 25.6, longitude: 85.1 } },
    { id: 'p2', updated: new Date().toISOString(), turns: 2, asked: 1, opening_question: 'how are you' },
  ],
};

function rail() {
  return (
    <Rail
      currentId={null}
      onOpen={() => {}}
      onNew={() => {}}
      onOpenView={() => {}}
      onAsk={() => {}}
      currentView="assistant"
      home={null}
      collapsed={false}
      onToggle={() => {}}
      pins={[]}
      onPin={() => {}}
      aliases={{}}
      onAlias={() => {}}
      onFindPlace={() => {}}
      onPlans={() => {}}
      onOwner={() => {}}
    />
  );
}

/* ---- a turn still working: chat.test.tsx's recorded engine reads -------------------------------------- */

/* chat.test.tsx, copied verbatim: the answer packet, the provisional first reading and the progress read a
   working turn is drawn from. The delay is the mechanism that spec already uses to look at the waiting state
   while it is still waiting. */
const FORECAST = {
  schema_version: 'weather-conversation-v1',
  conversation_id: '44444444-4444-4444-8444-444444444444',
  question: 'Will it rain in Ahmedabad?',
  status: 'answered',
  answer: 'Ahmedabad: forecast precipitation 0.3 mm.',
  facts: [{
    id: 't1-f1', label: 'Forecast rainfall', value: '0.3', unit: 'mm',
    place: 'Ahmedabad, Ahmadabad, State of Gujarat',
    start: '2026-09-15T06:30:00+05:30', end: '2026-09-15T12:30:00+05:30',
    source_id: 'S21', parameter: 'precipitation', entity_id: 'geonames:1279233',
    evidence_kind: 'forecast', evidence_version: 'a'.repeat(64), citation_ids: ['t1-c1'], task_id: 't1',
  }],
  citations: [{ id: 't1-c1', source_id: 'S21', provider: 'Open-Meteo', product: 'GFS forecast delivery',
                url: 'https://api.open-meteo.com/v1/forecast', retrieved_at_utc: '2026-09-14T10:39:00+00:00' }],
  notes: [], choices: [], charts: [], calculations: [], task_results: [], follow_up: null,
  answered_at_utc: '2026-09-14T10:47:00+00:00', expires_at_utc: '2026-09-14T11:47:00+00:00',
  operational_eligible: false,
  trace: { planning: { planner_policy: 'model', provider: 'DeepSeek' }, generation: { provider: 'DeepSeek' }, tools: [{ name: 'point_forecast' }], duration_seconds: 5.9 },
  retrieval_plan: [], task_coverage: { requested: 1, completed: 1, incomplete_ids: [] },
  resolved_points: { Ahmedabad: { selection_id: 'geonames:1279233', label: 'Ahmedabad, Gujarat', coordinates: { latitude: 23.02579, longitude: 72.58727 } } },
};

const PREVIEW = {
  schema_version: 'chat-preview-v1',
  provisional: true,
  note: 'A first reading by the deterministic rules planner, before any retrieval.',
  reading: { line: 'place: Ahmedabad · window: 15 Sep 2026 12:00-18:00 IST · asking about: rain · will read: a point forecast' },
};

const PROGRESS = {
  schema_version: 'chat-progress-v1',
  state: 'working',
  stage: 'retrieving',
  stage_label: 'Retrieving evidence',
  stages_seen: ['started', 'planned', 'resolving', 'retrieving'],
  queue: { waiting: 0, active: 1, capacity: 3, wait_seconds_before_refusal: 45 },
  stage_note: 'A stage names the work the server is in now. It is not a completion estimate.',
};

function chatHandlers(packet: Record<string, unknown>, options: { answerAfterMs?: number } = {}) {
  return [
    http.post('/api/chat/preview', () => HttpResponse.json(PREVIEW)),
    http.get('/api/chat/progress', () => HttpResponse.json(PROGRESS)),
    http.post('/api/chat', async () => {
      if (options.answerAfterMs) await new Promise(resolve => setTimeout(resolve, options.answerAfterMs));
      return HttpResponse.json(packet);
    }),
    http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 1, limit: 40, conversations: [], note: 'stored locally' })),
  ];
}

/* By its id rather than its English label, as chat.test.tsx asks: the composer's label is chrome, and this
   spec is not about the chrome. */
async function askQuestion(text: string) {
  const user = userEvent.setup();
  const box = document.getElementById('question') as HTMLTextAreaElement;
  await user.clear(box);
  await user.type(box, text);
  await user.click(screen.getByTestId('send-question'));
}

/* ---- the plan and watch panel: planwatch.parity.test.tsx's recorded reads ------------------------------ */

const WATCH = {
  id: 'w1', created_at: '2026-09-15T08:00:00+00:00',
  question: 'Notify me if a heavy rain warning is issued for Thiruvananthapuram, Kerala tomorrow',
  place: { name: 'Thiruvananthapuram, Kerala' }, hazard: 'heavy_rain',
  window_start: null, window_end: null, state: 'matched',
  last_checked_at: '2026-09-16T09:00:00+00:00', result: null,
  channels: ['local_inbox'], consent_record: { local_inbox: { granted_at: '2026-09-15T08:00:00+00:00', source: 'explicit_chat_request' } },
  fingerprint_sha256: 'abc', outbox_pending: 1, last_notification_at: '2026-09-16T10:00:00+00:00',
};
const ROWS = [
  { id: 'o1', watch_id: 'w1', correlation_id: 'c1', fingerprint_sha256: 'abc', state: 'sent',
    channel: 'local_inbox', created_at: '2026-09-16T10:00:00+00:00', updated_at: '2026-09-16T10:00:00+00:00',
    retry_count: 0, max_retries: 3, next_retry_at: null, last_error: null },
  { id: 'o2', watch_id: 'w1', correlation_id: 'c2', fingerprint_sha256: 'def', state: 'queued',
    channel: 'local_inbox', created_at: '2026-09-16T11:00:00+00:00', updated_at: '2026-09-16T11:00:00+00:00',
    retry_count: 0, max_retries: 3, next_retry_at: null, last_error: null },
];

const PLAN_PAYLOADS = {
  '/api/plans': { schema_version: 'plan-inbox-v1', mode: 'live', plans: [], notifications: [],
                  watcher: { running: false }, recorded_editions: 0, limits: [] },
  '/api/watches': { schema_version: 'watch-inbox-v1', delivery: 'local_inbox_and_opt_in_web_push', note: '',
                    checked_products: [], watches: [WATCH] },
  '/api/watch-health': { schema_version: 'watch-health-v1', mode: 'manual-only',
                         note: 'No hosted daemon or OS scheduler is installed.',
                         heartbeat: null, tick: { fresh: false, age_seconds: null, reason: 'no watch-check run has ever reported' },
                         outbox: { counts: { created: 0, queued: 2, claimed: 1, sent: 4, failed: 1, dead: 1, acked: 1, gone: 0 } },
                         watches: { total: 1, active: 1, expired: 0 }, plan_watcher: { running: false } },
  '/api/outbox': { schema_version: 'outbox-v1', delivery: 'local_inbox_and_opt_in_web_push', note: '', notifications: ROWS },
  '/api/watches/dma': { schema_version: 'watch-dma-v2', note: 'Counts of local notifications and the responses owners sent back, broken down by official source.',
    places: [{ place: 'Thiruvananthapuram, Kerala', watches: 1, notifications: 2, acked: 1, safe: 1, need_help: 0,
               evacuating: 0, seen: 0, unacked: 1, sources: { S15: { notifications: 2, acked: 1 } } }] },
  '/api/push/state': { schema_version: 'push-state-v1', delivery: 'local_inbox_and_opt_in_web_push', note: '', purged_expired: 0, subscriptions: { active: 0 } },
  '/api/push/vapid-key': { schema_version: 'push-vapid-v1', public_key: 'B'.repeat(86) + 'A' },
};

function servePlans() {
  for (const [route, payload] of Object.entries(PLAN_PAYLOADS)) {
    server.use(http.get(route, () => HttpResponse.json(payload)));
  }
}

/* ---- the national read: national.test.ts's recorded overview payload ---------------------------------- */

type Overview = Parameters<typeof describeNational>[0];

/* national.test.ts, copied verbatim: the envelope /api/overview answers in. home/overview.ts composes the
   picture and owns no DOM; the surfaces that draw it are src/modules/**, held by another lane. */
function overviewRead(national: Record<string, unknown> | undefined) {
  return {
    data: {
      schema_version: 'product-view-v1',
      view: 'overview',
      status: 'ok',
      generated_at_utc: '2026-09-19T06:30:00+00:00',
      data: { national, radar: { stations: 39, reported: 39 }, places: [] },
      sources: [],
    },
  } as unknown as Overview;
}

describe('X1 — the surfaces around the answer', () => {
  beforeEach(() => {
    try { window.localStorage.clear(); } catch { /* storage is optional */ }
  });

  /* The ground draws no number at all — CSS layers and one glyph — so it has no provenance to carry, and
     nothing here is excluded to make it pass: the check is that there is no digit in its text to begin with. */
  it('the field is chrome: it states the hour in colour and holds no number', () => {
    const { container } = mount(<Field expanded sky="rain" />);
    expect(container.textContent || '').not.toMatch(/\d/);
    expect(clean(container)).toEqual([]);
  });

  it('the bar states the station\'s reading with the source line that owns it, not only in a title', async () => {
    holdAPlace();
    serveTheStation();
    const { container } = mount(<SkyHarness />);
    const skyline = await screen.findByTestId('skyline');

    expect(skyline.querySelector('.g-skyline-value')).toHaveTextContent('29°C');
    /* The source line is a line a reader sees: who reported it, the id the registry knows it by, and when it
       was read. In a title attribute it was provenance for whoever hovered. */
    const source = skyline.querySelector('.g-claim-source');
    expect(source).toHaveTextContent('AHMEDABAD');
    expect(source).toHaveTextContent('S63');
    expect(source).toHaveTextContent('read 19 Sep 2026, 12:00 IST');
    expect(clean(container)).toEqual([]);
  });

  it('the welcome states the reading and the line that owns it as one region', async () => {
    holdAPlace();
    serveTheStation();
    const { container } = mount(<Welcome hour="noon" />);
    const reading = await screen.findByText('haze');

    const claim = reading.closest('.g-claim');
    expect(claim).not.toBeNull();
    expect(claim!.querySelector('.w-temp')).toHaveTextContent('29');
    expect(claim!.querySelector('.g-claim-source')).toHaveTextContent('AHMEDABAD · S63');
    expect(claim!.querySelector('.g-claim-source')).toHaveTextContent('read 19 Sep 2026, 12:00 IST');
    expect(clean(container)).toEqual([]);
  });

  /* The product's rule for this screen: with no place held there is no condition word, no number and no
     source line at all. Absence stays absent rather than becoming a zero or a default condition. */
  it('the welcome invents nothing when no place is held', async () => {
    const { container } = mount(<Welcome hour="noon" />);
    await screen.findByTestId('welcome');

    expect(document.querySelector('.w-glyph')?.getAttribute('data-kind')).toBe('hour');
    expect(container.querySelector('.w-reading')).toBeNull();
    expect(container.querySelector('.w-temp')).toBeNull();
    expect(container.querySelector('.w-source')).toBeNull();
    expect(clean(container)).toEqual([]);
  });

  it('the welcome says a unit the source did not state rather than supplying one', async () => {
    holdAPlace();
    server.use(http.get('/api/now', () => HttpResponse.json(station([
      { field: 'temp', value: 29, unit: null },
      { field: 'weather', value: 'haze', unit: null },
    ]))));
    const { container } = mount(<Welcome hour="noon" />);
    await screen.findByText('haze');

    expect(container.querySelector('.w-unit')).toBeNull();
    expect(container.querySelector('.g-claim-source')).toHaveTextContent('no unit in the source');
    expect(clean(container)).toEqual([]);
  });

  it('the rail states the place\'s reading with its source line, beside counts that are its own rows', async () => {
    holdAPlace();
    serveTheStation();
    server.use(http.get('/api/conversations', () => HttpResponse.json(LEDGER)));
    const { container } = mount(rail());
    await screen.findAllByText(/Patna/);

    const placeReading = container.querySelector('.g-place-reading');
    expect(placeReading).toHaveTextContent('29°C');
    /* The reading and its source line are one region, so the number is not separated from what owns it. */
    const claim = placeReading!.closest('.g-claim');
    expect(claim).not.toBeNull();
    /* '8.8 km away', not '8.8 km': the distance states its relation, which is the wording the plan's own drawn
       claim line uses and the wording the place page's station block was documented with. */
    expect(claim!.querySelector('.g-claim-source')).toHaveTextContent('AHMEDABAD · S63 · read 19 Sep 2026, 12:00 IST · 8.8 km away');

    /* Two numbers on this rail are not values this product read: the count of this machine's own
       conversations that resolved a place, and the ⌥-key label beside a row. Both are rendered here so the
       exclusions are excusing a region that exists rather than a region that was never drawn. */
    expect(container.querySelector('.g-place-count')).toHaveTextContent('1');
    expect(container.querySelector('.g-kbd-row')).toHaveTextContent('⌥1');
    expect(clean(container)).toEqual([]);
  });

  /* The wait measures itself — the stage the engine is on, how long the reader has waited, how deep the
     queue is, how much server work was recorded — and it prints the planner's provisional first reading as
     not-evidence. No number in it is the weather, and none is drawn as though it were. */
  it('a turn still working states its own measurements and no weather', async () => {
    server.use(...chatHandlers(FORECAST, { answerAfterMs: 600_000 }));
    renderAsk();
    await askQuestion('Will it rain in Ahmedabad?');
    const working = await screen.findByTestId('working-turn');

    expect(working.querySelector('.g-working-stage')).toHaveTextContent('Retrieving evidence');
    /* The clock is not announced: a region that ticks once a second would be read out once a second. */
    expect(working.querySelector('.g-working-clock')?.closest('[aria-hidden="true"]')).not.toBeNull();
    /* Both regions the audit names are really here: the planner's first reading, and the queue's facts. */
    expect(await screen.findByTestId('reading-line')).toHaveTextContent('place: Ahmedabad');
    expect(working.querySelector('.g-working-note')).not.toBeNull();
    expect(clean(working)).toEqual([]);
  });

  it('the plan and watch panel states its own delivery records, and nothing of the weather', async () => {
    servePlans();
    const { container } = mount(<PlanWatch onClose={() => {}} />);
    await screen.findByTestId('planwatch-watches');

    /* The counts the health read returned, the watch's own instant and the outbox's states are on screen, so
       the regions the audit names for them are regions that exist. */
    const queued = within(await screen.findByTestId('planwatch-health-outbox')).getByRole('rowheader', { name: 'queued' });
    expect(within(queued.closest('tr') as HTMLElement).getByText('2')).toBeInTheDocument();
    expect(screen.getByTestId('planwatch-health-totals')).toHaveTextContent('1 / 1 / 0');
    expect(container.querySelector('.planwatch table, .planwatch .module-table')).not.toBeNull();
    expect(clean(container)).toEqual([]);
  });

  it('the owner gate describes itself, and its own pause counts itself down', async () => {
    const explaining = mount(<OwnerGate onOpen={() => {}} onSkip={() => {}} onEnter={() => {}} />);
    /* The gate's explanation names the key-derivation function it uses, which contains digits and is a
       description of this machine rather than a value anything read. */
    expect(explaining.container.querySelector('.gate-explains')).toHaveTextContent('PBKDF2-SHA-256');
    expect(clean(explaining.container)).toEqual([]);
    explaining.unmount();

    /* The countdown only exists once the gate has paused itself, so the verifier is seeded directly: this
       spec is about the number on screen, and six hundred thousand iterations per refusal is the gate's own
       cost, not this check's subject. */
    window.localStorage.setItem(OWNER_KEY, JSON.stringify({ v: 1, salt: btoa('0123456789abcdef'), iterations: 1, hash: btoa('not-the-hash') }));
    const { container } = mount(<OwnerGate onOpen={() => {}} onSkip={() => {}} onEnter={() => {}} />);
    const user = userEvent.setup();
    for (let attempt = 1; attempt <= 5; attempt += 1) {
      await user.type(screen.getByLabelText('Passphrase'), 'the-wrong-passphrase');
      await user.click(screen.getByTestId('gate-unlock-button'));
      await waitFor(() => expect(screen.getByTestId('gate-state')).toHaveTextContent(attempt < 5 ? /attempt/i : /paused/i));
    }
    expect(screen.getByTestId('gate-countdown')).toHaveTextContent(/Paused: \d+ seconds remaining/);
    expect(clean(container)).toEqual([]);
  });

  /* The kit is primitives: it draws what a caller hands it and introduces no number of its own. The payloads
     are kit.test.tsx's own, so this is the same render its spec holds. */
  it('the component kit draws no number of its own', async () => {
    function Chrome() {
      const toast = useToast();
      return <Button onClick={() => toast.push('Copied the receipt.', 'good')}>Copy</Button>;
    }
    const { container } = mount(
      <ToastHost>
        <Panel>
          <HazardChip colour="yellow">yellow</HazardChip>
          <Stat label="Districts in this read" value="not recorded" foot="The read returned no count." />
          <KitField label="Register a watch"><input /></KitField>
          <Switch checked onChange={() => {}} label="Local inbox" />
          <Segmented label="Register" options={[{ value: 'brief', label: 'Brief' }]} value="brief" onChange={() => {}} />
          <Empty title="Nothing kept yet" hint="No row returned." />
          <SkeletonLines lines={3} />
          <Chrome />
        </Panel>
      </ToastHost>,
    );
    await screen.findByRole('button', { name: 'Copy' });

    expect(container.textContent || '').not.toMatch(/\d/);
    expect(clean(container)).toEqual([]);
  });

  /* Recorded, not excused: a Stat handed a number has no region to put its source line in yet — the value
     is bare and the `foot` slot a caller would put the source line in is not a shape the rule accepts — so
     the audit reports both. The fix belongs where the value is handed over, the module surfaces, which are
     another lane's; this is the finding written down rather than a shape invented to hide it. */
  it('a Stat handed a number has nowhere to carry its source, and the audit says so', () => {
    const { container } = mount(
      <Stat label="Districts in this read" value="298" foot="IMD district warning bulletin · 15 Sep edition · read 12:00 IST" />,
    );
    const offenders = clean(container);
    expect(offenders).toHaveLength(2);
    expect(offenders[0]).toContain('298');
    expect(offenders[0]).toContain('.stat-value');
    expect(offenders[1]).toContain('IMD district warning bulletin');
    expect(offenders[1]).toContain('.stat-foot');
  });

  /* home/** owns no DOM: overview.ts composes the national picture and the surfaces that draw it are
     src/modules/**. What can be held here is the composition X1 depends on — that every number the
     description hands over travels with the read that produced it, and that a read which stated no today
     block is not read as a quiet day. */
  it('the national read hands every count over with the read that carried it', () => {
    const picture = describeNational(overviewRead({
      districts: 756,
      today: { counts: { red: 0, orange: 3, yellow: 298, green: 445 } },
      newest_bulletin_date_in_this_read: '2026-09-15',
    }));
    expect(picture.statedToday).toBe(true);
    expect(picture.yellow).toBe(298);
    expect(picture.districts).toBe(756);
    expect(picture.sourceLine).toContain('IMD district warning bulletin');
    expect(picture.sourceLine).toContain('15 Sep edition');
    expect(picture.sourceLine).toContain('756 districts');
    expect(picture.sourceLine).toContain('read 12:00 IST');

    /* No today block: the counts are not to be printed, and the description says so rather than saying zero. */
    const unstated = describeNational(overviewRead({ districts: 756, bulletin_date: '2026-09-15' }));
    expect(unstated.statedToday).toBe(false);

    /* A read that has not answered carries no provenance line at all, so there is nothing to print beside. */
    expect(describeNational({ data: undefined } as unknown as Overview).sourceLine).toBeNull();
  });
});

/* ---- the nearest station in the reading panel ------------------------------------------------------------
   docs/127 recorded this as a gap it could not close: the panel drew the same station reading in `g-side-temp`
   and `g-side-source`, a vocabulary the audit's three shapes do not check, so X1 would have failed on it the
   moment anything looked. The fix was to make the block the product's own claim region, which is also the shape
   the welcome, the bar and the rail use; this is what looks. */

describe('the nearest station in the reading panel', () => {
  it('draws the reading and its source line as one checked claim region', async () => {
    holdAPlace();
    serveTheStation();
    const { container } = mount(<StationBlock />);
    await screen.findByText(/AHMEDABAD/);

    /* The number and the line that owns it are one region, so the audit's claim shape resolves - before this
       the temperature sat in a `.g-side-temp` that no shape checked and no exclusion named. */
    const source = container.querySelector('.g-side-source')!;
    const claim = source.closest('.g-claim');
    expect(claim).not.toBeNull();
    expect(claim!.querySelector('.g-side-temp')).toHaveTextContent('29');
    expect(clean(container)).toEqual([]);
  });

  it('states a source that printed no unit rather than supplying one, inside the same region', async () => {
    holdAPlace();
    server.use(http.get('/api/now', () => HttpResponse.json(station([{ field: 'temp', value: 29, unit: null }]))));
    const { container } = mount(<StationBlock />);
    await screen.findByText(/AHMEDABAD/);

    expect(container.querySelector('.g-claim-source')).toHaveTextContent('no unit in the source');
    expect(clean(container)).toEqual([]);
  });
});

