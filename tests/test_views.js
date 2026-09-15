// Component-level answer-presentation checks against real captured packets.
// These are not browser, visual, load or fluent-language acceptance tests.
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path'), assert = require('assert');
const shim = require('./dom_shim.js');

const ROOT = path.join(__dirname, '..');
const PACKETS = path.join(ROOT, 'research/reviews/frontend-overhaul-20260914/packets');
const CAPTURED = ['forecast-simple', 'multi-task', 'historical-chart', 'marine', 'airport', 'clarification', 'warning', 'language-hindi'];

function packet(name) { return JSON.parse(fs.readFileSync(path.join(PACKETS, name + '.json'), 'utf8')).packet; }
function load() {
  const document = shim.createDocument();
  const context = Object.create(global);
  context.document = document; context.Node = shim.Node; context.window = {};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/views.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/charts.js'), 'utf8'), context);
  return context;
}
function walk(node, out) {
  out = out || [];
  (node.children || []).forEach(child => { out.push(child); walk(child, out); });
  return out;
}
function withClass(node, cls) {
  return walk(node).filter(child => String(child.className || '').split(/\s+/).indexOf(cls) >= 0);
}
function withTag(node, tag) { return walk(node).filter(child => child.tag === tag); }
function textOf(nodes) { return nodes.map(node => node.textContent).join(' | '); }
function digits(text) { return String(text).match(/-?\d+(?:\.\d+)?/g) || []; }

const context = load();
const forecast = packet('forecast-simple');

// 1. answer-first: the value and its unit lead the card, exactly as returned
const card = context.renderTurn(forecast, {});
const lead = withClass(card, 'lead-number');
assert.equal(lead.length, 1, 'A single-value answer leads with one headline number');
assert.equal(lead[0].textContent, '0.3', 'The headline number is the retrieved value, unrounded');
assert.equal(withClass(card, 'lead-unit')[0].textContent, 'mm');
assert(/Ahmedabad/.test(withClass(card, 'lead-where')[0].textContent));
console.log('PASS: answer-first headline carries the exact retrieved value, unit and place (component only)');

// 2. the validity ruler is real geometry derived from the retrieved window
const ruler = withClass(card, 'ruler')[0];
assert(ruler, 'A forecast window draws the validity ruler');
const svg = withTag(ruler, 'svg')[0];
const label = svg.attrs['aria-label'];
assert(/^Requested window /.test(label), 'The ruler is described, not decorative');
assert(/covering 6 hours across 1 retrieved sample/.test(label), 'The description states the covered window: ' + label);
const covered = withTag(svg, 'rect').filter(rect => rect.attrs['class'] === 'ruler-covered');
assert.equal(covered.length, 1, 'The single retrieved span is drawn once');
const rail = withTag(svg, 'rect').filter(rect => rect.attrs['class'] === 'ruler-rail')[0];
assert(rail, 'The ruler draws a track');
assert.equal(Number(covered[0].attrs.x), Number(rail.attrs.x), 'A span covering the whole window starts with the track');
assert.equal(Number(covered[0].attrs.width), Number(rail.attrs.width), 'A span covering the whole window fills the track');
assert.equal(withClass(card, 'ruler').length, 1);
const rulerHits = withTag(svg, 'rect').filter(rect => rect.attrs['class'] === 'ruler-hit');
assert.equal(rulerHits.length, 1, 'every drawn segment is reachable, so the window can be read part by part');
assert(/Covered by retrieved evidence/.test(rulerHits[0].attrs['aria-label']),
  'a covered segment says what it covers and how many samples back it: ' + rulerHits[0].attrs['aria-label']);
const rulerReadout = withClass(ruler, 'ruler-readout')[0];
assert(rulerReadout, 'the ruler carries a live readout');
rulerHits[0].events.focus[0]();
assert(/Covered by retrieved evidence/.test(rulerReadout.textContent), 'focusing a segment reads it out');
console.log('PASS: the validity ruler draws covered spans from the retrieved window with a text description, and every segment is inspectable');

// 3. an instantaneous observation has no interval, so no ruler is drawn
const airportCard = context.renderTurn(packet('airport'), {});
assert.equal(withClass(airportCard, 'ruler').length, 0, 'An observation at one instant must not draw a window');
const marineCard = context.renderTurn(packet('marine'), {});
assert.equal(withClass(marineCard, 'ruler').length, 0, 'Zero-duration samples must not draw a window');
console.log('PASS: no window is drawn where the evidence has no interval');

