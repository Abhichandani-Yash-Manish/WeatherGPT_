/* The matrix geometry, checked as geometry rather than by eye: the collision the reader reported was two
   rows of bubbles running into their labels and into each other, and a picture that looks right at one
   fixture can collapse at another. These checks read the drawn attributes and assert the rules the code
   claims: the pitch is wider than two radii, no bubble enters the label gutter, and no count is clipped at
   the top of the canvas. */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BubbleMatrix } from './DashboardCharts';

/* The live shape of the read: one very large day (the newest edition dominates) beside small ones, which is
   exactly the case where a naive radius makes neighbouring rows touch. */
const CELLS = [
  { day: 1, colour: 'orange', count: 23 },
  { day: 2, colour: 'yellow', count: 433 },
  { day: 2, colour: 'green', count: 368 },
  { day: 3, colour: 'yellow', count: 394 },
  { day: 3, colour: 'green', count: 358 },
  { day: 4, colour: 'yellow', count: 300 },
  { day: 4, colour: 'green', count: 455 },
  { day: 5, colour: 'yellow', count: 305 },
  { day: 5, colour: 'green', count: 450 },
  { day: 1, colour: 'red', count: 1 },
];
const DAYS = [1, 2, 3, 4, 5].map(day => ({ day, label: '2026-09-1' + day }));

/* The matrix holds no query of its own: it draws the cells it is handed. */
function mount(node: JSX.Element) {
  return render(node);
}

function bubbles(): { cx: number; cy: number; r: number; colour: string; count: number }[] {
  const svg = screen.getByTestId('today-matrix');
  return Array.from(svg.querySelectorAll('circle')).map(node => ({
    cx: Number(node.getAttribute('cx')),
    cy: Number(node.getAttribute('cy')),
    r: Number(node.getAttribute('r')),
    colour: node.getAttribute('data-colour') || '',
    count: Number(node.getAttribute('data-count')),
  }));
}

describe('the published-colour matrix', () => {
  it('keeps every bubble out of the label gutter and off its neighbours', () => {
    mount(<BubbleMatrix cells={CELLS} days={DAYS} />);
    const drawn = bubbles();
    expect(drawn.length).toBe(CELLS.length);

    /* The gutter is 56 units wide in the viewBox and the labels are right-aligned at 48. */
    drawn.forEach(bubble => expect(bubble.cx - bubble.r).toBeGreaterThanOrEqual(58));

    /* No two bubbles may touch, whatever rows they are in. */
    drawn.forEach((left, index) => drawn.slice(index + 1).forEach(right => {
      const distance = Math.hypot(left.cx - right.cx, left.cy - right.cy);
      expect(distance).toBeGreaterThanOrEqual(left.r + right.r);
    }));

    /* The pitch is wider than two radii plus a line of text, so a count above a bubble cannot land on the
       row above it. */
    const rows = Array.from(new Set(drawn.map(bubble => bubble.cy))).sort((a, b) => a - b);
    const biggest = drawn.reduce((max, bubble) => Math.max(max, bubble.r), 0);
    for (let index = 1; index < rows.length; index += 1) {
      expect(rows[index] - rows[index - 1]).toBeGreaterThan(2 * biggest);
    }

    /* Nothing is clipped: the topmost count and bubble still sit inside the canvas. */
    const top = Math.min(...drawn.map(bubble => bubble.cy - bubble.r));
    expect(top).toBeGreaterThan(12);
    expect(drawn.every(bubble => bubble.count > 0)).toBe(true);
  });

  it('draws nothing at all for a cell the rows did not return, and says so on the figure', () => {
    mount(<BubbleMatrix cells={[{ day: 2, colour: 'yellow', count: 5 }]} days={DAYS} />);
    /* One cell returned, one bubble drawn: the other four days are gaps, not zero-sized marks. */
    expect(bubbles()).toHaveLength(1);
    expect(screen.getByText(/A cell with no returned rows is empty/)).toBeInTheDocument();
  });

  it('states no matrix at all when the rows carried no day and colour', () => {
    mount(<BubbleMatrix cells={[]} days={[]} />);
    expect(screen.queryByTestId('today-matrix')).toBeNull();
    expect(screen.getByText(/no matrix is drawn/)).toBeInTheDocument();
  });
});
