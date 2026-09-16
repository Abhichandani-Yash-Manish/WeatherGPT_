import { useEffect, useState } from 'react';
import { viewById, type ViewEntry } from './views';

/* The vanilla frontend routes on #/<view> and falls back to Ask; deep links such as ?watch= are kept
   in the query string so they survive a route change. This hook is the single place that reads the
   address, so a route cannot mean two things in two components. */
export function parseHash(hash: string): { view: ViewEntry; query: URLSearchParams } {
  const raw = (hash || '').replace(/^#\/?/, '');
  const [path, search] = raw.split('?');
  const found = viewById(path);
  return {
    view: found && found.id !== 'assistant' ? found : (viewById(path) ?? viewById('assistant')!),
    query: new URLSearchParams(search || ''),
  };
}

export function useHashRoute() {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));

  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);

  const open = (id: string, query?: Record<string, string>) => {
    const search = new URLSearchParams(query || {}).toString();
    window.location.hash = '#/' + id + (search ? '?' + search : '');
  };

  return { view: route.view, query: route.query, open };
}
