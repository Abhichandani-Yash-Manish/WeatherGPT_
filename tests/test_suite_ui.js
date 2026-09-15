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
  '/api/map/layers': envelope('map.layers', 'ok', { build_id: 'basemap-v1-test', layers: [{ name: 'districts', file: 'districts.geojson', bytes: 10, budget_bytes: 20 }], district_polygons: 756, skipped_without_a_name: 1, state_attribution: { districts: 756, attributed: 755, exact_name_matches: 619 }, attribution: 'IMD' }),
  '/api/forecast/changes': envelope('forecast.changes', 'ok', {
    point: { latitude: 23.02579, longitude: 72.58727 }, requested_point: { latitude: 23.02579, longitude: 72.58727 },
    retrievals: [{ retrieved_at_utc: '2026-09-14T22:34:10+00:00', product: 'forecast', request_date: '2026-09-12', response_sha256_prefix: 'abc123' }],
    retrieval_count: 2, overlapping_valid_hours: 6,
    parameters: { temperature_2m: { unit: '°C', valid_hours: 6, mean_abs_change: 0.7, max_abs_change: 4.8,
      example: { valid_time_utc: '2026-09-13T10:00:00+00:00', first_value: 29.1, last_value: 24.3,
                 first_retrieved_utc: '2026-09-12T07:38:40+00:00', last_retrieved_utc: '2026-09-12T20:40:23+00:00' } } },
    interpretation: 'vintage_variance_not_skill'
  }, { limitations: ['Not forecast skill.'], not_established: ['Forecast skill is not measured here.'] }),
  '/api/watches': { schema_version: 'watch-inbox-v1', delivery: 'local_inbox_only_no_push',
    note: 'Watches are evaluated only when asked.', checked_products: ['S15 IMD district warning product', 'S06 CAP relay assessment'],
    watches: [{ id: 'w1', created_at: '2026-09-15T08:00:00+00:00', question: 'Notify me if a heavy rain warning is issued for Thiruvananthapuram, Kerala tomorrow',
                place: { name: 'Thiruvananthapuram, Kerala' }, hazard: 'heavy_rain', window_start: null, window_end: null,
                state: 'registered_check_on_request', last_checked_at: null, result: null }] },
  '/api/watches/check': { schema_version: 'watch-check-v1', delivery: 'local_inbox_only_no_push',
    results: [{ id: 'w1', state: 'checked_no_match', matched: false, detail: 'No current day matches; this is not an all-clear.' }] },
  '/api/places/search': envelope('places.search', 'ok', { matches: [{ label: 'Surat, Sūrat, State of Gujarāt', name: 'Surat', source_id: 'geonames', kind: 'city', coordinates: { latitude: 21.1959, longitude: 72.8302 } }] }),
  '/api/conversations': { schema_version: 'conversation-ledger-v1', total: 1, limit: 6, conversations: [{ id: 'c1', opening_question: 'Will it rain in Surat tomorrow?', asked: 2, turns: 4, updated: '2026-09-14T18:00:00+00:00' }] },
  '/api/health': { available: true, products: [{ product: 'forecast', jobs: 12, newest_commit_utc: '2026-09-14T18:00:00+00:00' }], job_states: { ok: 12 }, active_leases: 0 }
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
  const stored = {};
  const window = { addEventListener: () => {}, matchMedia: () => ({ matches: false, addEventListener: () => {} }),
                   localStorage: { getItem: key => (key in stored ? stored[key] : null), setItem: (key, value) => { stored[key] = String(value); } },
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
  const expected = ['overview', 'warnings', 'map', 'observations', 'forecast', 'changes', 'climate', 'advisories', 'aviation', 'marine', 'settings', 'assistant'];
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

  const changes = await render('changes', place);
  const changesText = textOf(changes);
  assert(/not a forecast score/i.test(changesText), 'the changes surface states that vintage variance is not a score');
  assert(walk(changes).some(node => textOf(node) === '0.7'), 'the measured mean change is shown with its value');
  assert(walk(changes).some(node => textOf(node) === '4.8'), 'the largest absolute change is shown');
  assert(/not an error and neither retrieval is validated/i.test(changesText), 'the changes surface says a change is not a validation claim');
  assert(/Forecast skill is not measured here/.test(changesText), 'the skill limit from the payload is carried into the view');
  console.log('PASS: the changes surface reports vintage variance and its skill limit');

  const mapHost = await render('map', place);
  await settle(40);
  const paths = withClass(mapHost, 'district');
  assert.equal(paths.length, 2, 'one path per vendored district polygon');
  assert.equal(withClass(mapHost, 'is-placeholder').length, 1, 'a source bounding box is marked as a placeholder');
  assert(paths.some(node => /w-green/.test(node.className)), 'a quiet district-day is painted with its colour');
  assert(!paths.every(node => /w-green/.test(node.className)), 'a district without a warning row is not painted as quiet');
  assert(walk(mapHost).some(node => /source bounding box/i.test(textOf(node))), 'the placeholder is described in words');
  console.log('PASS: the map draws one path per district, flags placeholder geometry and never colours an unmapped district green');

  WG.wireNotify();
  h.document.getElementById('notify-panel').hidden = true;
  h.document.getElementById('notify-toggle').dispatch('click');
  await settle(30);
  const notify = h.document.getElementById('notify-body');
  assert(h.document.getElementById('notify-panel').hidden === false, 'the watch panel opens without a placeholder refusal');
  assert(/1 local watch\(es\) registered/.test(textOf(notify)), 'the panel reads the local watch inbox');
  assert(/Thiruvananthapuram/.test(textOf(notify)), 'a registered watch names its place');
  const checkButton = byTag(notify, 'button').find(node => textOf(node) === 'Check now');
  assert(checkButton, 'the panel offers a foreground check');
  checkButton.dispatch('click');
  await settle(30);
  assert(h.calls.some(call => call.path === '/api/watches/check'), 'Check now calls the foreground check route');
  assert(/Checked 1 watch\(es\) in the foreground/.test(textOf(notify)), 'the check reports what ran in the foreground');
  console.log('PASS: the watch panel reads the local inbox and checks watches only on request');

  WG.wireTheme();
  const themeToggle = h.document.getElementById('theme-toggle');
  assert.equal(themeToggle.textContent, 'System · day', 'with no stored choice the shell follows the system day desk');
  themeToggle.dispatch('click');
  assert.equal(h.document.documentElement.getAttribute('data-theme'), 'light', 'the first step applies the day desk to the document');
  themeToggle.dispatch('click');
  assert.equal(h.document.documentElement.getAttribute('data-theme'), 'dark', 'the next step applies the night desk');
  assert.equal(themeToggle.textContent, 'Night desk', 'the control names the appearance in words');
  themeToggle.dispatch('click');
  assert.equal(themeToggle.textContent, 'System · day', 'the cycle returns to the system and its stored choice survives');
  console.log('PASS: appearance cycles system, day and night and records the choice');

  await WG.paintHealthMini();
  const healthMini = h.document.getElementById('health-mini');
  assert(/forecast/.test(textOf(healthMini)) && /12 jobs/.test(textOf(healthMini)), 'the rail readout names the product and its job count');
  console.log('PASS: the rail readout shows collection health rows');

  WG.wirePalette();
  h.document.getElementById('palette-open').dispatch('click');
  await settle(40);
  const palette = h.document.getElementById('palette');
  const paletteBody = h.document.getElementById('palette-body');
  assert.equal(palette.hidden, false, 'the palette opens from the rail control');
  assert(withClass(paletteBody, 'palette-item').length >= 12, 'the palette lists every surface as a command');
  assert(/What changed/.test(textOf(paletteBody)), 'the palette names the changes surface');
  assert(/Recent conversations/.test(textOf(paletteBody)) && /rain in Surat/.test(textOf(paletteBody)), 'the palette offers stored conversations');
  assert(/2 asked/.test(textOf(paletteBody)), 'a stored conversation carries its asked count rather than an undefined field');
  const paletteInput = h.document.getElementById('palette-input');
  paletteInput.value = 'surat';
  paletteInput.dispatch('input');
  await settle(320);
  const filtered = withClass(paletteBody, 'palette-item');
  assert(filtered.some(node => /Surat, Sūrat/.test(textOf(node))), 'a typed place reaches the places endpoint and is listed');
  assert(filtered.some(node => /geonames/.test(textOf(node))), 'a place match carries its source in the note');
  assert(!filtered.some(node => /What changed/.test(textOf(node))), 'a typed query filters the surface commands');
  WG.palette.open();
  await settle(40);
  const surfaceItem = withClass(paletteBody, 'palette-item').find(node => /What changed/.test(textOf(node)));
  assert(surfaceItem, 'the changes surface is reachable from the palette');
  surfaceItem.dispatch('click');
  assert.equal(h.window.location.hash, '#/changes', 'running a palette item moves the shell to that surface');
  assert.equal(palette.hidden, true, 'running an item closes the palette');
  console.log('PASS: the command palette lists surfaces, places and recents and runs the chosen item');

  const untokened = h.calls.filter(call => call.headers['X-WeatherGPT-Token'] !== TOKEN);
  assert.equal(untokened.length, 0, 'every request carries the workspace token, missing on: ' + JSON.stringify(untokened.map(call => call.path)));
  console.log('PASS: every surface request carries the workspace token');


  process.exit(0);
}
run().catch(error => { console.error(error); process.exit(1); });
