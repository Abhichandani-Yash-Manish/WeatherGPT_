/* The edition histogram's date axis.

   Measured 21 September 2026 on the Today surface at 1440: the card returned six printed bulletin dates
   and drew a date under every bar. A date is eight characters of 11px mono - about 53 units of the 300-unit
   viewBox - and six bars leave 50 units each, so every label overlapped both of its neighbours and the axis
   read as a single smear of digits. The labels are thinned now. These two tests are the both-sides pair: it
   must thin when the bars are crowded, and it must NOT thin when they are not. */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { EditionHistogram } from './DashboardCharts';

function axisLabels(): string[] {
  const svg = screen.getByTestId('today-edition-profile');
  return Array.from(svg.querySelectorAll('.dash-axis')).map(node => node.textContent || '');
}

function dates(count: number): Record<string, number> {
  /* Consecutive days, so nothing is dropped for being an outlier - only for want of room. */
  const out: Record<string, number> = {};
  for (let day = 0; day < count; day += 1) out['2026-09-' + String(day + 1).padStart(2, '0')] = 10 + day;
  return out;
}

describe('the printed-edition axis', () => {
  it('draws a date under every bar when they are few enough to fit', () => {
    render(<EditionHistogram dates={dates(4)} newest="2026-09-04" oldestAge={3} behind={0} />);
    expect(axisLabels()).toEqual(['26-09-01', '26-09-02', '26-09-03', '26-09-04']);
  });

  it('thins the dates when the bars are too narrow to carry them', () => {
    render(<EditionHistogram dates={dates(12)} newest="2026-09-12" oldestAge={11} behind={0} />);
    const labels = axisLabels();
    expect(labels.length).toBeLessThan(12);
    expect(labels.length).toBeGreaterThan(1);
  });

  it('keeps the newest edition labelled, because it is the date the card reports', () => {
    render(<EditionHistogram dates={dates(12)} newest="2026-09-12" oldestAge={11} behind={0} />);
    expect(axisLabels()).toContain('26-09-12');
  });

  it('states every date in the accessible name even when the axis does not print it', () => {
    /* Thinning is a drawing decision. It must not be a disclosure decision. */
    render(<EditionHistogram dates={dates(12)} newest="2026-09-12" oldestAge={11} behind={0} />);
    const label = screen.getByTestId('today-edition-profile').getAttribute('aria-label') || '';
    for (let day = 1; day <= 12; day += 1) {
      expect(label).toContain('2026-09-' + String(day).padStart(2, '0'));
    }
  });
});
