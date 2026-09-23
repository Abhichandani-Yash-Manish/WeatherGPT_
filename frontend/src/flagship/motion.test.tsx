/* The one animated numeral in the product, and the rule it exists under.
   ============================================================================
   This used to count from zero to the retrieved value over nine hundred milliseconds. For most of a second
   the page showed measurements at display size, in the machine face, beside a real source and a real
   window, that the source never published - and any screenshot, print or photograph taken inside that
   window captured one of them.

   So the property pinned here is not "it animates". It is that the DOM never holds a number the tool did
   not return, at any point, including the first painted frame. */

import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { AnimatedNumber } from './motion';

afterEach(cleanup);

describe('a retrieved value', () => {
  it('is exact from the first render', () => {
    render(<AnimatedNumber value="9.6" className="v" />);
    expect(screen.getByText('9.6')).toBeInTheDocument();
    expect(document.querySelector('.v')).toHaveAttribute('data-value', '9.6');
  });

  it('never passes through zero on its way to a number', () => {
    const { container } = render(<AnimatedNumber value="27.4" />);
    expect(container.textContent).toBe('27.4');
    expect(container.textContent).not.toBe('0');
  });

  it('keeps a value that is not a numeral at all', () => {
    render(<AnimatedNumber value="not stated" />);
    expect(screen.getByText('not stated')).toBeInTheDocument();
  });

  it('keeps a zero reading distinguishable from an absent one', () => {
    const { container } = render(<AnimatedNumber value="0.0" />);
    expect(container.textContent).toBe('0.0');
  });

  it('keeps every significant figure the source printed', () => {
    const { container } = render(<AnimatedNumber value="1004.50" />);
    expect(container.textContent).toBe('1004.50');
  });
});
