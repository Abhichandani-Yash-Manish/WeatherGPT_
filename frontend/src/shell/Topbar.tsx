import { useQuery } from '@tanstack/react-query';

/* The topbar states facts the engine already publishes: whether the local service and store answer, and which
   languages may be offered. A failed read is shown as a failed read, never as a blank chip. */
type Health = { available: boolean; note?: string; products?: { product: string; jobs: number }[] };
type Languages = { service_configured: boolean; languages: { code: string; english_name: string; native_name: string; measured?: Record<string, boolean> }[] };

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { 'X-WeatherGPT-Token': document.querySelector('meta[name="workspace-token"]')?.getAttribute('content') || '' } });
  if (!response.ok) throw new Error(path + ' answered HTTP ' + response.status);
  return (await response.json()) as T;
}

export function Topbar({ language, onLanguage, onNew, theme, onTheme }: {
  language: string;
  onLanguage: (code: string) => void;
  onNew: () => void;
  theme: 'light' | 'dark' | 'system';
  onTheme: () => void;
}) {
  const health = useQuery({ queryKey: ['health'], queryFn: () => getJson<Health>('/api/health'), refetchInterval: 60_000 });
  const languages = useQuery({ queryKey: ['languages'], queryFn: () => getJson<Languages>('/api/languages'), staleTime: 300_000 });

  const service = health.isPending
    ? { label: 'Checking', tone: 'quiet' as const }
    : health.isError
      ? { label: 'Unreachable', tone: 'down' as const }
      : health.data.available
        ? { label: 'Store healthy', tone: 'ok' as const }
        : { label: 'No store yet', tone: 'quiet' as const };

  return (
    <header className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2" data-topbar="react">
      <span className="text-sm font-semibold tracking-wide">WeatherGPT</span>
      <span
        role="status"
        data-testid="service-state"
        className={'rounded-card px-2 py-0.5 text-xs ' + (service.tone === 'down' ? 'bg-warn text-paper' : 'bg-sand text-ink-soft')}
      >
        {service.label}
      </span>

      <label className="ml-auto text-xs text-mute" htmlFor="language">
        Answer in
      </label>
      <select
        id="language"
        value={language}
        onChange={event => onLanguage(event.target.value)}
        className="rounded-card border border-line bg-paper px-2 py-1 text-xs"
      >
        <option value="">Match my question</option>
        {(languages.data?.languages || []).map(entry => (
          <option key={entry.code} value={entry.code}>
            {entry.english_name}{entry.measured?.write === false ? ' (unmeasured)' : ''}
          </option>
        ))}
      </select>

      <button type="button" className="rounded-card border border-line px-2 py-1 text-xs" onClick={onTheme} data-testid="theme-toggle">
        {theme === 'system' ? 'System theme' : theme === 'dark' ? 'Dark' : 'Light'}
      </button>
      <button type="button" className="rounded-card border border-line px-2 py-1 text-xs" onClick={onNew} data-testid="new-conversation">
        New
      </button>
    </header>
  );
}
