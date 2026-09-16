import { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import * as Popover from '@radix-ui/react-popover';
import { useVirtualizer } from '@tanstack/react-virtual';
import { motion } from 'motion/react';
import './styles/app.css';

/* Development probe, not part of the product: it renders one component from each library the overhaul
   wants to use and reports what the served Content-Security-Policy did to them. Radix positions through
   style attributes, the virtualiser translates rows through style attributes, and Motion writes transforms;
   if any of them is blocked, the finding is a policy decision rather than a mystery in R2. */
type Finding = {
  component: string;
  styleAttributePresent: boolean;
  computed: string;
  applied: boolean;
  measured: boolean;
  note: string;
};

/* A blocked inline style is ignored by the browser while the attribute stays in the DOM, so the only
   honest measurement is the computed style: position, transform and opacity as the engine resolved them. */
function computed(el: Element | null, property: string) {
  return el ? window.getComputedStyle(el).getPropertyValue(property) : '';
}

/* Registered at module scope, before React mounts, so a violation raised while the first elements are
   parsed cannot be missed by a listener that attaches afterwards. */
const violations: string[] = [];
document.addEventListener('securitypolicyviolation', event => {
  violations.push(event.violatedDirective + ': ' + (event.blockedURI || 'inline'));
});

function Probe() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const listRef = useRef<HTMLDivElement | null>(null);

  const virtualizer = useVirtualizer({ count: 500, getScrollElement: () => listRef.current, estimateSize: () => 22 });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const popover = document.querySelector('[data-radix-popper-content-wrapper]');
      const row = document.querySelector('[data-probe-row]');
      const animated = document.querySelector('[data-probe-motion]');
      setFindings([
        {
          component: 'radix-popover', measured: Boolean(popover),
          styleAttributePresent: Boolean(popover && popover.getAttribute('style')),
          computed: computed(popover, 'position'),
          applied: computed(popover, 'position') === 'fixed',
          note: popover ? String(popover.getAttribute('style')).slice(0, 60) : 'not rendered',
        },
        {
          component: 'tanstack-virtual', measured: Boolean(row),
          styleAttributePresent: Boolean(row && row.getAttribute('style')),
          computed: computed(row, 'position'),
          applied: computed(row, 'position') === 'absolute',
          note: row ? String(row.getAttribute('style')).slice(0, 60) : 'not rendered',
        },
        {
          component: 'motion', measured: Boolean(animated),
          styleAttributePresent: Boolean(animated && animated.getAttribute('style')),
          computed: computed(animated, 'transform'),
          applied: computed(animated, 'transform') !== '' && computed(animated, 'transform') !== 'none',
          note: animated ? String(animated.getAttribute('style')).slice(0, 60) : 'not rendered',
        },
      ]);
    }, 700);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!findings.length) return;
    const report = { findings, violations: [...violations], href: window.location.href, reportedAt: new Date().toISOString() };
    (window as unknown as { __probe: unknown }).__probe = report;
    /* The page reports itself: CDP evaluation is flaky in the sandbox, and a POST cannot be missed. */
    void fetch('/__probe/report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(report) }).catch(() => undefined);
  }, [findings, violations]);

  return (
    <main style={{ padding: 24, fontFamily: 'system-ui' }}>
      <h1 data-probe="title">CSP probe</h1>
      <p data-probe="policy">Development probe: measures what the served policy allows these libraries to do.</p>

      <section>
        <h2>Radix popover</h2>
        <Popover.Root defaultOpen>
          <Popover.Trigger data-probe="radix-trigger">Anchor</Popover.Trigger>
          <Popover.Portal>
            <Popover.Content sideOffset={6} data-probe="radix-content">
              Positioned content
              <Popover.Arrow />
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
      </section>

      <section>
        <h2>TanStack virtual</h2>
        <div ref={listRef} data-probe="virtual-viewport" style={{ height: 120, overflow: 'auto', border: '1px solid #ccc' }}>
          <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
            {virtualizer.getVirtualItems().map(item => (
              <div key={item.key} data-probe-row style={{ position: 'absolute', top: 0, transform: 'translateY(' + item.start + 'px)', height: item.size }}>
                Row {item.index}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section>
        <h2>Motion</h2>
        <motion.div data-probe-motion animate={{ x: 40, opacity: 1 }} initial={{ x: 0, opacity: 0.4 }} transition={{ duration: 0.4 }}>
          Animated block
        </motion.div>
      </section>

      <section>
        <h2>Findings</h2>
        <pre data-probe="findings">{JSON.stringify({ findings, violations }, null, 2)}</pre>
      </section>
    </main>
  );
}

const host = document.getElementById('probe');
if (host) createRoot(host).render(<Probe />);
