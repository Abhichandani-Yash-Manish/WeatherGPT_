import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';
import { VIEWS } from './shell/views';
import { forgetOwner } from './landing/owner';

/* The shell's own contract: the front door, the workspace behind it, the rail from the registry, the
   keyboard contract the rail prints, and the gate that is described before it asks for anything. */
describe('the shell', () => {
  beforeEach(() => {
    window.location.hash = '';
    try {
      window.localStorage.clear();
    } catch {
      /* storage is optional */
    }
    forgetOwner();
  });

  it('shows the front door at an empty address, and one way in', () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Open the workspace/i })).toBeInTheDocument();
  });

  it('opens the workspace from the front door, with the question box ready', async () => {
    render(<App />);
    await userEvent.click(screen.getByRole('button', { name: /Open the workspace/i }));
    expect(window.location.hash).toBe('#/assistant');
    expect(await screen.findByLabelText('Your question')).toBeInTheDocument();
  });

  it('renders the rail from the registry and lands on Ask for its own route', async () => {
    window.location.hash = '#/assistant';
    render(<App />);
    const rail = within(screen.getByRole('navigation', { name: 'Workspace navigation' }));
    for (const view of VIEWS) {
      expect(rail.getByRole('button', { name: new RegExp('^' + view.label + '( ⌥[1-9])?$') })).toBeInTheDocument();
    }
    expect(screen.getByLabelText('Your question')).toBeInTheDocument();
  });

  it('names the surface in the tab, the history entry and a bookmark', async () => {
    window.location.hash = '#/warnings';
    render(<App />);
    await waitFor(() => expect(document.title).toBe('WeatherGPT — Warnings'));
    window.location.hash = '';
    render(<App />);
    await waitFor(() => expect(document.title).toMatch(/evidence-first weather/));
  });


  it('opens the plans panel from a ?watch= deep link, so a notification can land on what it is about', async () => {
    window.location.hash = '#/assistant?watch=w1';
    render(<App />);
    expect(await screen.findByRole('heading', { level: 2, name: /Plans, watches and the notification inbox/ })).toBeInTheDocument();
  });

  it('keeps the keyboard shortcut contract the rail prints', async () => {
    window.location.hash = '#/assistant';
    render(<App />);
    await userEvent.keyboard('{Alt>}2{/Alt}');
    expect(window.location.hash).toBe('#/overview');
  });

  it('honours a deep link instead of overriding it', () => {
    window.location.hash = '#/marine';
    render(<App />);
    expect(document.querySelector('[data-surface="marine"]')).not.toBeNull();
    expect(screen.queryByLabelText('Your question')).toBeNull();
  });

  it('opens the command palette from the keyboard and names every surface', async () => {
    window.location.hash = '#/assistant';
    render(<App />);
    await userEvent.keyboard('{Alt>}k{/Alt}');
    const palette = await screen.findByRole('dialog', { name: 'Command palette' });
    expect(within(palette).getByRole('option', { name: /Open Warnings/ })).toBeInTheDocument();
    expect(within(palette).getByRole('option', { name: /Start a new conversation/ })).toBeInTheDocument();
  });

  it('sends the interface to the owner gate on request, and the gate explains itself first', async () => {
    window.location.hash = '#/assistant';
    render(<App />);
    await userEvent.click(screen.getByRole('button', { name: 'Lock' }));
    expect(window.location.hash).toBe('#/signin');
    await waitFor(() => expect(screen.getByText(/not authentication/i)).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Skip/i })).toBeInTheDocument();
  });
});
