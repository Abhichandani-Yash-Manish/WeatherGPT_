/* The horizon: what it must be, and what it must never become.
   ============================================================================
   A decorative layer is the easiest thing in an interface to get wrong, because nothing fails when it is
   wrong - it just quietly starts competing with the content, or gets read out to somebody using a screen
   reader as a list of rectangles. These are the three promises it makes. */
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Horizon } from './Horizon';

describe('the city under the sky', () => {
  it('states nothing, so it is hidden from assistive technology and cannot be clicked', () => {
    /* It is a silhouette. It carries no information a reader could act on, which means announcing it
       would be noise and intercepting a pointer would be a bug. */
    const { container } = render(<Horizon />);
    const layer = container.querySelector('.g-horizon')!;
    expect(layer.getAttribute('aria-hidden')).toBe('true');
    expect(layer.textContent).toBe('');
    for (const svg of Array.from(container.querySelectorAll('svg'))) {
      expect(svg.getAttribute('focusable'), 'an SVG in the background must not take tab focus').toBe('false');
    }
  });

  it('is drawn as strokes, never filled', () => {
    /* The two-ridge filled band this replaced was a grey smear at four per cent and a wall of blocks at
       anything higher. As 1.25px strokes the same buildings are an etching - legible at a glance and
       quiet at the same time. A `fill` other than none here would put the smear back. */
    const { container } = render(<Horizon />);
    const city = container.querySelector('.g-horizon-city')!;
    expect(city).not.toBeNull();
    const group = city.querySelector('g')!;
    expect(group.getAttribute('fill')).toBe('none');
    expect(group.getAttribute('stroke')).toBe('currentColor');
    expect(city.querySelectorAll('[fill]:not([fill="none"])').length,
      'a filled shape crept back into the drawing').toBe(0);
  });

  it('flies four birds, on four separate clocks', () => {
    /* Four rather than one: a single bird reads as a glitch. Separate classes rather than one shared
       class because they must not fall into step - birds in formation stop being weather and start
       being a logo animation. */
    const { container } = render(<Horizon />);
    const birds = Array.from(container.querySelectorAll('.g-bird'));
    expect(birds).toHaveLength(4);
    /* getAttribute, not .className: on an SVG element className is an SVGAnimatedString rather than a
       string, so the obvious spelling throws instead of comparing. */
    const own = new Set(birds.map(bird => (bird.getAttribute('class') || '').replace('g-bird ', '')));
    expect(own.size, 'the birds share a class and would fly in formation').toBe(4);
  });
});
