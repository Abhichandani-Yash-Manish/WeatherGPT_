import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';
import { VIEWS } from './shell/views';

describe('the R1 shell', () => {
  beforeEach(() => {
    window.location.hash = '';
  });

  it('renders the rail from the registry and lands on Ask', () => {
    render(<App />);
    const rail = within(screen.getByRole('navigation', { name: 'Workspace navigation' }));
    for (const view of VIEWS) {
      // Scoped to the rail, and anchored: the composer also has a button called Ask, and "Forecast"
      // is a prefix of "Forecast verification", so a loose pattern would match two entries.
      expect(rail.getByRole('button', { name: new RegExp('^' + view.label + '( ⌥[1-9])?$') })).toBeInTheDocument();
    }
    expect(screen.getByLabelText('Your question')).toBeInTheDocument();
    expect(screen.getByTestId('r1-note')).toHaveTextContent(/not wired yet/i);
  });

  it('opens a module from the rail, and the route decides the surface', async () => {
    render(<App />);
    const rail = within(screen.getByRole('navigation', { name: 'Workspace navigation' }));
    await userEvent.click(rail.getByRole('button', { name: /Warnings/ }));
    expect(window.location.hash).toBe('#/warnings');
    const surface = document.querySelector('[data-surface="warnings"]');
    expect(surface).not.toBeNull();
    expect(surface?.textContent).toMatch(/not ported yet/i);
    expect(surface?.textContent).toMatch(/R3/);
  });

  it('keeps the keyboard shortcut contract the rail prints', async () => {
    render(<App />);
    await userEvent.keyboard('{Alt>}2{/Alt}');
    expect(window.location.hash).toBe('#/overview');
  });

  it('honours a deep link instead of overriding it', () => {
    window.location.hash = '#/settings';
    render(<App />);
    expect(document.querySelector('[data-surface="settings"]')).not.toBeNull();
    expect(screen.queryByLabelText('Your question')).toBeNull();
  });
});
