import { useEffect } from 'react';
import { VIEWS, shortcutView, type ViewEntry } from './views';

/* The rail is a secondary index now: the conversation is the front door and every module is reachable
   through it. The keyboard shortcuts stay the contract the rail prints in the vanilla frontend
   (Alt+1…9), and the group headings keep two levels of scanning. */
const GROUPS: { id: ViewEntry['group']; title?: string }[] = [
  { id: 'start' },
  { id: 'weather', title: 'Weather & advice' },
  { id: 'more', title: 'Models, history & specialists' },
];

export function Rail({ active, onOpen }: { active: string; onOpen: (id: string) => void }) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!event.altKey || event.ctrlKey || event.metaKey) return;
      const number = Number(event.key);
      if (!Number.isInteger(number)) return;
      const view = shortcutView(number);
      if (!view) return;
      event.preventDefault();
      onOpen(view.id);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onOpen]);

  return (
    <nav aria-label="Workspace navigation" className="w-56 shrink-0 border-r border-line px-2 py-3">
      {GROUPS.map(group => (
        <div key={group.id} className="mb-2">
          {group.title ? <h2 className="px-2 pt-2 text-xs uppercase tracking-wide text-mute">{group.title}</h2> : null}
          {VIEWS.filter(view => view.group === group.id).map(view => {
            const current = view.id === active;
            return (
              <button
                key={view.id}
                type="button"
                aria-current={current ? 'page' : undefined}
                data-view={view.id}
                onClick={() => onOpen(view.id)}
                className={
                  'flex w-full items-center justify-between rounded-card px-2 py-2 text-left text-sm ' +
                  /* A rail highlight is a sand wash with ink on it. The full sand is a rule colour, not a
                     surface: measured in a browser, muted ink on it reads at 2.29:1. */
                  (current ? 'bg-sand-wash font-semibold text-ink' : 'hover:bg-sand-wash/60')
                }
              >
                <span>{view.label}</span>
                {view.shortcut ? <span className="text-xs text-mute">⌥{view.shortcut}</span> : null}
              </button>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
