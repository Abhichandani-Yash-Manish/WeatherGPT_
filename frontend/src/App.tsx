/* The shell: one conversation at the centre, every module beside it, and a front door in front of both.

   The landing page is shown for an empty address and opens the workspace; the owner gate is shown only
   when a reader asks for it or when a verifier exists and the interface is locked. Every surface in
   between is reachable by its own deep link, which is what the vanilla workspace already promised. */

import { MotionConfig } from 'motion/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { AskSurface } from './chat/AskSurface';
import { Aurora } from './shell/Aurora';
import { ToastHost } from './ui/kit';
import { Landing } from './landing/Landing';
import { OwnerGate } from './landing/OwnerGate';
import { closeGate, hasOwnerVerifier, isGateOpen } from './landing/owner';
import { PinnedPlaces } from './modules/Evidence';
import { ErrorBoundary } from './shell/ErrorBoundary';
import { PlanWatch } from './plans/PlanWatch';
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

/* The View Transition API is optional here: this project runs in jsdom and in browsers that do not
   implement it, so it is named locally rather than read from the DOM types as a method that must exist. */
type ViewTransitionDocument = { startViewTransition?: (callback: () => void) => unknown };

function transitionDocument(): ViewTransitionDocument {
  return document as unknown as ViewTransitionDocument;
}

function routeKey(route: ReturnType<typeof useHashRoute>): string {
  return route.shell + '|' + route.view.id + '|' + route.query.toString();
}

/* Progressive enhancement: a route change is offered to the browser as a view transition when it offers
   document.startViewTransition, and stays a plain route state update when it does not. The two paths show
   the same surface — with no API the route is read straight from the hook, so a browser that has never
   heard of the API behaves exactly as before, and the transition is never required for anything to work. */
function useTransitionedRoute(): ReturnType<typeof useHashRoute> {
  const route = useHashRoute();
  const supported = typeof document !== 'undefined' && typeof transitionDocument().startViewTransition === 'function';
  const [shown, setShown] = useState(route);
  const shownKey = useRef(routeKey(route));
  useEffect(() => {
    const key = routeKey(route);
    if (key === shownKey.current) return;
    if (!supported) {
      /* No API: the hook's own route is rendered, so there is nothing to defer and nothing to attempt. */
      shownKey.current = key;
      return;
    }
    const update = () => {
      shownKey.current = key;
      /* The DOM update has to happen inside the callback or the browser captures the new surface twice. */
      flushSync(() => setShown(route));
    };
    /* A microtask rather than the effect body itself: React refuses a synchronous flush from inside a
       lifecycle, and the microtask runs before the browser paints, so the old surface is still on screen
       when the transition starts. */
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      transitionDocument().startViewTransition?.(update);
    });
    return () => {
      cancelled = true;
    };
  }, [route, supported]);
  return supported ? shown : route;
}

function Shell() {
  const { view, shell, open, go, query } = useTransitionedRoute();
  /* A deep link such as #/assistant?watch=<id> opens the panel the link names. The query is read here
     rather than in a surface, so the same link works from anywhere in the app. */
  const watchId = query.get('watch');
  const [theme, cycleTheme] = useTheme();
  const [language, setLanguage] = useState('');
  const [persona, setPersona] = useState('');
  const [palette, setPalette] = useState(false);
  const askedSeeded = useRef(false);
  const [railOpen, setRailOpen] = useState(false);
  const [plansOpen, setPlansOpen] = useState(false);
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

  useEffect(() => {
    if (watchId) setPlansOpen(true);
  }, [watchId]);

  /* A surface can hand a question to the conversation: #/assistant?ask=<question>. It is seeded once, so a
     re-render does not re-ask it, and the question is the caller's own words. */
  useEffect(() => {
    const asked = query.get('ask');
    if (!asked || askedSeeded.current) return;
    askedSeeded.current = true;
    setSeed({ question: asked, nonce: Date.now() });
    go('assistant');
  }, [query, go]);

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
      <Aurora />
      <SkyBackground />
      <Rail active={view.id} onOpen={open} open={railOpen} onClose={() => setRailOpen(false)} />
      <button
        type="button"
        className="rail-backdrop"
        aria-label="Close the navigation"
        hidden={!railOpen}
        onClick={() => setRailOpen(false)}
      />
      <main className="relative flex min-w-0 flex-1 flex-col">
        <Topbar
          language={language}
          onLanguage={setLanguage}
          persona={persona}
          onPersona={setPersona}
          theme={theme}
          onTheme={cycleTheme}
          onNew={() => { setSeed(null); go('assistant'); open('assistant'); }}
          onPalette={() => setPalette(true)}
          onPlans={() => setPlansOpen(true)}
          onMenu={() => setRailOpen(value => !value)}
          railOpen={railOpen}
          onOwner={() => {
            closeGate();
            go('signin');
          }}
        />
        {/* The places this browser remembers, in the shell rather than inside one surface: a reader can
            pin the place a read resolved and see it here from any route, and remove it from here. */}
        <PinnedPlaces />
        <ErrorBoundary onReset={() => open('assistant')}>
          {view.id === 'assistant' ? (
            <section className="mx-auto flex min-h-0 w-full max-w-6xl flex-1 flex-col px-4 py-4" data-surface="assistant">
              <AskSurface language={language} persona={persona} seed={seed} restoreId={query.get('conversation')} />
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
      {/* The plans, watches and inbox panel: not a surface, opened from the topbar or the palette. */}
      {plansOpen ? (
        <div className="planwatch-host" role="presentation">
          <PlanWatch onClose={() => setPlansOpen(false)} />
        </div>
      ) : null}
      <Palette
        open={palette}
        onClose={() => setPalette(false)}
        onOpenView={id => open(id)}
        onNewConversation={() => { setSeed(null); open('assistant'); }}
        onAsk={ask}
        onOpenConversation={id => open('assistant', { conversation: id })}
        actions={[{ id: 'plans', label: 'Open plans, watches and the inbox', hint: 'what the workspace will check again, and what it delivered', run: () => setPlansOpen(true) }]}
      />
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user">
        {/* The toast host states what a reader just did (copied, saved, refused). It sits outside the
            surfaces so a message survives a route change, and it is chrome, never evidence. */}
        <ToastHost>
          <Shell />
        </ToastHost>
      </MotionConfig>
    </QueryClientProvider>
  );
}
