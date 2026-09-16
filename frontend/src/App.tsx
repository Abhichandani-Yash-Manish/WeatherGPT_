import { useState } from 'react';
import { MotionConfig } from 'motion/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Rail } from './shell/Rail';
import { SkyBackground } from './shell/SkyBackground';
import { SurfaceHost } from './shell/SurfaceHost';
import { Topbar } from './shell/Topbar';
import { useHashRoute } from './shell/useHashRoute';

/* One client for the whole app: the engine answers from a local store and every read is a snapshot with its
   own retrieval time, so a query is cached only briefly and refetched on focus rather than trusted. */
const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: true } },
});

function Shell() {
  const { view, open } = useHashRoute();
  const [question, setQuestion] = useState('');
  const [language, setLanguage] = useState('');
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('system');

  const cycleTheme = () => {
    const next = theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system';
    setTheme(next);
    if (next === 'system') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', next);
  };

  return (
    <div className="flex h-full min-h-screen" data-shell="react" data-surface={view.id}>
      <SkyBackground />
      <Rail active={view.id} onOpen={open} />
      <main className="flex min-w-0 flex-1 flex-col">
        <Topbar language={language} onLanguage={setLanguage} onNew={() => setQuestion('')} theme={theme} onTheme={cycleTheme} />
        {view.id === 'assistant' ? (
          <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-4 px-6 py-10" data-surface="assistant">
            <form className="flex items-end gap-2 rounded-card border border-line bg-paper p-3" onSubmit={event => event.preventDefault()}>
              <label className="sr-only" htmlFor="question">
                Your question
              </label>
              <textarea
                id="question"
                value={question}
                onChange={event => setQuestion(event.target.value)}
                rows={2}
                className="min-h-11 flex-1 resize-none bg-transparent text-base outline-none"
                placeholder="What is it like right now in Ahmedabad?"
              />
              <button type="submit" className="rounded-card bg-data px-4 py-2 font-semibold text-paper">
                Ask
              </button>
            </form>
            <p className="text-xs text-mute" data-testid="r1-note">
              R1 shell: rail, routes, registry, topbar and the weather ground are in place. The transcript, the
              reading line and the evidence card arrive in R2; answers are not wired yet.
            </p>
          </section>
        ) : (
          <SurfaceHost view={view} />
        )}
      </main>
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user">
        <Shell />
      </MotionConfig>
    </QueryClientProvider>
  );
}
