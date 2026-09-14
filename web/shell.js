'use strict';
/* Suite shell: client transport, routing, shared components and working context.

   Every surface reads a product-view payload and renders it. Nothing here
   computes a measurement, invents a unit or upgrades a state: a payload that
   says unavailable renders unavailable, and a payload that names its limits
   renders those limits. DOM nodes are built rather than HTML strings, which
   keeps the page inside the served policy. */

/* panels.js and map.js attach to this object, so it must be a property of the
   global object rather than a lexical binding. */
window.WG = window.WG || { state: { view: null, place: null, freshness: null, drawer: null }, panels: {} };
const WG = window.WG;

(function () {
  const TOKEN = (document.querySelector('meta[name="workspace-token"]') || {}).content || '';
  const VIEWS = ['overview', 'warnings', 'map', 'observations', 'forecast', 'climate', 'advisories', 'aviation', 'marine', 'assistant', 'settings'];
  const DEFAULT_PLACE = { label: 'Ahmedabad, Gujarat', latitude: 23.02579, longitude: 72.58727 };

  /* ---------- transport ---------- */
  function classify(status, payload) {
    const message = (payload && payload.error) || '';
    if (status === 403) return new Error('This page no longer holds the workspace token. Reload the local page.');
    if (status === 404) return new Error('That view is not available on this workspace.');
    if (status === 503) return new Error(message || 'The local evidence store is unavailable. Check its files and retry.');
    return new Error(message || 'The request could not be completed.');
  }
  async function request(path) {
    const response = await fetch(path, { headers: { 'X-WeatherGPT-Token': TOKEN } });
    let payload = null;
    try { payload = await response.json(); } catch (error) { payload = null; }
    if (!response.ok) throw classify(response.status, payload);
    return payload;
  }
  function query(params) {
    const parts = [];
    Object.keys(params || {}).forEach(key => {
      const value = params[key];
      if (value === undefined || value === null || value === '') return;
      if (Array.isArray(value)) value.forEach(item => parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(item)));
      else parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(value));
    });
    return parts.length ? '?' + parts.join('&') : '';
  }
  function api(path, params) { return request(path + query(params)); }
  /* Binary map geometry is served as a file, so it is fetched rather than parsed. */
  async function apiJsonFile(path) {
    const response = await fetch(path, { headers: { 'X-WeatherGPT-Token': TOKEN } });
    if (!response.ok) throw classify(response.status, null);
    return response.json();
  }

  /* ---------- small DOM builders ---------- */
  function clear(node) { if (node) node.replaceChildren(); }
  function append(host, ...nodes) { nodes.forEach(node => { if (node && host) host.append(node); }); }
  function chip(text, cls) { return el('span', text, 'chip' + (cls ? ' ' + cls : '')); }
  function block(title, note) {
    const box = el('section', undefined, 'block');
    box.append(el('h2', title, 'block-title'));
    if (note) box.append(el('p', note, 'block-note'));
    return box;
  }
  function stateBlock(kind, message, detail) {
    const box = el('div', undefined, 'state state-' + kind);
    box.append(el('p', message, 'state-message'));
    if (detail) box.append(el('p', detail, 'state-detail'));
    return box;
  }
  function loading(message) { return stateBlock('loading', message || 'Reading the sources…'); }
  function table(headers, rows, options) {
    options = options || {};
    const node = el('table', undefined, 'data-table' + (options.cls ? ' ' + options.cls : ''));
    const head = el('tr');
    headers.forEach(label => { const th = el('th', label); th.scope = 'col'; head.append(th); });
    node.append(head);
    rows.forEach(cells => {
      const row = el('tr');
      cells.forEach(cell => {
        const td = el('td');
        if (cell === null || cell === undefined) td.append(el('span', '—', 'muted'));
        else if (cell.nodeType) td.append(cell);
        else td.textContent = String(cell);
        row.append(td);
      });
      node.append(row);
    });
    return node;
  }
  function colourChip(colour, text) {
    const label = text || colour || 'colour not supplied';
    return el('span', label, 'wchip ' + (colour ? 'is-' + colour : 'is-unknown'));
  }
  function provenanceList(sources) {
    const box = el('div', undefined, 'provenance');
    (sources || []).forEach(source => {
      const row = el('div', undefined, 'provenance-row');
      row.append(el('span', source.source_id + ' · ' + (source.product || 'source'), 'provenance-name'));
      const bits = [];
      if (source.layer) bits.push(source.layer);
      if (source.retrieved_at_utc) bits.push('retrieved ' + istStamp(source.retrieved_at_utc));
      if (source.sha256_prefix) bits.push('sha ' + source.sha256_prefix);
      if (source.integration_status) bits.push(source.integration_status);
      row.append(el('span', bits.join(' · '), 'provenance-meta'));
      if (source.usage_terms) row.append(el('span', 'Terms: ' + source.usage_terms, 'provenance-terms'));
      box.append(row);
    });
    return box;
  }
  function limitationList(view) {
    const box = el('div', undefined, 'limits');
    const limits = (view && view.limitations) || [];
    const open = (view && view.not_established) || [];
    if (limits.length) {
      const list = el('ul', undefined, 'notes');
      limits.forEach(note => list.append(el('li', note)));
      box.append(el('p', 'Limits of this view', 'field-label'), list);
    }
    if (open.length) {
      const list = el('ul', undefined, 'notes');
      open.forEach(note => list.append(el('li', note)));
      box.append(el('p', 'Not established here', 'field-label'), list);
    }
    return box;
  }
  function disclosure(summary, build, openState) {
    const box = el('details', undefined, 'disclosure');
    if (openState) box.open = true;
    box.append(el('summary', summary));
    const body = el('div', undefined, 'disclosure-body');
    build(body);
    box.append(body);
    return box;
  }
  function sourceDisclosure(view) {
    return disclosure('Sources and retrieval (' + ((view && view.sources) || []).length + ')', body => {
      body.append(provenanceList(view.sources));
      body.append(limitationList(view));
      if (view && view.coverage && Object.keys(view.coverage).length) {
        const rows = Object.keys(view.coverage).map(key => [key, String(view.coverage[key])]);
        body.append(table(['Coverage', 'Value'], rows));
      }
    });
  }
  function freshness(view) {
    if (!view || !view.generated_at_utc) return 'Not read yet';
    return 'Read ' + istStamp(view.generated_at_utc);
  }
  function openDrawer(title, build) {
    const drawer = document.getElementById('evidence-drawer');
    const bodyNode = document.getElementById('drawer-body');
    if (!drawer || !bodyNode) return;
    document.getElementById('drawer-title').textContent = title;
    clear(bodyNode);
    build(bodyNode);
    drawer.hidden = false;
    const close = document.getElementById('drawer-close');
    if (close) close.focus();
  }
  function closeDrawer() {
    const drawer = document.getElementById('evidence-drawer');
    if (drawer) drawer.hidden = true;
  }

  /* ---------- working place ---------- */
  function loadPlace() {
    try {
      const raw = window.localStorage.getItem('weathergpt.place');
      if (raw) return JSON.parse(raw);
    } catch (error) { /* private mode: the default stands */ }
    return DEFAULT_PLACE;
  }
  function setPlace(place) {
    WG.state.place = place;
    try { window.localStorage.setItem('weathergpt.place', JSON.stringify(place)); } catch (error) { /* ignore */ }
    const button = document.getElementById('active-place');
    if (button) button.textContent = place.label;
    render();
  }

  /* ---------- place search ---------- */
  function wirePlaceSearch() {
    const input = document.getElementById('place-input');
    const list = document.getElementById('place-suggest');
    if (!input || !list) return;
    let timer = null;
    function hide() { list.hidden = true; clear(list); }
    function show(matches) {
      clear(list);
      matches.forEach(match => {
        const item = el('li');
        const button = el('button', undefined, 'suggest-item');
        button.type = 'button';
        button.append(el('span', match.label || match.name, 'suggest-label'));
        button.append(el('span', [match.source_id, match.kind, match.match_type].filter(Boolean).join(' · '), 'suggest-meta'));
        button.addEventListener('click', () => {
          const coordinates = match.coordinates || {};
          setPlace({ label: match.label || match.name, latitude: coordinates.latitude, longitude: coordinates.longitude });
          input.value = '';
          hide();
        });
        item.append(button);
        list.append(item);
      });
      list.hidden = matches.length === 0;
    }
    input.addEventListener('input', () => {
      const value = input.value.trim();
      if (timer) clearTimeout(timer);
      if (value.length < 2) { hide(); return; }
      timer = setTimeout(async () => {
        try {
          const view = await api('/api/places/search', { q: value, limit: 8 });
          show(view.data.matches || []);
        } catch (error) { hide(); }
      }, 220);
    });
    input.addEventListener('keydown', event => { if (event.key === 'Escape') hide(); });
  }

  /* ---------- routing ---------- */
  function currentView() {
    const match = /^#\/([a-z]+)/.exec(window.location.hash || '');
    /* The conversation is the product, so it is where the workspace opens. */
    const name = match ? match[1] : 'assistant';
    return VIEWS.indexOf(name) >= 0 ? name : 'assistant';
  }
  function showView(name) {
    document.querySelectorAll('.surface').forEach(section => {
      section.hidden = section.getAttribute('data-surface') !== name;
    });
    document.querySelectorAll('.nav-item').forEach(item => {
      const active = item.getAttribute('data-view') === name;
      item.classList.toggle('is-active', active);
      if (active) item.setAttribute('aria-current', 'page'); else item.removeAttribute('aria-current');
    });
    WG.state.view = name;
  }
  function render() {
    const name = currentView();
    showView(name);
    const host = document.getElementById(name + '-body');
    if (!host) return;
    const renderer = WG.panels[name];
    clear(host);
    if (!renderer) { host.append(stateBlock('plain', 'This surface is not connected yet.')); return; }
    const spinner = loading();
    const panel = el('div', undefined, 'surface-panel');
    host.append(spinner, panel);
    Promise.resolve(renderer(panel, WG)).then(() => {
      spinner.remove();
      const chipNode = document.getElementById('freshness');
      if (chipNode && WG.state.freshness) chipNode.textContent = WG.state.freshness;
      const note = document.getElementById(name + '-note');
      if (note && WG.state.freshness) note.textContent = WG.state.freshness;
    }).catch(error => {
      spinner.remove();
      clear(panel);
      panel.append(stateBlock('error', error && error.message ? error.message : 'This surface could not read its sources.',
                              'Nothing is shown rather than a partial picture. Try again, or check the collection health in Settings.'));
    });
  }
  function wireRouter() {
    window.addEventListener('hashchange', render);
    document.querySelectorAll('[data-ask-about]').forEach(button => {
      button.addEventListener('click', () => askAbout(button.getAttribute('data-ask-about')));
    });
  }
  function askAbout(view) {
    const context = describeContext(view);
    const input = document.getElementById('question');
    if (input) input.value = context.question;
    const note = document.getElementById('assistant-context');
    if (note) note.textContent = 'Asked from ' + view + ': ' + context.summary;
    window.location.hash = '#/assistant';
    const box = document.getElementById('question');
    if (box) box.focus();
  }
  function describeContext(view) {
    const place = WG.state.place || DEFAULT_PLACE;
    const templates = {
      overview: 'What should I watch today for ' + place.label + '?',
      warnings: 'Is there any official warning for ' + place.label + ' right now?',
      map: 'Which districts near ' + place.label + ' carry an official warning today?',
      observations: 'What is the current observed weather near ' + place.label + '?',
      forecast: 'What is the forecast for ' + place.label + ' tomorrow?',
      climate: 'What does the published rainfall record show for ' + place.label + '?',
      advisories: 'What does the district bulletin advise for ' + place.label + '?',
      aviation: 'What is the airport report for VAAH?',
      marine: 'What are the wave conditions near ' + place.label + '?'
    };
    return { question: templates[view] || templates.overview, summary: place.label };
  }

  /* ---------- notifications placeholder ---------- */
  function wireNotify() {
    const toggle = document.getElementById('notify-toggle');
    const panel = document.getElementById('notify-panel');
    const close = document.getElementById('notify-close');
    const body = document.getElementById('notify-body');
    if (!toggle || !panel || !body) return;
    function paint() {
      clear(body);
      body.append(stateBlock('plain', 'No watch or delivery mechanism is connected yet.',
        'Watching a place and receiving an update when an official product changes is required by the problem statement and is not built. Until it exists, nothing here claims to notify you. Ask the assistant for the current official state instead.'));
      body.append(disclosure('What the warning journey does today', into => {
        const list = el('ul', undefined, 'notes');
        ['The district warning product is resolved to your place by point-in-polygon on official geometry.',
         'The CAP relay is reported beside it and never merged into one verdict.',
         'A quiet district day is not an all-clear, and no delivery is implied.'].forEach(note => list.append(el('li', note)));
        into.append(list);
      }, true));
    }
    toggle.addEventListener('click', () => {
      panel.hidden = !panel.hidden;
      toggle.setAttribute('aria-expanded', panel.hidden ? 'false' : 'true');
      if (!panel.hidden) paint();
    });
    if (close) close.addEventListener('click', () => { panel.hidden = true; toggle.setAttribute('aria-expanded', 'false'); });
  }

  /* ---------- startup ---------- */
  function start() {
    WG.state.place = loadPlace();
    const button = document.getElementById('active-place');
    if (button) {
      button.textContent = WG.state.place.label;
      button.addEventListener('click', () => {
        const input = document.getElementById('place-input');
        if (input) input.focus();
      });
    }
    const close = document.getElementById('drawer-close');
    if (close) close.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', event => { if (event.key === 'Escape') { closeDrawer(); } });
    wirePlaceSearch();
    wireRouter();
    wireNotify();
    render();
  }

  WG.api = api;
  WG.apiJsonFile = apiJsonFile;
  WG.clear = clear;
  WG.append = append;
  WG.chip = chip;
  WG.block = block;
  WG.table = table;
  WG.stateBlock = stateBlock;
  WG.loading = loading;
  WG.disclosure = disclosure;
  WG.sourceDisclosure = sourceDisclosure;
  WG.limitationList = limitationList;
  WG.provenanceList = provenanceList;
  WG.colourChip = colourChip;
  WG.openDrawer = openDrawer;
  WG.closeDrawer = closeDrawer;
  WG.setPlace = setPlace;
  WG.render = render;
  WG.freshness = freshness;
  WG.VIEWS = VIEWS;

  /* Every surface script is deferred and runs before load, so the first render waits
     for load to be sure map.js and panels.js have attached. */
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start);
})();
