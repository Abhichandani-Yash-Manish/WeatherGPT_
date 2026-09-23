import { render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Workspace } from '../gpt/Workspace';
import { PLACE_KEY } from '../modules/Evidence';

/* The front door is the conversation, so these pin the ways it can lie:
   ----------------------------------------------------------------------------
   1. Briefing a reader who asked nothing — the welcome states the reader's own sky, and the national count
      belongs to the Warnings home. The overview is not read here at all, and msw answers an unhandled
      request with a failure, so the missing handler is part of the check.
   2. Drawing weather nothing printed — with no place held there is no condition mark, no condition word and
      no number; the mark is the hour, which is astronomy.
   3. Losing the source — a condition a station printed arrives with the station, its id and its read time,
      or it does not arrive.
   4. Drawing a picture — the ground is CSS layers keyed to the hour, and no image or canvas is fetched.

   The national picture's own rules — an absent today block is not a quiet day, a number no read produced is
   never printed, every count carries the read time — moved with the picture itself when it left this screen.
   They are checked where the sentence is built, in national.test.ts. */

function envelope(data: Record<string, unknown>, status = 'ok') {
  return {
    schema_version: 'product-view-v1',
    view: 'now.composed',
    status,
    generated_at_utc: '2026-09-19T06:30:00+00:00',
    data,
    sources: [],
  };
}

/* A station that printed its own weather field, as GET /api/now returns one. */
function station(fields: { field: string; value: unknown; unit?: string | null }[]) {
  return envelope({
    schema_version: 'now-v1',
    point: { latitude: 23.0225, longitude: 72.5714, label: 'Ahmedabad, Gujarat' },
    observed: {
      status: 'ok',
      stations: [{
        kind: 'metar', name: 'AHMEDABAD', station_code: 'VAAH',
        observed_at_utc: '2026-09-19T06:30:00+00:00', distance_km: 8.8, source_id: 'S63', stale: false,
        parameters: fields,
      }],
    },
  });
}

function holdAPlace() {
  window.localStorage.setItem(PLACE_KEY, JSON.stringify({ label: 'Ahmedabad, Gujarat', latitude: 23.0225, longitude: 72.5714 }));
}

function renderFrontDoor() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <Workspace onOpen={() => {}} language="" onLanguage={() => {}} persona="" onPersona={() => {}} />
    </QueryClientProvider>,
  );
}

describe('the front door', () => {
  beforeEach(() => {
    try {
      window.localStorage.clear();
    } catch {
      /* storage is optional */
    }
  });

  it('asks for a question instead of briefing the reader, and never reads the national picture for it', async () => {
    renderFrontDoor();
    expect(await screen.findByTestId('welcome')).toBeInTheDocument();
    /* The one way in is the reader's own question box. */
    expect(screen.getByLabelText('Your question')).toBeInTheDocument();
    /* No count is printed because no count was asked for: not a quiet day, and not a zero. */
    expect(screen.queryByText(/districts are under|carry a yellow caution|does not state today|could not be read/i)).toBeNull();
  });

  it('draws no condition and prints no number when no place is held', async () => {
    renderFrontDoor();
    await screen.findByTestId('welcome');
    /* The mark is the hour — astronomy — and it is marked as such. */
    expect(document.querySelector('.w-glyph')?.getAttribute('data-kind')).toBe('hour');
    /* Nothing invented: no condition word, no temperature, no source line. */
    expect(document.querySelector('.w-reading')).toBeNull();
    expect(document.querySelector('.w-source')).toBeNull();
  });

  it('draws a station\'s own condition only when the station printed one, with its read time', async () => {
    holdAPlace();
    server.use(http.get('/api/now', () => HttpResponse.json(station([
      { field: 'temp', value: 29, unit: null },
      { field: 'weather', value: 'haze', unit: null },
    ]))));
    renderFrontDoor();
    const welcome = await screen.findByTestId('welcome');
    /* The station's own word, the station's own number, and the read time on it. The word appears twice by
       design — once as the reading, once in the bar as the place the answers are about — so the reading is
       read from the welcome itself. */
    expect(await within(welcome).findByText('haze')).toBeInTheDocument();
    expect(within(welcome).getByText('29')).toBeInTheDocument();
    expect(document.querySelector('.w-glyph')?.getAttribute('data-kind')).toBe('condition');
    const source = document.querySelector('.w-source');
    expect(source?.textContent).toContain('AHMEDABAD');
    expect(source?.textContent).toContain('S63');
    expect(source?.textContent).toContain('read 19 Sep 2026, 12:00 IST');
    /* The unit was not in the source, so no unit is printed and the absence is said. */
    expect(source?.textContent).toContain('no unit stated by the source');
    expect(document.querySelector('.w-unit')).toBeNull();
  });

  it('prints a station\'s unit when the source stated one', async () => {
    holdAPlace();
    server.use(http.get('/api/now', () => HttpResponse.json(station([
      { field: 'temp', value: 29, unit: '°C' },
      { field: 'weather', value: 'thunderstorm', unit: null },
    ]))));
    renderFrontDoor();
    const welcome = await screen.findByTestId('welcome');
    expect(await within(welcome).findByText('thunderstorm')).toBeInTheDocument();
    expect(document.querySelector('.w-unit')?.textContent).toBe('°C');
    expect(document.querySelector('.w-source')?.textContent).not.toContain('no unit stated by the source');
    expect(document.querySelector('.w-glyph')?.getAttribute('data-kind')).toBe('condition');
  });

  it('keeps the selected light ground decorative', async () => {
    renderFrontDoor();
    await screen.findByTestId('welcome');
    /* Meridian supersedes the solar glass direction. The atmosphere is DRAWN now - a contour field and a
       geostrophic flow on two canvases - rather than a raster of one, so what this pins is the property
       that mattered about the image and matters more about a moving field: it is decoration, it is inside
       an aria-hidden subtree, and it offers a screen reader nothing to announce and nothing to mistake for
       a reading. A canvas with a role or a label would be a weather map, and this is not one. */
    expect(document.querySelector('[data-design="meridian"]')).not.toBeNull();
    const atmosphere = [...document.querySelectorAll('canvas.g-skyfield, canvas.g-skywind')];
    expect(atmosphere.length).toBeGreaterThan(0);
    atmosphere.forEach(layer => {
      expect(layer.closest('[aria-hidden="true"]')).not.toBeNull();
      expect(layer.getAttribute('role')).toBeNull();
      expect(layer.getAttribute('aria-label')).toBeNull();
      expect(layer.textContent).toBe('');
    });
    expect(screen.queryByText(/condition report/i)).toBeNull();
  });

  it('moves the ground when a station printed a condition, and leaves it alone when it did not', async () => {
    holdAPlace();
    server.use(http.get('/api/now', () => HttpResponse.json(station([{ field: 'weather', value: 'light rain', unit: null }]))));
    renderFrontDoor();
    await within(await screen.findByTestId('welcome')).findByText('light rain');
    /* A condition reaches the ground as a token, never as a drawn picture of the weather. */
    expect(document.querySelector('.g-field')?.getAttribute('data-sky')).toBe('rain');
  });
});
