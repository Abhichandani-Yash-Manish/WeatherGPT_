/* The place's own page: what it states, what it refuses, and how a reader reaches it.
   ============================================================================
   Three rules the batch asked to be held, each checked here rather than described:
     1. the address rule — a name and a coordinate pair that parse as numbers and fall inside the world, or
        nothing at all is applied, and no read is made for a refused address;
     2. a place with nothing published says so in words, and never renders a zero, a dash or an empty list
        that a reader could take for a value;
     3. every block keeps the source line the payload carried, and the panel that holds a place can send a
        reader to the page while the link docs/115 recorded keeps working. */

import type { ReactElement } from 'react';
import { render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';
import { server } from '../test/msw';
import { App } from '../App';
import { ReadingPanel } from '../gpt/ReadingPanel';
import { PLACE_KEY, rememberPlace } from '../modules/Evidence';
import { PlacePage, type PlaceParams } from './PlacePage';
import { readPlaceAddress } from './place';

const KOCHI: PlaceParams = { label: 'Kochi, Kerala', latitude: '9.93', longitude: '76.26' };

function envelope(data: Record<string, unknown>, extra: Record<string, unknown> = {}) {
  return { schema_version: 'product-view-v1', view: 'x', status: 'ok', data, sources: [], ...extra };
}

const EMPTY_LEDGER = { schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] };

function servePlace() {
  server.use(
    http.get('/api/now', () => HttpResponse.json(envelope({
      point: { latitude: 9.93, longitude: 76.26, label: 'Kochi, Kerala' },
      observed: {
        status: 'ok',
        stations: [{
          name: 'KOCHI', source_id: 'S63', observed_at_utc: '2026-09-19T06:30:00+00:00', distance_km: 4.2,
          parameters: [{ field: 'temp', value: 29, unit: '°C' }, { field: 'weather', value: 'Haze' }],
        }],
      },
    }))),
    http.get('/api/warnings/place', () => HttpResponse.json(envelope(
      { district: 'Ernakulam', state: 'Kerala', issued_at_utc: '2026-09-19T03:00:00+00:00',
        days: [{ date_local: '2026-09-19', label: 'Day 1', colour: 'yellow', hazards: ['Heavy rain'] }] },
      { sources: [{ source_id: 'S15', layer: 'imd:district_warnings_india' }] },
    ))),
    http.get('/api/forecast', () => HttpResponse.json(envelope({
      rows: [{ at: '2026-09-19T09:00:00+05:30', temperature_2m: 30, precipitation_probability: 80 }],
      unit: { temperature_2m: '°C', precipitation_probability: '%' },
      source_id: 'S21', model: 'GFS', starts: '2026-09-19T09:00:00+05:30', ends: '2026-09-21T09:00:00+05:30',
    }))),
    http.get('/api/conversations', () => HttpResponse.json({
      schema_version: 'conversation-ledger-v1', total: 1, limit: 40,
      conversations: [{
        id: 'c1', updated: '2026-09-19T06:00:00+00:00', turns: 2, asked: 1,
        opening_question: 'Will it rain in Kochi?',
        place: { label: 'Kochi, Kerala', latitude: 9.93, longitude: 76.26 },
      }],
    })),
  );
}

