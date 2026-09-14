// Component checks for the suite shell, the surface panels and the map.
// These are not browser acceptance tests: they run against a DOM shim with
// recorded payloads, so layout, styling and real endpoints are out of scope.
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path'), assert = require('assert');
const shim = require('./dom_shim.js');

const ROOT = path.join(__dirname, '..');
const TOKEN = 'test-token';

function walk(node, out) {
  out = out || [];
  (node.children || []).forEach(child => { out.push(child); walk(child, out); });
  return out;
}
function withClass(node, cls) { return walk(node).filter(child => String(child.className || '').split(/\s+/).indexOf(cls) >= 0); }
function byTag(node, tag) { return walk(node).filter(child => child.tag === tag); }
function withTag(node, tag) { return byTag(node, tag); }
function textOf(node) { return (node && node.textContent) || ''; }

function envelope(view, status, data, extra) {
  return Object.assign({ schema_version: 'product-view-v1', generated_at_utc: '2026-09-14T18:00:00+00:00',
                         view: view, status: status, data: data, sources: [], coverage: {},
                         limitations: ['A stated limit of this view.'], not_established: ['Something not established here.'] }, extra || {});
}
function day(index, colour, codes, hazards) {
  return { day: index, date_utc: '2026-09-14', colour: colour, colour_code: null, hazard_codes: codes || [1],
           hazards: hazards || ['No warning in this product'], source_text: null, unknown_hazard_codes: [],
           quiet: (hazards || ['No warning in this product'])[0] === 'No warning in this product' };
}
const DISTRICT = { key: 'PATNA', district: 'PATNA', state: 'BIHAR', bulletin_date: '2026-09-14',
                   issued_at_utc: '2026-09-14T06:00:00+00:00', updated_at: '2026-09-14T12:35:18Z',
                   days: [day(1, 'green'), day(2, 'yellow', [4], ['Thunderstorm/lightning/squall'])] };

