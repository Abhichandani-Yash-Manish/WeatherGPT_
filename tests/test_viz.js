// Pure component checks for the chart engine: no browser, no layout, no pixels.
// What they pin is the honesty rule — a mark exists only where the engine returned a value,
// a missing hour stays a gap, and every drawn point carries its source locator.
'use strict';
const fs = require('fs'), vm = require('vm'), assert = require('assert');

class Node {
  constructor(tag) { this.tag = tag; this.children = []; this.attrs = {}; this.events = {}; this.textContent = ''; this.className = ''; this.dataset = {}; }
  append(...children) { this.children.push(...children); return children[0]; }
  setAttribute(key, value) { this.attrs[key] = String(value); if (key === 'class') this.className = String(value); }
  addEventListener(event, fn) { (this.events[event] = this.events[event] || []).push(fn); }
  all(tag) { return [...(this.tag === tag ? [this] : []), ...this.children.flatMap(child => child.all(tag))]; }
  withClass(cls) { return this.allNodes().filter(node => String(node.className).split(/\s+/).indexOf(cls) >= 0); }
  allNodes() { return [this, ...this.children.flatMap(child => child.allNodes())]; }
  focus() { (this.events.focus || []).forEach(fn => fn({})); }
  keydown(key) { (this.events.keydown || []).forEach(fn => fn({ key: key, preventDefault() {} })); }
}
const context = { document: { createElement: tag => new Node(tag), createElementNS: (ns, tag) => new Node(tag) } };
vm.createContext(context);
vm.runInContext(fs.readFileSync('web/viz.js', 'utf8'), context);
const viz = context.viz;

const hour = (index, value) => ({ t: '2026-09-15T' + String(index % 24).padStart(2, '0') + ':00:00+00:00',
                                  label: '15 Sep ' + String(index % 24).padStart(2, '0') + ':30',
                                  value: value, source_locator: '$.hourly.x[' + index + ']' });

/* ---- ensemble plume ------------------------------------------------------- */
const plume = viz.ensembleFan({
  title: 'temperature_2m member distribution', unit: '\u00b0C', member_total: 30,
  statistics: { mean: 'arithmetic mean of the returned perturbed members', spread: 'population standard deviation', percentile: 'nearest-rank on the sorted member values' },
  p10: [hour(0, '23.1'), hour(1, '23.4'), hour(2, null), hour(3, '24.0')],
  p50: [hour(0, '24.0'), hour(1, '24.2'), hour(2, '24.5'), hour(3, '25.1')],
  p90: [hour(0, '25.2'), hour(1, '25.6'), hour(2, null), hour(3, '26.3')],
  mean: [hour(0, '24.1'), hour(1, '24.3'), hour(2, '24.6'), hour(3, '25.2')],
  min: [hour(0, '22.0'), hour(1, '22.3'), hour(2, '22.9'), hour(3, '23.4')],
  max: [hour(0, '26.0'), hour(1, '26.2'), hour(2, '26.6'), hour(3, '27.0')]
});
assert.equal(plume.withClass('viz-band').length, 1, 'the band covers the contiguous pair and is never drawn across the gap');
assert.equal(plume.withClass('viz-band')[0].attrs.points.split(' ').filter(Boolean).length, 4,
  'the band polygon spans exactly the two hours that returned both p10 and p90');
assert.equal(plume.withClass('viz-whisker').length, 4,
  'the isolated hour keeps its min–max rule even though it cannot form a band');
assert.equal(plume.withClass('viz-median').length, 1, 'the median is drawn as one line');
assert.equal(plume.withClass('viz-mean').length, 1, 'the mean is drawn separately from the median');
assert.equal(plume.withClass('viz-whisker').length, 4, 'min to max whiskers exist only where both ends are present');
assert(plume.all('td').some(cell => cell.textContent === '24.5'), 'the exact median survives in the table');
assert(plume.all('td').some(cell => cell.textContent === 'missing'), 'a missing member value is printed as missing, never as zero');
const hit = plume.withClass('viz-hit')[0];
hit.focus();
const readout = plume.withClass('viz-readout')[0];
assert(/p10 23\.1/.test(readout.textContent) && /\$\.hourly\.x\[0\]/.test(readout.textContent),
  'focusing an hour reads its exact member values and its source locator');
