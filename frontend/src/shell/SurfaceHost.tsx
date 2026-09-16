import type { ViewEntry } from './views';

/* A module that has not been ported yet says so, with the stage it belongs to and the questions it will
   answer. This keeps a placeholder from passing as a working surface: the wording is generated from the
   registry, not hand-written per page. */
export function SurfaceHost({ view }: { view: ViewEntry }) {
  return (
    <section className="mx-auto w-full max-w-3xl px-6 py-8" data-surface={view.id}>
      <h1 className="text-lg font-semibold">{view.label}</h1>
      <p className="mt-1 text-sm text-ink-soft">
        This module is not ported yet. It arrives in <strong>{view.portedIn}</strong>; the vanilla workspace
        still serves it at <code className="text-xs">#/{view.id}</code> in the meantime.
      </p>
      <p className="mt-4 text-xs uppercase tracking-wide text-mute">Questions it will answer</p>
      <ul className="mt-1 list-disc pl-5 text-sm">
        {view.intents.map(intent => (
          <li key={intent}>{intent}</li>
        ))}
      </ul>
    </section>
  );
}