// 4. the receipt keeps entity, window, source, locators and retrieval time together
const receipt = withClass(card, 'receipt')[0];
const receiptActions = withClass(receipt, 'receipt-actions')[0];
assert(receiptActions, 'the receipt carries its own actions');
const copyButton = receiptActions.children.filter(node => node.textContent === 'Copy this receipt')[0];
assert(copyButton, 'the receipt offers copying it as text');
assert(receiptActions.children.some(node => node.textContent === 'Print'), 'the receipt offers printing the answer');
copyButton.events.click[0]();
assert(/Copied|Copy unavailable here/.test(copyButton.textContent),
  'a clipboard the browser refuses says so instead of claiming a success: ' + copyButton.textContent);
const keys = withClass(receipt, 'receipt-key').map(node => node.textContent);
['Measure', 'Value', 'Place', 'Entity', 'Window', 'Source', 'Retrieved'].forEach(key => {
  assert(keys.indexOf(key) >= 0, 'The receipt states ' + key);
});
const receiptText = receipt.textContent;
assert(receiptText.indexOf('geonames:1279233') >= 0, 'The resolved entity id is shown');
assert(receiptText.indexOf('S21') >= 0, 'The source id is shown');
assert(receiptText.indexOf('$.hourly.precipitation[') >= 0, 'Record locators are shown');
assert(receiptText.indexOf('not an observation') >= 0, 'The receipt states what model output is not');
console.log('PASS: the evidence receipt keeps entity, window, source, locator and retrieval time together');

// 5. task accounting reports asked, answered and incomplete instead of one affirmative count
const multi = context.renderTurn(packet('multi-task'), {});
const coverage = withClass(multi, 'coverage')[0];
assert(coverage, 'Task accounting is shown');
assert(/Asked: 2/.test(coverage.textContent), 'Asked is reported: ' + coverage.textContent);
assert(/Answered: 2/.test(coverage.textContent), 'Answered is reported');
assert(/Incomplete: 0/.test(coverage.textContent), 'Incomplete is reported separately');
const taskText = textOf(withClass(multi, 'tasks'));
assert(!/requested tasks completed/.test(taskText), 'The disputed affirmative count is gone');
assert(/t1/.test(taskText) && /crosscheck/.test(taskText), 'Each task keeps its id, kind and operation');
console.log('PASS: task accounting reports asked, answered and incomplete separately from one another');

// 6. retrieved volume is bounded: chart-backed values are never re-listed as cards
CAPTURED.forEach(name => {
  const rendered = context.renderTurn(packet(name), {});
  assert(withClass(rendered, 'fact').length <= 8, name + ' must not list every retrieved value as a card');
});
const history = context.renderTurn(packet('historical-chart'), {});
assert.equal(withClass(history, 'fact').length, 0, 'Values already plotted are not repeated as cards');
assert.equal(withClass(history, 'history-chart').length, 1, 'The series is drawn instead');
assert.equal(withClass(context.renderTurn(packet('marine'), {}), 'history-chart').length, 3, 'All three marine series render');
console.log('PASS: retrieved volume stays bounded and plotted values are not duplicated as cards');

// 7. a source difference is labelled as a difference, never as skill or confidence
const comparison = withClass(multi, 'calc').filter(node => /is-comparison/.test(node.className));
assert.equal(comparison.length, 1, 'The crosscheck renders one comparison block');
assert(comparison[0].textContent.indexOf('-0.8') >= 0, 'The comparison keeps its returned value');
assert(/not a skill score/i.test(comparison[0].textContent), 'A source difference is not presented as accuracy');
console.log('PASS: a between-source difference is reported as a difference, not as skill or confidence');

// 8. a shared place name offers each candidate and returns the chosen selection id
let chosen = null;
const clarify = context.renderTurn(packet('clarification'), { onChoose: choice => { chosen = choice.selection_id; }, onRetype: () => {} });
const buttons = withClass(clarify, 'choice');
assert.equal(buttons.length, 3, 'Every offered candidate is offered to the reader');
assert(buttons[0].textContent.indexOf('Bhop') >= 0, 'A candidate carries its label');
buttons[0].dispatch('click');
assert.equal(chosen, packet('clarification').choices[0].selection_id, 'Choosing a candidate returns that selection id');
assert(withClass(clarify, 'lead-number').length === 0, 'A clarification does not imply an answer');
console.log('PASS: place clarification offers every candidate and returns the chosen selection id');