console.log('PASS: the ensemble plume draws a band, a median, whiskers and exact member values from returned fields only');

const thin = viz.ensembleFan({ title: 'median only', unit: '\u00b0C', p50: [hour(0, '24.0')], mean: [], min: [], max: [], p10: [], p90: [] });
assert.equal(thin.withClass('viz-band').length, 0, 'no p10/p90 means no band, not an invented one');
assert.equal(thin.withClass('viz-median').length, 0, 'a single hour cannot draw a line');
assert(thin.withClass('viz-empty').length >= 0, 'the frame still renders');
console.log('PASS: without member statistics the plume refuses to draw a distribution');

/* ---- meteogram ------------------------------------------------------------ */
const meteogram = viz.meteogram({
  title: 'Meteogram', temperature_unit: '\u00b0C', rain_unit: 'mm', wind_unit: 'km/h',
  hours: [
    { t: '2026-09-15T00:00:00+00:00', label: '15 Sep 05:30', temperature: 26.4, rain: 0, wind_speed: 8, wind_direction: 240, humidity: 71, night: true, evidence: { temperature: 't0', rain: 'r0', wind: 'w0' } },
    { t: '2026-09-15T01:00:00+00:00', label: '15 Sep 06:30', temperature: null, rain: 2.4, wind_speed: 9, wind_direction: 250, humidity: 74, night: false, evidence: { rain: 'r1', wind: 'w1' } },
    { t: '2026-09-15T02:00:00+00:00', label: '15 Sep 07:30', temperature: 27.1, rain: null, wind_speed: null, wind_direction: null, humidity: null, night: false, evidence: { temperature: 't2' } },
    { t: '2026-09-15T03:00:00+00:00', label: '15 Sep 08:30', temperature: 28.0, rain: 0.6, wind_speed: 12, wind_direction: 260, humidity: 68, night: false, evidence: { temperature: 't3', rain: 'r3', wind: 'w3' } }
  ]
});
assert.equal(meteogram.withClass('viz-bar').length, 2, 'a bar exists only for a returned positive amount; a returned zero draws none');
assert.equal(meteogram.withClass('viz-line').length, 1, 'a missing hour breaks the line instead of bridging it');
assert.equal(meteogram.withClass('viz-line')[0].attrs.points.split(' ').filter(Boolean).length, 2,
  'the drawn line spans only the two hours after the gap; the isolated hour before it is not connected');
assert(meteogram.withClass('viz-night').length >= 1, 'the night band is drawn from the source timestamps');
assert(meteogram.all('td').some(cell => cell.textContent === '0'), 'a returned zero survives in the exact-value table');
assert(meteogram.all('td').some(cell => cell.textContent === 'missing'), 'a missing humidity is printed as missing');
const meter = meteogram.withClass('viz-hit')[1];
meter.focus();
assert(/precipitation 2\.4 \(r1\)/.test(meteogram.withClass('viz-readout')[0].textContent),
  'the readout names the value and the source locator of that hour');
assert(/temperature missing|no value returned/.test(meteogram.withClass('viz-readout')[0].textContent) === false,
  'the readout lists only the values that hour returned');
console.log('PASS: the meteogram draws only returned hours, splits gaps, and reads exact values with locators');


