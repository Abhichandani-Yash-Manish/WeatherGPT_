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
  '/api/observations/network': envelope('observations.near', 'ok',
    { kind: 'metar', stations: [{ name: 'AHMEDABAD', station_code: 'VAAH', distance_km: 6.9, observed_at_utc: '2026-09-14T15:30:00+00:00', age_minutes: 30, stale: false, parameters: [], time_notes: [] }],
      rejected: [{ index: 3, reason: 'no coordinates' }], query: {} },
    { coverage: { stations_in_layer: 145, stations_within_radius: 1 } }),
  '/api/radar': envelope('networks.radar', 'ok',
    { stations: [{ name: 'Leh', code: 'leh', latitude: 34.28333333, longitude: 77.28333333, status: '0',
                   remarks: 'The image has not been updated.', last_updated_date: '04 JUN 2026', last_updated_time: '05:10:01 UTC' },
                 { name: 'Srinagar', code: 'srn', latitude: 34.05, longitude: 74.81, status: null, remarks: null,
                   last_updated_date: null, last_updated_time: null }],
      rejected: [], reported: 1, not_reported: 1 },
    { coverage: { stations: 2 } }),
  '/api/basins': envelope('networks.basins', 'ok',
    { basins: [{ name: 'Jiabharali at NT road Xing', basin: 'Brahmaputra', subbasin: 'Jiabharali at NT road Xing',
                 area_sqkm: '10472.6046637', fmo: 'GUWAHATI', fmo_code: '12', river_basi: '014',
                 day_fields: { day1: '2', day2: '2', day3: '2' } },
               { name: 'Sabarmati at Ahmedabad', basin: 'Sabarmati', subbasin: 'Sabarmati at Ahmedabad',
                 area_sqkm: '2100', fmo: 'AHMEDABAD', fmo_code: '05', river_basi: '031',
                 day_fields: { day1: '', day2: '', day3: '' } }],
      with_day_fields: 1, rejected: [{ index: 7, reason: 'no sub-basin name' }] }),
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
  '/api/warnings/alert-brief': envelope('warnings.alert_brief', 'ok', {
    status: 'ok', place: { district: 'PATNA', state: 'BIHAR' },
    day: { day: 1, label: '15 Sep 2026', starts_utc: '2026-09-14T18:30:00+00:00', ends_utc: '2026-09-15T18:30:00+00:00' },
    status_line: 'Official district warning: yellow - Thunderstorm/lightning/squall',
    day_status: { colour: 'yellow', colour_code: 3, hazards: ['Thunderstorm/lightning/squall'], quiet: false, official_wording: null,
                  wording_note: 'the product states a colour and hazard codes for this district-day and no free-text wording is recorded' },
    issuer: { source_id: 'S63', product: 'IMD district warning product', issued_at_utc: '2026-09-15T00:00:00+00:00',
              retrieved_at_utc: '2026-09-15T04:11:36+00:00', source_locator: '$.features[605]' },
    relay: { source_id: 'S06', messages: 9, eligible_by_lifecycle: 0, note: 'reported separately and never merged with the district guidance' },
    what_would_change_this: ['A newer bulletin of the same product replaces these day rows.'],
    not_established: ['This is district-level guidance from one published product. It is not point-level, not a flood or cyclone warning, and not an all-clear.'],
    brief_id: '34b32c8d335658f0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718'
  }, { limitations: ['Day windows are derived from the bulletin date.'] }),
  '/api/watches': { schema_version: 'watch-inbox-v1', delivery: 'local_inbox_only_no_push',
    note: 'Watches are evaluated only when asked.', checked_products: ['S15 IMD district warning product', 'S06 CAP relay assessment'],
    watches: [{ id: 'w1', created_at: '2026-09-15T08:00:00+00:00', question: 'Notify me if a heavy rain warning is issued for Thiruvananthapuram, Kerala tomorrow',
                place: { name: 'Thiruvananthapuram, Kerala' }, hazard: 'heavy_rain', window_start: null, window_end: null,
                state: 'registered_check_on_request', last_checked_at: null, result: null }] },
  '/api/watches/check': { schema_version: 'watch-check-v1', delivery: 'local_inbox_only_no_push',
    results: [{ id: 'w1', state: 'checked_no_match', matched: false, detail: 'No current day matches; this is not an all-clear.' }] },
  '/api/plans': { schema_version: 'plan-inbox-v1', mode: 'live', delivery: 'local_inbox_and_browser_notifications_while_the_workspace_runs',
    plans: [{ id: 'p1', title: 'Cotton spraying · Rajkot, Gujarat · Monday 21 Sep morning', state: 'waiting_for_coverage',
              state_words: 'waiting for IMD coverage', hazards: 'heavy rain, thunderstorm & lightning and strong surface winds',
              last_checked_at: '2026-09-15T05:00:00+00:00', not_connected: null }],
    notifications: [{ id: 3, plan_id: 'p1', kind: 'change', created_at: '2026-09-15T07:00:00+00:00', visible_at: '2026-09-15T07:00:00+00:00', visible: true,
                      title: 'Monday 21 Sep · Rajkot, Gujarat · official warning issued',
                      text: 'Monday 21 Sep for your cotton spraying in Rajkot, Gujarat changed: no warning for your watched hazards → Thunderstorm/lightning/squall (yellow).',
                      receipt: { place: 'Rajkot, Gujarat', date: '2026-09-21', district: 'RAJKOT', hazards: ['Thunderstorm/lightning/squall'], colour: 'yellow',
                                 source_id: 'S63', origin_authentication: 'unverified' } }],
    watcher: { running: true, interval_seconds: 1800, last_cycle_at: '2026-09-15T07:00:00+00:00', last_error: null },
    recorded_editions: 0, limits: ['No warning for your watched hazards is not an all-clear.'] },
  '/api/plans/check': { schema_version: 'plan-check-v1', result: { checked: 1, notified: 0, read: true } },
  '/api/places/search': envelope('places.search', 'ok', { matches: [{ label: 'Surat, Sūrat, State of Gujarāt', name: 'Surat', source_id: 'geonames', kind: 'city', coordinates: { latitude: 21.1959, longitude: 72.8302 } }] }),
  '/api/conversations': { schema_version: 'conversation-ledger-v1', total: 1, limit: 6, conversations: [{ id: 'c1', opening_question: 'Will it rain in Surat tomorrow?', asked: 2, turns: 4, updated: '2026-09-14T18:00:00+00:00' }] },
  '/api/now': envelope('now.composed', 'ok',
    { schema_version: 'now-v1', generated_at_utc: '2026-09-14T18:00:00+00:00',
      point: { latitude: 23.03, longitude: 72.59, label: null },
      observed: { status: 'ok', rows_in_radius: 1, stations: [{ kind: 'metar', network: 'metar', name: 'AHMEDABAD',
        station_code: 'VAAH', distance_km: 6.9, observed_at_utc: '2026-09-14T17:00:00+00:00', age_minutes: 25.8,
        parameters: [{ field: 'temp', value: 26, unit: null, unit_stated_by_source: false }], source_id: 'S63' }] },
      in_force: { status: 'ok', district: 'AHMADABAD', state: 'GUJARAT', day: 1, day_label: '14 Sep 2026',
        starts_utc: '2026-09-13T18:30:00+00:00', ends_utc: '2026-09-14T18:30:00+00:00', colour: 'yellow',
        hazards: ['Thunderstorm/lightning/squall'], quiet: false,
        status_line: 'Official district warning: yellow - Thunderstorm/lightning/squall',
        issued_at_utc: '2026-09-14T06:00:00+00:00', source_id: 'S63', source_locator: '$.features[112]' },
      next_hours: { status: 'ok', source_id: 'S62', rows: [
        { at: '2026-09-14T18:00:00+00:00', temperature_2m: 26.5, precipitation_probability: 1, precipitation: 0, wind_speed_10m: 9.4 },
        { at: '2026-09-14T19:00:00+00:00', temperature_2m: 26.2, precipitation_probability: 0, precipitation: 0, wind_speed_10m: 9.5 }] },
      summary: 'Freshest station report here: AHMEDABAD, 6.9 km away.',
      not_connected: ['radar and satellite imagery'], limitations: ['A quiet day is not an all-clear.'], not_established: [] }),
  '/api/air-quality': envelope('air_quality.point', 'ok',
    { parameters: { pm2_5: { unit: '\u03bcg/m\u00b3', points: [{ t: '2026-09-14T00:00:00+00:00', v: 7.3, source_locator: '$.hourly.pm2_5[0]' }] },
                    us_aqi: { unit: 'US AQI', points: [{ t: '2026-09-14T00:00:00+00:00', v: 53, source_locator: '$.hourly.us_aqi[0]' }] } },
      current: { pm2_5: 12.6, us_aqi: 53 }, grid: { latitude: 23.0, longitude: 72.6 },
      domain: 'CAMS global (Open-Meteo automatic domain)', requested: { latitude: 23.03, longitude: 72.59 } },
    { not_established: ['An air-quality index is the source\u2019s own index, and no health advice, risk score or official warning is produced from it.'] }),
  '/api/ensemble': envelope('ensemble.spread', 'ok',
    { parameters: { temperature_2m_mean: { unit: '\u00b0C', points: [{ t: '2026-09-14T00:00:00+00:00', v: '24.860', source_locator: '$.hourly.temperature_2m*[0]' }] },
                    temperature_2m_spread: { unit: '\u00b0C', points: [{ t: '2026-09-14T00:00:00+00:00', v: '1.204', source_locator: '$.hourly.temperature_2m*[0]' }, { t: '2026-09-14T01:00:00+00:00', v: '1.318', source_locator: '$.hourly.temperature_2m*[1]' }] },
                    temperature_2m_p10: { unit: '\u00b0C', points: [{ t: '2026-09-14T00:00:00+00:00', v: '23.100', source_locator: '$.hourly.temperature_2m*[0]' }, { t: '2026-09-14T01:00:00+00:00', v: '23.400', source_locator: '$.hourly.temperature_2m*[1]' }] },
                    temperature_2m_p50: { unit: '\u00b0C', points: [{ t: '2026-09-14T00:00:00+00:00', v: '24.050', source_locator: '$.hourly.temperature_2m*[0]' }, { t: '2026-09-14T01:00:00+00:00', v: '24.220', source_locator: '$.hourly.temperature_2m*[1]' }] },
                    temperature_2m_p90: { unit: '\u00b0C', points: [{ t: '2026-09-14T00:00:00+00:00', v: '25.200', source_locator: '$.hourly.temperature_2m*[0]' }, { t: '2026-09-14T01:00:00+00:00', v: '25.600', source_locator: '$.hourly.temperature_2m*[1]' }] },
                    temperature_2m_min: { unit: '\u00b0C', points: [{ t: '2026-09-14T00:00:00+00:00', v: '22.000', source_locator: '$.hourly.temperature_2m*[0]' }, { t: '2026-09-14T01:00:00+00:00', v: '22.300', source_locator: '$.hourly.temperature_2m*[1]' }] },
                    temperature_2m_max: { unit: '\u00b0C', points: [{ t: '2026-09-14T00:00:00+00:00', v: '26.000', source_locator: '$.hourly.temperature_2m*[0]' }, { t: '2026-09-14T01:00:00+00:00', v: '26.200', source_locator: '$.hourly.temperature_2m*[1]' }] } },
      statistics: { mean: 'arithmetic mean of the returned perturbed members', spread: 'population standard deviation across the returned members' },
      member_total: { temperature_2m: 30 }, model: 'gfs025', days: 1, grid: { latitude: 23.0, longitude: 72.6 },
      requested: { latitude: 23.03, longitude: 72.59 } },
    { not_established: ['Spread is not a probability, a confidence, a risk or a skill measure.'] }),
  '/api/corpus': envelope('corpus.documents', 'ok',
    { documents: [
        { sha256: 'a'.repeat(64), sha_prefix: 'a'.repeat(12), family: 'national_bulletin',
          family_label: 'All India Weather Summary and Forecast Bulletin', scope: 'national', region: null, state: null,
          district: null, issue_date: '2026-09-14', language: 'en', pages: 12, passages: 48, first_page: 1, last_page: 12,
          source_id: 'S07', address: 'https://example.test/national.pdf', retrieved_at_utc: '2026-09-14T06:10:00+00:00',
          checked_at_utc: '2026-09-14T06:10:00+00:00', age_days: 0, currency_recorded_at_intake: 'current_on_the_retrieval_date',
          body: 'available', quarantined_passages: 0, extraction_status: 'family_extraction_reviewed_in_intake' },
        { sha256: 'b'.repeat(64), sha_prefix: 'b'.repeat(12), family: 'district_agromet',
          family_label: 'District agromet advisory bulletin', scope: 'district', region: 'Ahmedabad', state: 'Gujarat',
          district: 'Ahmedabad', issue_date: '2026-08-01', language: 'en', pages: 7, passages: 31, first_page: 1,
          last_page: 7, source_id: 'S57', address: 'https://example.test/district.pdf',
          retrieved_at_utc: '2026-08-02T05:00:00+00:00', checked_at_utc: '2026-08-02T05:00:00+00:00', age_days: 1,
          currency_recorded_at_intake: 'measured_at_intake', body: 'pruned', quarantined_passages: 2, extraction_status: null }],
      families: [{ family: 'district_agromet', label: 'District agromet advisory bulletin', documents: 1, passages: 31, newest_issue_date: '2026-08-01' },
                 { family: 'national_bulletin', label: 'All India Weather Summary and Forecast Bulletin', documents: 1, passages: 48, newest_issue_date: '2026-09-14' }],
      counts: { documents: 2, documents_listed: 2, documents_matching: 2, passages: 79, regions: 1, pruned: 1,
                bodies_available: 1, documents_without_a_printed_issue_date: 0 },
      index: '/tmp/index.sqlite', filters: { family: '', q: '', documents_listed: 2 }, reason: '' },
    { coverage: { documents: 2, documents_listed: 2, passages: 79, regions: 1, families: 2, bodies_available: 1, bodies_pruned: 1 },
      limitations: ['A body is pruned after the retention window while its hash, extracted pages and passages stay indexed; a pruned document is a different state from a document that was never published.'],
      not_established: ['Nothing here establishes that a document applies to a place, a crop or a decision.'] }),
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
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/viz.js'), 'utf8'), context);
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
  const expected = ['overview', 'warnings', 'map', 'observations', 'forecast', 'changes', 'climate', 'advisories', 'air-quality', 'aviation', 'ensemble', 'compare', 'marine', 'documents', 'settings', 'assistant'];
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
  assert.equal(withClass(overview, 'viz-now').length, 1, 'Today opens with the Now band');
  assert.equal(withClass(overview, 'viz-now-mark').length, 3, 'one lane exists per product the reading returned');
  withClass(overview, 'viz-now-mark')[0].events.focus[0]();
  assert(/AHMEDABAD/.test(textOf(withClass(overview, 'viz-readout')[0])), 'a lane reads out its own values');
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
  const briefButton = byTag(warnings, 'button').find(node => /Write the alert brief/.test(textOf(node)));
  assert(briefButton, 'the warnings surface offers the alert brief');
  briefButton.dispatch('click');
  await settle(160);
  const briefDrawer = h.document.getElementById('evidence-drawer');
  const briefText = textOf(h.document.getElementById('drawer-body'));
  assert(briefDrawer.hidden === false, 'the brief opens in the drawer');
  assert(h.calls.some(call => /^\/api\/warnings\/alert-brief\?lat=/.test(call.path)), 'the brief is composed for the working point, not for a guessed one');
  assert(/Official district warning: yellow/.test(briefText), 'the brief states the day status in the product’s terms');
  assert(/S63/.test(briefText) && /S06/.test(briefText), 'the brief names both the warning product and the relay');
  assert(/not an all-clear/.test(briefText), 'the brief keeps its not-an-all-clear limit');
  assert(/revoked|is safe|all clear for/i.test(briefText) === false, 'the brief never claims safety or withdrawal');
  h.document.getElementById('drawer-close').dispatch('click');
  assert(withClass(warnings, 'viz-cell').length >= 2, 'the national product is drawn as a district-day matrix');
  assert(/Colour printed per district-day/.test(textOf(warnings)), 'the matrix names what a cell carries');
  assert(/never turns it into an all-clear/.test(textOf(warnings)), 'the matrix keeps the all-clear refusal');
  console.log('PASS: the warnings surface writes an alert brief that names its sources and its limits');

  const observations = await render('observations', place);
  assert(walk(observations).some(node => textOf(node) === 'AHMEDABAD'), 'a named station is listed');
  assert(withClass(observations, 'is-current').length >= 1, 'a fresh station is marked current');
  assert(walk(observations).some(node => /not stated by the source/i.test(textOf(node))), 'an unstated unit is shown as unstated');
  assert(walk(observations).some(node => /The layer carries 145 station\(s\)/.test(textOf(node))),
    'the network inventory prints the layer station count beside the list');
  assert(walk(observations).some(node => /no coordinates/.test(textOf(node))),
    'a rejected network feature is named rather than dropped silently');
  assert(walk(observations).some(node => /The image has not been updated\./.test(textOf(node))),
    'the radar board shows the source remarks verbatim');
  assert(walk(observations).some(node => /not reported/.test(textOf(node))),
    'a radar station without a published status is shown as not reported');
  console.log('PASS: the observations surface lists stations, freshness, unstated units, the layer inventory and the radar board');

  const forecast = await render('forecast', place);
  assert(withTag(forecast, 'svg').length >= 1, 'the forecast surface draws a chart');
  assert(withClass(forecast, 'viz').length >= 1, 'the hourly reading is drawn as one composite timeline');
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
  assert(walk(marine).some(node => textOf(node) === 'Jiabharali at NT road Xing'), 'the national sub-basin list is reachable from the same surface');
  assert(walk(marine).some(node => textOf(node) === '2'), 'a published sub-basin day field is shown verbatim');
  assert(walk(marine).some(node => /not stated/.test(textOf(node))), 'an absent day field is shown as not stated, never as zero');
  assert(walk(marine).some(node => /meaning of a day field is not documented by the layer/i.test(textOf(node))),
    'the layer limitation travels with the sub-basin table');
  console.log('PASS: the marine surface names the answering cell or its limit and lists the national sub-basins verbatim');

  const airQuality = await render('air-quality', place);
  assert(walk(airQuality).some(node => /CAMS modelled concentrations/.test(textOf(node))), 'air quality states what it is');
  assert(walk(airQuality).some(node => textOf(node) === '12.6'), 'the source current instant is shown as a value');
  assert(walk(airQuality).some(node => /Answering cell 23, 72.6/.test(textOf(node))), 'the answering cell is named');
  assert(/no health advice/i.test(textOf(airQuality)) || /no health assessment/i.test(textOf(airQuality)), 'air quality keeps its limit');
  console.log('PASS: the air-quality surface plots the model and keeps the source current hour apart from the window');

  const ensemble = await render('ensemble', place);
  assert(walk(ensemble).some(node => /30 member\(s\) returned/.test(textOf(node))), 'the member count is named');
  assert(walk(ensemble).some(node => /nearest-rank percentiles/.test(textOf(node))), 'the percentile method is stated');
  assert(withTag(ensemble, 'svg').length >= 1, 'the ensemble surface draws the member statistics');
  assert(/not a probability/i.test(textOf(ensemble)), 'the ensemble surface refuses the probability reading');
  assert(withClass(ensemble, 'viz-band').length >= 1, 'the member plume draws the p10-p90 band from returned statistics');
  assert(withClass(ensemble, 'viz-median').length >= 1, 'the plume draws the median as its own line');
  assert(withClass(ensemble, 'viz-hit').length >= 2, 'every drawn hour is focusable for its exact values');
  console.log('PASS: the ensemble surface draws member statistics without scoring them');

  const documents = await render('documents');
  assert(/2 document\(s\) \u00b7 79 passage\(s\)/.test(textOf(documents)), 'the corpus summary counts documents and passages');
  assert(walk(documents).some(node => textOf(node) === 'Ahmedabad'), 'a district edition names its region');
  assert(walk(documents).some(node => /body held/.test(textOf(node))), 'a held body is stated');
  assert(walk(documents).some(node => /body pruned/.test(textOf(node))), 'a pruned body is stated rather than hidden');
  const savedLinks = withTag(documents, 'a').filter(node => String(node.href || '').indexOf('/api/documents/') === 0);
  assert(savedLinks.length >= 2, 'a held body offers the saved file to open and download');
  assert(savedLinks.every(node => String(node.href).indexOf('a'.repeat(64)) > 0),
    'the saved-file links point at the held document and never at the pruned one');
  assert.equal(withClass(documents, 'viz-card').length, 2, 'each listed edition is drawn as a library card');
  assert(withClass(documents, 'is-pruned').length >= 1, 'a pruned body is stated on its card');
  assert(/2 day\(s\) after the printed issue date|1 day\(s\) after the printed issue date/.test(textOf(documents)),
    'currency is measured from the printed issue date against the retrieval date');
  assert(/not a current warning/i.test(textOf(documents)), 'the panel keeps the record-is-not-a-warning limit');
  console.log('PASS: the published-documents surface lists the corpus with its printed dates, body states and limits');

  const hints = {};
  fs.readFileSync(path.join(ROOT, 'web/index.html'), 'utf8').split('\n').forEach(line => {
    const view = (line.match(/data-view="([a-z]+)"/) || [])[1];
    const hint = (line.match(/\u2325(\d)/) || [])[1];
    if (view && hint) hints[hint] = view;
  });
  const promised = Object.keys(hints).map(key => [String(Number(key)), hints[key]]).sort();
  const actual = Object.keys(WG.VIEW_SHORTCUTS).map(key => [String(Number(key)), WG.VIEW_SHORTCUTS[key]]).sort();
  assert(promised.length >= 9, 'the rail prints nine keyboard hints');
  assert.deepEqual(actual, promised, 'Alt+1\u20269 must open the surface its rail hint names');
  console.log('PASS: the printed keyboard hints and the Alt+1-9 mapping agree');

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
  const mapReadout = withClass(mapHost, 'map-readout')[0];
  assert(mapReadout, 'the map carries a live readout');
  paths[0].dispatch('mouseenter', {});
  assert(/PATNA/.test(textOf(mapReadout)) && /yellow|green|orange|red|colour not supplied/.test(textOf(mapReadout)),
    'hovering a district reads out its name, state, colour and hazard wording: ' + textOf(mapReadout));
  assert(/district polygon\(s\)/.test(textOf(mapHost)) && /cities/.test(textOf(mapHost)),
    'the legend states what is drawn and how many of each');
  const cityDots = withClass(mapHost, 'place');
  assert(cityDots.length >= 1, 'the vendored city layer is drawn');
  assert(/is-pinnable/.test(cityDots[0].className), 'a city is offered as a working place when the map can set one');
  cityDots[0].dispatch('mouseenter', {});
  assert(/Patna/.test(textOf(mapReadout)) && /25\.6, 85\.1/.test(textOf(mapReadout)),
    'hovering a city reads out its coordinates from the geometry: ' + textOf(mapReadout));
  cityDots[0].dispatch('click', {});
  const pinned = h.api().state.place;
  assert(pinned && String(pinned.label).indexOf('Patna') === 0 && pinned.latitude === 25.6 && pinned.longitude === 85.1,
    'selecting a city makes it the working place at the geometry coordinates: ' + JSON.stringify(pinned));
  console.log('PASS: the map draws one path per district, flags placeholder geometry and never colours an unmapped district green');
  console.log('PASS: the map reads out what is under the pointer and a city selection sets the working place at source coordinates');

  const districtPaths = withClass(mapHost, 'district');
  assert.equal(districtPaths.filter(node => node.getAttribute('tabindex') === '0').length, 1,
    'the map keeps one tab stop for its districts rather than hundreds');
  districtPaths[0].dispatch('keydown', { key: 'ArrowRight' });
  assert.equal(districtPaths[1].getAttribute('tabindex'), '0', 'an arrow key moves the map tab stop to the next district');
  assert.equal(districtPaths[0].getAttribute('tabindex'), '-1', 'the district the cursor left is no longer tabbable');
  assert(districtPaths[1].focused === true, 'focus follows the map cursor');
  assert.equal(withClass(mapHost, 'district').filter(node => node.getAttribute('tabindex') === '0').length, 1,
    'exactly one district remains tabbable after moving');
  districtPaths[0].dispatch('keydown', { key: 'End' });
  assert.equal(districtPaths[districtPaths.length - 1].getAttribute('tabindex'), '0', 'End jumps to the last district');
  districtPaths[districtPaths.length - 1].dispatch('keydown', { key: 'Enter' });
  assert.equal(h.document.getElementById('evidence-drawer').hidden, false, 'Enter on the cursor opens the district detail');
  h.document.getElementById('drawer-close').dispatch('click');
  console.log('PASS: the districts behave as one tab stop with arrow keys, Home and End, and Enter opens the district');

  WG.wireNotify();
  h.document.getElementById('notify-panel').hidden = true;
  h.document.getElementById('notify-toggle').dispatch('click');
  await settle(30);
  const notify = h.document.getElementById('notify-body');
  assert(h.document.getElementById('notify-panel').hidden === false, 'the watch panel opens without a placeholder refusal');
  assert(/1 local watch\(es\) registered/.test(textOf(notify)), 'the panel reads the local watch inbox');
  assert(/Thiruvananthapuram/.test(textOf(notify)), 'a registered watch names its place');
  assert(/Cotton spraying · Rajkot, Gujarat · Monday 21 Sep morning/.test(textOf(notify)), 'the panel lists a saved plan');
  assert(/waiting for IMD coverage/.test(textOf(notify)), 'a plan states its state in words');
  assert(/no warning for your watched hazards → Thunderstorm/.test(textOf(notify)), 'the panel shows a plan notification with what changed');
  assert(/not an all-clear/.test(textOf(notify)), 'the plan limits are offered');
  assert(byTag(notify, 'button').some(node => textOf(node) === 'Ask about this change'), 'a change can be handed to the assistant');
  assert(!byTag(notify, 'button').some(node => textOf(node) === 'Replay recorded editions'), 'replay is not offered without two recorded editions');
  const checkPlans = byTag(notify, 'button').find(node => textOf(node) === 'Check plans now');
  assert(checkPlans, 'the panel offers a plan check');
  checkPlans.dispatch('click');
  await settle(30);
  assert(h.calls.some(call => call.path === '/api/plans/check'), 'Check plans now calls the plan check route');
  console.log('PASS: the watch panel lists saved plans and their notifications, and checks plans on request');
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

  let transitions = 0;
  h.document.startViewTransition = fn => { transitions += 1; fn(); };
  h.api().render();
  assert.equal(transitions, 1, 'a surface change is offered as a view transition when the browser has the API');
  delete h.document.startViewTransition;
  h.api().render();
  assert.equal(transitions, 1, 'without the API the surface still renders, with no transition attempted');
  console.log('PASS: view transitions are offered when available and never required');

  const memory = h.api();
  memory.pinPlace({ label: 'Kochi, Kerala', latitude: 9.93, longitude: 76.27 });
  assert(memory.pinnedPlaces().some(item => item.label === 'Kochi, Kerala'), 'a pinned place is remembered locally');
  assert(memory.isPinned({ label: 'Kochi, Kerala' }), 'a pinned place reads as pinned');
  assert(typeof memory.paintPinned === 'function', 'the topbar strip can be repainted from the palette action');
  memory.unpinPlace({ label: 'Kochi, Kerala' });
  assert(!memory.isPinned({ label: 'Kochi, Kerala' }), 'unpinning forgets it');
  memory.pinPlace({ label: 'Nowhere', latitude: null, longitude: null });
  assert(!memory.pinnedPlaces().some(item => item.label === 'Nowhere'),
    'a place without coordinates is refused, so a pin can never invent a location');
  console.log('PASS: pinned places are remembered locally and a pin without coordinates is refused');

  const loadingNode = h.api().loading('Reading the sources…');
  assert.equal(withClass(loadingNode, 'skeleton-bar').length, 3, 'a loading state shows the shape of the answer that is coming');
  assert(withClass(loadingNode, 'skeleton-frame').length === 1, 'a loading state reserves the chart frame before it arrives');
  assert(!/[0-9]/.test(textOf(loadingNode)), 'a skeleton carries no number, because it has no source');
  console.log('PASS: loading states reserve the shape of the answer without inventing a value');

  const tray = h.api();
  tray.addToCompare({ label: 'Ahmedabad, Gujarat', latitude: 23.02579, longitude: 72.58727 });
  tray.addToCompare({ label: 'Patna, Bihar', latitude: 25.5941, longitude: 85.1376 });
  assert.equal(tray.comparePlaces().length, 2, 'the compare tray holds the places added to it');
  tray.addToCompare({ label: 'Nowhere', latitude: null, longitude: null });
  assert(!tray.comparePlaces().some(item => item.label === 'Nowhere'), 'a place without coordinates cannot enter the tray');

  const compare = await render('compare');
  assert.equal(withClass(compare, 'compare-column').length, 2, 'one column is drawn per place in the tray');
  assert(walk(compare).some(node => textOf(node) === 'Ahmedabad, Gujarat'), 'a column names its own place');
  assert.equal(withClass(compare, 'viz-now').length, 2, 'each column draws the reading that place returned');
  assert(/never subtracts them/.test(textOf(compare)), 'the surface states that it computes no difference between places');
  console.log('PASS: the compare tray reads two places side by side and refuses to difference them');

  tray.clearCompare();
  const emptyCompare = await render('compare');
  assert(/compare tray is empty/i.test(textOf(emptyCompare)), 'an empty tray says so instead of drawing nothing');
  console.log('PASS: an empty compare tray states its own emptiness');

  const untokened = h.calls.filter(call => call.headers['X-WeatherGPT-Token'] !== TOKEN);
  assert.equal(untokened.length, 0, 'every request carries the workspace token, missing on: ' + JSON.stringify(untokened.map(call => call.path)));
  console.log('PASS: every surface request carries the workspace token');


  process.exit(0);
}
run().catch(error => { console.error(error); process.exit(1); });