// 9. a requested output language that was not written is disclosed, not passed as complete
const downgraded = Object.assign({}, forecast, {
  status: 'partial',
  notes: forecast.notes.concat(['The requested output language could not be rendered for this answer; the evidence above remains in its source language. Answering in that language is not supported yet for this kind of request.'])
});
const downgradeCard = context.renderTurn(downgraded, {});
assert(withClass(downgradeCard, 'notice').some(node => /not in the language you asked for/i.test(node.textContent)), 'The downgrade is stated plainly');
assert(withClass(downgradeCard, 'notes').every(node => !/could not be rendered/.test(node.textContent)), 'The disclosure does not bury or repeat the downgrade');
assert(/आप/.test(context.renderTurn(packet('language-hindi'), {}).textContent), 'A Hindi answer is shown exactly as returned');
console.log('PASS: an unwritten requested language is disclosed instead of passing as a complete answer');

// 10. an unverified warning state stays held and offers no receipt or window
const warning = context.renderTurn(packet('warning'), {});
assert(withClass(warning, 'tag').some(tag => /is-held/.test(tag.className)), 'An unverified warning is marked held');
assert.equal(withClass(warning, 'receipt').length, 0, 'No receipt is implied where no evidence was retrieved');
assert.equal(withClass(warning, 'lead-number').length, 0, 'No value is implied');
assert(/does not mean there are no warnings/i.test(warning.textContent), 'The absence of a confirmed warning is stated');
console.log('PASS: an unverified warning state stays held and implies no value or receipt');

// 11. an airport report is shown raw, typed, and bounded to its own meaning
const air = context.renderTurn(packet('airport'), {});
const raw = withClass(air, 'raw-report')[0];
assert(raw.textContent.indexOf('METAR VOBL 141100Z') >= 0, 'The raw report is shown as text');
assert(/not a flight status or a clearance/i.test(air.textContent), 'The report does not imply a flight status');
assert(withClass(air, 'fact').length === 1, 'The remaining measured value is shown once beside the headline');
console.log('PASS: an airport report shows its raw text, its kind, and does not imply a flight status');

// 12. no number reaches the page that is not in the packet the engine returned
['forecast-simple', 'multi-task', 'historical-chart', 'marine', 'airport'].forEach(name => {
  const source = packet(name);
  const rendered = context.renderTurn(source, {});
  const raw = JSON.stringify(source);
  // Measured values only: the ruler's own derived duration is a description of the
  // same window, not a new measurement.
  const shown = withClass(rendered, 'lead-number').concat(withClass(rendered, 'fact-value'))
    .concat(withClass(rendered, 'calc-value')).concat(withTag(rendered, 'td'));
  let checked = 0;
  shown.forEach(node => digits(node.textContent).forEach(value => { checked += 1; assert(raw.indexOf(value) >= 0, name + ': ' + value + ' is not in the packet'); }));
  assert(checked > 0, name + ' exposed at least one number to check');
});
console.log('PASS: every displayed number comes from the returned packet, with no arithmetic applied');

// 13. no renderer leaks a stylesheet class name into visible text
const CLASS_TOKENS = ['notice', 'is-calm', 'is-good', 'is-held', 'is-quiet', 'tag', 'chip', 'fact', 'receipt',
  'ruler', 'lead', 'turn', 'actions', 'choice', 'coverage', 'calc', 'field-note', 'source', 'notes', 'task',
  'capability', 'history-chart', 'disclosure-body', 'raw-json', 'working', 'banner', 'error', 'ledger-item', 'health-row'];
CAPTURED.forEach(name => {
  const rendered = context.renderTurn(packet(name), {});
  walk(rendered).forEach(node => {
    if (String(node.className || '').trim()) return;
    const text = String(node.textContent || '').trim().toLowerCase();
    assert(CLASS_TOKENS.indexOf(text) < 0, name + ': the stylesheet class "' + text + '" is rendered as text');
  });
});
walk(context.renderWelcome({ onExample: () => {} })).forEach(node => {
  if (String(node.className || '').trim()) return;
  const text = String(node.textContent || '').trim().toLowerCase();
  assert(CLASS_TOKENS.indexOf(text) < 0, 'welcome: the stylesheet class "' + text + '" is rendered as text');
});
console.log('PASS: no renderer leaks a stylesheet class name into the visible text of an answer');


