import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Topbar } from './Topbar';

function renderTopbar(overrides: Partial<Parameters<typeof Topbar>[0]> = {}) {
  const props = {
    language: '',
    onLanguage: vi.fn(),
    onNew: vi.fn(),
    theme: 'system' as const,
    onTheme: vi.fn(),
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
    server.use(http.get('/api/health', () => HttpResponse.json({ available: false, note: 'No ingestion store exists yet.' })));
    renderTopbar();
    await waitFor(() => expect(screen.getByTestId('service-state')).toHaveTextContent('No store yet'));
  });

  it('shows a failed read as unreachable rather than healthy', async () => {
    server.use(http.get('/api/health', () => new HttpResponse(null, { status: 503 })));
    renderTopbar();
    await waitFor(() => expect(screen.getByTestId('service-state')).toHaveTextContent('Unreachable'));
  });

  it('offers only the languages the engine publishes, marking unmeasured ones', async () => {
    server.use(
      http.get('/api/languages', () =>
        HttpResponse.json({
          service_configured: true,
          languages: [
            { code: 'hi', english_name: 'Hindi', native_name: 'हिन्दी', measured: { write: true } },
            { code: 'ta', english_name: 'Tamil', native_name: 'தமிழ்', measured: { write: false } },
          ],
        })),
    );
    const props = renderTopbar();
    await waitFor(() => expect(screen.getByRole('option', { name: /Hindi/ })).toBeInTheDocument());
    expect(screen.getByRole('option', { name: /Tamil \(unmeasured\)/ })).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('Answer in'), 'ta');
    expect(props.onLanguage).toHaveBeenCalledWith('ta');
  });
});
