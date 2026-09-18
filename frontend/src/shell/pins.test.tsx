/* Pinned places. The vanilla component check (tests/test_suite_ui.js, check 27) held a local shortlist
   of places — remembered in the browser, removable, and refusing a place that has no coordinates — and
   that shortlist was also reachable from the shell. This spec holds the React shell's own list, the pin
   control the place rows carry, and the refusal, against the place payload the route returns. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { PIN_KEY, PinPlaceButton, PinnedPlaces, pinPlace, readPins } from '../modules/Evidence';
import { Surface as BriefcaseSurface } from '../modules/BriefcaseSurface';

const PINNED = { label: 'Kochi, Kerala', latitude: 9.93, longitude: 76.27 };

const placeRow = {
  label: 'AHMADABAD',
  latitude: 23.02579,
  longitude: 72.58727,
  admin1: 'Gujarat',
  admin2: 'Ahmadabad',
  selection_id: 'geonames:1279233',
};

/* The recorded /api/places/search payload: a row states its own label and coordinates, and a pin keeps
   exactly those two things. */
function placesPayload() {
  return {
    schema_version: 'product-view-v1', view: 'places.search', status: 'ok', data: { matches: [placeRow] },
    sources: [], limitations: [], not_established: [],
  };
}

const briefsPayload = {
  schema_version: 'briefcase-v1', delivery: 'local_only_no_delivery',
  note: 'Kept in the local store. Nothing is delivered, pushed or published from here.',
  briefs: [],
};

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

describe('pinned places', () => {
  beforeEach(() => {
    window.location.hash = '#/assistant';
    try {
      window.localStorage.clear();
    } catch {
      /* storage is optional */
    }
  });

  it('lists the places this browser remembers in the shell, and removes one when the reader asks', async () => {
    window.localStorage.setItem(PIN_KEY, JSON.stringify([PINNED]));
    mount(<PinnedPlaces />);

    const panel = screen.getByTestId('pinned-places');
    expect(within(panel).getByText('Kochi, Kerala')).toBeInTheDocument();
    expect(within(panel).getByText('9.93, 76.27')).toBeInTheDocument();

    await userEvent.click(within(panel).getByRole('button', { name: 'Remove pin Kochi, Kerala' }));
    expect(within(panel).getByTestId('pinned-places-empty')).toHaveTextContent('No place is pinned in this browser yet');
    expect(readPins()).toEqual([]);
    expect(window.localStorage.getItem(PIN_KEY)).toBe('[]');
  });

  it('pins the place a read resolved, keeps only its name and coordinates, and remembers it in this browser', async () => {
    server.use(
      http.get('/api/briefs', () => HttpResponse.json(briefsPayload)),
      http.get('/api/places/search', () => HttpResponse.json(placesPayload())),
      http.get('/api/briefing/latest', () => HttpResponse.json({
        schema_version: 'briefing-latest-v1', present: false, directory: '/tmp/briefings',
        detail: 'No briefing has been written to this series directory yet.',
      })),
    );
    mount(
      <>
        <PinnedPlaces />
        <BriefcaseSurface />
      </>,
    );

    await userEvent.type(await screen.findByLabelText('Name a place'), 'AHMADABAD');
    await userEvent.click(await screen.findByRole('button', { name: /AHMADABAD · Ahmadabad, Gujarat/ }));
    const point = await screen.findByTestId('briefcase-point');
    expect(point).toHaveTextContent('23.02579, 72.58727');

    const pointPin = screen
      .getAllByRole('button', { name: 'Pin this place' })
      .find(button => button.getAttribute('aria-describedby') === 'briefcase-point-facts');
    expect(pointPin, 'the resolved point offers a pin control').toBeTruthy();
    await userEvent.click(pointPin!);

    expect(readPins()).toEqual([{ label: 'AHMADABAD', latitude: 23.02579, longitude: 72.58727 }]);
    const stored: unknown = JSON.parse(window.localStorage.getItem(PIN_KEY) || '[]');
    expect(stored).toEqual([{ label: 'AHMADABAD', latitude: 23.02579, longitude: 72.58727 }]);

    const panel = screen.getByTestId('pinned-places');
    expect(within(panel).getByText('AHMADABAD')).toBeInTheDocument();
    /* The row the reader chose and the resolved point the brief read are offered by the same control
       over the same local list: both read the pin just stored. */
    expect(screen.getAllByRole('button', { name: 'Unpin this place' })).toHaveLength(2);
    await userEvent.click(within(panel).getByRole('button', { name: 'Remove pin AHMADABAD' }));
    expect(within(panel).getByTestId('pinned-places-empty')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Pin this place' })).toHaveLength(2);
  });

  it('refuses a place the record did not give coordinates for, so a pin can never invent a location', () => {
    mount(<PinPlaceButton place={{ label: 'Nowhere', latitude: null, longitude: null }} />);

    expect(screen.getByText(/cannot be pinned: a pin is never guessed/)).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
    expect(pinPlace({ label: 'Nowhere', latitude: null, longitude: null })).toEqual([]);
    expect(readPins()).toEqual([]);
    expect(window.localStorage.getItem(PIN_KEY)).toBeNull();
  });

  it('states that a pin is a shortcut to a place name, never a saved answer or a claim about it', () => {
    mount(<PinnedPlaces />);

    const panel = screen.getByTestId('pinned-places');
    expect(panel).toHaveTextContent('A pin is a shortcut to a place name you resolved.');
    expect(panel).toHaveTextContent('It saves no answer and makes no claim about the place');
    expect(panel).toHaveTextContent("kept in this browser's local storage and sent nowhere");
    expect(within(panel).getByTestId('pinned-places-empty')).toBeInTheDocument();
  });
});
