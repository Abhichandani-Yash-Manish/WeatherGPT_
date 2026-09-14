// Component-level bulletin-passage checks: citation binding, page locators and
// literal source text. Not a browser, visual or fluent-language acceptance test.
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path'), assert = require('assert');
const shim = require('./dom_shim.js');

const ROOT = path.join(__dirname, '..');
const document = shim.createDocument();
const context = Object.create(global);
context.document = document; context.Node = shim.Node; context.window = {};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/views.js'), 'utf8'), context);
vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/charts.js'), 'utf8'), context);

function walk(node, out) {
  out = out || [];
  (node.children || []).forEach(child => { out.push(child); walk(child, out); });
  return out;
}
function links(node) { return walk(node).filter(child => child.tag === 'a'); }
function summaries(node) { return walk(node).filter(child => child.tag === 'summary'); }
function paragraphs(node) { return walk(node).filter(child => child.tag === 'p'); }
function byText(node, tag, text) {
  return walk(node).filter(child => child.tag === tag && child.textContent === text)[0] || null;
}
function packetWith(passage, citation) {
  return {
    schema_version: 'weather-conversation-v1', conversation_id: 'x', question: 'What does the bulletin say?',
    status: 'answered', answer: 'Published passage', facts: [], notes: [], choices: [], charts: [], calculations: [],
    task_results: [], follow_up: null, expires_at_utc: null, answered_at_utc: '2026-09-13T05:00:00+00:00',
    trace: {}, resolved_points: {}, passages: [passage],
    citations: [{ id: 'other', url: 'https://example.com/unrelated', source_id: 'S00' }, citation]
  };
}
const basePassage = {
  id: 'p1', crop: 'Rice', stage: 'Tillering', district: 'Kamrup', page: 2,
  issue_date: '2026-09-11', forecast_start: '2026-09-12', forecast_end: '2026-09-16',
  text: '<script>untrusted source text</script>', citation_ids: ['t1-doc']
};

// 1. a passage uses its own bound citation, keeps the page locator, escapes text and refuses unsafe URLs
const bound = { id: 't1-doc', url: 'https://imdagrimet.gov.in/Services/DistrictBulletin.php?district=Kamrup', source_id: 'S27' };
let card = context.renderTurn(packetWith(Object.assign({}, basePassage), bound), {});
const page = byText(card, 'a', 'Open the original bulletin page');
assert(page, 'A passage links to its own bound source');
assert(page.href.indexOf('district=Kamrup#page=2') >= 0, 'The link carries the page locator: ' + page.href);
assert.equal(page.rel, 'noopener noreferrer');
assert(byText(card, 'p', '<script>untrusted source text</script>'), 'Source text is inserted as text, never as markup');
assert(summaries(card).some(node => /Rice/.test(node.textContent) && /Kamrup/.test(node.textContent)), 'The passage names its crop and district');
console.log('PASS: passage uses its bound citation, page locator, literal source text and HTTPS-only link (component only)');

// 2. a non-HTTPS citation never becomes a link
card = context.renderTurn(packetWith(Object.assign({}, basePassage), { id: 't1-doc', url: 'javascript:alert(1)', source_id: 'S27' }), {});
assert(!byText(card, 'a', 'Open the original bulletin page'), 'A javascript: URL is never offered as a link');
assert(links(card).every(link => String(link.href).indexOf('javascript:') !== 0), 'No unsafe href reaches the page');
console.log('PASS: a non-HTTPS source URL is never offered as a link');

// 3. an immutable saved PDF with the same page is preferred, and still downloadable
const saved = { id: 't1-doc', url: 'https://imdagrimet.gov.in/current.pdf', source_id: 'S27', local_document_path: '/api/documents/' + 'a'.repeat(64) };
card = context.renderTurn(packetWith(Object.assign({}, basePassage), saved), {});
const savedOpen = byText(card, 'a', 'Open the saved source PDF');
assert(savedOpen, 'The stored copy is offered');
assert.equal(savedOpen.href, '/api/documents/' + 'a'.repeat(64) + '#page=2');
assert(!byText(card, 'a', 'Open the original bulletin page'), 'The changing publisher URL is not preferred over the stored copy');
console.log('PASS: immutable stored PDF page is preferred to a changing publisher URL');

// 4. parent bulletin context is labelled apart from crop evidence and states its own limit
const parentPassage = Object.assign({}, basePassage, { evidence_kind: 'published_bulletin_context', section: 'Weather Warning', crop: '', stage: '' });
card = context.renderTurn(packetWith(parentPassage, saved), {});
assert(summaries(card).some(node => /^Bulletin context: Weather Warning/.test(node.textContent)), 'Parent context is labelled as context');
assert(paragraphs(card).some(node => /current warning and individual field applicability remain unverified/.test(node.textContent)), 'Context states that warning status stays unverified');
assert(byText(card, 'a', 'Open the saved source PDF'), 'A context passage still links its page');
console.log('PASS: parent context is labelled separately from crop evidence and current alerts');

// 5. the saved PDF keeps a same-origin download fallback
const download = byText(card, 'a', 'Download saved PDF');
assert(download, 'A download fallback exists beside the open action');
assert.equal(download.href, saved.local_document_path);
assert.equal(download.download, 'bulletin-' + 'a'.repeat(64) + '.pdf');
assert(links(card).filter(link => String(link.href).indexOf('//') === -1).length >= 2, 'Saved-document links stay on this origin');
console.log('PASS: saved PDF has a same-origin download fallback');
