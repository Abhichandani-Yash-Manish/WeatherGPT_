/* The React mount for the served chart engine.

   `web/viz.js` is the one tracked copy of the chart engine, served to this build at `/viz.js` and pinned by nine
   checks (`charts/viz.parity.test.ts`, `tests/test_react_vendor_assets.py`). The R4 plan said the React side would
   wrap it; that wrapper was never written, so six figures the vanilla frontend drew — the meteogram, the district ×
   day matrix, the now band, the published-day timeline, the ensemble fan and the library cards — were absent from
   every surface while their code stayed served and tested. This is that wrapper.

   The engine is loaded once, from this origin (the CSP allows `script-src 'self'`), and it draws into a host node.
   Nothing is re-implemented here: the engine keeps its own rules, which is the point of using it rather than a copy —
   a mark exists only where the read returned a value, a missing hour stays a gap, and every drawn point carries its
   source locator into the readout and the exact-value table.

   Where the engine cannot be loaded (a test DOM, or a browser that refused the file) the figure is simply absent and
   the surface's own tables still hold every value, so no reading depends on it. */
import { useEffect, useRef } from 'react';
import './viz.css';

export type VizKind = 'meteogram' | 'warningMatrix' | 'nowBand' | 'dayTimeline' | 'ensembleFan' | 'libraryCards';

type VizEngine = Record<VizKind, (spec: unknown) => Node>;

let pending: Promise<VizEngine | null> | null = null;

/* One load for the page: every figure shares it, and a failure is remembered as "no engine", never retried in a loop. */
export function loadViz(): Promise<VizEngine | null> {
  if (typeof window === 'undefined' || typeof document === 'undefined') return Promise.resolve(null);
  const holder = window as unknown as { viz?: VizEngine };
  if (holder.viz) return Promise.resolve(holder.viz);
  if (!pending) {
    pending = new Promise<VizEngine | null>(resolve => {
      const script = document.createElement('script');
      script.src = '/viz.js';
      script.async = true;
      script.addEventListener('load', () => resolve(holder.viz || null));
      script.addEventListener('error', () => resolve(null));
      document.head.append(script);
    });
  }
  return pending;
}

/* `spec` is the payload the engine's own function takes. Callers build it with `useMemo`, so a figure is drawn once
   per change of the read rather than on every render. */
export function VizFigure({ kind, spec, className }: { kind: VizKind; spec: unknown; className?: string }): JSX.Element {
  const host = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let live = true;
    void loadViz().then(engine => {
      const node = host.current;
      if (!live || !node) return;
      const draw = engine && engine[kind];
      if (typeof draw !== 'function') return;
      try {
        node.replaceChildren(draw(spec));
      } catch {
        /* A figure that cannot be drawn is left out; the surface's tables still carry every value. */
        node.replaceChildren();
      }
    });
    return () => {
      live = false;
    };
  }, [kind, spec]);

  return <div className={'viz-host' + (className ? ' ' + className : '')} ref={host} />;
}
