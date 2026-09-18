/* Motion that answers the reader.
   ============================================================================
   Three pieces, used once each per answer: a value counts from zero to the number the tool returned; a
   block rises into place when it lands; the sentence reveals word by word. None of them loops, none of them
   runs on hover, and every one collapses to a plain render under prefers-reduced-motion and in tests. */

import { animate, useReducedMotion } from 'motion/react';
import { useEffect, useRef, useState, type ReactNode } from 'react';

/** True when motion should not run: the reader asked for less, or there is no real browser to run it in. */
export function useStill(): boolean {
  const reduced = useReducedMotion();
  return Boolean(reduced) || typeof window === 'undefined' || !('requestAnimationFrame' in window) || navigator.userAgent.includes('jsdom');
}

/** A numeral that counts to the value the tool returned, starting the moment it mounts so it has settled
    within a second of appearing. The text content is the exact value once settled, so a test or a reader
    reading the DOM sees the tool's number, never an interpolation. */
export function AnimatedNumber({ value, className }: { value: string; className?: string }) {
  const still = useStill();
  const numeric = /^-?\d+(?:\.\d+)?$/.test(value.trim());
  const decimals = numeric && value.includes('.') ? value.split('.')[1].length : 0;
  const target = numeric ? Number(value) : NaN;
  const [shown, setShown] = useState(still || !numeric ? value : '0');
  const ref = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    if (still || !numeric) {
      setShown(value);
      return;
    }
    const controls = animate(0, target, {
      duration: 0.9,
      ease: [0.2, 0.8, 0.2, 1],
      onUpdate: latest => setShown(latest.toFixed(decimals)),
      onComplete: () => setShown(value),
    });
    return () => controls.stop();
  }, [value, still, numeric, target, decimals]);

  return (
    <span ref={ref} className={className} data-value={value}>
      {shown}
    </span>
  );
}

/** A block that rises into place once. */
export function Rise({ children, delay = 0, className }: { children: ReactNode; delay?: 0 | 1 | 2 | 3 | 4; className?: string }) {
  const still = useStill();
  return (
    <div className={(still ? '' : 'f-rise ') + (className || '')} data-delay={delay || undefined}>
      {children}
    </div>
  );
}

/** A sentence that reveals word by word. The words are in the DOM in order from the first frame, so
    selection, search and screen readers see the whole sentence at once. */
export function Reveal({ text, className, as: Tag = 'p', ...rest }: { text: string; className?: string; as?: 'p' | 'h1' | 'span' } & Record<string, unknown>) {
  const still = useStill();
  if (still || text.length > 320) {
    return <Tag className={className} {...rest}>{text}</Tag>;
  }
  const words = text.split(/(\s+)/);
  let index = 0;
  return (
    <Tag className={className} {...rest}>
      {words.map((word, position) => {
        if (/^\s+$/.test(word)) return word;
        index += 1;
        return (
          <span
            key={position}
            className="f-rise"
            style={{ display: 'inline-block', animationDelay: Math.min(index * 22, 900) + 'ms', animationDuration: '420ms' }}
          >
            {word}
          </span>
        );
      })}
    </Tag>
  );
}
