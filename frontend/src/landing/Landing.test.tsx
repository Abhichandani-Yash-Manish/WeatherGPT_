import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { VIEWS } from '../shell/views';
import { Landing } from './Landing';

/* The reads go through src/api/client.ts unchanged: src/test/setup.ts supplies Node's AbortController,
   which is the class this environment's fetch accepts, and msw answers the same envelopes the engine
   serves. Nothing here fakes the client or the payload route. */

/* Recorded shapes: the two envelopes the strip reads, trimmed to the fields the page uses. */
const CAPABILITIES = {
  schema_version: 'settings.capabilities-v1',
  view: 'settings.capabilities',
  status: 'ok',
  data: {
    capabilities: [
      { tool: 'forecast.point', kind: 'forecast' },
      { tool: 'warnings.district', kind: 'warning' },
      { tool: 'corpus.documents', kind: 'document' },
    ],
    sources: [],
    registered_sources: 70,
    connected_sources: 29,
  },
  coverage: { capabilities: 3, sources_in_use: 29 },
};

const CORPUS = {
  schema_version: 'corpus.documents-v1',
  status: 'ok',
  data: {
    documents: [{ sha256: 'a'.repeat(64) }],
    families: [
      { family: 'district-warning', documents: 4 },
      { family: 'national-bulletin', documents: 2 },
    ],
    counts: { documents: 90, documents_listed: 1, documents_matching: 90, passages: 1200, regions: 12 },
  },
};

function renderLanding(onEnter: () => void = () => {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <Landing onEnter={onEnter} />
    </QueryClientProvider>,
  );
}

/* The page reads three endpoints on mount; awaiting the settled strip keeps every assertion inside act(). */
async function settleReads() {
  await waitFor(() => expect(screen.getByTestId('live-health').textContent).not.toMatch(/Reading the local workspace/));
  await waitFor(() => expect(screen.getByTestId('live-families').textContent).not.toMatch(/Reading the workspace/));
}

describe('the landing page', () => {
  beforeEach(() => {
    server.use(
      http.get('/api/settings/capabilities', () => HttpResponse.json(CAPABILITIES)),
      http.get('/api/corpus', () => HttpResponse.json(CORPUS)),
    );
  });

  it('renders one h1 and the page landmarks', async () => {
    renderLanding();
    await settleReads();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('WeatherGPT');
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });

  it('shows the live strip counts with the time each read happened', async () => {
    renderLanding();
    await settleReads();
    const capabilities = screen.getByTestId('live-capabilities');
    expect(within(capabilities).getByText('3')).toBeInTheDocument();
    expect(within(capabilities).getByText(/read \d{2} [A-Z][a-z]{2} \d{4}, \d{2}:\d{2} IST/)).toBeInTheDocument();
    expect(within(screen.getByTestId('live-connected-sources')).getByText('29')).toBeInTheDocument();
    expect(within(screen.getByTestId('live-documents')).getByText('90')).toBeInTheDocument();
    expect(within(screen.getByTestId('live-families')).getByText('2')).toBeInTheDocument();
    expect(screen.getByTestId('live-health')).toHaveTextContent(/answered on this machine/i);
  });

  it('shows a failure sentence instead of a number when the capabilities read fails', async () => {
    server.use(
      http.get('/api/settings/capabilities', () =>
        HttpResponse.json({ error: 'The capabilities view could not be read.' }, { status: 500 })),
    );
    renderLanding();
    const capabilities = await screen.findByTestId('live-capabilities');
    expect(await within(capabilities).findByText(/the read failed/i)).toBeInTheDocument();
    expect(await within(capabilities).findByText(/could not be read/i)).toBeInTheDocument();
    expect(capabilities.textContent).not.toMatch(/\d/);
  });

  it('renders every registered surface with the questions it answers', async () => {
    renderLanding();
    await settleReads();
    for (const view of VIEWS) {
      const card = document.querySelector('[data-view="' + view.id + '"]');
      expect(card).not.toBeNull();
      expect(card?.textContent).toContain(view.label);
      expect(card?.textContent).toContain('#/' + view.id);
      for (const intent of view.intents) expect(card?.textContent).toContain(intent);
    }
  });

  it('states the limits in the repository own wording', async () => {
    renderLanding();
    await settleReads();
    expect(screen.getByText(/CAP lifecycle diagnostics never authorise dissemination/)).toBeInTheDocument();
    expect(screen.getByText(/No confidence, risk, suitability or probability value is computed for display/)).toBeInTheDocument();
    expect(screen.getByText(/No observed water level, gauge reading, danger level, flood extent/)).toBeInTheDocument();
    expect(screen.getByText(/Plans and watches are evaluated while the workspace runs/)).toBeInTheDocument();
    expect(screen.getByText(/Coverage is per direction and measured/)).toBeInTheDocument();
    expect(
      screen.getByText(/Nothing here claims nationwide coverage, validated forecast skill, operational clearance or full problem-statement compliance/),
    ).toBeInTheDocument();
  });

  it('lists the recorded screenshots with their size and what each one shows', async () => {
    renderLanding();
    await settleReads();
    const pictures = screen.getAllByRole('img');
    expect(pictures).toHaveLength(8);
    for (const picture of pictures) {
      expect(picture).toHaveAttribute('width', '1440');
      expect(picture).toHaveAttribute('height', '900');
      expect(picture.getAttribute('alt')).toMatch(/\w{4,}/);
      expect(picture.getAttribute('src')).toMatch(/^\/shots\/\d{2}-[a-z-]+\.png$/);
    }
  });

  it('opens the workspace from the one primary action, beside the assistant link', async () => {
    const onEnter = vi.fn();
    renderLanding(onEnter);
    await settleReads();
    const link = screen.getByRole('link', { name: /assistant/i });
    expect(link).toHaveAttribute('href', '#/assistant');
    expect(screen.getAllByRole('button', { name: /^open the workspace$/i })).toHaveLength(1);
    await userEvent.setup().click(screen.getByRole('button', { name: /^open the workspace$/i }));
    expect(onEnter).toHaveBeenCalledTimes(1);
  });
});
