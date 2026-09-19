/* The nine component checks the deleted tests/test_viz.js held against the served chart engine, run here
   against the same bytes: this spec reads web/viz.js — the one tracked copy the React build is served at
   /viz.js — from disk and evaluates it in the stand-in DOM the vanilla suite used. Nothing is copied out of
   the engine, so these checks see a change to web/viz.js whenever one is made.

   What they pin is the honesty rule: a mark exists only where the engine returned a value, a missing hour
   stays a gap, and every drawn point carries its source locator. */

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createContext, runInContext } from 'node:vm';

const SVG_NS = 'http://www.w3.org/2000/svg';

/* Pure component stand-in: no browser, no layout, no pixels. `class` lands in className, attributes are
   readable as text, and listeners are recorded so a check can fire focus or click itself. */
class StandInNode {
  readonly tag: string;
  children: StandInNode[] = [];
  attrs: Record<string, string> = {};
  events: Record<string, Array<(event: unknown) => void>> = {};
  textContent = '';
  className = '';
  dataset: Record<string, string> = {};
  namespace?: string;
  href = '';
  target = '';
  rel = '';
  download = '';
  type = '';
  constructor(tag: string) { this.tag = tag; }
  append(...children: StandInNode[]) { this.children.push(...children); return children[0]; }
  setAttribute(key: string, value: unknown) { this.attrs[key] = String(value); if (key === 'class') this.className = String(value); }
  addEventListener(event: string, fn: (event: unknown) => void) { (this.events[event] = this.events[event] || []).push(fn); }
  all(tag: string): StandInNode[] { return [...(this.tag === tag ? [this] : []), ...this.children.flatMap(child => child.all(tag))]; }
  withClass(cls: string): StandInNode[] { return this.allNodes().filter(node => String(node.className).split(/\s+/).indexOf(cls) >= 0); }
  allNodes(): StandInNode[] { return [this, ...this.children.flatMap(child => child.allNodes())]; }
  focus() { (this.events.focus || []).forEach(fn => fn({})); }
  keydown(key: string) { (this.events.keydown || []).forEach(fn => fn({ key: key, preventDefault() {} })); }
}

const ENGINE = resolve(dirname(fileURLToPath(import.meta.url)), '../../../web/viz.js');
const sandbox = createContext({
  document: {
    createElement: (tag: string) => new StandInNode(tag),
    createElementNS: (namespace: string, tag: string) => {
      const node = new StandInNode(tag);
      node.namespace = namespace;
      return node;
    },
  },
});
runInContext(readFileSync(ENGINE, 'utf8'), sandbox);
const viz = sandbox.viz as any;

const hour = (index: number, value: string | null) => ({
  t: '2026-09-15T' + String(index % 24).padStart(2, '0') + ':00:00+00:00',
  label: '15 Sep ' + String(index % 24).padStart(2, '0') + ':30',
  value: value,
  source_locator: '$.hourly.x[' + index + ']',
});

