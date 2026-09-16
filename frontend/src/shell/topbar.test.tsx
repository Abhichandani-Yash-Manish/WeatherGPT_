import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Topbar } from './Topbar';
import { server } from '../test/msw';

const LANGUAGES = {
  schema_version: 'language-support-view-v1',
  service_configured: true,
  languages: [
    { code: 'hi', english_name: 'Hindi', native_name: 'हिन्दी', measured: { write: 'verified', speak: 'verified' } },
    { code: 'ta', english_name: 'Tamil', native_name: 'தமிழ்', measured: { write: 'failed', speak: 'unmeasured' } },
    { code: 'en', english_name: 'English', native_name: 'English', measured: { write: 'verified', speak: 'verified' } },
  ],
};

function renderTopbar(overrides: Partial<React.ComponentProps<typeof Topbar>> = {}) {
  const props = {
    language: '',
    onLanguage: vi.fn(),
    persona: '',
    onPersona: vi.fn(),
    theme: 'system' as const,
    onTheme: vi.fn(),
    onNew: vi.fn(),
    onPalette: vi.fn(),
    onOwner: vi.fn(),
    onMenu: vi.fn(),
    railOpen: false,
    onPlans: vi.fn(),
    ...overrides,
  };
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <Topbar {...props} />
    </QueryClientProvider>,
  );
  return props;
}

describe('the topbar', () => {
  it('states the store state it read, and never a blank chip', async () => {
    server.use(http.get('/api/health', () => HttpResponse.json({ available: true, total_jobs: 164, streams: 60, products: [] })));
    renderTopbar();
    expect(await screen.findByText('Store healthy')).toBeInTheDocument();
  });

  it('shows a store with no jobs as its own state, not as healthy', async () => {
    server.use(http.get('/api/health', () => HttpResponse.json({ available: false, note: 'no jobs yet', products: [] })));
    renderTopbar();
    expect(await screen.findByText('No stored jobs yet')).toBeInTheDocument();
  });

  it('shows an unreachable store as unreachable', async () => {
    server.use(http.get('/api/health', () => HttpResponse.json({ error: 'the local evidence store is unavailable' }, { status: 503 })));
    renderTopbar();
    expect(await screen.findByText('Store unreachable')).toBeInTheDocument();
  });

  it('offers every known language, marked where this project has not measured its writing', async () => {
    server.use(http.get('/api/languages', () => HttpResponse.json(LANGUAGES)));
    renderTopbar();
    await waitFor(() => expect(screen.getByRole('option', { name: /English/ })).toBeInTheDocument());
    expect(screen.getByRole('option', { name: /Tamil — writing not measured/ })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /Hindi — writing not measured/ })).toBeNull();
  });

  it('reports the chosen answer language to the shell', async () => {
    server.use(http.get('/api/languages', () => HttpResponse.json(LANGUAGES)));
    const props = renderTopbar();
    await waitFor(() => expect(screen.getByRole('option', { name: /Hindi/ })).toBeInTheDocument());
    await userEvent.selectOptions(screen.getByLabelText('Answer in'), 'hi');
    expect(props.onLanguage).toHaveBeenCalledWith('hi');
  });

  it('offers the reading positions the engine published, and states that they change no value', async () => {
    server.use(
      http.get('/api/personas', () =>
        HttpResponse.json({ data: { personas: [{ id: 'farmer', label: 'Farmer', who: 'a field plan' }] } })),
    );
    const props = renderTopbar();
    await waitFor(() => expect(screen.getByRole('option', { name: 'Farmer' })).toBeInTheDocument());
    await userEvent.selectOptions(screen.getByLabelText('Reading as'), 'farmer');
    expect(props.onPersona).toHaveBeenCalledWith('farmer');
    expect(screen.getByLabelText('Reading as')).toHaveAttribute('title', expect.stringContaining('changes no value'));
  });


  it('offers the navigation drawer control, and reports its state', async () => {
    const props = renderTopbar({ railOpen: true });
    const toggle = screen.getByTestId('rail-toggle');
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(toggle).toHaveAttribute('aria-controls', 'workspace-rail');
    await userEvent.click(toggle);
    expect(props.onMenu).toHaveBeenCalled();
  });


  it('offers the plans and watches inbox', async () => {
    const props = renderTopbar();
    await userEvent.click(screen.getByTestId('plans-open'));
    expect(props.onPlans).toHaveBeenCalled();
  });

  it('names the theme it would move to, and the two actions beside it', async () => {
    const props = renderTopbar({ theme: 'system' });
    expect(screen.getByTestId('theme-toggle')).toHaveTextContent('System theme');
    await userEvent.click(screen.getByTestId('new-conversation'));
    expect(props.onNew).toHaveBeenCalled();
    await userEvent.click(screen.getByTestId('palette-open'));
    expect(props.onPalette).toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Lock' }));
    expect(props.onOwner).toHaveBeenCalled();
  });
});
