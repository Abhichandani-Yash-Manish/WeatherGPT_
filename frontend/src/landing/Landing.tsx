import { useQuery } from '@tanstack/react-query';
import {
  ArrowRight, Compass, Database, Gauge, Images, Layers, ListChecks, ShieldCheck, Sparkles,
} from 'lucide-react';
import { Button } from '../ui/kit';
import { getJson, withQuery } from '../api/client';
import type { CapabilitiesData, Envelope, Health } from '../api/types';
import { istStamp } from '../lib/time';
import { VIEWS } from '../shell/views';
import './landing.css';

/* The front page.
   ============================================================================
   It states only what this repository states, and it names the same limits the README names. Two rules it
   follows literally:
   1. Every number on it comes from a live read of this machine, with the read time beside it. A failed read
      says the read failed; a placeholder number is never rendered.
   2. The module map is the shared registry (src/shell/views.ts), not a hand-written copy, so the front page
      cannot claim a surface the workspace does not serve.
   Motion is the existing .rise utility from styles/app.css, which collapses under prefers-reduced-motion. */

type CorpusData = {
  counts?: { documents?: number; passages?: number; regions?: number; pruned?: number };
  families?: { family?: string; label?: string; documents?: number; passages?: number }[];
};

type Reading = {
  key: string;
  label: string;
  unit: string;
  value: number | null;
  readAt: number;
  failure: string | null;
};

const GROUPS: { id: 'start' | 'weather' | 'more'; title: string; note: string }[] = [
  { id: 'start', title: 'Start here', note: 'The conversation, the working place and the day.' },
  { id: 'weather', title: 'Weather & advice', note: 'The guided weather surfaces, in the rail order.' },
  { id: 'more', title: 'Models, history & specialists', note: 'What was read, what changed and what is specialised.' },
];

/* The receipt structure, with words where a value would go. It is the one thing a reader takes away from a
   WeatherGPT answer, so the front page shows its shape rather than a sample value that was never read. */
const SHAPE: { key: string; value: string }[] = [
  { key: 'Measure', value: 'the parameter that was asked for' },
  { key: 'Value and unit', value: 'exactly as the source printed it' },
  { key: 'Place and entity', value: 'the resolved point, and its distance' },
  { key: 'Window', value: 'the validity the source states' },
  { key: 'Source, retrieved', value: 'which source, and when it was read' },
  { key: 'Not established', value: 'what this answer could not show' },
];

/* The four steps the retrieval path actually takes, in the order it takes them. */
const METHOD: { name: string; text: string }[] = [
  {
    name: 'Capture',
    text: 'The place, the window and the measure are read out of the question as written. A slot that is not there is asked for, never guessed.',
  },
  {
    name: 'Verify',
    text: 'The task is handed to a governed tool that owns that measure. When no connected tool owns what was asked for, the answer says so instead of describing something else.',
  },
  {
    name: 'Catalogue',
    text: 'Every value that comes back keeps its source, retrieval time, unit and page or locator attached. A value no source printed stays unknown.',
  },
  {
    name: 'Answer',
    text: 'The written sentence is built around those tool-owned facts, with the receipt beneath it: what was read, when, and what is missing.',
  },
];

/* Quoted from README.md, "What it deliberately does not do". The page and the repository must say the same
   thing, so the wording is copied rather than paraphrased. */
const REFUSALS: { lead: string; text: string }[] = [
  {
    lead: 'No invented warnings or all-clears.',
    text: 'CAP lifecycle diagnostics never authorise dissemination, and a resolved document hash or a quiet day is never an alert.',
  },
  {
    lead: 'No invented numbers.',
    text: 'No confidence, risk, suitability or probability value is computed for display; no arithmetic is applied to source values; no skill claim is made from prototype checks.',
  },
  {
    lead: 'No observation where none exists.',
    text: 'No observed water level, gauge reading, danger level, flood extent, tide, current or sea-surface temperature, and no station observation for an arbitrary place.',
  },
  {
    lead: 'No field, marine, medical or travel clearance.',
    text: 'No crop diagnosis, no pesticide dosage, no flood-impact prediction, no road or route advice.',
  },
  {
    lead: 'No delivery service.',
    text: 'Plans and watches are evaluated while the workspace runs; notifications are local or consented browser push. SMS, IVR and WhatsApp are not connected channels.',
  },
  {
    lead: 'No universal language claim.',
    text: 'Coverage is per direction and measured; the four refused languages are named with their reasons.',
  },
];

/* Captions name what each capture shows. The files are this build's own screenshots, taken 17 September 2026
   at 1440x900 in headless Chrome against a throwaway copy of the store, so no reader's conversation appears
   in them; the intrinsic size below is the size they were taken at. */