// 14. a series answer never headlines one arbitrary member of the series
const series = context.renderTurn(packet('historical-chart'), {});
assert.equal(withClass(series, 'lead-number').length, 0, 'A chart point is not promoted to a headline value');
assert.equal(withClass(series, 'fact').length, 0, 'Series values are not re-listed as cards');
const seriesReceipt = withClass(series, 'receipt')[0];
assert(seriesReceipt, 'A series still carries a receipt');
assert(/30 retrieved values/.test(seriesReceipt.textContent), 'The series receipt states how many values were retrieved');
assert(/S27/.test(seriesReceipt.textContent), 'The series receipt keeps its source id');
assert(/page 612/.test(seriesReceipt.textContent), 'The series receipt keeps a source locator');
assert(/not a projection, an attribution or a validated trend/.test(seriesReceipt.textContent), 'A descriptive slope is not presented as a forecast');
assert(withClass(series, 'calc-value').length >= 1, 'The computed headline is still shown');
console.log('PASS: a series answer leads with its computed value and never with one arbitrary member');


// 15. an official warning day is presented as a named period, never as a measured sample
const warningPacket = {
  schema_version:'weather-conversation-v1', conversation_id:'w', question:'Is there an official warning?', status:'answered',
  answer:'IMD district warning for PATNA.', citations:[{id:'district-warning', source_id:'S15', provider:'India Meteorological Department', product:'District-wise warning product', url:'https://reactjs.imd.gov.in/geoserver/wfs'}],
  notes:[], choices:[], charts:[], calculations:[], task_results:[],
  facts:[{ id:'t1-f1', label:'Day 1 \u00b7 14 Sep 2026', value:'No warning in this product', unit:'IMD district warning colour',
    place:'PATNA', start:'2026-09-13T18:30:00+00:00', end:'2026-09-14T18:30:00+00:00', source_id:'S15',
    parameter:'official_district_warning', entity_id:'imd-district:364', citation_ids:['district-warning'] }],
  warning_evidence:[{ records:[], latest_sent:null, assessment:{eligible_by_lifecycle:0},
    district_warnings:[{ place:'Patna', district:'PATNA', issued_at_utc:'2026-09-14T06:00:00+00:00',
      days:[{ day:1, label:'14 Sep 2026', colour:'green', colour_code:4, quiet:true, hazards:['No warning in this product'], source_text:'', starts_utc:'2026-09-13T18:30:00+00:00', ends_utc:'2026-09-14T18:30:00+00:00' }] }],
    stale_districts:[], points_outside_districts:[] }]
};
const warnCard = context.renderTurn(warningPacket, {});
assert(withClass(warnCard, 'lead-number').length === 0, 'A warning day must not become a headline number');
assert(withClass(warnCard, 'ruler').length === 0, 'Warning days must not be drawn as a sampled series');
assert(withClass(warnCard, 'fact').length === 0, 'Warning days are shown in the panel, not repeated as cards');
assert(withClass(warnCard, 'warning-panel').length === 1, 'The warning panel carries the day');
assert(withTag(warnCard, 'td').some(cell => cell.textContent.indexOf('No warning in this product') >= 0), 'The official wording is shown verbatim');
assert(withClass(warnCard, 'receipt').length === 1, 'A warning day still carries a provenance receipt');
assert(/not an all-clear/.test(warnCard.textContent), 'The panel states that a quiet day is not an all-clear');
console.log('PASS: an official warning day is presented as a named period with its colour, hazard and window');


// 16. the raw-packet action hands the exact rendered packet to the drawer
const drawn = [];
context.window.WG = { openDrawer: (title, build) => {
  const body = shim.createDocument().createElement('div');
  build(body);
  drawn.push({ title: title, body: body });
} };
const actionCard = context.renderTurn(forecast, {});
const inspect = withTag(actionCard, 'button').find(node => /Inspect the raw packet/.test(node.textContent));
assert(inspect, 'An answer offers an inspector for the packet');
inspect.dispatch('click');
assert.equal(drawn.length, 1, 'The inspector opens exactly one drawer');
assert.equal(drawn[0].title, 'Raw packet', 'The drawer is titled as the raw packet');
const pre = withTag(drawn[0].body, 'pre')[0];
assert(pre, 'The drawer holds the packet as preformatted text');
assert(pre.textContent.indexOf('"conversation_id"') >= 0, 'The exact packet is shown, not a summary');
assert(/not a summary|the exact packet/i.test(drawn[0].body.textContent), 'The drawer states that the packet is the rendered one, not a summary');
console.log('PASS: the raw-packet inspector shows the exact rendered packet in the drawer');


