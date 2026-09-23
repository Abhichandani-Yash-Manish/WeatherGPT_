/* Motion that answers the reader.
   ============================================================================
   Three pieces, used once each per answer: a value arrives; a block rises into place when it lands; the
   sentence reveals word by word. None of them loops, none of them runs on hover, and every one collapses
   to a plain render under prefers-reduced-motion and in tests.

   THE VALUE DOES NOT COUNT UP, AND THAT IS A PRODUCT RULE RATHER THAN A TASTE. It used to: it animated
   from zero to the retrieved number over nine hundred milliseconds, which meant that for most of a second
   this page displayed measurements at full size, in the machine face, beside a real source and a real
   window - that the source never published. 0.0, 3.1, 7.4 and forty other readings of Pune's rainfall
   that no tool ever returned. Every one of them was a false claim with a citation under it, and any
   screenshot, print or photograph taken inside that window captured one. The engine spends a whole
   retrieval layer refusing to state what it has not read; the presentation layer may not undo that for a
   flourish. So the value is exact from its first painted frame and what moves is the PRESENTATION of it. */

import { animate, useReducedMotion } from 'motion/react';
import { useEffect, useRef, type ReactNode } from 'react';

/** True when motion should not run: the reader asked for less, or there is no real browser to run it in. */
export function useStill(): boolean {
  const reduced = useReducedMotion();
  return Boolean(reduced) || typeof window === 'undefined' || !('requestAnimationFrame' in window) || navigator.userAgent.includes('jsdom');
}

/** The tool's value, exact from the first frame it paints, arriving rather than accumulating.

    The name is kept because this is still the one animated numeral in the product and every call site
    means the same thing by it; what changed is that the animation is now on the element and never on the
    number. A reader who photographs this mid-entrance gets a slightly faint, slightly low 9.6 - which is
    9.6. A reader who photographed the previous version mid-count got 4.1.

    Under prefers-reduced-motion, or anywhere without a real browser, it is a plain span. */
export function AnimatedNumber({ value, className }: { value: string; className?: string }) {
  const still = useStill();
  const ref = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    const element = ref.current;
    if (still || !element) return;
    /* Opacity and transform only: never width, never font-size. Scaling a numeral to animate it is how a
       reading ends up sub-pixel blurred at exactly the moment a reader is trying to read it. */
    const controls = animate(element,
      { opacity: [0, 1], transform: ['translateY(6px)', 'translateY(0px)'] },
      { duration: 0.42, ease: [0.2, 0.8, 0.2, 1] });
    return () => controls.stop();
  }, [still, value]);

  return (
    <span ref={ref} className={className} data-value={value}>
      {value}
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