describe('the served chart engine (the nine checks tests/test_viz.js held)', () => {
  it('draws the ensemble band, median, whiskers and exact member values from returned fields only', () => {
    const plume = viz.ensembleFan({
      title: 'temperature_2m member distribution', unit: '°C', member_total: 30,
      statistics: { mean: 'arithmetic mean of the returned perturbed members', spread: 'population standard deviation', percentile: 'nearest-rank on the sorted member values' },
      p10: [hour(0, '23.1'), hour(1, '23.4'), hour(2, null), hour(3, '24.0')],
      p50: [hour(0, '24.0'), hour(1, '24.2'), hour(2, '24.5'), hour(3, '25.1')],
      p90: [hour(0, '25.2'), hour(1, '25.6'), hour(2, null), hour(3, '26.3')],
      mean: [hour(0, '24.1'), hour(1, '24.3'), hour(2, '24.6'), hour(3, '25.2')],
      min: [hour(0, '22.0'), hour(1, '22.3'), hour(2, '22.9'), hour(3, '23.4')],
      max: [hour(0, '26.0'), hour(1, '26.2'), hour(2, '26.6'), hour(3, '27.0')],
    });
    expect(plume.withClass('viz-band')).toHaveLength(1);
    expect(plume.withClass('viz-band')[0].attrs.points.split(' ').filter(Boolean)).toHaveLength(4);
    expect(plume.withClass('viz-whisker')).toHaveLength(4);
    expect(plume.withClass('viz-median')).toHaveLength(1);
    expect(plume.withClass('viz-mean')).toHaveLength(1);
    expect(plume.all('td').some((cell: StandInNode) => cell.textContent === '24.5')).toBe(true);
    expect(plume.all('td').some((cell: StandInNode) => cell.textContent === 'missing')).toBe(true);
    const hit = plume.withClass('viz-hit')[0];
    hit.focus();
    const readout = plume.withClass('viz-readout')[0].textContent;
    expect(/p10 23\.1/.test(readout)).toBe(true);
    expect(/\$\.hourly\.x\[0\]/.test(readout)).toBe(true);
  });

  it('refuses to draw a distribution without member statistics', () => {
    const thin = viz.ensembleFan({ title: 'median only', unit: '°C', p50: [hour(0, '24.0')], mean: [], min: [], max: [], p10: [], p90: [] });
    expect(thin.withClass('viz-band')).toHaveLength(0);
    expect(thin.withClass('viz-median')).toHaveLength(0);
    expect(thin.withClass('viz-empty').length).toBeGreaterThanOrEqual(0);
  });

  it('draws only returned hours, splits gaps and reads exact values with locators (meteogram)', () => {
    const meteogram = viz.meteogram({
      title: 'Meteogram', temperature_unit: '°C', rain_unit: 'mm', wind_unit: 'km/h',
      hours: [
        { t: '2026-09-15T00:00:00+00:00', label: '15 Sep 05:30', temperature: 26.4, rain: 0, wind_speed: 8, wind_direction: 240, humidity: 71, night: true, evidence: { temperature: 't0', rain: 'r0', wind: 'w0' } },
        { t: '2026-09-15T01:00:00+00:00', label: '15 Sep 06:30', temperature: null, rain: 2.4, wind_speed: 9, wind_direction: 250, humidity: 74, night: false, evidence: { rain: 'r1', wind: 'w1' } },
        { t: '2026-09-15T02:00:00+00:00', label: '15 Sep 07:30', temperature: 27.1, rain: null, wind_speed: null, wind_direction: null, humidity: null, night: false, evidence: { temperature: 't2' } },
        { t: '2026-09-15T03:00:00+00:00', label: '15 Sep 08:30', temperature: 28.0, rain: 0.6, wind_speed: 12, wind_direction: 260, humidity: 68, night: false, evidence: { temperature: 't3', rain: 'r3', wind: 'w3' } },
      ],
    });
    expect(meteogram.withClass('viz-bar')).toHaveLength(2);
    expect(meteogram.withClass('viz-line')).toHaveLength(1);
    expect(meteogram.withClass('viz-line')[0].attrs.points.split(' ').filter(Boolean)).toHaveLength(2);
    expect(meteogram.withClass('viz-night').length).toBeGreaterThanOrEqual(1);
    expect(meteogram.all('td').some((cell: StandInNode) => cell.textContent === '0')).toBe(true);
    expect(meteogram.all('td').some((cell: StandInNode) => cell.textContent === 'missing')).toBe(true);
    meteogram.withClass('viz-hit')[1].focus();
    const readout = meteogram.withClass('viz-readout')[0].textContent;
    expect(/precipitation 2\.4 \(r1\)/.test(readout)).toBe(true);
    expect(/temperature missing|no value returned/.test(readout)).toBe(false);
  });

  it('carries source colours, flags unknown codes and prints nothing it was not given (warning matrix)', () => {
    let opened: unknown = null;
    const matrix = viz.warningMatrix({
      title: 'National district warning matrix',
      days: [{ key: 1, label: 'Day 1', date: '2026-09-14' }, { key: 2, label: 'Day 2', date: '2026-09-15' }],
      rows: [
        { district: 'PATNA', state: 'BIHAR', days: [
            { colour: 'yellow', hazards: ['Thunderstorm/lightning/squall'], unknown_hazard_codes: [] },
            { colour: null, hazards: [], unknown_hazard_codes: [99] }] },
        { district: 'LAKSHADWEEP', state: null, days: [
            { colour: 'green', hazards: ['No warning in this product'], unknown_hazard_codes: [] },
            { colour: 'red', hazards: ['Heavy rainfall'], unknown_hazard_codes: [] }] },
      ],
      onOpen: (row: { district: string }, index: number) => { opened = [row.district, index]; },
    });
    expect(matrix.withClass('viz-cell')).toHaveLength(4);
    expect(matrix.withClass('is-yellow')).toHaveLength(1);
    expect(matrix.withClass('is-unknown')).toHaveLength(1);
    expect(matrix.withClass('is-unverified')).toHaveLength(1);
    matrix.withClass('viz-cell')[0].focus();
    const readout = matrix.withClass('viz-readout')[0].textContent;
    expect(/PATNA, BIHAR/.test(readout)).toBe(true);
    expect(/Thunderstorm\/lightning\/squall/.test(readout)).toBe(true);
    expect(/contains an unknown hazard code/.test(matrix.withClass('viz-cell')[1].attrs['aria-label'])).toBe(true);
    expect(matrix.allNodes().some((node: StandInNode) => node.textContent === 'LAKSHADWEEP · state not stated')).toBe(true);
    matrix.withClass('viz-cell')[0].events.click[0]();
    expect(opened).toEqual(['PATNA', 0]);
    expect(matrix.all('td').some((cell: StandInNode) => cell.textContent === 'not stated — no hazard wording printed')).toBe(true);
  });

  it('states printed dates, body state and links on the library cards', () => {
    let opened: unknown = null;
    const held = 'a'.repeat(64);
    const prunedSha = 'b'.repeat(64);
    const cards = viz.libraryCards({
      documents: [
        { sha256: held, sha_prefix: 'a'.repeat(12), family: 'national_bulletin', family_label: 'All India Weather Summary and Forecast Bulletin',
          scope: 'national', region: null, state: null, district: null, issue_date: '2026-09-14', pages: 12, passages: 48,
          body: 'available', age_days: 0, currency_recorded_at_intake: 'current_on_the_retrieval_date',
          retrieved_at_utc: '2026-09-14T06:10:00+00:00', source_id: 'S07' },
        { sha256: prunedSha, sha_prefix: 'b'.repeat(12), family: 'district_agromet', family_label: 'District agromet advisory bulletin',
          scope: 'district', region: 'Ahmedabad', state: 'Gujarat', district: 'Ahmedabad', issue_date: null, pages: 7, passages: 31,
          body: 'pruned', age_days: null, currency_recorded_at_intake: 'printed_issue_not_stated', retrieved_at_utc: null, source_id: 'S57' },
      ],
      onOpen: (document: { family: string }) => { opened = document.family; },
    });
    expect(cards.withClass('viz-card')).toHaveLength(2);
    const links = cards.all('a').filter((link: StandInNode) => String(link.href).indexOf('/api/documents/') === 0);
    expect(links).toHaveLength(2);
    expect(links.every((link: StandInNode) => String(link.href).indexOf(held) > 0)).toBe(true);
    expect(cards.withClass('is-pruned')).toHaveLength(1);
    expect(cards.allNodes().some((node: StandInNode) => node.textContent === 'body held')).toBe(true);
    expect(cards.allNodes().some((node: StandInNode) => node.textContent === 'not stated')).toBe(true);
    expect(/retention window/.test(cards.allNodes().map((node: StandInNode) => node.textContent).join(' '))).toBe(true);
    cards.withClass('viz-card-open')[0].events.click[0]();
    expect(opened).toBe('national_bulletin');
  });

  it('places each product lane from returned timestamps and never draws a window for an instant (now band)', () => {
    const band = viz.nowBand({
      title: 'Now', place: 'Ahmedabad, Gujarat', read_at: '2026-09-15T17:24:58+00:00',
      lanes: [
        { key: 'observed', label: 'Observed', kind: 'observed', from: '2026-09-15T17:00:00+00:00',
          detail: 'AHMEDABAD, 6.9 km away', source: 'S63' },
        { key: 'published', label: 'Published', kind: 'published', from: '2026-09-14T18:30:00+00:00',
          to: '2026-09-15T18:30:00+00:00', colour: 'yellow', detail: 'Official district warning: yellow', source: 'S63' },
        { key: 'model', label: 'Model next', kind: 'model', from: '2026-09-15T17:00:00+00:00',
          to: '2026-09-15T22:00:00+00:00', detail: '6 hour(s) returned', source: 'S62' },
      ],
    });
    expect(band.withClass('viz-now-mark')).toHaveLength(3);
    expect(band.withClass('viz-now-mark')[0].tag).toBe('line');
    expect(band.withClass('viz-now-mark')[1].tag).toBe('rect');
    expect(band.withClass('is-yellow')).toHaveLength(1);
    expect(band.withClass('viz-now-readat')).toHaveLength(1);
    band.withClass('viz-now-mark')[0].focus();
    const readout = band.withClass('viz-readout')[0].textContent;
    expect(/Observed/.test(readout)).toBe(true);
    expect(/AHMEDABAD/.test(readout)).toBe(true);
    expect(/S63/.test(readout)).toBe(true);
    expect(band.all('td').some((cell: StandInNode) => cell.textContent === 'an instant, not a window')).toBe(true);
    const empty = viz.nowBand({ title: 'Now', lanes: [{ label: 'Observed' }] });
    expect(empty.withClass('viz-now-mark')).toHaveLength(0);
    expect(empty.withClass('viz-empty').length).toBeGreaterThanOrEqual(1);
    const labels = band.all('text').map((node: StandInNode) => node.textContent);
    expect(labels.indexOf('Observed') >= 0 && labels.indexOf('Published') >= 0 && labels.indexOf('Model next') >= 0).toBe(true);
    expect(band.all('text').every((node: StandInNode) => node.namespace === SVG_NS)).toBe(true);
  });

  it('lays out published days, counts model hours into IST days and places the station', () => {
    const timeline = viz.dayTimeline({
      title: 'The five published days',
      read_at: '2026-09-15T17:31:14+00:00',
      days: [
        { day: 1, date_utc: '2026-09-15', colour: 'yellow', hazards: ['Thunderstorm/lightning/squall'], unknown_hazard_codes: [] },
        { day: 2, date_utc: '2026-09-16', colour: 'green', hazards: ['No warning in this product'], quiet: true, unknown_hazard_codes: [] },
        { day: 3, date_utc: '2026-09-17', colour: null, hazards: [], unknown_hazard_codes: [99] },
      ],
      hours: [{ at: '2026-09-15T17:00:00+00:00' }, { at: '2026-09-15T20:00:00+00:00' },
              { at: '2026-09-16T01:00:00+00:00' }, { at: '2026-09-17T02:00:00+00:00' }],
      observed: { label: 'AHMEDABAD, 6.9 km away', at: '2026-09-15T17:00:00+00:00' },
    });
    expect(timeline.withClass('viz-daycol')).toHaveLength(3);
    expect(timeline.withClass('viz-daycol')[0].className.indexOf('is-yellow') >= 0).toBe(true);
    expect(timeline.withClass('is-unknown')).toHaveLength(1);
    expect(timeline.withClass('is-unverified')).toHaveLength(1);
    timeline.withClass('viz-daycol')[0].focus();
    const readout = timeline.withClass('viz-readout')[0].textContent;
    expect(/Day 1/.test(readout) && /colour yellow/.test(readout) && /Thunderstorm\/lightning\/squall/.test(readout)).toBe(true);
    const rows = timeline.all('tr').map((row: StandInNode) => (row.children || []).map((cell: StandInNode) => cell.textContent));
    const rowForDate = (date: string) => rows.find((cells: string[]) => cells[1] === date) || [];
    expect(rowForDate('2026-09-16')[4]).toBe('2');
    expect(rowForDate('2026-09-15')[4]).toBe('1');
    expect(rowForDate('2026-09-17')[4]).toBe('1');
    expect(timeline.allNodes().some((node: StandInNode) => /AHMEDABAD, 6\.9 km away reported here/.test(node.textContent))).toBe(true);
    /* The rule is that an absent colour is named rather than drawn as one; the casing is not the rule.
       The engine used to shout the colour word, which put the all-caps tell in JavaScript where a check
       reading stylesheets could never see it. A colour now prints as the source published it. */
    expect(timeline.allNodes().some((node: StandInNode) => node.textContent === 'not stated')).toBe(true);
  });

  it('discloses a repeated bulletin date instead of presenting five dated days', () => {
    const repeated = viz.dayTimeline({
      days: [1, 2, 3, 4, 5].map((day: number) => ({ day: day, date_utc: '2026-09-15', colour: day === 1 ? 'yellow' : 'green', hazards: [], unknown_hazard_codes: [] })),
      hours: [{ at: '2026-09-15T18:00:00+00:00' }],
      observed: { label: 'AHMEDABAD, 7.5 km away', at: '2026-09-15T17:00:00+00:00' },
    });
    const heads = repeated.allNodes().filter((node: StandInNode) => String(node.className) === 'viz-daycol-head').map((node: StandInNode) => node.textContent);
    expect(heads.filter((head: string) => head.indexOf('2026-09-15') >= 0)).toHaveLength(1);
    expect(heads.filter((head: string) => head.indexOf('date not stated by the source') >= 0)).toHaveLength(4);
    expect(repeated.withClass('viz-daycol-observed')).toHaveLength(1);
  });

  it('shows a derived day its own label, its IST window and whether it is today', () => {
    const windowed = viz.dayTimeline({
      days: [
        { day: 1, date_utc: '2026-09-15', label: '15 Sep 2026', colour: 'yellow', hazards: ['Thunderstorm/lightning/squall'],
          unknown_hazard_codes: [], starts_utc: '2026-09-14T18:30:00+00:00', ends_utc: '2026-09-15T18:30:00+00:00', is_today: true },
        { day: 2, date_utc: '2026-09-16', label: '16 Sep 2026', colour: 'green', hazards: ['No warning in this product'],
          unknown_hazard_codes: [], starts_utc: '2026-09-15T18:30:00+00:00', ends_utc: '2026-09-16T18:30:00+00:00', is_today: false },
      ],
      hours: [],
    });
    const heads = windowed.allNodes().filter((node: StandInNode) => String(node.className) === 'viz-daycol-head').map((node: StandInNode) => node.textContent);
    expect(heads[0]).toBe('Day 1 · 15 Sep 2026');
    const windows = windowed.allNodes().filter((node: StandInNode) => String(node.className) === 'viz-daycol-window').map((node: StandInNode) => node.textContent);
    expect(windows[0]).toBe('IST window 00:00–24:00 (derived from the bulletin date)');
    expect(windowed.withClass('viz-daycol-today')).toHaveLength(1);
  });
});