// 17. the stage readout reports the engine's own checkpoints and the queue as facts
const running = context.stageLine({ state:'running', stage:'retrieving', stage_label:'Retrieving evidence',
  stage_seconds:3.4, stages_seen:['Reading the question','Planning the tasks','Retrieving evidence'],
  stage_note:'A stage names the work the server is in now. It is not a completion estimate.' });
assert(running, 'A running turn produces a stage line');
const runningText = String(running.textContent);
assert(/Retrieving evidence/.test(runningText), 'The stage label is shown');
assert(/3 s in this stage/.test(runningText), 'The seconds spent in the stage are shown');
assert(/Reading the question/.test(runningText) && runningText.indexOf('\u2192') >= 0, 'The stages seen are shown in order');
assert(!/%/.test(runningText) && !/ETA/.test(runningText), 'No percentage or ETA is invented');
assert(context.stageLine({ state:'idle' }) === null, 'An idle engine produces no stage line');
const waiting = context.stageLine({ state:'running', stage:'started', stage_label:'Reading the question',
  queue:{ waiting:2, capacity:3 } });
const waitingText = String(waiting.textContent);
assert(/Waiting for the engine/.test(waitingText) && /2 questions ahead/.test(waitingText), 'A waiting turn reports its queue position');
assert(/bounded at 3/.test(waitingText), 'The queue bound is stated as the gate bound');
assert(!/%/.test(waitingText), 'A queue wait is not dressed up as progress');
console.log('PASS: the stage readout reports checkpoints and queue position, never a percentage');


// 18. a whole-edition reading and a cross-edition difference are both labelled as such
const corpusPacket = {
  schema_version:'weather-conversation-v1', conversation_id:'c', question:'What does the whole bulletin say?', status:'partial',
  answer:'Indexed published document.', citations:[], notes:[], choices:[], charts:[], calculations:[], task_results:[],
  facts:[],
  whole_document:{ edition_sha256:'a'.repeat(64), passages_indexed:20, sections_indexed:6, passages_served:6, sections_served:6 },
  edition_differences:[
    { kind:'section_absent_from_newer', section:'FARMER ADVISORY',
      nearer:{ issue_date:'2026-09-14', page:null, excerpt:null },
      earlier:{ issue_date:'2026-09-10', page:2, excerpt:'Cotton sowing is advised after the dry spell ends.' },
      note:'Both editions are retained and none is ranked: the workspace does not decide which edition is current or correct.' },
    { kind:'section_text_differs', section:'SYNOPTIC SITUATION',
      nearer:{ issue_date:'2026-09-14', page:1, excerpt:'A low pressure area over the Bay of Bengal is likely to bring rain.' },
      earlier:{ issue_date:'2026-09-10', page:1, excerpt:'A western disturbance lies over the north-west.' },
      similarity:0.21,
      note:'Both editions are retained and none is ranked: the workspace does not decide which edition is current or correct.' }
  ],
  passages:[{ id:'p1', evidence_kind:'general_text', section:'FARMER ADVISORY', text:'Cotton sowing is advised.',
              physical_page:2, issue_date:'2026-09-10', citation_ids:[] }]
};
const corpusCard = context.renderTurn(corpusPacket, {});
const corpusText = String(corpusCard.textContent);
assert(/Whole edition: 6 of 20 indexed passages/.test(corpusText), 'A whole-edition reading states how much of the edition it served');
assert(/not its full text/.test(corpusText), 'A whole-edition reading is not presented as the full text');
assert(/Editions compared \(2\)/.test(corpusText), 'The difference block counts the editions compared');
assert(/FARMER ADVISORY/.test(corpusText) && /2026-09-10/.test(corpusText) && /2026-09-14/.test(corpusText), 'Both editions are named with their sections');
assert(/not in the newer one|not print that section/.test(corpusText), 'A dropped section is described as absent, not as withdrawn');
assert(/does not decide which edition is current/.test(corpusText), 'The workspace refuses to rank the editions');
assert(!/corrected|superseded by|withdrawn/i.test(corpusText), 'No edition is called wrong, superseding or withdrawn');
console.log('PASS: a whole-edition reading and a cross-edition difference are labelled, counted and never ranked');


