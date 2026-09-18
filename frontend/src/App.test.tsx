import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';
import { forgetOwner } from './landing/owner';

/* The shell's own contract: the front door, the workspace behind it, each route's own surface with the
   conversation beside it, and the gate that is described before it asks for anything. */
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

  it('shows the front door at an empty address, with one way in and a computed light', () => {
    render(<App />);
    /* The one way in is the reader's own question box. The front door no longer offers a second door
       beside it: the conversation is the product, so the box is the door. */
    expect(screen.getByLabelText('Your question')).toBeInTheDocument();
    /* Paper, ink and the published colours: no photograph, no canvas, nothing that needs a disclaimer. */
    expect(document.querySelector('[data-design="gpt"]')).not.toBeNull();
    /* The field is one canvas painted from the hour. No photograph is ever fetched. */
    expect(document.querySelector('img')).toBeNull();
    expect(document.querySelector('canvas.g-field-canvas')).not.toBeNull();
  });

  it('hands the front door question to the conversation', async () => {
    const { http, HttpResponse } = await import('msw');
    const { server } = await import('./test/msw');
    /* The question is taken by the conversation rather than carried somewhere else, so the send is answered
       here: a test that passes while printing unhandled-request noise is not evidence. */
    server.use(http.post('/api/chat', () => HttpResponse.json({ error: 'the engine is not part of this check' }, { status: 503 })));
    render(<App />);
    await userEvent.type(screen.getByLabelText('Your question'), 'Will it rain in Surat tomorrow?');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));
    /* The page is the conversation, so asking stays on the page: the reader's own words appear in the
       transcript instead of the app navigating to a different surface. */
    expect(window.location.hash).toBe('');
    const asked = await screen.findAllByText(/Will it rain in Surat tomorrow\?/);
    expect(asked.length).toBeGreaterThan(0);
  });

  /* The rail of eighteen peer surfaces is gone: a module now opens **beside** the conversation, in the same
     frame, and the reader never loses the thread by looking something up. What the rail used to guarantee —
     that a route renders its surface — is what this test keeps. */
  it('renders the surface the address names, with the conversation still beside it', async () => {
    window.location.hash = '#/assistant';
    render(<App />);
    expect(screen.getByLabelText('Your question')).toBeInTheDocument();

    window.location.hash = '#/climate';
    render(<App />);
    const modules = await screen.findAllByRole('region', { name: 'Climate records surface' });
    expect(modules.length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText('Your question').length).toBeGreaterThan(0);
  });

  it('names the surface in the tab, the history entry and a bookmark', async () => {
    window.location.hash = '#/warnings';
    render(<App />);
    await waitFor(() => expect(document.title).toBe('WeatherGPT — Warnings'));
    window.location.hash = '';
    render(<App />);
    await waitFor(() => expect(document.title).toBe('WeatherGPT'));
  });


  it('opens the plans panel from a ?watch= deep link, so a notification can land on what it is about', async () => {
    window.location.hash = '#/assistant?watch=w1';
    render(<App />);
    expect(await screen.findByRole('heading', { level: 2, name: /Plans, watches and the notification inbox/ })).toBeInTheDocument();
  });


  it('opens a stored conversation named in the address', async () => {
    const { http, HttpResponse } = await import('msw');
    const { server } = await import('./test/msw');
    server.use(
      http.get('/api/conversations/:id', () =>
        HttpResponse.json({ schema_version: 'conversation-transcript-v1', id: '11111111-1111-4111-8111-111111111111',
          updated: '2026-09-17T10:00:00+00:00', turns: [
            { role: 'user', content: 'Will it rain in Surat tomorrow?' },
            { role: 'assistant', content: 'Surat: forecast precipitation 0.3 mm.' },
          ], note: 'Restored transcript.' })),
    );
    window.location.hash = '#/assistant?conversation=11111111-1111-4111-8111-111111111111';
    render(<App />);
    expect(await screen.findByText(/Surat: forecast precipitation 0.3 mm/)).toBeInTheDocument();
  });

  it('honours a deep link, and keeps the conversation available beside the module', async () => {
    window.location.hash = '#/marine';
    render(<App />);
    expect(await screen.findByRole('region', { name: 'Sea and rivers surface' })).toBeInTheDocument();
    /* Beside, never instead of: the question box is still there to ask about what is on the screen. */
    expect(screen.getByLabelText('Your question')).toBeInTheDocument();
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
    await userEvent.click(screen.getByRole('button', { name: 'Owner gate' }));
    expect(window.location.hash).toBe('#/signin');
    await waitFor(() => expect(screen.getByText(/not authentication/i)).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Skip/i })).toBeInTheDocument();
  });
});