function mount(node: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const sectionWith = (label: string) => {
  const heading = screen.getByText(label);
  const section = heading.closest('section');
  if (!section) throw new Error('no section carries ' + label);
  return section;
};

beforeEach(() => {
  window.localStorage.clear();
});

describe("the place's own page", () => {
  it('states the place with the station, the published district day and the model hours, each with its own source', async () => {
    servePlace();
    mount(<PlacePage params={KOCHI} />);

    expect(await screen.findByRole('heading', { name: 'Kochi, Kerala' })).toBeInTheDocument();
    /* The point and where it came from: the address's own words, not a place resolved from a question. */
    expect(screen.getByText(/Latitude 9\.93, longitude 76\.26/)).toBeInTheDocument();
    expect(screen.getByText(/not resolved from the wording of a question/)).toBeInTheDocument();

    /* The station that answered: its own name, the source id the payload carried, and how far away it is. */
    const station = sectionWith('The nearest station');
    expect(await within(station).findByText(/KOCHI · S63 · read /)).toBeInTheDocument();
    expect(station.textContent).toContain('4.2 km away');
    expect(station.textContent).toContain('29');
    expect(station.textContent).toContain('°C');
    expect(station.textContent).toContain('Haze');

    /* What is published for the district: the colour the product printed, the hazard wording, and the
       registered source it came through. */
    const district = sectionWith('Published for this district');
    expect(await within(district).findByText('yellow')).toBeInTheDocument();
    expect(within(district).getByText('Heavy rain')).toBeInTheDocument();
    expect(within(district).getByText(/Ernakulam, Kerala · issued/)).toBeInTheDocument();
    expect(within(district).getByText('S15 imd:district_warnings_india')).toBeInTheDocument();

    /* The hours the model returned, with the unit the payload stated under its own source line. */
    const hours = sectionWith('The next hours');
    expect(await within(hours).findByText(/S21 · GFS · /)).toBeInTheDocument();
    expect(hours.textContent).toContain('30');
    expect(hours.textContent).toContain('°C');
    expect(hours.textContent).toContain('80');
    expect(hours.textContent).toContain('% rain chance');

    /* The stored conversations whose own answers resolved this place, linked back to the conversation. */
    expect(await screen.findByRole('link', { name: 'Will it rain in Kochi?' }))
      .toHaveAttribute('href', '#/assistant?conversation=c1');
    expect(sectionWith('This machine’s conversations about this place').textContent).toContain('2 turns');

    /* The way back to the conversation about this place carries the place in its own address. */
    const ask = screen.getByRole('link', { name: 'Ask about this place' });
    expect(ask.getAttribute('href')).toContain('#/assistant?');
    expect(ask.getAttribute('href')).toContain('plat=9.93');
    expect(readPlaceAddress(new URLSearchParams(String(ask.getAttribute('href')).split('?')[1])).place)
      .toEqual({ label: 'Kochi, Kerala', latitude: 9.93, longitude: 76.26 });

    /* Arriving here holds the place, exactly as the assistant link does. */
    expect(JSON.parse(String(window.localStorage.getItem(PLACE_KEY))).label).toBe('Kochi, Kerala');
  });

  it('says what is missing in words when every read comes back empty, and never draws a zero', async () => {
    server.use(
      http.get('/api/now', () => HttpResponse.json(envelope({
        point: { latitude: 9.93, longitude: 76.26, label: 'Kochi, Kerala' },
        observed: { status: 'ok', stations: [] },
      }))),
      http.get('/api/warnings/place', () => HttpResponse.json(envelope({ district: null, state: null, days: [] }))),
      http.get('/api/forecast', () => HttpResponse.json(envelope({ rows: [] }))),
      http.get('/api/conversations', () => HttpResponse.json(EMPTY_LEDGER)),
    );
    const { container } = mount(<PlacePage params={KOCHI} />);

    expect(await screen.findByText(/returned no station for the point/)).toBeInTheDocument();
    expect(await screen.findByText(/published no day for this district, which is not the same as a quiet one/)).toBeInTheDocument();
    expect(await screen.findByText(/no hourly row for the point/)).toBeInTheDocument();
    expect(await screen.findByText(/holds no conversation whose own answers resolved “Kochi, Kerala”/)).toBeInTheDocument();

    /* No hazard chip at all — and no value-shaped number anywhere: a missing state is not a zero, a dash or
       an empty list on this page. */
    expect(container.querySelector('.wchip')).toBeNull();
    expect(container.textContent).not.toMatch(/\d+\s?(°C|mm|%|km|turn)/);
  });

  const REFUSALS: [string, PlaceParams, RegExp][] = [
    ['an address with no name', { label: null, latitude: '9.93', longitude: '76.26' }, /names no place/],
    ['an address with one coordinate', { label: 'Kochi, Kerala', latitude: '9.93', longitude: null }, /half-written/],
    ['coordinates that are not numbers', { label: 'Kochi, Kerala', latitude: '9.93N', longitude: '76.26' }, /not a number/],
    ['a point outside the world', { label: 'Kochi, Kerala', latitude: '91', longitude: '76.26' }, /outside the world/],
  ];

  it.each(REFUSALS)('refuses %s, reads nothing and holds nothing', async (_name, params, sentence) => {
    const reads: string[] = [];
    server.use(
      http.get('/api/now', () => { reads.push('now'); return HttpResponse.json(envelope({})); }),
      http.get('/api/warnings/place', () => { reads.push('warnings'); return HttpResponse.json(envelope({ days: [] })); }),
      http.get('/api/forecast', () => { reads.push('forecast'); return HttpResponse.json(envelope({ rows: [] })); }),
      http.get('/api/conversations', () => { reads.push('conversations'); return HttpResponse.json(EMPTY_LEDGER); }),
    );
    mount(<PlacePage params={params} />);

    expect(await screen.findByRole('heading', { name: 'No place to show' })).toBeInTheDocument();
    /* The refusal sentence is the page's own answer; the paragraph under it is the standing rule, and its
       wording repeats some of the same words, so the sentence is read where it is stated rather than by text. */
    expect(document.querySelector('.g-hero-sub')?.textContent || '').toMatch(sentence);
    expect(document.querySelector('.g-side-note')?.textContent || '').toMatch(/refused rather than half-applied/);
    expect(screen.getByRole('link', { name: /Back to the conversation/ })).toHaveAttribute('href', '#/assistant');
    /* Refused means refused: no station, district, hour or store read was made for the address, and the place
       this browser holds was not overwritten with half of one. */
    expect(reads).toEqual([]);
    expect(window.localStorage.getItem(PLACE_KEY)).toBeNull();
  });

  it('lets the reading panel send a reader to the page, with the place in the address', async () => {
    server.use(http.get('/api/now', () => HttpResponse.json(envelope({
      point: { latitude: 25.59, longitude: 85.14, label: 'Patna, Bihar' },
      observed: { status: 'ok', stations: [{ name: 'PATNA', source_id: 'S63', parameters: [] }] },
    }))));
    /* The place this browser holds, set the way the picker and the rail set it. */
    rememberPlace({ label: 'Patna, Bihar', latitude: 25.59, longitude: 85.14 });
    mount(
      <ReadingPanel
        sources={[]} language="" onLanguage={() => {}} persona="" onPersona={() => {}} personas={[]}
        onFindPlace={() => {}} onOpenView={() => {}} onClose={() => {}}
      />,
    );

    const link = await screen.findByRole('link', { name: /place’s own page/ });
    const href = String(link.getAttribute('href'));
    expect(href.startsWith('#/place?')).toBe(true);
    /* The link the panel offers is an address the page itself accepts: the same three names, read by the
       same rule. */
    expect(readPlaceAddress(new URLSearchParams(href.split('?')[1])).place)
      .toEqual({ label: 'Patna, Bihar', latitude: 25.59, longitude: 85.14 });
  });

  it('is the shell route a place link lands on, and it names itself in the tab', async () => {
    servePlace();
    window.location.hash = '#/place?place=Kochi%2C+Kerala&plat=9.93&plon=76.26';
    mount(<App />);

    expect(await screen.findByRole('heading', { name: 'Kochi, Kerala' })).toBeInTheDocument();
    expect(document.title).toBe('WeatherGPT — Kochi, Kerala');
    /* The page is a destination, not the conversation: no question box, and the main landmark is the page's
       own — this shell route has no rail to skip past, so it carries no skip link (neither the front door nor
       the owner gate does). */
    expect(screen.queryByLabelText('Your question')).toBeNull();
    expect(screen.queryByTestId('skip-links')).toBeNull();
    expect(document.getElementById('main')).not.toBeNull();
  });

  it('refuses a half-written address through the shell route rather than falling back to the conversation', async () => {
    window.location.hash = '#/place?place=Kochi%2C+Kerala&plat=9.93N&plon=76.26';
    mount(<App />);

    expect(await screen.findByRole('heading', { name: 'No place to show' })).toBeInTheDocument();
    expect(screen.getByText(/not a number/)).toBeInTheDocument();
    expect(document.title).toBe('WeatherGPT — no place to show');
  });
});
