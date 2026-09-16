/* The chart block's checks, ported from the rules tests/test_charts.js holds the vanilla renderer to: only a
   returned value is drawn, a missing point is a gap, every point names its exact source value and evidence id,
   and the same numbers are reachable as a table. */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChartBlock } from './ChartBlock';

const SERIES = {
  title: 'Annual rainfall',
  unit: 'mm',
  axis_label: 'Year',
  points: [
    { year: 1981, x: 1981, value: 812.4, evidence_id: 'E1' },
    { year: 1982, x: 1982, value: null, evidence_id: 'E2' },
    { year: 1983, x: 1983, value: 640, evidence_id: 'E3' },
  ],
};

describe('the chart block', () => {
  it('draws only returned values, leaves a missing point as a gap, and keeps the table alongside', async () => {
    render(<ChartBlock chart={SERIES} />);
    const figure = screen.getByTestId('chart-block');
    expect(within(figure).getByRole('group', { name: /Annual rainfall in mm/ })).toBeInTheDocument();
    expect(figure.querySelectorAll('circle')).toHaveLength(2);
    expect(figure.querySelectorAll('polyline')).toHaveLength(0);
    const user = userEvent.setup();
    await user.click(within(figure).getByRole('button', { name: /1981: 812.4 mm · E1/ }));
    expect(within(figure).getByText(/1981: 812.4 mm · E1/, { selector: 'p' })).toBeInTheDocument();
    await user.click(within(figure).getByText('View exact values and evidence IDs'));
    const table = within(figure).getByRole('table');
    expect(within(table).getByText('Missing')).toBeInTheDocument();
    expect(within(table).getByText('E2')).toBeInTheDocument();
  });

  it('says so when every point is missing rather than drawing an empty frame', () => {
    render(<ChartBlock chart={{ ...SERIES, points: [{ year: 1981, x: 1981, value: null }] }} />);
    expect(screen.getByText(/nothing is drawn/i)).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: /Annual rainfall in mm/ })).toBeNull();
  });

  it('says so when the series came back with no points at all', () => {
    render(<ChartBlock chart={{ ...SERIES, points: [] }} />);
    expect(screen.getByTestId('chart-empty')).toHaveTextContent(/no points at all/i);
  });
});