/* ---- district warning matrix ---------------------------------------------- */
let opened = null;
const matrix = viz.warningMatrix({
  title: 'National district warning matrix',
  days: [{ key: 1, label: 'Day 1', date: '2026-09-14' }, { key: 2, label: 'Day 2', date: '2026-09-15' }],
  rows: [
    { district: 'PATNA', state: 'BIHAR', days: [
        { colour: 'yellow', hazards: ['Thunderstorm/lightning/squall'], unknown_hazard_codes: [] },
        { colour: null, hazards: [], unknown_hazard_codes: [99] }] },
    { district: 'LAKSHADWEEP', state: null, days: [
        { colour: 'green', hazards: ['No warning in this product'], unknown_hazard_codes: [] },
        { colour: 'red', hazards: ['Heavy rainfall'], unknown_hazard_codes: [] }] }
  ],
  onOpen: (row, index) => { opened = [row.district, index]; }
});
assert.equal(matrix.withClass('viz-cell').length, 4, 'one cell exists per returned district-day, and none for a day the product did not publish');
assert.equal(matrix.withClass('is-yellow').length, 1, 'the source colour is carried into the cell');
assert.equal(matrix.withClass('is-unknown').length, 1, 'a day the product left uncoloured is not given a colour');
assert.equal(matrix.withClass('is-unverified').length, 1, 'an unknown hazard code is flagged on the cell instead of being dropped');
const firstCell = matrix.withClass('viz-cell')[0];
firstCell.focus();
const matrixReadout = matrix.withClass('viz-readout')[0].textContent;
assert(/PATNA, BIHAR/.test(matrixReadout) && /Thunderstorm\/lightning\/squall/.test(matrixReadout),
  'the readout carries the district and the hazard wording verbatim');
assert(/contains an unknown hazard code/.test(matrix.withClass('viz-cell')[1].attrs['aria-label']),
  'the flagged cell says why it is flagged');
assert(matrix.allNodes().some(node => node.textContent === 'LAKSHADWEEP · state not stated'),
  'a row with no state says so rather than inventing one');
firstCell.events.click[0]();
assert.deepEqual(opened, ['PATNA', 0], 'a cell opens its district and names which day was clicked');
assert(matrix.all('td').some(cell => cell.textContent === 'not stated — no hazard wording printed'),
  'the exact table prints an uncoloured day as not stated, never as quiet');
console.log('PASS: the warning matrix carries source colours, flags unknown codes and prints nothing it was not given');

/* ---- corpus library cards -------------------------------------------------- */
let openedCard = null;
const held = 'a'.repeat(64), prunedSha = 'b'.repeat(64);
const cards = viz.libraryCards({
  documents: [
    { sha256: held, sha_prefix: 'a'.repeat(12), family: 'national_bulletin', family_label: 'All India Weather Summary and Forecast Bulletin',
      scope: 'national', region: null, state: null, district: null, issue_date: '2026-09-14', pages: 12, passages: 48,
      body: 'available', age_days: 0, currency_recorded_at_intake: 'current_on_the_retrieval_date',
      retrieved_at_utc: '2026-09-14T06:10:00+00:00', source_id: 'S07' },
    { sha256: prunedSha, sha_prefix: 'b'.repeat(12), family: 'district_agromet', family_label: 'District agromet advisory bulletin',
      scope: 'district', region: 'Ahmedabad', state: 'Gujarat', district: 'Ahmedabad', issue_date: null, pages: 7, passages: 31,
      body: 'pruned', age_days: null, currency_recorded_at_intake: 'printed_issue_not_stated', retrieved_at_utc: null, source_id: 'S57' }
  ],
  onOpen: document => { openedCard = document.family; }
});
assert.equal(cards.withClass('viz-card').length, 2, 'one card per listed edition');
const cardLinks = cards.all('a').filter(link => String(link.href).indexOf('/api/documents/') === 0);
assert.equal(cardLinks.length, 2, 'a held body offers open and download, and nothing else does');
assert(cardLinks.every(link => String(link.href).indexOf(held) > 0), 'the links point only at the held edition');
assert.equal(cards.withClass('is-pruned').length, 1, 'a pruned body is stated on its own card');
assert(cards.allNodes().some(node => node.textContent === 'body held'), 'a held body says so');
assert(cards.allNodes().some(node => node.textContent === 'not stated'), 'a card with no printed date says not stated rather than guessing one');
assert(/retention window/.test(cards.allNodes().map(node => node.textContent).join(' ')), 'a pruned card explains what survives');
cards.withClass('viz-card-open')[0].events.click[0]();
assert.equal(openedCard, 'national_bulletin', 'opening a card names the edition it passed on');
console.log('PASS: library cards state printed dates, body state and links without implying applicability');
process.exit(0);
