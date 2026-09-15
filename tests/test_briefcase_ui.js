// Component checks for the reading position and the briefcase.
// These run against the DOM shim with recorded payloads: they pin what the page
// shows and what it asks the server for. They are not browser, styling or
// delivery acceptance tests.
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path'), assert = require('assert');
const shim = require('./dom_shim.js');

const ROOT = path.join(__dirname, '..');
const PANELS = fs.readFileSync(path.join(ROOT, 'web/panels.js'), 'utf8');

function walk(node, out) {
  out = out || [];
  (node.children || []).forEach(child => { out.push(child); walk(child, out); });
  return out;
}
function textOf(node) { return walk(node).map(child => child.textContent).join(' | '); }
function buttons(node) { return walk(node).filter(child => child.tag === 'button'); }
function buttonNamed(node, name) { return buttons(node).filter(child => String(child.textContent).indexOf(name) >= 0)[0] || null; }

function entry(id, title) {
  return { id: id, saved_at: '2026-09-15T06:30:00+00:00', kind: 'alert_brief', title: title,
           place: { district: 'PATNA', state: 'BIHAR', label: 'Patna, Bihar' },
           window: { label: '15 Sep 2026', starts_utc: '2026-09-15T18:30:00+00:00', ends_utc: '2026-09-16T18:30:00+00:00' },
           content_sha256: 'ab'.repeat(32), sources: ['S63'], status: 'ok',
           evidence: { sources: ['S63'], not_established: ['No all-clear is implied.'], notes: [] },
           delivery: 'local_only_no_delivery' };
}

function load(payloads) {
  const document = shim.createDocument();
  const context = Object.create(global);
  context.document = document; context.Node = shim.Node; context.window = {};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/views.js'), 'utf8'), context);
  const calls = [], downloads = [], drawers = [];
  let renders = 0;
  context.window.WG = context.WG = {
    state: {}, panels: {},
    api: (route, params) => { calls.push({ route: route, params: params }); return Promise.resolve(payloads[route] || {}); },
    apiText: route => { calls.push({ route: route }); return Promise.resolve('# Alert brief - PATNA, BIHAR\n\nKept body.'); },
    post: (route, body) => { calls.push({ route: route, body: body }); return Promise.resolve({ entry: { title: 'Alert brief — PATNA, BIHAR' } }); },
    download: (name, text, kind) => downloads.push({ name: name, text: text, kind: kind }),
    clear: node => node.replaceChildren(),
    openDrawer: (title, build) => { const body = new shim.Node('div'); build(body); drawers.push({ title: title, body: body }); },
    render: () => { renders += 1; },
    freshness: () => 'Read just now',
    colourChip: (colour, label) => { const node = new shim.Node('span'); node.textContent = label; return node; },
    block: (title, note) => { const node = new shim.Node('section'); node.append(context.el('h2', title)); if (note) node.append(context.el('p', note)); return node; },
    stateBlock: (kind, message, detail) => { const node = new shim.Node('div'); node.append(context.el('p', message)); if (detail) node.append(context.el('p', detail)); return node; },
    table: (head, rows) => { const node = new shim.Node('table'); node.textContent = head.join(' | ') + ' -- ' + rows.map(row => row.join(' : ')).join(' ;; '); return node; }
  };
  vm.runInContext(PANELS, context);
  return { context: context, calls: calls, downloads: downloads, drawers: drawers, renders: () => renders };
}

