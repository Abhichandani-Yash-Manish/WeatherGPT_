/* View transitions on a route change. The vanilla component check (tests/test_suite_ui.js, check 26)
   held that a surface change is offered as a view transition when the document has the API, and that
   without the API the surface still renders with no transition attempted. This spec holds the React
   route: the shell's own surface swap, driven by the address. */
import { act, render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { App } from '../App';

/* jsdom does not implement the View Transition API, so the document is given one here when the check
   needs it and the property is removed again afterwards. Object.defineProperty and Reflect keep this a
   property on the object under test rather than a typed method the DOM types insist must exist. */
function installTransition(handler: (callback: () => void) => unknown) {
  Object.defineProperty(document, 'startViewTransition', { configurable: true, value: handler });
}

function removeTransition() {
  Reflect.deleteProperty(document, 'startViewTransition');
}

const offersTransition = () => typeof (document as { startViewTransition?: unknown }).startViewTransition === 'function';

/* The Warnings surface is the route the transition starts from, so its one read is recorded here. */
const WARNINGS = {
  schema_version: 'product-view-v1', view: 'warnings.national', status: 'ok',
  data: { districts: [], tally: {}, skipped: [] },
  sources: [], coverage: {}, limitations: [], not_established: [],
};

async function changeRoute(hash: string) {
  await act(async () => {
    window.location.hash = hash;
  });
}

describe('view transitions on a route change', () => {
  beforeEach(() => {
    server.use(http.get('/api/warnings/national', () => HttpResponse.json(WARNINGS)));
    removeTransition();
    window.location.hash = '';
    try {
      window.localStorage.clear();
    } catch {
      /* storage is optional */
    }
  });

  afterEach(() => {
    removeTransition();
  });

  it('uses the document view transition for a route change when the browser offers it, and the surface still changes', async () => {
    window.location.hash = '#/warnings';
    render(<App />);
    await waitFor(() => expect(document.querySelector('[data-surface="warnings"]')).not.toBeNull());

    const attempts: string[] = [];
    let surfaceWhenCallbackReturned: string | null | undefined;
    installTransition(callback => {
      attempts.push('offered');
      callback();
      /* The swap has to be inside the callback, or the browser would capture the new surface as both
         the old and the new state and there would be nothing to transition between. */
      surfaceWhenCallbackReturned = document.querySelector('[data-surface]')?.getAttribute('data-surface');
    });

    await changeRoute('#/overview');
    await waitFor(() => expect(document.querySelector('[data-surface="overview"]')).not.toBeNull());
    expect(attempts).toEqual(['offered']);
    expect(surfaceWhenCallbackReturned).toBe('overview');
    expect(document.querySelector('[data-surface="warnings"]')).toBeNull();
  });

  it('changes the surface without attempting a transition when the browser has no such API', async () => {
    window.location.hash = '#/warnings';
    render(<App />);
    await waitFor(() => expect(document.querySelector('[data-surface="warnings"]')).not.toBeNull());
    expect(offersTransition()).toBe(false);

    await changeRoute('#/overview');
    await waitFor(() => expect(document.querySelector('[data-surface="overview"]')).not.toBeNull());
    expect(document.querySelector('[data-surface="warnings"]')).toBeNull();
    expect(offersTransition()).toBe(false);
  });

  it('offers no transition for shell state that is not a route change', async () => {
    window.location.hash = '#/assistant';
    render(<App />);
    await waitFor(() => expect(document.querySelector('[data-surface="assistant"]')).not.toBeNull());

    const attempts: string[] = [];
    installTransition(callback => {
      attempts.push('offered');
      callback();
    });

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', altKey: true }));
    });
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Command palette' })).toBeInTheDocument());
    expect(attempts).toEqual([]);
  });
});
