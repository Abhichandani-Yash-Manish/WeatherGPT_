/* The surface host: the real module when one is ported, and a stated placeholder when one is not.

   The placeholder is generated from the registry, shows the stage the module arrives in, and lets the
   reader ask one of its questions in the conversation now rather than pretending the route works. */

import { Suspense, lazy, useMemo } from 'react';
import { moduleFor } from '../modules/registry';
import type { ViewEntry } from './views';

export function SurfaceHost({ view, onAsk }: { view: ViewEntry; onAsk: (question: string) => void }) {
  const entry = moduleFor(view.id);
  /* A module exports its surface by name, so the lazy loader names it as the default React expects. */
  const Lazy = useMemo(() => (entry ? lazy(() => entry.load().then(module => ({ default: module.Surface }))) : null), [entry]);

  if (Lazy) {
    return (
      /* A surface longer than the viewport scrolls, so it takes focus itself: otherwise the only way to read
         the rest of it is a pointer or a scroll wheel (axe: scrollable-region-focusable). */
      <div
        className="min-h-0 flex-1 overflow-y-auto px-6 py-5"
        data-surface={view.id}
        tabIndex={0}
        role="region"
        aria-label={view.label + ' surface'}
      >
        <Suspense
          fallback={
            <p className="text-xs quiet" role="status">
              Loading the {view.label} module. It reads this machine's local evidence store; nothing is fetched from
              anywhere else.
            </p>
          }
        >
          <Lazy />
        </Suspense>
      </div>
    );
  }

  return (
    <section className="mx-auto w-full max-w-3xl px-6 py-8" data-surface={view.id}>
      <h1 className="display">{view.label}</h1>
      <p className="reading mt-2">
        This module is not ported yet. It arrives in <strong>{view.portedIn}</strong>; the vanilla workspace still serves
        it at <code className="evidence">#/{view.id}</code> in the meantime.
      </p>
      <p className="eyebrow mt-5">Questions it will answer</p>
      <ul className="mt-2 space-y-2">
        {view.intents.map(intent => (
          <li key={intent} className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm">{intent}</span>
            <button type="button" className="chip" onClick={() => onAsk(intent)}>
              Ask this in the conversation
            </button>
          </li>
        ))}
      </ul>
      <p className="mt-6 text-xs quiet">
        Asking sends the question to the conversation, where the same engine answers it with its sources attached.
      </p>
    </section>
  );
}