const PICTURES: { file: string; alt: string }[] = [
  {
    file: '03-ask-working.png',
    alt: 'A turn while it works: the stages the server reports one by one, the first reading marked as a reading and not evidence, and the stop control.',
  },
  {
    file: '02-ask-welcome.png',
    alt: 'Ask as the front door: the openings the workspace offers, the reading register and the stored conversations beside the conversation.',
  },
  {
    file: '04-ask-answer.png',
    alt: 'An evidence answer: the question kept above it, the tool-owned fact with its unit and distance, the source line and the written reading beneath.',
  },
  {
    file: '05-today.png',
    alt: 'Today: the national district picture from the published product, the colour tally exactly as returned, and the coverage limits stated under it.',
  },
  {
    file: '06-warnings.png',
    alt: 'Warnings: one row per district-day with the colour the product printed, the hazard wording as published, and the filter that says it only filters the rows already read.',
  },
  {
    file: '07-forecast.png',
    alt: 'Forecast: the point that was resolved, each parameter as its own table, and the statement that a missing point is a gap and never a zero.',
  },
  {
    file: '09-documents.png',
    alt: 'Published documents: the family, scope, printed issue date and currency of each indexed edition, with the counts for the whole index.',
  },
  {
    file: '10-settings.png',
    alt: 'Sources and settings: every capability the suite can answer, which source each uses, and what the local store, the watch loop and the providers are doing.',
  },
];

function readStamp(at: number): string {
  return at ? 'read ' + istStamp(at) : 'read time not recorded';
}

function failureSentence(error: unknown): string {
  return error instanceof Error && error.message ? error.message : 'the workspace gave no reason';
}

const STEP_ICONS = [Compass, Layers, Database, Gauge];

/* A tile says which read it is with an icon, from the same map the surfaces use. */
function LiveIcon({ name }: { name: string }) {
  const Icon = LIVE_ICONS[name] ?? Gauge;
  return <Icon size={14} aria-hidden="true" />;
}

const LIVE_ICONS: Record<string, typeof Gauge> = {
  health: Gauge,
  capabilities: ListChecks,
  corpus: Database,
  warnings: ShieldCheck,
};