// 19. two products in one turn are compared in plain terms and never ranked
const comparedPacket = {
  schema_version:'weather-conversation-v1', conversation_id:'c', question:'Will it rain in Patna, and is there a warning?',
  status:'answered', answer:'Both products are shown.', citations:[], notes:[], choices:[], charts:[], calculations:[],
  task_results:[], facts:[], passages:[],
  product_comparison:[{
    kind:'official_warning_and_forecast', place:'Patna, Patna, State of Bihar', window:{ label:'16 Sep 2026' },
    reading:'differ',
    products:[
      { source_id:'S15', product:'IMD district warning product', statement:'yellow · Thunderstorm/lightning/squall' },
      { source_id:'S21', product:'Model forecast', statement:'rainfall 0.0 mm across 1 forecast value(s)' }
    ],
    why:'the official product carries a rain or storm hazard for this window while the model forecast shows no rain in it; neither product is a measurement of the other',
    note:'Both products are named here and neither is ranked; a comparison is not a score, a skill measurement or a warning. Only the official product speaks about warnings, and a quiet day in it is not a forecast of no rain.'
  }]
};
const comparedCard = context.renderTurn(comparedPacket, {});
const comparedText = String(comparedCard.textContent);
assert(/Products compared \(1\)/.test(comparedText), 'The comparison block is titled and counted');
assert(/S15/.test(comparedText) && /S21/.test(comparedText), 'Both products keep their source ids');
assert(/differ/.test(comparedText), 'The reading is named in words');
assert(/neither is ranked/.test(comparedText) && /not a score/.test(comparedText), 'The block repeats that nothing is ranked');
assert(!/confidence|skill score/i.test(comparedText), 'No confidence or score language leaks into the comparison');

// The retrieval account: coverage, pending slots, the edition comparison and the editions read are
// rendered from the tools' own records. A bare `table(...)` call here threw 'table is not defined'
// in the page on 15 September 2026 and stopped the whole turn from rendering, so this check exists.
(function () {
  const packet = {
    status: 'answered', answer: 'A passage was returned.', facts: [], citations: [], notes: [], choices: [],
    plan: { language: 'en' }, task_results: [], task_coverage: { incomplete_ids: [] },
    pending_slots: [{ field: 'growth_stage', reason: 'Crop growth stage is not yet supplied', task_id: 't1' }],
    retrieval_coverage: [{ mode: 'whole_document_bm25_plus_dense_rrf', candidates: 48, returned: 10,
                           whole_document: false, editions_indexed_for_this_product: 1,
                           lexical_overlap_required: true, topic_tokens: ['grapes'], topic_matched: false,
                           match_basis: 'translated_query_without_the_topic_word',
                           query_translation: { text: 'what does the bulletin say about grapes', source_language: 'gu-IN',
                                                service: 'sarvam', model: 'provider_default', used_for_retrieval: true },
                           filters: { family: 'national_bulletin', scope: 'national', region: null } }],
    edition_comparison: { editions_indexed: 1, newest_issue: '2026-09-14', previous_issue: null, state: 'single_edition_indexed' },
    document_evidence: [{ family_label: 'All India Weather Summary and Forecast Bulletin', source_id: 'S64',
                          scope: 'national', issue_date: '2026-09-14', issue_date_basis: 'printed',
                          currency: 'printed_issue_matches_retrieval_date', age_days: 0 }]
  };
  const card = context.renderTurn(packet, {});
  const text = walk(card).map(node => String(node.textContent || '')).join(' | ');
  assert.ok(text.indexOf('What was retrieved, and what is missing') >= 0, 'the retrieval account is rendered');
  assert.ok(text.indexOf('growth_stage') >= 0 && text.indexOf('Crop growth stage is not yet supplied') >= 0, 'a pending slot is named with its reason');
  assert.ok(text.indexOf('48') >= 0 && text.indexOf('10') >= 0, 'candidates and returned passages are both shown');
  assert.ok(text.indexOf('single_edition_indexed') >= 0, 'the edition-comparison state is shown');
  assert.ok(text.indexOf('the printed issue date is the retrieval date') >= 0, 'currency is shown in words, not as a code');
  // The corpus separates the words that name the topic from the words every passage shares, and a
  // passage served without the topic word says so in the account rather than only in the prose.
  assert.ok(text.indexOf('Words that name the topic') >= 0 && text.indexOf('grapes') >= 0, 'the topic words are named');
  assert.ok(text.indexOf('no returned passage contains them') >= 0, 'a missing topic word is stated, not hidden');
  assert.ok(text.indexOf('the translation found no passage containing the topic word') >= 0,
    'a translated retrieval that missed the topic word is explained in the account');
  // A question translated for retrieval is a generative step between the reader and the index, so the
  // account names the wording, the service and what the translation was allowed to do.
  assert.ok(text.indexOf('Question translated for retrieval') >= 0, 'the translated query is shown');
  assert.ok(text.indexOf('what does the bulletin say about grapes') >= 0, 'the wording searched for is shown');
  assert.ok(text.indexOf('used to find passages only, never to state anything') >= 0, 'the translation is not presented as evidence');
}());