const PAYLOADS = {
  '/api/overview': envelope('overview', 'ok', { national: { districts: 756, tally: { yellow: 10, green: 700 }, skipped: 8, bulletin_date: '2026-09-14', bulletin_dates: { '2026-09-14': 740 } },
    radar: { stations: 39, reported: 39 }, places: [{ label: 'Patna', district: 'PATNA', state: 'BIHAR', bulletin_date: '2026-09-14', days: DISTRICT.days, note: null }] }),
  '/api/warnings/cap': envelope('warnings.cap', 'ok', { messages: 9, eligible_by_lifecycle: 0, latest_sent: '2026-09-09T07:24:34+00:00', records: [] }),
  '/api/warnings/national': envelope('warnings.national', 'ok', { districts: [DISTRICT], tally: { yellow: 1 }, skipped: [{ obj_id: 9, reason: 'no district name' }], basemap_build: 'basemap-v1-test' },
    { coverage: { features_returned: 764, districts_listed: 1, skipped_without_a_name: 1, basemap_districts: 756 } }),
  '/api/warnings/place': envelope('warnings.place', 'ok', { district: 'PATNA', state: 'BIHAR', issued_at_utc: '2026-09-14T06:00:00+00:00', day_boundary_basis: 'Derived from the bulletin date.', days: DISTRICT.days }),
  '/api/observations/near': envelope('observations.both', 'ok', { networks: { metar: [{ name: 'AHMEDABAD', station_code: 'VAAH', distance_km: 7.45, observed_at_utc: '2026-09-14T15:30:00+00:00', age_minutes: 30, stale: false, parameters: [{ field: 'temp', value: '25', unit: null }], time_notes: [] }], aws: [] }, query: {} }),
  '/api/forecast': envelope('forecast.point', 'ok', { parameters: { temperature_2m: { unit: '°C', model: 'test model', quality_flags: [], points: [{ t: '2026-09-14T00:00:00+00:00', v: 26, source_locator: '$.hourly.temperature_2m[0]' }] } }, days: 1, source_family: 'hourly_forecast', grid: { latitude: 23.02, longitude: 72.6 }, requested: { latitude: 23.03, longitude: 72.59 }, time_basis: 'UTC' }),
  '/api/climate/index': envelope('climate.index', 'ok', { states: [{ state: 'Gujarat', districts: [{ district: 'Ahmedabad', years: 110, first_year: 1901, last_year: 2010 }] }], districts: 1 }),
  '/api/climate/series': envelope('climate.series', 'ok', { district: 'Ahmedabad', state: 'Gujarat', series_id: 'IMD110-P611', points: [{ year: 1981, value: '880.4', source_page: '612', source_row: 82, label: 'AHMEDABAD', asset_sha256_prefix: 'abc123' }], first_year: 1981, last_year: 1981 }),
  '/api/advisories/states': envelope('advisories.states', 'ok', { states: [{ id: 'Gujarat', label: 'Gujarat' }] }),
  '/api/advisories/districts': envelope('advisories.districts', 'ok', { state: 'Gujarat', districts: [{ id: 'Ahmedabad', label: 'Ahmedabad' }] }),
  '/api/aviation': envelope('aviation.station', 'ok', { stations: [{ station_id: 'VAAH', observed_at_utc: '2026-09-14T16:00:00+00:00', age_seconds: 500, freshness: 'within_prototype_age_limit', raw_report: 'METAR VAAH 141600Z', temperature_c: 25, dewpoint_c: 23, wind_speed_kt: 6, wind_direction_native: 150 }], kind: 'metar', missing: [] },
    { not_established: ['A station report is not a flight status, a route briefing or a clearance.'] }),
  '/api/marine': envelope('marine.point', 'ok', { parameters: { wave_height: { unit: 'm', model: 'test', quality_flags: [], points: [{ t: '2026-09-14T00:00:00+00:00', v: 1.04, source_locator: '$.hourly.wave_height[0]' }] } }, days: 1, grid: { latitude: 9.95, longitude: 76.2 }, requested: { latitude: 9.93, longitude: 76.26 }, grid_distance_km: 5.2 },
    { not_established: ['No official sea-area bulletin, observed buoy value, tide, current or sea-surface temperature is retrieved here.'] }),
  '/api/river': envelope('river.point', 'ok', { parameters: { river_discharge: { unit: 'm³/s', model: 'test', quality_flags: [], points: [{ t: '2026-09-14', v: 7.45, source_locator: '$.daily.river_discharge[0]' }] } }, days: 1, grid: { latitude: 23.02, longitude: 72.57 }, grid_distance_km: 1.1 }),
  '/api/settings/capabilities': envelope('settings.capabilities', 'ok', { capabilities: [{ tool: 'official_warning', kind: 'warning', operations: ['lookup'], purpose: 'official warning guidance' }], sources: [{ source_id: 'S15', product: 'IMD public warning-map WFS', integration_status: 'prototype_adapter_tested', user_review: 'pending', usage_terms: 'unresolved', selection: 'proposed' }], registered_sources: 63, connected_sources: 1 }),
  '/api/map/layers': envelope('map.layers', 'ok', { build_id: 'basemap-v1-test', layers: [{ name: 'districts', file: 'districts.geojson', bytes: 10, budget_bytes: 20 }], district_polygons: 756, skipped_without_a_name: 1, state_attribution: { districts: 756, attributed: 755, exact_name_matches: 619 }, attribution: 'IMD' })
};
const GEOMETRY = {
  districts: { type: 'FeatureCollection', features: [
    { type: 'Feature', properties: { k: 'PATNA', n: 'PATNA', s: 'BIHAR' }, geometry: { type: 'Polygon', coordinates: [[[85, 25], [86, 25], [86, 26], [85, 26], [85, 25]]] } },
    { type: 'Feature', properties: { k: 'LAKSHADWEEP', n: 'LAKSHADWEEP', s: null, p: 1 }, geometry: { type: 'Polygon', coordinates: [[[71, 7], [74, 7], [74, 12], [71, 12], [71, 7]]] } } ] },
  land: { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { k: 'india' }, geometry: { type: 'MultiPolygon', coordinates: [[[[85, 25], [86, 25], [86, 26], [85, 26], [85, 25]]]] } }] },
  states: { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { k: 'BIHAR', n: 'BIHAR' }, geometry: { type: 'Polygon', coordinates: [[[85, 25], [86, 25], [86, 26], [85, 26], [85, 25]]] } }] },
  'coast-zones': { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { k: 'SOUTHGUJRAT', n: 'South Gujrat' }, geometry: { type: 'Polygon', coordinates: [[[72, 20], [73, 20], [73, 21], [72, 21], [72, 20]]] } }] },
  places: { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { n: 'Patna', t: 'PPLA', a: 'Bihar' }, geometry: { type: 'Point', coordinates: [85.1, 25.6] } }] }
};