async function main() {
  // 1. Kept entries render with their own provenance and no invented delivery.
  const view = { schema_version: 'briefcase-v1', delivery: 'local_only_no_delivery',
                 note: 'Kept in the local store. Nothing is delivered, pushed or published from here.',
                 briefs: [entry('11111111-2222-3333-4444-555555555555', 'Alert brief — PATNA, BIHAR')] };
  const saved = { schema_version: 'briefcase-entry-v1', delivery: 'local_only_no_delivery', entry: view.briefs[0],
                  markdown: '# Alert brief - PATNA, BIHAR\n\nKept body.' };
  const one = load({ '/api/briefs': view, '/api/briefs/get': saved });
  const host = new shim.Node('div');
  await one.context.WG.panels.briefcase(host, one.context.WG);
  assert.ok(textOf(host).indexOf('Alert brief — PATNA, BIHAR') >= 0, 'the kept title is shown');
  assert.ok(textOf(host).indexOf('Kept 2026-09-15T06:30:00+00:00') >= 0, 'when it was kept is shown');
  assert.ok(textOf(host).indexOf('S63') >= 0, 'the sources it named are shown');
  assert.ok(textOf(host).indexOf('Nothing is delivered') >= 0 || textOf(host).indexOf('never delivered') >= 0 || textOf(host).indexOf('local_only_no_delivery') >= 0, 'the store says it delivers nothing');

  // 2. Opening an entry reads it through the token-authenticated route and shows the stored limits.
  const open = buttonNamed(host, 'Open');
  assert.ok(open, 'each kept entry offers an open action');
  open.dispatch('click', {});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(one.calls.filter(call => call.route === '/api/briefs/get').length, 1, 'opening reads the kept entry from the store');
  assert.equal(one.calls.filter(call => call.route === '/api/briefs/get')[0].params.id, '11111111-2222-3333-4444-555555555555', 'it reads the entry that was opened');
  assert.equal(one.drawers.length, 1, 'the entry opens in the evidence drawer');
  assert.ok(textOf(one.drawers[0].body).indexOf('Kept body.') >= 0, 'the drawer shows what would be exported');
  assert.ok(textOf(one.drawers[0].body).indexOf('No all-clear is implied.') >= 0, 'the stored limits travel with the entry');
  assert.ok(textOf(one.drawers[0].body).indexOf('abababababababab') >= 0, 'the content hash recorded at composition is shown');

  // 3. Export fetches the file route and writes a .md file; nothing claims delivery.
  const exportButton = buttonNamed(host, 'Export Markdown');
  assert.ok(exportButton, 'each kept entry offers an export action');
  exportButton.dispatch('click', {});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(one.calls.filter(call => String(call.route).indexOf('/api/briefs/export?id=') === 0).length, 1, 'export reads the file route for that entry');
  assert.equal(one.downloads.length, 1, 'export hands exactly one file to the browser');
  assert.ok(/^alert-brief-patna-bihar-11111111\.md$/.test(one.downloads[0].name), 'the file name is derived from the entry: ' + one.downloads[0].name);
  assert.equal(one.downloads[0].kind, 'text/markdown', 'the export is Markdown');

  // 4. Delete posts the identifier and re-renders the surface.
  const remove = buttonNamed(host, 'Delete');
  assert.ok(remove, 'each kept entry offers a delete action');
  remove.dispatch('click', {});
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(one.calls.filter(call => call.route === '/api/briefs/delete')[0].body, { id: '11111111-2222-3333-4444-555555555555' }, 'delete names the entry');
  assert.equal(one.renders(), 1, 'the surface is re-read after a delete rather than assumed');

  // 5. An empty store says so and invents no entry.
  const empty = load({ '/api/briefs': { schema_version: 'briefcase-v1', delivery: 'local_only_no_delivery', note: 'Kept in the local store.', briefs: [] } });
  const emptyHost = new shim.Node('div');
  await empty.context.WG.panels.briefcase(emptyHost, empty.context.WG);
  assert.ok(textOf(emptyHost).indexOf('Nothing is kept yet.') >= 0, 'an empty store says nothing is kept');
  assert.equal(buttons(emptyHost).filter(node => String(node.textContent).indexOf('Export') >= 0).length, 0, 'an empty store offers no export');

  // 6. The save action sends a request to compose, never a payload to store (static check).
  assert.ok(PANELS.indexOf("'/api/briefs/save', { kind: 'alert_brief', lat: place.latitude, lon: place.longitude, day: 1 }") >= 0,
            'saving asks the server to compose the brief for a point and a day');
  assert.equal(PANELS.split("'/api/briefs/save'").length - 1, 1, 'the page asks the server to compose a brief in exactly one place');
  assert.ok(PANELS.indexOf("kind: 'alert_brief', lat: place.latitude, lon: place.longitude, day: 1") >= 0,
            'the request carries a point and a day, not a brief body');

  // 7. The reading position is disclosed in the answer accounting and never as a finding.
  const persona = { id: 'farmer', label: 'Farmer or field adviser',
                    note: 'A persona chooses the emphasis and the surfaces a reader starts from. It changes no value, unit, window, warning level, source identifier or evidence class.',
                    surfaces: ['advisories'], starters: ['Will it rain over this field in the next two days?'] };
  const tasks = load({}).context.renderTasks({ task_results: [{ id: 't1', status: 'answered', request: { kind: 'forecast', operation: 'lookup', parameters: ['rainfall'] } }],
                                                task_coverage: { incomplete_ids: [] }, persona: persona });
  assert.ok(textOf(tasks).indexOf('Read as: Farmer or field adviser') >= 0, 'the answer names the position it was read under');
  assert.ok(textOf(tasks).indexOf('changes no value') >= 0, 'the disclosure carries the no-finding rule');

  // 8. The welcome offers the persona's own questions first and still says what is not connected.
  const welcome = load({});
  welcome.context.WG.personaEntry = () => persona;
  const welcomeNode = welcome.context.renderWelcome({ onExample: () => {} });
  assert.ok(textOf(welcomeNode).indexOf('Reading as Farmer or field adviser') >= 0, 'the welcome names the position');
  assert.ok(textOf(welcomeNode).indexOf('Ask as farmer or field adviser') >= 0, 'the persona questions are offered with the position named');
  assert.ok(textOf(welcomeNode).indexOf('not connected') >= 0, 'the welcome keeps naming what is not connected');

  console.log('PASS: the briefcase keeps, reopens, exports and deletes composed briefs, and the reading position is disclosed rather than treated as evidence');
}

main().catch(error => { console.error(error); process.exit(1); });
