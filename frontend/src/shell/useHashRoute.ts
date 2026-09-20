import { useCallback, useEffect, useState } from 'react';
import { PLACE_ROUTE, viewById, type ViewEntry } from './views';

/* The vanilla frontend routes on #/<view> and falls back to Ask; deep links such as ?watch= are kept
   in the query string so they survive a route change. This hook is the single place that reads the
   address, so a route cannot mean two things in two components. Three shell routes sit outside the
   surface registry: the front door (an empty hash), the owner gate, and a place's own page
   (`#/place?place=…&plat=…&plon=…`, docs/122), which is a destination for the place an address names
   rather than a peer surface in the rail. */

export type ShellRoute = 'landing' | 'signin' | 'place' | 'unknown';

export function parseHash(hash: string): { view: ViewEntry; query: URLSearchParams; shell: ShellRoute | null; unknown?: string } {
  const raw = (hash || '').replace(/^#\/?/, '');
  const [path, search] = raw.split('?');
  const query = new URLSearchParams(search || '');
  if (path === 'signin') return { view: viewById('assistant')!, query, shell: 'signin' };
  /* A place page is read on arrival rather than redirected: a half-written address is refused in words on
     the page it names, which a redirect to the conversation could not do. */
  if (path === PLACE_ROUTE) return { view: viewById('assistant')!, query, shell: 'place' };
  if (!path) return { view: viewById('assistant')!, query, shell: 'landing' };
  const found = viewById(path);
  /* A page the registry does not hold is named in words on the conversation, never shown as if it were it. */
  if (!found) return { view: viewById('assistant')!, query, shell: 'unknown', unknown: path };
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

  return { view: route.view, query: route.query, shell: route.shell, unknown: route.unknown || null, open, go };
}
