/* The accessibility check: axe-core run over the real components in jsdom, surface by surface.

   jsdom has no layout engine, so the colour-contrast rule cannot be evaluated here and is disabled rather than
   reported as passing; that rule belongs to a browser run (R5 against the served build). Everything else runs:
   names, roles, labels, heading order, duplicate ids, landmark structure, link text and table structure.

   With AXE_REPORT set to a path, the run also writes the report it produced, so the batch can record what was
   actually evaluated next to the number of violations it found. */

import axe from 'axe-core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { writeFileSync } from 'node:fs';
/* The Ask surface is the shell itself now: the legacy chat page was deleted with the rest of the legacy
   tree, and this scan is worth more against the surface that actually ships. */
import { Workspace as AskSurface } from '../gpt/Workspace';
import { Workspace } from '../gpt/Workspace';
import { OwnerGate } from '../landing/OwnerGate';
import { SurfaceHost } from '../shell/SurfaceHost';
import { viewById } from '../shell/views';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';

/* The contrast rule needs a layout engine and a colour-resolving cascade, neither of which jsdom has. It is
   disabled here and named in the report so the absence is visible rather than implied. */
const OPTIONS: axe.RunOptions = { rules: { 'color-contrast': { enabled: false } } };

const REPORTS: { surface: string; violations: number; passes: number; incomplete: number; disabled: string[] }[] = [];

function mount(node: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

async function scan(surface: string, node: React.ReactElement) {
  const { container, unmount } = mount(node);
  const results = await axe.run(container, OPTIONS);
  REPORTS.push({
    surface,
    violations: results.violations.length,
    passes: results.passes.length,
    incomplete: results.incomplete.length,
    disabled: ['color-contrast (needs a layout engine; run in a browser instead)'],
  });
  const summary = results.violations.map(violation => violation.id + ' (' + violation.nodes.length + ')').join(', ');
  expect(summary, surface + ' accessibility violations').toBe('');
  unmount();
}

const WARNINGS = {
  schema_version: 'product-view-v1',
  view: 'warnings.national',
  status: 'ok',
  data: {
    districts: [
      { key: 'patna', district: 'PATNA', state: 'BIHAR', bulletin_date: '2026-09-15',
        days: [{ date: '2026-09-15', day_label: 'Day 1', colour: 'yellow', hazards: ['Thunderstorm'], wording: 'Thunderstorm/lightning/squall' }] },
    ],
    tally: { yellow: 1 },
    skipped: [],
  },
  sources: [{ source_id: 'S15', product: 'IMD district warning', retrieved_at_utc: '2026-09-15T06:00:00+00:00' }],
  coverage: { districts_listed: 1 },
  limitations: ['A quiet district-day is not an all-clear.'],
  not_established: ['Radar imagery is not connected here.'],
};

describe('accessibility of the rendered surfaces', () => {
  afterAll(() => {
    const target = process.env.AXE_REPORT;
    if (!target) return;
    writeFileSync(
      target,
      JSON.stringify(
        {
          checked_at_utc: new Date().toISOString(),
          tool: 'axe-core',
          environment: 'jsdom (vitest) — no layout engine, so colour contrast is not measured here',
          options: OPTIONS,
          surfaces: REPORTS,
          totals: {
            surfaces: REPORTS.length,
            violations: REPORTS.reduce((sum, entry) => sum + entry.violations, 0),
            passes: REPORTS.reduce((sum, entry) => sum + entry.passes, 0),
          },
        },
        null,
        2,
      ),
    );
  });

  /* The front door is the conversation now, so this scans the face the reader actually meets at an empty
     address — the same page the browser gate checks over the served build. */
  it('has no violations on the front door', async () => {
    await scan('workspace', <Workspace onOpen={() => {}} language="" onLanguage={() => {}} persona="" onPersona={() => {}} />);
  });

  it('has no violations on the conversation at rest', async () => {
    await scan('ask (welcome)', <AskSurface onOpen={() => {}} language="" onLanguage={() => {}} persona="" onPersona={() => {}} />);
  });

  it('has no violations on a ported module surface', async () => {
    server.use(http.get('/api/warnings/national', () => HttpResponse.json(WARNINGS)));
    await scan('warnings', <SurfaceHost view={viewById('warnings')!} onAsk={() => {}} />);
  });

  it('has no violations on an unported surface placeholder', async () => {
    await scan('marine (placeholder)', <SurfaceHost view={viewById('marine')!} onAsk={() => {}} />);
  });

  it('has no violations on the owner gate', async () => {
    await scan('owner gate', <OwnerGate onOpen={() => {}} onSkip={() => {}} onEnter={() => {}} />);
  });
});
