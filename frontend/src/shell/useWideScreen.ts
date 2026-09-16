/* Whether the viewport is wide enough for the conversation's stored-conversation column to sit beside
   the transcript rather than under it. One instance is rendered either way: two copies would duplicate
   the filter field's id and every control in it, which is exactly what an accessibility check flags. */

import { useEffect, useState } from 'react';

export const WIDE_QUERY = '(min-width: 80rem)';

export function useWideScreen(): boolean {
  const [wide, setWide] = useState(() =>
    typeof window.matchMedia === 'function' ? window.matchMedia(WIDE_QUERY).matches : true,
  );
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const query = window.matchMedia(WIDE_QUERY);
    const sync = () => setWide(query.matches);
    sync();
    query.addEventListener('change', sync);
    return () => query.removeEventListener('change', sync);
  }, []);
  return wide;
}
