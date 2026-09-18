import { useEffect } from 'react';
import { motion } from 'motion/react';
import { Command, PanelLeftClose, Sparkles } from 'lucide-react';
import { cn } from '../ui/cn';
import { SURFACE_ICONS } from '../ui/icons';
import { VIEWS, shortcutView, type ViewEntry } from './views';

/* The rail is a secondary index: the conversation is the front door and every module is reachable
   through it. The keyboard shortcuts stay the contract the vanilla frontend printed (Alt+1…9), and
   the group headings keep two levels of scanning. Each entry carries the icon its surface is drawn
   with, from one map, so the rail, the palette and a surface header cannot disagree. */
const GROUPS: { id: ViewEntry['group']; title?: string }[] = [
  { id: 'start' },
  { id: 'weather', title: 'Weather & advice' },
  { id: 'more', title: 'Models, history & specialists' },
];

export type RailProps = {
  active: string;
  onOpen: (id: string) => void;
  /** Below the wide breakpoint the rail is a drawer: closed by default, opened from the topbar. */
  open: boolean;
  onClose: () => void;
};

export function Rail({ active, onOpen, open, onClose }: RailProps) {
  useEffect(() => {
    if (!open) return;
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onEscape);
    return () => window.removeEventListener('keydown', onEscape);
  }, [open, onClose]);

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
    <nav
      aria-label="Workspace navigation"
      id="workspace-rail"
      data-open={open ? 'true' : 'false'}
      className="rail z-20 flex w-64 shrink-0 flex-col overflow-y-auto px-3 py-4"
    >
      <div className="mb-4 flex items-center gap-2.5 px-1">
        <span className="icon-tile" aria-hidden="true"><Sparkles size={17} /></span>
        <span className="min-w-0">
          <span className="block truncate text-[length:var(--step-1)] font-semibold tracking-tight text-ink">WeatherGPT</span>
          <span className="block truncate text-[length:var(--step--1)] quiet">Evidence-first workspace</span>
        </span>
        <button
          type="button"
          className="btn btn-ghost narrow-only ml-auto"
          aria-label="Close the navigation"
          onClick={onClose}
        >
          <PanelLeftClose size={16} />
        </button>
      </div>

      <div className="flex flex-1 flex-col gap-4">
        {GROUPS.map(group => (
          <div key={group.id} className="flex flex-col gap-1">
            {group.title ? (
              <h2 className="px-2 pb-1 text-[length:var(--step--1)] font-semibold uppercase tracking-[var(--track-wide)] text-mute">
                {group.title}
              </h2>
            ) : null}
            {VIEWS.filter(view => view.group === group.id).map(view => {
              const current = view.id === active;
              const Icon = SURFACE_ICONS[view.id] ?? Sparkles;
              return (
                <button
                  key={view.id}
                  type="button"
                  aria-current={current ? 'page' : undefined}
                  data-view={view.id}
                  onClick={() => {
                    onOpen(view.id);
                    onClose();
                  }}
                  className={cn(
                    'group relative flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-[length:var(--step-0)] transition-colors',
                    current ? 'font-semibold text-ink' : 'text-ink-soft hover:bg-glass-3 hover:text-ink',
                  )}
                >
                  {current ? (
                    <motion.span
                      layoutId="rail-active"
                      className="absolute inset-0 -z-10 rounded-xl border border-glass-line bg-glass shadow-lift-1"
                      transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                    />
                  ) : null}
                  <span
                    className={cn('grid h-7 w-7 shrink-0 place-items-center rounded-lg',
                      current ? 'bg-[color-mix(in_oklab,var(--data)_16%,transparent)] text-data' : 'text-mute group-hover:text-data')}
                    aria-hidden="true"
                  >
                    <Icon size={16} />
                  </span>
                  <span className="min-w-0 flex-1 truncate">{view.label}</span>
                  {/* The shortcut is part of the control's own name ("Ask ⌥1"), so a screen reader
                      hears the binding the rail prints; it is revealed on hover or focus. */}
                  {view.shortcut ? (
                    <span className="text-xs text-mute opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                      {'⌥' + view.shortcut}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {/* The one key hint the rail owes a reader, and it is a real binding. */}
      <p className="mt-4 flex items-center gap-2 rounded-xl border border-glass-line bg-glass-3 px-2.5 py-2 text-[length:var(--step--1)] quiet">
        <Command size={14} aria-hidden="true" />
        <span><span className="evidence">Alt K</span> opens the command palette</span>
      </p>
    </nav>
  );
}
