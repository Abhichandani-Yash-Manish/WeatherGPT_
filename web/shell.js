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
  const VIEWS = ['workspace', 'overview', 'warnings', 'map', 'observations', 'forecast', 'changes', 'climate', 'advisories', 'aviation', 'marine', 'assistant', 'briefcase', 'settings'];
  const VIEW_LABELS = { workspace: 'Workspace', assistant: 'Ask', overview: 'Today', warnings: 'Warnings', map: 'Map', forecast: 'Forecast',
                        changes: 'What changed', observations: 'Observations', advisories: 'Farm advisories',
                        climate: 'Climate records', marine: 'Sea and rivers', aviation: 'Aviation', briefcase: 'Briefcase',
                        settings: 'Sources and settings' };
  const VIEW_GLYPHS = { workspace: '◒', assistant: '✦', overview: '◎', warnings: '▲', map: '◈', forecast: '〜', changes: '∆',
                        observations: '⌖', advisories: '☘', climate: '◔', marine: '≈', aviation: '✈', briefcase: '❑',
                        settings: '⚙' };
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
  /* The briefcase is the one place the page sends a request of its own, so it gets its
     own helper: a token, a JSON body, and the same classified error path. */
  async function post(path, body) {
    const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-WeatherGPT-Token': TOKEN }, body: JSON.stringify(body) });
    let payload = null;
    try { payload = await response.json(); } catch (error) { payload = null; }
    if (!response.ok) throw classify(response.status, payload);
    return payload;
  }
  /* An export is served as a file behind the token, so it is fetched as text rather than
     parsed, and written to disk from a blob the page owns. */
  async function apiText(path) {
    const response = await fetch(path, { headers: { 'X-WeatherGPT-Token': TOKEN } });
    if (!response.ok) {
      let payload = null;
      try { payload = await response.json(); } catch (error) { payload = null; }
      throw classify(response.status, payload);
    }
    return response.text();
  }
  function download(name, text, kind) {
    const blob = new Blob([text], { type: (kind || 'text/plain') + ';charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
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
    // Each opening owns its content. A late source response from a closed
    // drawer can only update that detached content, never a newer task.
    const content = el('div', undefined, 'drawer-content');
    bodyNode.replaceChildren(content);
    build(content);
    drawer.hidden = false;
    const close = document.getElementById('drawer-close');
    if (close) close.focus();
  }
  function closeDrawer() {
    const drawer = document.getElementById('evidence-drawer');
    if (drawer) drawer.hidden = true;
  }

  /* ---------- reading position ---------- */
  /* A persona is a reading position: it changes the emphasis, the surfaces offered first
     and the questions suggested. It never changes a value, a source or a warning level, and
     every answer carries the position it was read under. */
  const PERSONA_KEY = 'weathergpt.persona';
  let personaCatalogue = { personas: [] };
  function personaId() {
    try { return window.localStorage.getItem(PERSONA_KEY) || ''; } catch (error) { return WG.state.persona || ''; }
  }
  function personaEntry(id) {
    const wanted = id === undefined ? personaId() : id;
    return (personaCatalogue.personas || []).filter(item => item.id === wanted)[0] || null;
  }
  function applyPersonaFocus(entry) {
    const focus = entry ? (entry.surfaces || []) : [];
    document.querySelectorAll('.rail .rail-group').forEach(group => {
      const items = Array.from(group.querySelectorAll('[data-view]'));
      if (items.length < 2) return;
      items.forEach((item, index) => { if (!item.dataset.order) item.dataset.order = String(index); });
      items.slice().sort((left, right) => {
        const rank = item => {
          const at = focus.indexOf(item.getAttribute('data-view'));
          return at < 0 ? focus.length + Number(item.dataset.order) : at;
        };
        return rank(left) - rank(right);
      }).forEach(item => group.append(item));
    });
  }
  function paintPersonaNote(entry) {
    const note = document.getElementById('briefcase-note');
    if (!note) return;
    note.textContent = entry
      ? 'Briefs the workspace composed and kept, read as ' + entry.label + ': ' + entry.who + ' A persona changes the emphasis, never a value, a source or a warning level. Nothing here is delivered, pushed or published; an export is a file you keep.'
      : 'Briefs the workspace composed from its sources and kept. Nothing here is delivered, pushed or published; an export is a file you keep.';
  }
  function setPersona(id) {
    try {
      if (id) window.localStorage.setItem(PERSONA_KEY, id);
      else window.localStorage.removeItem(PERSONA_KEY);
    } catch (error) { /* private mode: the choice lasts this page only */ }
    WG.state.persona = id || '';
    const entry = personaEntry(id);
    applyPersonaFocus(entry);
    paintPersonaNote(entry);
  }
  async function loadPersonas() {
    try {
      const view = await api('/api/personas');
      personaCatalogue = view.data || { personas: [] };
    } catch (error) { personaCatalogue = { personas: [] }; }
    const select = document.getElementById('persona');
    if (select) {
      (personaCatalogue.personas || []).forEach(item => {
        const option = el('option', item.label);
        option.value = item.id;
        option.title = item.who;
        select.append(option);
      });
      select.value = personaId();
      select.addEventListener('change', () => setPersona(select.value));
    }
    WG.state.persona = personaId();
    const entry = personaEntry();
    applyPersonaFocus(entry);
    paintPersonaNote(entry);
    if (window.WeatherGPT && typeof window.WeatherGPT.refreshWelcome === 'function') window.WeatherGPT.refreshWelcome();
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
    if (window.WeatherGPT) window.WeatherGPT.refreshWelcome();
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
          setPlace({ label: match.label || match.name, queryLabel: [match.name, (match.admin1 || '').replace(/^State of /, '')].filter(Boolean).join(', '), latitude: coordinates.latitude, longitude: coordinates.longitude });
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
    /* A fresh visit opens the workspace; conversation deep links still open Ask. */
    const name = match ? match[1] : 'workspace';
    return VIEWS.indexOf(name) >= 0 ? name : 'assistant';
  }
  function showView(name) {
    document.querySelectorAll('.surface').forEach(section => {
      section.hidden = section.getAttribute('data-surface') !== name;
    });
    document.querySelectorAll('.nav-item').forEach(item => {
      const active = item.getAttribute('data-view') === name;
      item.classList.toggle('is-active', active);
      if (active) {
        item.setAttribute('aria-current', 'page');
        const group = item.closest('details');
        if (group) group.open = true;
      } else item.removeAttribute('aria-current');
    });
    WG.state.view = name;
  }
  function render() {
    const name = currentView();
    WG.state.freshness = null;
    const stamp = document.getElementById('freshness');
    if (stamp) stamp.textContent = name === 'workspace' ? 'Sources dated separately' : 'Not read yet';
    showView(name);
    const host = document.getElementById(name + '-body');
    if (!host) return;
    const renderer = WG.panels[name];
    clear(host);
    if (!renderer) { host.append(stateBlock('plain', 'This surface is not connected yet.')); return; }
    const spinner = loading();
    const panel = el('div', undefined, 'surface-panel');
    if (name !== 'workspace') host.append(spinner);
    host.append(panel);
    Promise.resolve(renderer(panel, WG)).then(() => {
      spinner.remove();
      if (WG.state.view !== name || !panel.isConnected) return;
      const chipNode = document.getElementById('freshness');
      if (chipNode && WG.state.freshness) chipNode.textContent = WG.state.freshness;
      const note = document.getElementById(name + '-note');
      if (note && WG.state.freshness) note.textContent = WG.state.freshness;
    }).catch(error => {
      spinner.remove();
      clear(panel);
      panel.append(stateBlock('error', error && error.message ? error.message : 'This surface could not read its sources.',
                              'Retry this view, or check Sources and settings.'));
      const retry = el('button', 'Retry this view', 'secondary');
      retry.type = 'button';
      retry.addEventListener('click', render);
      panel.append(retry);
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
    WG.prepareQuestion(context.question, 'From ' + VIEW_LABELS[view] + ' · ' + context.summary);
  }
  // Opening a tool is an explicit new task. Draft it for review without inheriting
  // an unrelated crop, station, source or pending slot from an older conversation.
  function prepareQuestion(question, summary) {
    const app = window.WeatherGPT;
    if (app && app.state.busy) {
      window.location.hash = '#/assistant';
      return false;
    }
    if (app && app.newConversation) app.newConversation();
    const input = document.getElementById('question');
    if (input) { input.value = question; input.dispatchEvent(new Event('input')); }
    const note = document.getElementById('assistant-context');
    if (note) note.textContent = summary || 'Review the question, then ask. Follow-ups stay in this conversation.';
    window.location.hash = '#/assistant';
    render();
    if (input) input.focus();
    return true;
  }
  function describeContext(view) {
    const place = WG.state.place || DEFAULT_PLACE;
    const selected = (WG.state.surfaceContexts || {})[view];
    if (selected) return selected;
    const templates = {
      overview: 'What should I watch today for ' + place.label + '?',
      warnings: 'Is there any official warning for ' + place.label + ' right now?',
      map: 'Which districts near ' + place.label + ' carry an official warning today?',
      observations: 'What is the current observed weather near ' + place.label + '?',
      forecast: 'What is the forecast for ' + place.label + ' tomorrow?',
      changes: 'What changed between the stored forecast retrievals for ' + place.label + '?',
      climate: 'What does the published rainfall record show for ' + place.label + '?',
      advisories: 'What does the district bulletin advise for ' + place.label + '?',
      aviation: 'What is the airport report for VAAH?',
      marine: 'What are the wave conditions near ' + place.label + '?'
    };
    return { question: templates[view] || templates.overview, summary: place.label };
  }

  /* ---------- the local watch inbox ---------- */
  function wireNotify() {
    const toggle = document.getElementById('notify-toggle');
    const panel = document.getElementById('notify-panel');
    const close = document.getElementById('notify-close');
    const body = document.getElementById('notify-body');
    if (!toggle || !panel || !body) return;
    async function postJson(path, payload) {
      const response = await fetch(path, { method:'POST', headers:{ 'Content-Type':'application/json', 'X-WeatherGPT-Token':TOKEN },
                                           body:JSON.stringify(payload || {}) });
      let parsed = null;
      try { parsed = await response.json(); } catch (error) { parsed = null; }
      if (!response.ok) throw classify(response.status, parsed);
      return parsed;
    }
    function limits() {
      return disclosure('What a watch can and cannot do', into => {
        const list = el('ul', undefined, 'notes');
        ['Ask the assistant “Notify me if ... ” to register one; a watch records the place, hazard and window it resolved.',
         'Watches are evaluated only when you press Check now or call the local check route. There is no background daemon.',
         'A notification is enqueued only when a check observes a changed official state; an identical state notifies nothing.',
         'Enable browser notifications below to receive pushed notifications on this machine. Nothing is pushed anywhere else.',
         'A flood or cyclone watch is recorded but the connected official products do not carry it; it is never mapped onto a similar-sounding product.',
         'A no-match result is not an all-clear, and origin authentication of the official products remains unverified.'].forEach(note => list.append(el('li', note)));
        into.append(list);
      }, true);
    }
    function urlBase64ToUint8Array(base64) {
      const padding = '='.repeat((4 - (base64.length % 4)) % 4);
      const raw = window.atob(base64.replace(/-/g, '+').replace(/_/g, '/') + padding);
      const bytes = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
      return bytes;
    }
    async function subscribeBrowser(watchId) {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') throw new Error('Notification permission was not granted.');
      const vapid = await api('/api/push/vapid-key');
      const registration = await navigator.serviceWorker.register('/sw.js');
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(vapid.public_key)
      });
      const raw = subscription.toJSON();
      return postJson('/api/push/subscribe', {
        endpoint: raw.endpoint, keys: raw.keys || {},
        expirationTime: raw.expirationTime || null,
        watch_id: watchId || null
      });
    }
    async function pushPanel(into, watches) {
      const supported = ('serviceWorker' in navigator) && ('PushManager' in window) && ('Notification' in window);
      if (!supported) {
        into.append(stateBlock('plain', 'Push notifications are not supported in this browser.',
          'The local inbox above still lists every notification. Nothing is pushed.'));
        return;
      }
      let state = null;
      try { state = await api('/api/push/state'); }
      catch (error) { into.append(stateBlock('down', 'Push status could not be read.', error.message)); return; }
      const counts = (state && state.subscriptions) || {};
      into.append(stateBlock('plain', 'Push subscriptions: ' + (counts.active || 0) + ' active.',
        'Permission is ' + Notification.permission + '. Purged expired: ' + (state.purged_expired || 0) + '.'));
      try {
        const registration = await navigator.serviceWorker.getRegistration('/sw.js');
        const existing = registration && registration.pushManager ? await registration.pushManager.getSubscription() : null;
        if (Notification.permission === 'granted' && !existing) {
          into.append(stateBlock('plain', 'This browser has no push subscription (it may have been retired).',
            'Press Subscribe below to restore it; bound watches regain push on resubscribe.'));
        }
      } catch (error) { /* status stays as reported; the button below still works */ }
      const enable = el('button', Notification.permission === 'granted' ? 'Subscribe this browser' : 'Enable notifications', 'ghost');
      enable.type = 'button';
      enable.addEventListener('click', async () => {
        enable.disabled = true;
        try { await subscribeBrowser(null); paint(); }
        catch (error) {
          enable.disabled = false;
          into.append(stateBlock('down', 'Notifications could not be enabled.', error.message));
        }
      });
      into.append(enable);
      (watches || []).filter(watch => (watch.channels || []).indexOf('web_push') < 0).forEach(watch => {
        const label = (watch.place && (watch.place.name || watch.place.label)) || 'this place';
        const bind = el('button', 'Push to ' + label, 'ghost');
        bind.type = 'button';
        bind.setAttribute('aria-label', 'Subscribe this browser to push for ' + label);
        bind.addEventListener('click', async () => {
          bind.disabled = true;
          try { await subscribeBrowser(watch.id); paint(); }
          catch (error) {
            bind.disabled = false;
            into.append(stateBlock('down', 'Push could not be bound to ' + label + '.', error.message));
          }
        });
        into.append(bind);
      });
    }
    async function paint() {
      clear(body);
      body.append(loading('Reading your plans and the local watch inbox…'));
      let plans = null, planError = null, packet = null;
      try { plans = await api('/api/plans'); } catch (error) { planError = error; }
      try { packet = await api('/api/watches'); }
      catch (error) {
        clear(body);
        if (plans) paintPlans(plans);
        body.append(stateBlock('down', 'The local watch inbox could not be read.', error.message));
        return;
      }
      clear(body);
      if (plans) paintPlans(plans);
      else body.append(stateBlock('down', 'Saved plans could not be read.', planError ? planError.message : ''));
      markPlansSeen(plans);
      body.append(el('h3', 'Earlier watch requests', 'notify-heading'));
      const watches = packet.watches || [];
      body.append(stateBlock('plain', watches.length ? watches.length + ' local watch(es) registered.' : 'No watches registered yet.',
        'Register one by asking the assistant to notify you. Watches are checked only when asked; a no-match result is not an all-clear.'));
      if (watches.length) {
        body.append(table(['Hazard', 'Place', 'State', 'Pending', 'Last checked', 'Last notified'], watches.map(watch => [
          watch.hazard,
          (watch.place && (watch.place.name || watch.place.label)) || '—',
          watch.state,
          String(watch.outbox_pending || 0),
          watch.last_checked_at || 'not yet checked',
          watch.last_notification_at || 'never notified'
        ])));
        const retireList = el('ul', undefined, 'notes');
        watches.forEach(watch => {
          const item = el('li', (watch.place && (watch.place.name || watch.place.label)) || 'watch' + ' · ' + watch.state + ' · ');
          const retire = el('button', 'Retire', 'ghost');
          retire.type = 'button';
          retire.setAttribute('aria-label', 'Retire the watch for ' + ((watch.place && (watch.place.name || watch.place.label)) || 'this place'));
          retire.addEventListener('click', async () => {
            retire.disabled = true;
            try { await postJson('/api/watches/delete', { id: watch.id }); paint(); }
            catch (error) { retire.disabled = false; body.append(stateBlock('down', 'The watch could not be retired.', error.message)); }
          });
          item.append(retire);
          const channels = watch.channels || ['local_inbox'];
          const consent = watch.consent_record || {};
          const channelNote = el('span', ' Channels: ' + channels.join(', ') +
            (consent.web_push ? ' (push granted ' + String((consent.web_push.granted_at || '')).slice(0, 10) + ')' : ''), 'field-note');
          item.append(channelNote);
          const hasPush = channels.indexOf('web_push') >= 0;
          const toggle = el('button', hasPush ? 'Disable push' : 'Enable push', 'ghost');
          toggle.type = 'button';
          toggle.setAttribute('aria-label', (hasPush ? 'Disable push for ' : 'Enable push for ') + ((watch.place && (watch.place.name || watch.place.label)) || 'this place'));
          toggle.addEventListener('click', async () => {
            toggle.disabled = true;
            const next = hasPush ? channels.filter(channel => channel !== 'web_push') : channels.concat(['web_push']);
            try { await postJson('/api/watches/channels', { id: watch.id, channels: next }); paint(); }
            catch (error) {
              toggle.disabled = false;
              body.append(stateBlock('down', 'Channels could not be changed.' +
                (hasPush ? '' : ' Subscribe this browser first, then enable push.'), error.message));
            }
          });
          item.append(toggle);
          retireList.append(item);
        });
        body.append(retireList);
        try {
          const outbox = await api('/api/outbox');
          const rows = outbox.notifications || [];
          const queued = rows.filter(row => row.state === 'queued' || row.state === 'created');
          body.append(stateBlock('plain', queued.length ? queued.length + ' notification(s) waiting in the local outbox.' : 'The local outbox is empty.',
            'A notification is enqueued only when a check observes a changed official state. Nothing is pushed.'));
          if (rows.length) {
            body.append(table(['Watch', 'Channel', 'State', 'Retries', 'Updated'], rows.slice(0, 10).map(row => [
              String(row.watch_id || '').slice(0, 8),
              row.channel || '—',
              row.state || '—',
              String(row.retry_count || 0) + '/' + String(row.max_retries || 0),
              row.updated_at || '—'
            ])));
            rows.slice(0, 10).filter(row => row.state === 'sent').forEach(row => {
              const answers = el('div', undefined, 'brief-tools');
              answers.append(el('span', 'Notification ' + String(row.id).slice(0, 8) + ': are you ', 'field-note'));
              [['safe', 'Safe'], ['need_help', 'Need help'], ['evacuating', 'Evacuating'], ['seen', 'Seen']].forEach(pair => {
                const button = el('button', pair[1], 'ghost');
                button.type = 'button';
                button.addEventListener('click', async () => {
                  button.disabled = true;
                  try { await postJson('/api/outbox/' + row.id + '/ack', { response: pair[0] }); paint(); }
                  catch (error) { button.disabled = false; body.append(stateBlock('down', 'The response could not be recorded.', error.message)); }
                });
                answers.append(button);
              });
              body.append(answers);
            });
          }
        } catch (error) { body.append(stateBlock('down', 'The local outbox could not be read.', error.message)); }
      }
      const check = el('button', 'Check now', 'ghost');
      check.addEventListener('click', async () => {
        check.disabled = true; check.textContent = 'Checking…';
        try {
          const result = await postJson('/api/watches/check', {});
          clear(body);
          body.append(stateBlock('plain', 'Checked ' + ((result.results || []).length) + ' watch(es) in the foreground.',
            'No daemon or push is installed. A no-match result is not an all-clear.'));
          (result.results || []).forEach(row => body.append(stateBlock(row.matched ? 'plain' : 'plain',
            (row.matched ? 'Matched: ' : 'No match: ') + row.state, row.detail || '')));
          body.append(check); check.disabled = false; check.textContent = 'Check now';
        } catch (error) {
          check.disabled = false; check.textContent = 'Check now';
          body.append(stateBlock('down', 'The check could not run.', error.message));
        }
      });
      body.append(check);
      const createHost = el('div', undefined, 'watch-create');
      createHost.append(el('p', 'Register a watch for explicit coordinates (no place guessing; the warning tool still resolves the district at check time).', 'field-note'));
      const nameInput = el('input', undefined, 'palette-input');
      nameInput.placeholder = 'Place name';
      const latInput = el('input', undefined, 'palette-input');
      latInput.placeholder = 'Latitude';
      const lonInput = el('input', undefined, 'palette-input');
      lonInput.placeholder = 'Longitude';
      const hazardInput = el('input', undefined, 'palette-input');
      hazardInput.placeholder = 'Hazard (optional, e.g. heavy rain)';
      const create = el('button', 'Register watch', 'ghost');
      create.type = 'button';
      create.addEventListener('click', async () => {
        create.disabled = true;
        try {
          await postJson('/api/watches/create', { place: { name: nameInput.value, latitude: latInput.value, longitude: lonInput.value }, hazard: hazardInput.value || null });
          paint();
        } catch (error) {
          create.disabled = false;
          body.append(stateBlock('down', 'The watch could not be registered.', error.message));
        }
      });
      [nameInput, latInput, lonInput, hazardInput, create].forEach(node => createHost.append(node));
      body.append(createHost);
      const pushHost = el('div', undefined, 'push-panel');
      body.append(pushHost);
      pushPanel(pushHost, watches);
      body.append(limits());
    }
    const KIND_LABELS = { change: 'Change', check_in: 'Evening check-in', degraded: 'Watch degraded' };
    function paintPlans(packet) {
      const section = el('section', undefined, 'plan-inbox');
      section.append(el('h3', packet.mode === 'replay_of_recorded_editions' ? 'Replay of recorded IMD editions' : 'Your plans', 'notify-heading'));
      const plans = packet.plans || [];
      if (!plans.length) {
        section.append(stateBlock('plain', 'No saved plans yet.',
          'Tell the assistant what you are planning and ask it to let you know if anything changes, for example “I am spraying my cotton in Rajkot on Monday, let me know if anything changes.”'));
      }
      plans.forEach(plan => {
        const row = el('div', undefined, 'plan-row is-' + (plan.state || 'unknown'));
        row.append(el('p', plan.title, 'plan-title'));
        const meta = el('p', undefined, 'plan-meta');
        [plan.state_words, plan.not_connected ? 'not connected' : 'watching ' + plan.hazards,
         plan.last_checked_at ? 'checked ' + istStamp(plan.last_checked_at) : 'not checked yet'].filter(Boolean)
          .forEach(part => meta.append(el('span', part)));
        row.append(meta);
        if (plan.last_error) row.append(el('p', plan.last_error, 'field-note'));
        if (packet.mode !== 'replay_of_recorded_editions') {
          const tools = el('div', undefined, 'plan-tools');
          const actions = plan.state === 'paused' ? [['Resume', 'resume']] : (plan.state === 'ended' || plan.state === 'not_connected' ? [] : [['Pause', 'pause']]);
          actions.concat([['Delete', 'delete']]).forEach(([label, action]) => {
            const button = el('button', label, 'ghost');
            button.type = 'button';
            button.addEventListener('click', async () => {
              button.disabled = true;
              try { await postJson('/api/plans/update', { id: plan.id, action: action }); paint(); }
              catch (error) { button.disabled = false; row.append(stateBlock('down', 'The plan could not be updated.', error.message)); }
            });
            tools.append(button);
          });
          row.append(tools);
        }
        section.append(row);
      });
      const notes = packet.notifications || [];
      section.append(el('h3', 'Notifications', 'notify-heading'));
      if (!notes.length) section.append(stateBlock('plain', 'No notifications yet.', 'A notification is written only when the official state for a plan changes, the evening before a dated plan, or when checking has failed for three hours.'));
      notes.forEach(note => {
        const item = el('article', undefined, 'plan-note is-' + note.kind);
        const head = el('p', undefined, 'plan-note-head');
        head.append(el('span', KIND_LABELS[note.kind] || note.kind, 'tag'));
        head.append(el('span', istStamp(note.created_at), 'tag is-quiet'));
        if (!note.visible) head.append(el('span', 'held for quiet hours until ' + istStamp(note.visible_at), 'tag is-quiet'));
        item.append(head);
        item.append(el('p', note.text, 'plan-note-text'));
        const receipt = note.receipt || {};
        const rows = ['district', 'date', 'hazards', 'colour', 'before', 'bulletin_issued_at_utc', 'retrieved_at_utc', 'edition_sha256',
                      'source_id', 'layer', 'mode', 'origin_authentication', 'derived_window']
          .filter(key => receipt[key] !== undefined && receipt[key] !== null && String(receipt[key]) !== '')
          .map(key => [key.replace(/_/g, ' '), Array.isArray(receipt[key]) ? receipt[key].join(', ') : String(receipt[key])]);
        if (rows.length) item.append(disclosure('Evidence receipt', into => into.append(table(['Field', 'Value'], rows))));
        if (note.kind === 'change' && receipt.place && receipt.date) {
          const ask = el('button', 'Ask about this change', 'ghost');
          ask.type = 'button';
          ask.addEventListener('click', () => {
            const input = document.getElementById('question');
            if (input) input.value = 'Is there an official warning for ' + receipt.place + ' on ' + receipt.date + '?';
            panel.hidden = true; toggle.setAttribute('aria-expanded', 'false');
            window.location.hash = '#/assistant';
            if (input) input.focus();
          });
          item.append(ask);
        }
        section.append(item);
      });
      const watcher = packet.watcher || {};
      section.append(el('p', 'Checked every ' + Math.round((watcher.interval_seconds || 1800) / 60) + ' minutes while WeatherGPT runs · ' +
        (watcher.running ? 'watcher running' : 'watcher not running in this process') +
        (watcher.last_cycle_at ? ' · last check ' + istStamp(watcher.last_cycle_at) : '') +
        (watcher.last_error ? ' · last error: ' + watcher.last_error : ''), 'field-note'));
      const tools = el('div', undefined, 'plan-tools');
      if (packet.mode !== 'replay_of_recorded_editions') {
        const check = el('button', 'Check plans now', 'ghost');
        check.type = 'button';
        check.addEventListener('click', async () => {
          check.disabled = true; check.textContent = 'Checking plans…';
          try { await postJson('/api/plans/check', {}); paint(); }
          catch (error) { check.disabled = false; check.textContent = 'Check plans now'; section.append(stateBlock('down', 'The plan check could not run.', error.message)); }
        });
        tools.append(check);
        if ((packet.recorded_editions || 0) >= 2) {
          const replay = el('button', 'Replay recorded editions', 'ghost');
          replay.type = 'button';
          replay.addEventListener('click', async () => {
            replay.disabled = true;
            try {
              const result = await postJson('/api/plans/replay', {});
              clear(body);
              body.append(stateBlock('plain', 'Replay of recorded IMD editions.', (result.result && result.result.note) || 'Nothing here is current.'));
              paintPlans(result.inbox);
              const back = el('button', 'Back to live plans', 'ghost');
              back.type = 'button';
              back.addEventListener('click', paint);
              body.append(back);
            } catch (error) { replay.disabled = false; section.append(stateBlock('down', 'The replay could not run.', error.message)); }
          });
          tools.append(replay);
        }
        if (typeof window.Notification === 'function' && window.Notification.permission === 'default') {
          const allow = el('button', 'Allow browser notifications', 'ghost');
          allow.type = 'button';
          allow.addEventListener('click', () => { requestPlanNotifications(); allow.remove(); });
          tools.append(allow);
        }
      }
      section.append(tools);
      section.append(disclosure('What Plan Watch can and cannot do', into => {
        const list = el('ul', undefined, 'notes');
        (packet.limits || []).forEach(note => list.append(el('li', note)));
        into.append(list);
      }));
      body.append(section);
    }
    toggle.addEventListener('click', () => {
      panel.hidden = !panel.hidden;
      toggle.setAttribute('aria-expanded', panel.hidden ? 'false' : 'true');
      if (!panel.hidden) paint();
    });
    if (close) close.addEventListener('click', () => { panel.hidden = true; toggle.setAttribute('aria-expanded', 'false'); });
    try {
      const deep = /[?&]watch=([^&]+)/.exec((window.location && window.location.search) || '');
      if (deep && deep[1]) {
        panel.hidden = false;
        toggle.setAttribute('aria-expanded', 'true');
        paint();
      }
    } catch (error) { /* the deep link is optional; the panel still opens by hand */ }
  }

  /* ---------- plan notifications: an unread count, and browser notifications if allowed ---------- */
  const PLAN_SEEN_KEY = 'weathergpt.plans.seen';
  const PLAN_NOTIFIED_KEY = 'weathergpt.plans.notified';
  const PLAN_POLL_MS = 30000;
  function storedNumber(key) {
    try { const value = window.localStorage.getItem(key); return value === null ? null : Number(value) || 0; }
    catch (error) { return null; }
  }
  function storeNumber(key, value) { try { window.localStorage.setItem(key, String(value)); } catch (error) { /* private mode */ } }
  function newestId(packet) { return Math.max(0, ...((packet && packet.notifications) || []).map(item => Number(item.id) || 0)); }
  function markPlansSeen(packet) {
    if (!packet || packet.mode !== 'live') return;
    storeNumber(PLAN_SEEN_KEY, newestId(packet));
    const toggle = document.getElementById('notify-toggle');
    if (toggle) toggle.textContent = 'Plans & inbox';
  }
  function requestPlanNotifications() {
    if (typeof window.Notification !== 'function' || window.Notification.permission !== 'default') return;
    try { window.Notification.requestPermission(); } catch (error) { /* the inbox still works */ }
  }
  async function pollPlans() {
    let packet = null;
    try { packet = await api('/api/plans'); } catch (error) { return null; }
    const visible = (packet.notifications || []).filter(item => item.visible);
    const seen = storedNumber(PLAN_SEEN_KEY) || 0;
    const unread = visible.filter(item => Number(item.id) > seen).length;
    const toggle = document.getElementById('notify-toggle');
    if (toggle) toggle.textContent = unread ? 'Plans & inbox · ' + unread : 'Plans & inbox';
    const notified = storedNumber(PLAN_NOTIFIED_KEY);
    const newest = Math.max(0, ...visible.map(item => Number(item.id) || 0));
    // The first poll on a fresh page records what already exists instead of replaying it.
    if (notified !== null && typeof window.Notification === 'function' && window.Notification.permission === 'granted') {
      visible.filter(item => Number(item.id) > notified).slice(0, 3).forEach(item => {
        try { new window.Notification(item.title, { body: item.text, tag: 'weathergpt-plan-' + item.id }); } catch (error) { /* inbox only */ }
      });
    }
    if (notified === null || newest > notified) storeNumber(PLAN_NOTIFIED_KEY, newest);
    return packet;
  }
  function startPlanPolling() {
    pollPlans();
    setInterval(pollPlans, PLAN_POLL_MS);
  }
  WG.onPlanChanged = watch => {
    if (watch && watch.action === 'saved') requestPlanNotifications();
    pollPlans();
  };
  WG.pollPlans = pollPlans;

  /* ---------- appearance: day desk, night desk, or the system ---------- */
  const THEME_KEY = 'weathergpt.theme';
  function preferredTheme() {
    try {
      const stored = window.localStorage.getItem(THEME_KEY);
      if (stored === 'light' || stored === 'dark' || stored === 'auto') return stored;
    } catch (error) { /* private mode: follow the system */ }
    return 'auto';
  }
  function systemTheme() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function applyTheme(mode) {
    const effective = mode === 'auto' ? systemTheme() : mode;
    document.documentElement.setAttribute('data-theme', effective);
    const button = document.getElementById('theme-toggle');
    if (button) {
      button.textContent = mode === 'auto' ? 'System · ' + (effective === 'dark' ? 'night' : 'day')
                                           : (mode === 'dark' ? 'Night desk' : 'Day desk');
      button.title = 'Appearance: ' + mode + '. Click to cycle day, night and system.';
    }
  }
  function cycleTheme() {
    const order = ['auto', 'light', 'dark'];
    const next = order[(order.indexOf(preferredTheme()) + 1) % order.length];
    try { window.localStorage.setItem(THEME_KEY, next); } catch (error) { /* appearance still applies */ }
    applyTheme(next);
    return next;
  }
  function wireTheme() {
    applyTheme(preferredTheme());
    const button = document.getElementById('theme-toggle');
    if (button) button.addEventListener('click', cycleTheme);
    if (window.matchMedia) {
      const media = window.matchMedia('(prefers-color-scheme: dark)');
      const listener = () => { if (preferredTheme() === 'auto') applyTheme('auto'); };
      if (media.addEventListener) media.addEventListener('change', listener);
    }
  }

  /* ---------- command palette ---------- */
  function wirePalette() {
    const root = document.getElementById('palette');
    const input = document.getElementById('palette-input');
    const body = document.getElementById('palette-body');
    const opener = document.getElementById('palette-open');
    if (!root || !input || !body) return;
    let items = [], active = 0, placeMatches = [], timer = null;

    function closePalette() { root.hidden = true; document.removeEventListener('keydown', onKey); }
    function openPalette() {
      root.hidden = false; input.value = ''; placeMatches = []; renderItems('');
      loadRecent();
      input.focus();
      document.addEventListener('keydown', onKey);
    }
    function actions() {
      const list = Object.keys(VIEW_LABELS).map(view => ({ group: 'Surfaces', glyph: VIEW_GLYPHS[view] || '·',
        label: VIEW_LABELS[view], note: '#' + view, run: () => { window.location.hash = '#/' + view; } }));
      list.push({ group: 'Actions', glyph: '✚', label: 'New conversation', note: 'start over', run: () => { const b = document.getElementById('new-conversation'); if (b) b.click(); } });
      list.push({ group: 'Actions', glyph: '◐', label: 'Switch appearance', note: 'day, night or system', run: () => { cycleTheme(); } });
      list.push({ group: 'Actions', glyph: '◷', label: 'Check watches now', note: 'foreground only', run: () => { const b = document.getElementById('notify-toggle'); if (b) b.click(); } });
      list.push({ group: 'Actions', glyph: '⤓', label: 'Save this conversation', note: 'markdown', run: () => { const b = document.getElementById('export-transcript'); if (b) b.click(); } });
      list.push({ group: 'Actions', glyph: '⎙', label: 'Print the open answer', note: 'print', run: () => { if (window.print) window.print(); } });
      return list;
    }
    function filtered(query) {
      const base = actions().concat(placeMatches).concat(WG.state.recent || []);
      const needle = query.trim().toLowerCase();
      if (!needle) return base;
      return base.filter(item => ((item.label || '') + ' ' + (item.note || '')).toLowerCase().indexOf(needle) >= 0);
    }
    function select(index) {
      active = Math.max(0, Math.min(index, Math.max(0, items.length - 1)));
      const buttons = body.querySelectorAll ? body.querySelectorAll('.palette-item') : [];
      for (let i = 0; i < buttons.length; i += 1) buttons[i].classList.toggle('is-active', i === active);
    }
    function renderItems(query) {
      items = filtered(query); active = 0;
      clear(body);
      let group = null;
      items.forEach((item, index) => {
        if (item.group !== group) { group = item.group; body.append(el('p', group, 'palette-group')); }
        const button = el('button', undefined, 'palette-item' + (index === 0 ? ' is-active' : ''));
        button.type = 'button';
        button.append(el('span', item.glyph || '·', 'glyph'), el('span', item.label || '', 'palette-label'));
        if (item.note) button.append(el('span', item.note, 'palette-note'));
        button.addEventListener('click', () => runItem(item));
        body.append(button);
      });
      if (!items.length) body.append(stateBlock('plain', 'Nothing matches that yet.', 'Try a surface name, a place, an action, or a recent question.'));
    }
    function runItem(item) { closePalette(); if (item && item.run) item.run(); }
    function onKey(event) {
      if (event.key === 'Escape') { event.preventDefault(); closePalette(); return; }
      if (event.key === 'ArrowDown') { event.preventDefault(); select(active + 1); return; }
      if (event.key === 'ArrowUp') { event.preventDefault(); select(active - 1); return; }
      if (event.key === 'Enter' && items[active]) { event.preventDefault(); runItem(items[active]); }
    }
    async function searchPlaces(value) {
      if (value.trim().length < 2) { placeMatches = []; return; }
      try {
        const view = await api('/api/places/search', { q: value, limit: 6 });
        placeMatches = (view.data.matches || []).map(match => ({ group: 'Places', glyph: '⌖', label: match.label || match.name,
          note: [match.source_id, match.kind].filter(Boolean).join(' · '),
          run: () => { const c = match.coordinates || {}; setPlace({ label: match.label || match.name, latitude: c.latitude, longitude: c.longitude }); window.location.hash = '#/assistant'; } }));
      } catch (error) { placeMatches = []; }
    }
    async function loadRecent() {
      try {
        const packet = await api('/api/conversations', { limit: 6 });
        WG.state.recent = (packet.conversations || []).slice(0, 6).map(row => ({ group: 'Recent conversations', glyph: '▤',
          label: row.opening_question || 'Stored conversation',
          note: row.asked !== undefined ? row.asked + ' asked' : (row.turns !== undefined ? row.turns + ' turns' : 'stored turn'),
          run: () => { const app = window.WeatherGPT; if (app && app.restore) app.restore({ id: row.id }); else window.location.hash = '#/assistant'; } }));
      } catch (error) { WG.state.recent = []; }
      renderItems(input.value);
    }
    input.addEventListener('input', () => {
      renderItems(input.value);
      if (timer) clearTimeout(timer);
      timer = setTimeout(async () => { await searchPlaces(input.value); renderItems(input.value); }, 200);
    });
    if (opener) opener.addEventListener('click', openPalette);
    root.addEventListener('click', event => { if (event.target === root) closePalette(); });
    WG.palette = { open: openPalette, close: closePalette };
  }

  /* ---------- rail health readout ---------- */
  async function paintHealthMini() {
    const rail = document.getElementById('rail');
    if (!rail) return;
    let host = document.getElementById('health-mini');
    if (!host) {
      const group = el('div', undefined, 'rail-group');
      group.append(el('h2', 'Collection health', 'rail-title'));
      host = el('div', undefined, 'health-mini');
      host.id = 'health-mini';
      group.append(host);
      const note = document.getElementById('nav-note');
      rail.insertBefore(group, note || null);
    }
    try {
      const health = await api('/api/health');
      clear(host);
      if (!health.available) {
        host.append(el('p', health.note || 'No collection history exists yet.', 'nav-note'));
        return;
      }
      (health.products || []).slice(0, 3).forEach(product => {
        const row = el('div', undefined, 'health-row');
        row.append(el('span', product.product, 'health-key'));
        row.append(el('span', String(product.jobs) + ' jobs', 'health-stream'));
        row.append(el('span', product.newest_commit_utc ? istStamp(product.newest_commit_utc) : 'no commit', 'health-val'));
        host.append(row);
      });
      host.append(el('p', (health.job_states && Object.keys(health.job_states).length ? Object.keys(health.job_states).map(k => k + ' ' + health.job_states[k]).join(' · ') : 'no jobs') + ' · ' + (health.active_leases || 0) + ' in flight', 'readout-line'));
    } catch (error) {
      clear(host);
      host.append(el('p', 'Collection health is unavailable.', 'nav-note'));
    }
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
    startPlanPolling();
    wireTheme();
    wirePalette();
    paintHealthMini();
    /* Ask the server to read the slow layers for the place this page is working with, so the
       first question is not the first read. It is a background read of the same governed adapters;
       the page does not wait for it and nothing is inferred from it. */
    (function warmWorkingPlace() {
      const place = WG.state.place || {};
      if (place.latitude === undefined || place.longitude === undefined) return;
      post('/api/warm', { lat: place.latitude, lon: place.longitude, label: place.label }).catch(function () { return null; });
    })();
    loadPersonas();
    document.addEventListener('keydown', event => {
      if ((event.metaKey || event.ctrlKey) && String(event.key).toLowerCase() === 'k') {
        event.preventDefault();
        if (WG.palette) WG.palette.open();
        return;
      }
      // Alt+1…9 jumps to the first nine surfaces without leaving the keyboard.
      if (event.altKey && /^[1-9]$/.test(String(event.key))) {
        const target = VIEWS[Number(event.key) - 1];
        if (target) { event.preventDefault(); window.location.hash = '#/' + target; }
      }
    });
    render();
  }

  WG.prepareQuestion = prepareQuestion;
  WG.api = api;
  WG.apiJsonFile = apiJsonFile;
  WG.post = post;
  WG.apiText = apiText;
  WG.download = download;
  WG.personaEntry = personaEntry;
  WG.setPersona = setPersona;
  WG.loadPersonas = loadPersonas;
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
  WG.wireNotify = wireNotify;  /* exposed for the component checks, which never fire load */
  WG.wireTheme = wireTheme;
  WG.wirePalette = wirePalette;
  WG.paintHealthMini = paintHealthMini;
  WG.cycleTheme = cycleTheme;
  WG.applyTheme = applyTheme;

  /* Every surface script is deferred and runs before load, so the first render waits
     for load to be sure map.js and panels.js have attached. */
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start);
})();
