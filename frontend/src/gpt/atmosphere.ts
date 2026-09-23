import { useCallback, useEffect, useState } from 'react';

const KEY = 'weathergpt.atmosphere';

/** Decorative motion is optional. This preference never changes weather evidence. */
export function useAtmosphere() {
  const [enabled, setEnabled] = useState(() => {
    try { return localStorage.getItem(KEY) !== 'paused'; } catch { return true; }
  });
  const [visible, setVisible] = useState(() => !document.hidden);
  useEffect(() => {
    const update = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', update);
    return () => document.removeEventListener('visibilitychange', update);
  }, []);
  const toggle = useCallback(() => setEnabled(value => {
    try { localStorage.setItem(KEY, value ? 'paused' : 'active'); } catch { /* optional storage */ }
    return !value;
  }), []);
  return { enabled, running: enabled && visible, toggle };
}