export function Landing({ onEnter }: { onEnter: () => void }) {
  const health = useQuery({ queryKey: ['landing', 'health'], queryFn: () => getJson<Health>('/api/health'), retry: false, staleTime: 30_000 });
  const capabilities = useQuery({
    queryKey: ['landing', 'capabilities'],
    queryFn: () => getJson<Envelope<CapabilitiesData>>('/api/settings/capabilities'),
    retry: false,
    staleTime: 30_000,
  });
  /* One document is listed; the counts in this envelope always describe the whole index rather than the
     returned page, so the strip reads the whole index while asking for one row. */
  const corpus = useQuery({
    queryKey: ['landing', 'corpus'],
    queryFn: () => getJson<Envelope<CorpusData>>(withQuery('/api/corpus', { limit: 1 })),
    retry: false,
    staleTime: 30_000,
  });

  const capabilitiesFailure = capabilities.isError ? failureSentence(capabilities.error) : null;
  const corpusFailure = corpus.isError ? failureSentence(corpus.error) : null;

  const readings: Reading[] = [
    {
      key: 'capabilities',
      label: 'Tool-owned capabilities',
      unit: 'in the catalogue',
      value: capabilities.data?.data.capabilities?.length ?? null,
      readAt: capabilities.dataUpdatedAt,
      failure: capabilitiesFailure,
    },
    {
      key: 'connected-sources',
      label: 'Connected sources',
      unit: 'with a registered connector',
      value: capabilities.data?.data.connected_sources ?? null,
      readAt: capabilities.dataUpdatedAt,
      failure: capabilitiesFailure,
    },
    {
      key: 'documents',
      label: 'Documents in the corpus index',
      unit: 'indexed editions',
      value: corpus.data?.data.counts?.documents ?? null,
      readAt: corpus.dataUpdatedAt,
      failure: corpusFailure,
    },
    {
      key: 'families',
      label: 'Document families',
      unit: 'families in the index',
      value: corpus.data?.data.families?.length ?? null,
      readAt: corpus.dataUpdatedAt,
      failure: corpusFailure,
    },
  ];

  return (
    <div className="landing rise" data-surface="landing">
      <header className="landing-header">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-3 px-6 py-3">
          <p className="eyebrow">WeatherGPT · SIH26068</p>
          <p className="text-xs text-mute">A local workspace on this machine</p>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-6">
        {/* The hero states the product in one breath and shows the shape of an answer beside it. The panel on
            the right carries no number: it is the structure of a receipt, labelled as such, because a front
            page that showed an unread value would make the one claim this product refuses to make. */}
        <section aria-labelledby="landing-hero" className="glass-strong landing-hero relative mt-6 overflow-hidden px-6 py-10 sm:px-10">
          <span className="landing-hero-band" aria-hidden="true" />
          <div className="relative grid gap-8 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] lg:items-start">
            <div>
              <p className="pill pill-accent mb-1"><Sparkles size={13} aria-hidden="true" />WeatherGPT · SIH26068 · a local workspace</p>
              <h1 id="landing-hero" className="display landing-title mt-3">WeatherGPT</h1>
              <p className="reading mt-5">
                A local, evidence-first conversational weather workspace for India: ask about a place and a time in
                your own words, and the answer keeps the entity, window, unit, source and retrieval time attached to
                every value.
              </p>
              <p className="landing-refusal mt-4">
                It refuses to invent a warning, an observation, a water level, a forecast or a confidence score, and
                it states missing evidence as missing.
              </p>
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <Button variant="primary" size="lg" icon={<ArrowRight size={16} />} data-testid="open-workspace" onClick={onEnter}>
                  Open the workspace
                </Button>
                <a className="btn" href="#/assistant">
                  <Sparkles size={15} aria-hidden="true" />
                  Open the assistant directly
                </a>
              </div>
              <ul className="mt-6 flex flex-wrap gap-2" aria-label="What the workspace guarantees about its answers">
                <li className="pill"><ShieldCheck size={13} aria-hidden="true" />Loopback only, per-process token</li>
                <li className="pill"><Database size={13} aria-hidden="true" />Every value keeps its source and retrieval time</li>
                <li className="pill pill-quiet">No confidence score is produced anywhere</li>
              </ul>
            </div>

            <aside className="glass-soft landing-card p-4" aria-labelledby="landing-shape">
              <p className="eyebrow" id="landing-shape">The shape of an answer</p>
              <p className="mt-2 text-xs text-mute">
                Not a reading: the receipt structure every answer fills in. This page prints no measurement it did
                not read from this machine.
              </p>
              <dl className="landing-receipt mt-4">
                {SHAPE.map(row => (
                  <div key={row.key} className="receipt-row">
                    <dt className="receipt-key">{row.key}</dt>
                    <dd className="receipt-val">{row.value}</dd>
                  </div>
                ))}
              </dl>
              <p className="receipt-chain mt-3 text-xs text-ink-soft">
                <span className="evidence">S…</span>
                <span aria-hidden="true">→</span>
                <span>retrieved at a stated time</span>
                <span aria-hidden="true">→</span>
                <span>typed contract, not a written guess</span>
              </p>
            </aside>
          </div>
        </section>

        <section aria-labelledby="landing-method" className="landing-rule pt-8">
          <div className="flex items-center gap-3"><span className="icon-tile" aria-hidden="true"><ListChecks size={18} /></span><h2 id="landing-method" className="display m-0">Ask, and the evidence answers</h2></div>
          <p className="landing-note landing-prose mt-2 text-sm">
            The four steps between a question and an answer, in the order the retrieval path takes them.
          </p>
          <ol className="landing-prose mt-5 grid list-none gap-3 p-0 sm:grid-cols-2">
            {METHOD.map((step, index) => (
              <li key={step.name} className="glass-soft flex items-start gap-3 p-4">
                <span className="icon-tile shrink-0" aria-hidden="true">
                  {STEP_ICONS[index] ? (() => { const Step = STEP_ICONS[index]; return <Step size={16} />; })() : null}
                </span>
                <span>
                  <span className="block font-semibold">{step.name}</span>
                  <span className="mt-1 block text-sm text-ink-soft">{step.text}</span>
                </span>
              </li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="landing-live" className="landing-rule pt-8">
          <div className="flex items-center gap-3"><span className="icon-tile" aria-hidden="true"><Gauge size={18} /></span><h2 id="landing-live" className="display m-0">What this machine is holding right now</h2></div>
          <p className="landing-note landing-prose mt-2 text-sm">
            Read live from the local workspace, with the read time beside every number. A read that fails says
            it failed instead of showing a number.
          </p>
          <p role="status" className="reading mt-3 text-sm" data-testid="live-health">
            {health.isPending
              ? 'Reading the local workspace…'
              : health.isError
                ? 'The health read failed: ' + failureSentence(health.error)
                : health.data.available
                  ? 'The workspace answered on this machine.'
                  : 'The workspace answered that it is not available.'}
            {health.dataUpdatedAt ? <span className="landing-read"> · {readStamp(health.dataUpdatedAt)}</span> : null}
          </p>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" data-testid="live-strip">
            {readings.map(reading => (
              <li
                key={reading.key}
                className={'glass landing-card p-4' + (reading.failure ? ' border-dashed' : '')}
                data-testid={'live-' + reading.key}
              >
                <p className="eyebrow flex items-center gap-2">
                  <LiveIcon name={reading.key} />
                  {reading.label}
                </p>
                {reading.failure ? (
                  <>
                    <p className="mt-2 text-sm font-semibold text-ink-soft">The read failed.</p>
                    <p className="mt-1 text-xs text-mute">{reading.failure}</p>
                    <p className="landing-read mt-2">No read time: the read did not complete.</p>
                  </>
                ) : reading.value === null ? (
                  <>
                    <p className="mt-2 text-sm text-mute">Reading the workspace…</p>
                    <p className="landing-read mt-2">{readStamp(reading.readAt)}</p>
                  </>
                ) : (
                  <>
                    <p className="mt-2 flex items-baseline gap-2">
                      <span className="landing-count leading-none">{reading.value}</span>
                      <span className="text-xs text-mute">{reading.unit}</span>
                    </p>
                    <p className="landing-read mt-2">{readStamp(reading.readAt)}</p>
                  </>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="landing-modules" className="landing-rule pt-8">
          <div className="flex items-center gap-3"><span className="icon-tile" aria-hidden="true"><Layers size={18} /></span><h2 id="landing-modules" className="display m-0">The surfaces, and the questions they answer</h2></div>
          <p className="landing-note landing-prose mt-2 text-sm">
            Every surface the workspace registry declares, grouped the way the rail groups them. Each one names
            the questions the conversation can reach it with, and the deep link that opens it.
          </p>
          {GROUPS.map(group => {
            const views = VIEWS.filter(view => view.group === group.id);
            return (
              <div key={group.id} className="mt-6">
                <h3 className="eyebrow">{group.title}</h3>
                <p className="landing-note mt-1 text-xs">{group.note}</p>
                <ul className="mt-3 grid gap-3 md:grid-cols-2">
                  {views.map(view => (
                    <li key={view.id} className="landing-card" data-view={view.id}>
                      <p className="flex flex-wrap items-baseline justify-between gap-2">
                        <span className="font-semibold">{view.label}</span>
                        <code className="evidence text-xs text-mute">#/{view.id}</code>
                      </p>
                      <ul className="mt-2 space-y-1 text-sm text-ink-soft">
                        {view.intents.map(intent => (
                          <li key={intent}>“{intent}”</li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </section>

        <section aria-labelledby="landing-refusals" className="landing-rule pt-8">
          <div className="flex items-center gap-3"><span className="icon-tile" aria-hidden="true"><ShieldCheck size={18} /></span><h2 id="landing-refusals" className="display m-0">What it deliberately does not do</h2></div>
          <p className="reading mt-3">
            <strong>Operational acceptance is not achieved.</strong> This is a working prototype whose limits are
            part of the interface: it says what it did not read, which state is unknown, and when a value is model
            output, published wording, an observation or an official warning.
          </p>
          <p className="landing-note landing-prose mt-3 text-sm">
            The interface states these limits instead of filling them:
          </p>
          <ul className="landing-prose mt-4 space-y-3">
            {REFUSALS.map(refusal => (
              <li key={refusal.lead} className="glass-soft flex items-start gap-2 p-3 text-sm">
                <ShieldCheck size={15} className="mt-0.5 shrink-0 text-mute" aria-hidden="true" />
                <span><strong>{refusal.lead}</strong> {refusal.text}</span>
              </li>
            ))}
          </ul>
          <p className="landing-note landing-prose mt-4 text-sm">
            Missing evidence is stated as missing. Nothing here claims nationwide coverage, validated forecast
            skill, operational clearance or full problem-statement compliance.
          </p>
        </section>

        <section aria-labelledby="landing-pictures" className="landing-rule pt-8 pb-10">
          <div className="flex items-center gap-3"><span className="icon-tile" aria-hidden="true"><Images size={18} /></span><h2 id="landing-pictures" className="display m-0">The workspace, as recorded</h2></div>
          <p className="landing-note landing-prose mt-2 text-sm">
            Eight pictures of this build, captured 17 September 2026 at 1440×900 in headless Chrome against a
            throwaway copy of the store, so no reader conversation appears in them. They show the same surfaces
            this page lists, at the sizes they were taken.
          </p>
          <ul className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {PICTURES.map(picture => (
              <li key={picture.file} className="landing-figure glass overflow-hidden p-1">
                <img
                  className="h-auto w-full rounded-card"
                  src={'/shots/' + picture.file}
                  alt={picture.alt}
                  width={1440}
                  height={900}
                  loading="lazy"
                />
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="landing-rule">
        <div className="mx-auto w-full max-w-5xl px-6 py-6 text-xs text-mute">
          <p>
            WeatherGPT runs on this machine: the workspace server answers on loopback only and checks a
            per-process session token on every request. A provider key stays in local backend configuration and
            never reaches browser code or a conversation.
          </p>
          <p className="mt-2">
            Hosting is on hold and the desktop web is the current surface; mobile and voice remain open
            requirements. GeoNames place data is used under CC BY 4.0.
          </p>
        </div>
      </footer>
    </div>
  );
}