function harness() {
  const document = shim.createDocument();
  const calls = [];
  const context = Object.create(global);
  const define = (key, value) => Object.defineProperty(context, key, { value: value, writable: true, configurable: true, enumerable: true });
  const window = { addEventListener: () => {}, localStorage: { getItem: () => null, setItem: () => {} },
                   location: { hash: '#/overview' }, WG: { state: {}, panels: {} } };
  define('document', document);
  define('Node', shim.Node);
  define('window', window);
  define('navigator', { onLine: true });
  define('URL', URL);
  define('requestAnimationFrame', fn => setTimeout(fn, 0));
  define('fetch', async (target, options) => {
    calls.push({ path: target, headers: (options && options.headers) || {} });
    const key = String(target).split('?')[0];
    if (key.startsWith('/api/map/static/')) {
      const name = key.replace('/api/map/static/', '');
      return { ok: true, status: 200, json: async () => GEOMETRY[name] || { type: 'FeatureCollection', features: [] } };
    }
    if (!PAYLOADS[key]) return { ok: false, status: 404, json: async () => ({ error: 'Not found' }) };
    return { ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(PAYLOADS[key])) };
  });
  vm.createContext(context);
  // Loaded in the same order as the page: the shell owns the transport and the shared
  // builders, then the map, then the panels that attach to it.
  document.readyState = 'loading';
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/views.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/charts.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/shell.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/map.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/panels.js'), 'utf8'), context);
  document.readyState = 'complete';
  return { context, document, window, calls, api: () => window.WG };
}
function settle(ms) { return new Promise(resolve => setTimeout(resolve, ms === undefined ? 40 : ms)); }

