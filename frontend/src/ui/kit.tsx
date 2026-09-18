/* The component kit the shell and the surfaces are built from: the shadcn/ui idiom (variants through
   class-variance-authority, class merging through tailwind-merge) over the tokens, with Lucide icons and
   Motion for the transitions. Two rules from the design system hold here:

   1. A component never carries a colour that means something the data did not say. The hazard ramp is
      reached only through the `data-colour` attribute, which callers set from a published colour.
   2. Nothing here invents a value: a Stat, a Meter and a Sparkline draw what they are handed, and an
      absent value is rendered as the words the caller passes, not as a zero. */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion } from 'motion/react';
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { cn } from './cn';
import { HAZARD, type Hazard } from './colour';

/* ---- surfaces ------------------------------------------------------------------------------ */

export function Panel({ className, children, raised, as = 'section', ...rest }: {
  className?: string; children: ReactNode; raised?: boolean; as?: 'section' | 'div' | 'article' | 'aside';
} & React.HTMLAttributes<HTMLElement>) {
  const Tag = as;
  return <Tag className={cn(raised ? 'glass-strong' : 'glass', 'p-4', className)} {...rest}>{children}</Tag>;
}

export function SectionHead({ icon, title, hint, actions, className }: {
  icon?: ReactNode; title: ReactNode; hint?: ReactNode; actions?: ReactNode; className?: string;
}) {
  return (
    <div className={cn('flex flex-wrap items-start justify-between gap-3', className)}>
      <div className="flex min-w-0 items-start gap-3">
        {icon ? <span className="icon-tile shrink-0" aria-hidden="true">{icon}</span> : null}
        <div className="min-w-0">
          <h2 className="m-0 text-[length:var(--step-2)] font-semibold tracking-tight text-ink">{title}</h2>
          {hint ? <p className="module-note mt-1">{hint}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

/* ---- buttons ------------------------------------------------------------------------------- */

const button = cva('inline-flex items-center justify-center gap-2 whitespace-nowrap font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-55', {
  variants: {
    variant: {
      primary: 'btn btn-primary',
      glass: 'btn',
      ghost: 'btn btn-ghost',
      danger: 'btn btn-danger',
      subtle: 'border border-transparent bg-transparent text-ink-soft hover:bg-glass-3 hover:text-ink',
    },
    size: {
      sm: 'min-h-8 rounded-full px-3 text-[length:var(--step--1)]',
      md: 'min-h-10 rounded-full px-3.5 text-[length:var(--step--1)]',
      lg: 'min-h-11 rounded-full px-5 text-[length:var(--step-0)]',
      icon: 'h-10 w-10 rounded-xl p-0',
      'icon-sm': 'h-8 w-8 rounded-lg p-0',
    },
  },
  defaultVariants: { variant: 'glass', size: 'md' },
});

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof button> & {
  icon?: ReactNode;
  trailing?: ReactNode;
  tip?: string;
};

export function Button({ className, variant, size, icon, trailing, tip, children, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      className={cn(button({ variant, size }), tip && 'tooltip-host', className)}
      data-tip={tip}
      {...rest}
    >
      {icon ? <span aria-hidden="true" className="shrink-0">{icon}</span> : null}
      {children}
      {trailing ? <span aria-hidden="true" className="shrink-0">{trailing}</span> : null}
    </button>
  );
}

export function IconButton({ label, icon, className, ...rest }: Omit<ButtonProps, 'children' | 'icon'> & { label: string; icon: ReactNode }) {
  return (
    <Button aria-label={label} size="icon" className={className} {...rest}>
      <span aria-hidden="true" className="grid place-items-center">{icon}</span>
    </Button>
  );
}

/* ---- chips and tags ------------------------------------------------------------------------ */

const badge = cva('inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[length:var(--step--1)] font-semibold', {
  variants: {
    tone: {
      neutral: 'border-glass-line bg-glass-3 text-ink-soft',
      accent: 'pill-accent border-transparent',
      quiet: 'border-dashed border-glass-line bg-transparent font-medium text-mute',
      good: 'border-transparent bg-[color-mix(in_oklab,var(--green)_16%,transparent)] text-clear',
      held: 'border-transparent bg-[color-mix(in_oklab,var(--yellow)_18%,transparent)] text-caution',
      alert: 'border-transparent bg-[color-mix(in_oklab,var(--red)_16%,transparent)] text-alert',
    },
  },
  defaultVariants: { tone: 'neutral' },
});

export function Badge({ tone, className, children, ...rest }: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badge>) {
  return <span className={cn(badge({ tone }), className)} {...rest}>{children}</span>;
}

/* A hazard chip: the only component that draws a hazard colour, and only when a published colour names
   one. The colour name stays in the text, so the chip is readable without the colour. */
export function HazardChip({ colour, children, className }: { colour?: string | null; children?: ReactNode; className?: string }) {
  const stated = typeof colour === 'string' ? colour.trim().toLowerCase() : '';
  const hazard = (HAZARD as readonly string[]).includes(stated) ? (stated as Hazard) : null;
  return (
    <span
      className={cn('chip chip-colour', hazard ? '' : 'chip-unstated', className)}
      data-colour={hazard || undefined}
    >
      <span className="h-2 w-2 rounded-full bg-current" aria-hidden="true" />
      {children ?? (hazard || 'colour not stated')}
    </span>
  );
}

/* ---- statistics ---------------------------------------------------------------------------- */

export function Stat({ label, value, unit, foot, icon, meter, className }: {
  label: ReactNode; value: ReactNode; unit?: ReactNode; foot?: ReactNode; icon?: ReactNode; meter?: number | null; className?: string;
}) {
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <div className="flex items-center gap-2">
        {icon ? <span className="icon-tile icon-tile-sm icon-tile-quiet" aria-hidden="true">{icon}</span> : null}
        <span className="stat-label">{label}</span>
      </div>
      <p className="stat-value m-0 flex items-baseline gap-1.5 text-ink">
        {value}
        {unit ? <span className="stat-unit">{unit}</span> : null}
      </p>
      {typeof meter === 'number' ? (
        <div className="meter" role="presentation"><span style={{ width: Math.max(0, Math.min(100, meter)) + '%' }} /></div>
      ) : null}
      {foot ? <p className="stat-foot m-0">{foot}</p> : null}
    </div>
  );
}

/* ---- forms --------------------------------------------------------------------------------- */

export function Field({ label, hint, htmlFor, children, className }: {
  label: ReactNode; hint?: ReactNode; htmlFor?: string; children: ReactNode; className?: string;
}) {
  return (
    <label className={cn('module-field', className)} htmlFor={htmlFor}>
      <span>{label}</span>
      {children}
      {hint ? <span className="text-[length:var(--step--1)] text-mute">{hint}</span> : null}
    </label>
  );
}

export function Switch({ checked, onChange, label, className }: {
  checked: boolean; onChange: (value: boolean) => void; label: ReactNode; className?: string;
}) {
  return (
    <label className={cn('dash-toggle', className)}>
      <input type="checkbox" checked={checked} onChange={event => onChange(event.target.checked)} />
      <span>{label}</span>
    </label>
  );
}

export function Segmented<T extends string>({ options, value, onChange, label }: {
  options: { value: T; label: ReactNode }[]; value: T; onChange: (value: T) => void; label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="inline-flex gap-1 rounded-full border border-glass-line bg-glass-3 p-1">
      {options.map(option => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={active}
            className={cn('relative rounded-full px-3 py-1.5 text-[length:var(--step--1)] font-semibold transition-colors',
              active ? 'text-ink' : 'text-mute hover:text-ink')}
            onClick={() => onChange(option.value)}
          >
            {active ? (
              <motion.span
                layoutId={'segmented-' + label}
                className="absolute inset-0 -z-10 rounded-full bg-glass shadow-lift-1"
                transition={{ type: 'spring', stiffness: 420, damping: 34 }}
              />
            ) : null}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

/* ---- empty and loading --------------------------------------------------------------------- */

export function Empty({ icon, title, hint, action, className }: {
  icon?: ReactNode; title: ReactNode; hint?: ReactNode; action?: ReactNode; className?: string;
}) {
  return (
    <div className={cn('flex flex-col items-start gap-3 rounded-2xl border border-dashed border-glass-line bg-glass-3 p-5', className)}>
      {icon ? <span className="icon-tile icon-tile-quiet" aria-hidden="true">{icon}</span> : null}
      <p className="m-0 font-semibold text-ink">{title}</p>
      {hint ? <p className="module-note m-0">{hint}</p> : null}
      {action}
    </div>
  );
}

export function SkeletonLines({ lines = 3, frame }: { lines?: number; frame?: boolean }) {
  return (
    <div className="flex flex-col gap-2" aria-hidden="true">
      {Array.from({ length: lines }).map((_, index) => (
        <span key={index} className="block h-2.5 rounded-full bg-[color-mix(in_oklab,var(--line-strong)_35%,transparent)] pulse-soft"
          style={{ width: index === lines - 1 ? '58%' : index % 2 ? '88%' : '100%' }} />
      ))}
      {frame ? <span className="mt-1 block h-24 rounded-2xl border border-dashed border-glass-line bg-glass-3" /> : null}
    </div>
  );
}

/* ---- overlays ------------------------------------------------------------------------------ */

export function Modal({ open, onClose, title, children, labelledBy = 'modal-title' }: {
  open: boolean; onClose: () => void; title: ReactNode; children: ReactNode; labelledBy?: string;
}) {
  const [node, setNode] = useState<HTMLDialogElement | null>(null);
  useEffect(() => {
    if (!node) return;
    if (open && !node.open) node.showModal?.();
    if (!open && node.open) node.close?.();
  }, [open, node]);
  useEffect(() => {
    if (!node) return;
    const onCancel = (event: Event) => { event.preventDefault(); onClose(); };
    node.addEventListener('cancel', onCancel);
    return () => node.removeEventListener('cancel', onCancel);
  }, [node, onClose]);
  return (
    <dialog ref={setNode} aria-labelledby={labelledBy} className="card w-[min(44rem,94vw)] p-0 backdrop:bg-[var(--scrim)]">
      <div className="flex items-center justify-between gap-4 border-b border-glass-line px-4 py-3">
        <h2 id={labelledBy} className="m-0 text-[length:var(--step-1)] font-semibold text-ink">{title}</h2>
        <IconButton label="Close" variant="subtle" size="icon-sm" icon={<X size={16} />} onClick={onClose} />
      </div>
      <div className="max-h-[70vh] overflow-y-auto p-4">{children}</div>
    </dialog>
  );
}

/* ---- toasts --------------------------------------------------------------------------------
   A toast states what the reader just did (copied, saved, refused). It is transient chrome, never
   evidence: nothing a toast says may be quoted as a value, and the message is the caller's words. */
type Toast = { id: number; message: string; tone: 'info' | 'good' | 'alert' };
const ToastContext = createContext<{ push: (message: string, tone?: Toast['tone']) => void }>({ push: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

export function ToastHost({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((message: string, tone: Toast['tone'] = 'info') => {
    const id = Date.now() + Math.random();
    setItems(current => [...current.slice(-3), { id, message, tone }]);
    window.setTimeout(() => setItems(current => current.filter(item => item.id !== id)), 4200);
  }, []);
  const value = useMemo(() => ({ push }), [push]);
  const icon = (tone: Toast['tone']) => tone === 'good' ? <CheckCircle2 size={16} /> : tone === 'alert' ? <AlertTriangle size={16} /> : <Info size={16} />;
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[min(22rem,90vw)] flex-col gap-2" aria-live="polite">
        {items.map(item => (
          <motion.p
            key={item.id}
            initial={{ opacity: 0, y: 12, scale: .98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ type: 'spring', stiffness: 380, damping: 30 }}
            role="status"
            className="glass-strong pointer-events-auto m-0 flex items-start gap-2 p-3 text-[length:var(--step--1)] text-ink"
          >
            <span className={cn('mt-0.5 shrink-0', item.tone === 'good' ? 'text-clear' : item.tone === 'alert' ? 'text-alert' : 'text-data')} aria-hidden="true">{icon(item.tone)}</span>
            <span>{item.message}</span>
          </motion.p>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
