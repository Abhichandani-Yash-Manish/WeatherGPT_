/* The component kit's own checks: the two rules of the design system it has to keep, and the pieces the
   shell leans on. A kit component may not introduce a colour the payload did not state, and a toast is
   chrome, never evidence. */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Button, HazardChip, Segmented, Stat, ToastHost, useToast } from './kit';

describe('the component kit', () => {
  it('draws a hazard chip only when a published colour names one', () => {
    const { container, unmount } = render(<HazardChip colour="yellow">yellow</HazardChip>);
    expect(container.querySelector('[data-colour="yellow"]')).not.toBeNull();
    unmount();

    const { container: plain } = render(<HazardChip colour="chartreuse">chartreuse</HazardChip>);
    expect(plain.querySelector('[data-colour]')).toBeNull();
    expect(plain.querySelector('.chip-unstated')).not.toBeNull();
    expect(screen.getByText('chartreuse')).toBeInTheDocument();
  });

  it('keeps the caller words in a button and marks its icon decorative', async () => {
    const run = vi.fn();
    render(<Button icon={<span data-testid="glyph">*</span>} onClick={run}>Collect fresh evidence</Button>);
    const button = screen.getByRole('button', { name: 'Collect fresh evidence' });
    expect(button).toBeInTheDocument();
    expect(screen.getByTestId('glyph').closest('[aria-hidden="true"]')).not.toBeNull();
    await userEvent.click(button);
    expect(run).toHaveBeenCalledTimes(1);
  });

  it('states a statistic exactly as it is handed over', () => {
    render(<Stat label="Districts in this read" value="not recorded" foot="The read returned no count." />);
    expect(screen.getByText('Districts in this read')).toBeInTheDocument();
    expect(screen.getByText('not recorded')).toBeInTheDocument();
  });

  it('moves one selected option at a time in a segmented control', async () => {
    const changes: string[] = [];
    render(
      <Segmented
        label="Register"
        options={[{ value: 'brief', label: 'Brief' }, { value: 'full', label: 'Full evidence' }]}
        value="brief"
        onChange={value => changes.push(value)}
      />,
    );
    await userEvent.click(screen.getByRole('tab', { name: 'Full evidence' }));
    expect(changes).toEqual(['full']);
    expect(screen.getByRole('tab', { name: 'Brief' })).toHaveAttribute('aria-selected', 'true');
  });

  it('announces a toast as chrome, in the caller words', async () => {
    function Host() {
      const toast = useToast();
      return (
        <>
          <Button onClick={() => toast.push('Copied the receipt.', 'good')}>Copy</Button>
          <Button onClick={() => toast.push('The read refused.', 'alert')}>Refuse</Button>
        </>
      );
    }
    render(<ToastHost><Host /></ToastHost>);
    await userEvent.click(screen.getByRole('button', { name: 'Copy' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Copied the receipt.');
    await userEvent.click(screen.getByRole('button', { name: 'Refuse' }));
    const lines = await screen.findAllByRole('status');
    expect(lines.map(line => line.textContent)).toEqual(['Copied the receipt.', 'The read refused.']);
    /* Retirement is a 4.2 s timeout, so it is not awaited here: the host keeps the last four messages
       and drops them by id, which is the part a caller can observe without holding the clock. */
  });
});