async function run() {
  const h = harness();
  const WG = h.api();
  const expected = ['overview', 'warnings', 'map', 'observations', 'forecast', 'climate', 'advisories', 'aviation', 'marine', 'settings', 'assistant'];
  expected.forEach(name => assert.equal(typeof WG.panels[name], 'function', name + ' panel is registered'));
  assert.equal(typeof WG.map.render, 'function', 'the map renderer is registered');
  console.log('PASS: every surface has a renderer, including the map (component only)');

  async function render(name, place) {
    const host = h.document.createElement('div');
    if (place) WG.state.place = place;
    await WG.panels[name](host, WG);
    await settle(20);
    return host;
  }
  const place = { label: 'Patna, Bihar', latitude: 25.5941, longitude: 85.1376 };

  const overview = await render('overview', place);
  assert(walk(overview).some(node => textOf(node).indexOf('National warning picture') >= 0), 'overview names the national picture');
  assert(withClass(overview, 'wchip').length >= 2, 'overview shows the warning tally as colours');
  assert(walk(overview).some(node => /not an all-clear/i.test(textOf(node))), 'overview keeps the all-clear caveat');
  console.log('PASS: the overview surface paints the national tally and keeps its caveats');

  const warnings = await render('warnings', place);
  const chips = withClass(warnings, 'wchip');
  assert.equal(chips.length, 2, 'the warning table shows one colour chip per district-day in the payload');
  const districtLink = byTag(warnings, 'button').find(node => String(node.className).indexOf('link-button') >= 0);
  assert(districtLink, 'a district opens its own detail');
  districtLink.dispatch('click');
  const drawer = h.document.getElementById('drawer-body');
  assert(/Thunderstorm\/lightning\/squall/.test(textOf(drawer)), 'the official hazard wording is shown in the district detail');
  assert(/not the atoll|not a coastline|bulletin date/.test(textOf(drawer)) || /IST calendar day/.test(textOf(drawer)), 'the day boundary basis is stated with the detail');
  assert(walk(warnings).some(node => /no district name/i.test(textOf(node)) || /cannot be keyed/i.test(textOf(node))), 'districts without a source name are explained');
  assert(walk(warnings).some(node => /never merged with district guidance/i.test(textOf(node))), 'the CAP relay is presented as separate');
  console.log('PASS: the warnings surface shows district-days, the official wording and the source gaps');

  const observations = await render('observations', place);
  assert(walk(observations).some(node => textOf(node) === 'AHMEDABAD'), 'a named station is listed');
  assert(withClass(observations, 'is-current').length >= 1, 'a fresh station is marked current');
  assert(walk(observations).some(node => /not stated by the source/i.test(textOf(node))), 'an unstated unit is shown as unstated');
  console.log('PASS: the observations surface lists stations, freshness and unstated units');

  const forecast = await render('forecast', place);
  assert(withTag(forecast, 'svg').length >= 1, 'the forecast surface draws a chart');
  console.log('PASS: the forecast surface renders a series chart');

  const climate = await render('climate', place);
  assert(walk(climate).some(node => textOf(node).indexOf('880.4') >= 0), 'the published value is shown');
  console.log('PASS: the climate surface renders the published record');

  const aviation = await render('aviation', place);
  assert(walk(aviation).some(node => textOf(node) === 'METAR VAAH 141600Z'), 'the raw report is shown verbatim');
  assert(walk(aviation).some(node => /flight status/i.test(textOf(node))), 'aviation states what a report is not');
  console.log('PASS: the aviation surface shows the raw report and its limit');

  const marine = await render('marine', place);
  assert(walk(marine).some(node => /wave grid cell|sea grid cell|not an official|Answering cell/i.test(textOf(node))), 'marine names its answering cell or its limit');
  console.log('PASS: the marine surface names the answering cell or its limit');

  const settings = await render('settings', place);
  assert(walk(settings).some(node => textOf(node) === 'S15'), 'settings lists the source');
  assert(walk(settings).some(node => /usage terms|unresolved/i.test(textOf(node))), 'settings states the unresolved terms');
  console.log('PASS: the settings surface lists capabilities, sources and their terms');

  const advisories = await render('advisories', place);
  assert(withClass(advisories, 'chip-button').length >= 1, 'advisories offers district entries');
  console.log('PASS: the advisories surface offers the district directory');

  const mapHost = await render('map', place);
  await settle(40);
  const paths = withClass(mapHost, 'district');
  assert.equal(paths.length, 2, 'one path per vendored district polygon');
  assert.equal(withClass(mapHost, 'is-placeholder').length, 1, 'a source bounding box is marked as a placeholder');
  assert(paths.some(node => /w-green/.test(node.className)), 'a quiet district-day is painted with its colour');
  assert(!paths.every(node => /w-green/.test(node.className)), 'a district without a warning row is not painted as quiet');
  assert(walk(mapHost).some(node => /source bounding box/i.test(textOf(node))), 'the placeholder is described in words');
  console.log('PASS: the map draws one path per district, flags placeholder geometry and never colours an unmapped district green');

  const untokened = h.calls.filter(call => call.headers['X-WeatherGPT-Token'] !== TOKEN);
  assert.equal(untokened.length, 0, 'every request carries the workspace token, missing on: ' + JSON.stringify(untokened.map(call => call.path)));
  console.log('PASS: every surface request carries the workspace token');


  process.exit(0);
}
run().catch(error => { console.error(error); process.exit(1); });
