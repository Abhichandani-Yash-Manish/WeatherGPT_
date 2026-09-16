import { useCallback, useEffect, useState } from 'react';
import { viewById, type ViewEntry } from './views';

/* The vanilla frontend routes on #/<view> and falls back to Ask; deep links such as ?watch= are kept
   in the query string so they survive a route change. This hook is the single place that reads the
   address, so a route cannot mean two things in two components. Two shell routes sit outside the
   surface registry: the front door (an empty hash) and the owner gate. */

export type ShellRoute = 'landing' | 'signin';

export function parseHash(hash: string): { view: ViewEntry; query: URLSearchParams; shell: ShellRoute | null } {
  const raw = (hash || '').replace(/^#\/?/, '');
  const [path, search] = raw.split('?');
  const query = new URLSearchParams(search || '');
  if (path === 'signin') return { view: viewById('assistant')!, query, shell: 'signin' };
  if (!path) return { view: viewById('assistant')!, query, shell: 'landing' };
  const found = viewById(path);
  if (!found) return { view: viewById('assistant')!, query, shell: null };
  return { view: found, query, shell: null };
}

export function useHashRoute() {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));

  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);

  const open = useCallback((id: string, query?: Record<string, string>) => {
    const search = new URLSearchParams(query || {}).toString();
    window.location.hash = '#/' + id + (search ? '?' + search : '');
  }, []);

  const go = useCallback((target: ShellRoute | 'assistant') => {
    window.location.hash = target === 'landing' ? '#/' : target === 'signin' ? '#/signin' : '#/assistant';
  }, []);

  return { view: route.view, query: route.query, shell: route.shell, open, go };
}
