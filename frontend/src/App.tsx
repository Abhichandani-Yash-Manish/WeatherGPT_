/* The shell: one conversation at the centre, every module beside it, and a front door in front of both.

   The landing page is shown for an empty address and opens the workspace; the owner gate is shown only
   when a reader asks for it or when a verifier exists and the interface is locked. Every surface in
   between is reachable by its own deep link, which is what the vanilla workspace already promised. */

import { MotionConfig } from 'motion/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import { AskSurface } from './chat/AskSurface';
import { Landing } from './landing/Landing';
import { OwnerGate } from './landing/OwnerGate';
import { closeGate, hasOwnerVerifier, isGateOpen } from './landing/owner';
import { ErrorBoundary } from './shell/ErrorBoundary';
import { Palette } from './shell/Palette';
import { Rail } from './shell/Rail';
import { SkyBackground } from './shell/SkyBackground';
import { SurfaceHost } from './shell/SurfaceHost';
import { Topbar } from './shell/Topbar';
import { useHashRoute } from './shell/useHashRoute';
import { useSkyPhase, useTheme } from './shell/theme';

/* One client for the whole app: the engine answers from a local store and every read is a snapshot with its
   own retrieval time, so a query is cached only briefly and refetched on focus rather than trusted. */
const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: true } },
});

export type Seed = { question: string; nonce: number } | null;

function Shell() {
  const { view, shell, open, go } = useHashRoute();
  const [theme, cycleTheme] = useTheme();
  const [language, setLanguage] = useState('');
  const [persona, setPersona] = useState('');
  const [palette, setPalette] = useState(false);
  const [seed, setSeed] = useState<Seed>(null);
  useSkyPhase();

  /* The gate exists but does not stand in the way by default: with no verifier set, the workspace is exactly
     as open as it has always been. It appears when an owner has set a passphrase and the interface was left
     locked, or when a reader asks for it. */
  const locked = hasOwnerVerifier() && !isGateOpen();

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey && (event.key === 'k' || event.key === 'K')) {
        event.preventDefault();
        setPalette(value => !value);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  /* The document title follows the surface, so a deep link is identifiable in the tab, in the history and in
     a bookmark. It names the product first for the same reason the rail does. */
  useEffect(() => {
    if (shell === 'landing') document.title = 'WeatherGPT — evidence-first weather, on this machine';
    else if (shell === 'signin') document.title = 'WeatherGPT — owner gate';
    else if (view.id === 'assistant') document.title = 'WeatherGPT — Ask';
    else document.title = 'WeatherGPT — ' + view.label;
  }, [shell, view.id, view.label]);

  const ask = useCallback(
    (question: string) => {
      setSeed({ question, nonce: Date.now() });
      go('assistant');
    },
    [go],
  );

  if (shell === 'landing') {
    return <Landing onEnter={() => go('assistant')} />;
  }

  if (shell === 'signin' || locked) {
    return <OwnerGate onOpen={() => go('assistant')} onSkip={() => go('assistant')} onEnter={() => go('assistant')} />;
  }

  return (
    <div className="flex h-full min-h-screen" data-shell="react" data-surface={view.id}>
      {/* A visible-on-focus skip link, and it moves focus rather than only scrolling: the question box is
          where a keyboard reader wants to be on arrival. */}
      <a
        className="skip-link"
        href="#question"
        onClick={event => {
          const box = document.getElementById('question');
          if (!box) return;
          event.preventDefault();
          box.focus();
        }}
      >
        Skip to the question box
      </a>
      <SkyBackground />
      <Rail active={view.id} onOpen={open} />
      <main className="flex min-w-0 flex-1 flex-col">
        <Topbar
          language={language}
          onLanguage={setLanguage}
          persona={persona}
          onPersona={setPersona}
          theme={theme}
          onTheme={cycleTheme}
          onNew={() => { setSeed(null); go('assistant'); open('assistant'); }}
          onPalette={() => setPalette(true)}
          onOwner={() => {
            closeGate();
            go('signin');
          }}
        />
        <ErrorBoundary onReset={() => open('assistant')}>
          {view.id === 'assistant' ? (
            <section className="mx-auto flex min-h-0 w-full max-w-5xl flex-1 flex-col px-4 py-4" data-surface="assistant">
              <AskSurface language={language} persona={persona} seed={seed} />
            </section>
          ) : (
            <SurfaceHost view={view} onAsk={ask} />
          )}
        </ErrorBoundary>
        <p className="px-4 pb-3 text-[11px] quiet" data-print="drop">
          Every value on this page arrived with its source, its window and the time it was retrieved. The workspace
          answers on this machine only and will not invent a warning, an observation, a water level or a forecast.
        </p>
      </main>
      <Palette
        open={palette}
        onClose={() => setPalette(false)}
        onOpenView={id => open(id)}
        onNewConversation={() => { setSeed(null); open('assistant'); }}
      />
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
