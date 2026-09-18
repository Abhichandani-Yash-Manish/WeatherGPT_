/* The shell: one conversation at the centre, every module beside it, and a front door in front of both.

   The landing page is shown for an empty address and opens the workspace; the owner gate is shown only
   when a reader asks for it or when a verifier exists and the interface is locked. Every surface in
   between is reachable by its own deep link, which is what the vanilla workspace already promised. */

import { MotionConfig } from 'motion/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { ToastHost } from './ui/kit';
import { Home } from './home/Home';
import { OwnerGate } from './landing/OwnerGate';
import { closeGate, hasOwnerVerifier, isGateOpen } from './landing/owner';
import { ErrorBoundary } from './shell/ErrorBoundary';
import { PlanWatch } from './plans/PlanWatch';
import { Palette } from './shell/Palette';
import { useHashRoute } from './shell/useHashRoute';

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
  const { view, shell, open, go, query, unknown } = useTransitionedRoute();
  /* A deep link such as #/assistant?watch=<id> opens the panel the link names. The query is read here
     rather than in a surface, so the same link works from anywhere in the app. */
  const watchId = query.get('watch');
  /* No theme switch: the light engine decides the palette from the reader's own sun, so a manual toggle would
     be a second, contradicting answer to the same question. */
  const [language, setLanguage] = useState('');
  const [persona, setPersona] = useState('');
  const [palette, setPalette] = useState(false);
  const askedSeeded = useRef(false);
  const [plansOpen, setPlansOpen] = useState(false);
  const [seed, setSeed] = useState<Seed>(null);

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
    if (shell === 'landing') document.title = 'WeatherGPT';
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

  /* The front door is the conversation's own door: it opens on the country's weather as this machine read
     it, lit by the reader's own hour, and hands a question straight to the assistant. The page it replaced
     is still in the tree as Landing.tsx; it is no longer served. */
  if (shell === 'landing') {
    return (
      <Home
        onOpen={open}
        onAsk={ask}
        onNew={() => { setSeed(null); open('assistant'); }}
        onPlans={() => setPlansOpen(true)}
        onOwner={() => { closeGate(); go('signin'); }}
        seed={seed}
        language={language}
        onLanguage={setLanguage}
        persona={persona}
        onPersona={setPersona}
      />
    );
  }

  if (shell === 'signin' || locked) {
    return <OwnerGate onOpen={() => go('assistant')} onSkip={() => go('assistant')} onEnter={() => go('assistant')} />;
  }

  /* The surfaces that carry a question box are the two the skip link can point at; every other surface
     points at the main landmark instead, which exists on all of them. */
  const hasQuestionBox = view.id === 'assistant' || view.id === 'workspace';

  return (
    <div className="flex h-full min-h-screen" data-shell="react" data-surface={view.id}>
      {/* A visible-on-focus skip link, and it moves focus rather than only scrolling. It is wrapped in its own
          landmark: a skip link that sits outside every landmark is reported by axe as unlandmarked content
          (measured 18 September 2026 on all 17 surfaces that have no question box), and it pointed at #question
          on surfaces where that id does not exist, so the link did nothing and axe reported a missing target.
          The target is now chosen from what the surface actually has: the question box where one exists, the
          main landmark everywhere else. */}
      <nav aria-label="Skip to" className="skip-links" data-testid="skip-links">
        <a
          className="skip-link"
          href={hasQuestionBox ? '#question' : '#main'}
          onClick={event => {
            const box = document.getElementById(hasQuestionBox ? 'question' : 'main');
            if (!box) return;
            event.preventDefault();
            box.focus();
          }}
        >
          {hasQuestionBox ? 'Skip to the question box' : 'Skip to the main content'}
        </a>
      </nav>
      {/* One shell for the whole product.
          The instrument chrome — the rail of eighteen peer surfaces, the dashboard top bar, the aurora, the
          system-theme control — is no longer mounted. The conversation is the page, every module opens beside it
          in the same frame, and the light engine decides the theme rather than a switch. Those components remain
          in the tree, unreferenced here, until their tests are retired with them. */}
      <section id="main" tabIndex={-1} className="flex min-h-0 flex-1 flex-col focus:outline-none">
        <ErrorBoundary onReset={() => open('assistant')}>
          <Home
            view={view}
            onOpen={open}
            onAsk={ask}
            onNew={() => {
              setSeed(null);
              open('assistant');
            }}
            onPlans={() => setPlansOpen(true)}
            onOwner={() => {
              closeGate();
              go('signin');
            }}
            language={language}
            onLanguage={setLanguage}
            persona={persona}
            onPersona={setPersona}
            seed={seed}
            restoreId={query.get('conversation')}
            unknownRoute={shell === 'unknown' ? unknown : null}
          />
        </ErrorBoundary>
      </section>
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