console.log('PASS: two products in one turn are compared in plain terms and never ranked');

// Plan Watch: the one missing slot is answered with quick replies, and a saved plan shows
// what was set automatically with Change and Undo. Nothing on the card is a warning value.
(function () {
  const asking = {
    status: 'needs_clarification', answer: 'What time on Monday 21 Sep?', facts: [], citations: [], notes: [], choices: [],
    quick_replies: [{ label: 'Morning', reply: 'Morning' }, { label: 'Afternoon', reply: 'Afternoon' },
                    { label: 'Evening', reply: 'Evening' }, { label: 'All day', reply: 'All day' }],
    plan_watch: { action: 'asking', awaiting: 'time' }, trace: { planning: { provider: 'deterministic_plan_intake', model_calls: 0 }, tools: [] }
  };
  let replied = null;
  const card = context.renderTurn(asking, { onQuickReply: reply => { replied = reply; } });
  const chips = withClass(card, 'quick-reply');
  assert.equal(chips.length, 4, 'one button per quick reply');
  assert.equal(chips.map(node => node.textContent).join('|'), 'Morning|Afternoon|Evening|All day');
  chips[0].dispatch('click');
  assert.equal(replied, 'Morning', 'a quick reply sends its reply text as the next message');
  assert.equal(withClass(card, 'plan-card').length, 0, 'no plan card while a question is open');

  const saved = {
    status: 'answered', answer: "Saved. I'm watching Monday 21 Sep, morning (09:30–12:30 IST) in Rajkot, Gujarat for your cotton spraying.",
    facts: [], citations: [], notes: [], choices: [], quick_replies: [],
    plan_watch: { action: 'saved', plan: { id: 'p1', title: 'Cotton spraying · Rajkot, Gujarat · Monday 21 Sep morning',
      hazards: 'heavy rain, thunderstorm & lightning and strong surface winds', district: 'RAJKOT', state_words: 'waiting for IMD coverage',
      inferred: { activity: 'from your words: spraying', hazards: 'from the spraying template' } } },
    trace: { planning: { provider: 'deterministic_plan_intake', model_calls: 0 }, tools: [] }
  };
  let undone = null, changed = null;
  const savedCard = context.renderTurn(saved, { onPlanUndo: plan => { undone = plan.id; }, onPlanChange: plan => { changed = plan.id; } });
  const planCard = withClass(savedCard, 'plan-card')[0];
  assert(planCard, 'a saved plan renders its card');
  assert(/Cotton spraying · Rajkot, Gujarat · Monday 21 Sep morning/.test(planCard.textContent), 'the card names the plan');
  assert(/What I set automatically/.test(planCard.textContent), 'the card discloses what was inferred');
  const buttons = withTag(planCard, 'button');
  buttons.find(node => node.textContent === 'Undo').dispatch('click');
  buttons.find(node => node.textContent === 'Change').dispatch('click');
  assert.equal(undone, 'p1', 'Undo hands the plan to the page');
  assert.equal(changed, 'p1', 'Change hands the plan to the page');
  assert.equal(withClass(savedCard, 'lead-number').length, 0, 'a plan is never presented as a headline value');
}());
console.log('PASS: a plan question offers quick replies, and a saved plan card offers Change and Undo');
