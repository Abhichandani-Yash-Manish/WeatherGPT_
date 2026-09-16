'use strict';
/* Workspace client. One question at a time against the loopback API, with the
   engine's own state machine surfaced rather than smoothed over: a refusal, an
   abstention, a lock collision and a cancelled turn are each shown as what they
   are. Nothing here upgrades a status into a success. */

(function () {
  const TOKEN = (document.querySelector('meta[name="workspace-token"]') || {}).content || '';
  const byId = id => document.getElementById(id);
  /* The language to answer in is a field on the request. It used to be appended to
     the question as an English instruction for the planner to read back out, which is
     how an explicit choice could be lost to inference. */
  const LANGUAGES = { loaded:false, rows:[], speakable:new Set() };
  const state = { conversationId:null, busy:false, controller:null, language:'', startedAt:0, ticker:null, ledger:null, lastSeen:null,
                  requestId:null, cancelRequested:false, stageTimer:null, lastReceipt:null, previewSeq:0 };

  /* ---------- surface state ---------- */
  function setService(text, cls) {
    const chip = byId('service-state');
    if (!chip) return;
    chip.textContent = text;
    chip.className = 'chip' + (cls ? ' ' + cls : '');
  }
  function setBusy(on, message) {
    state.busy = on;
    const status = byId('busy');
    if (status) status.textContent = message || (on ? 'Working…' : 'Ready');
    const cancel = byId('cancel');
    if (cancel) cancel.hidden = !on;
    ['ask','rail-toggle'].forEach(id => { const button = byId(id); if (button) button.disabled = on; });
    const fields = byId('use-fields');
    if (fields) fields.disabled = on;
    if (on) { state.startedAt = Date.now(); startTicker(); startStage(); } else { stopTicker(); stopStage(); }
  }
  /* The engine's own checkpoints, read while a turn is in flight. This line never
     invents a percentage or an ETA; it reports the stage and the queue as they are. */
  function paintStage(progress) {
    const host = byId('stage');
    if (!host) return;
    host.textContent = '';
    const line = (typeof stageLine === 'function') ? stageLine(progress) : null;
    if (!line) { host.hidden = true; return; }
    host.hidden = false;
    host.append(line);
  }
  function startStage() {
    stopStage();
    const read = async () => {
      try { paintStage(await call('/api/chat/progress', { headers: tokenHeader() })); }
      catch (error) { /* the stage line is an extra; a missing route must not fail the turn */ }
    };
    read();
    state.stageTimer = setInterval(read, 900);
  }
  function stopStage() {
    if (state.stageTimer) { clearInterval(state.stageTimer); state.stageTimer = null; }
    paintStage(null);
  }
  /* The engine's own first reading of the question, asked for beside the real turn. It is
     provisional by contract, so it fills the placeholder and nothing else; the answer card
     replaces the whole placeholder. A reading that never arrives costs the turn nothing. */
  function paintReading(host, packet) {
    if (!host) return;
    const line = (typeof readingLine === 'function') ? readingLine(packet) : null;
    if (!line) return;
    host.textContent = '';
    host.append(line);
    host.hidden = false;
  }
  async function askPreview(question, working, seq) {
    const host = working && working.querySelector ? working.querySelector('.working-reading') : null;
    if (!host) return;
    const body = { question:question };
    if (state.conversationId) body.conversation_id = state.conversationId;
    let packet = null;
    try { packet = await call('/api/chat/preview', jsonRequest('POST', body, state.controller ? state.controller.signal : null)); }
    catch (error) { return; /* the first reading is an extra; its absence must not fail the turn */ }
    if (seq !== state.previewSeq) return;
    paintReading(host, packet);
  }
  /* The receipt the conversation already holds: where it last read, and when the server answered.
     It is shown as the conversation's own receipt, never as fresh evidence. */
  function istClock(iso) {
    const when = new Date(iso);
    if (isNaN(when.getTime())) return '';
    try {
      return new Intl.DateTimeFormat('en-IN', { timeZone:'Asia/Kolkata', day:'2-digit', month:'short',
        hour:'2-digit', minute:'2-digit', hour12:false }).format(when) + ' IST';
    } catch (error) { return ''; }
  }
  function rememberReceipt(packet) {
    const facts = (packet && packet.facts) || [];
    const plan = (packet && packet.plan) || {};
    const place = (facts.length && facts[0].place) ||
      ((plan.places || []).map(item => item && item.name).filter(Boolean).join(', ')) || '';
    const at = istClock(packet && packet.answered_at_utc);
    state.lastReceipt = (place && at) ? { place:place, at:at } : null;
  }
  function startTicker() {
    stopTicker();
    state.ticker = setInterval(() => {
      const clock = document.querySelector('.working-clock');
      if (!clock) return;
      const since = Number(clock.dataset.since || state.startedAt);
      clock.textContent = Math.round((Date.now() - since) / 1000) + ' s elapsed';
    }, 1000);
  }
  function stopTicker() { if (state.ticker) { clearInterval(state.ticker); state.ticker = null; } }
  function showError(message, calm) {
    const box = byId('error');
    if (!box) return;
    box.textContent = message;
    box.className = 'error' + (calm ? ' is-calm' : '');
    box.hidden = false;
  }
  function clearError() { const box = byId('error'); if (box) { box.hidden = true; box.textContent = ''; } }

  /* ---------- transport ---------- */
  function RequestError(message, status, kind) {
    const error = new Error(message);
    error.name = 'RequestError'; error.status = status; error.kind = kind;
    return error;
  }
  function classify(status, payload) {
    const message = (payload && payload.error) || '';
    if (status === 403) return RequestError('This page no longer holds the workspace token. Reload the local page to continue.', 403, 'auth');
    if (status === 503) return RequestError(message || 'The local evidence store is unavailable. Check its files, then retry.', 503, 'down');
    if (/maximum number of waiting questions|busy longer than the queue allows/i.test(message)) {
      return RequestError(message, 429, 'busy');
    }
    if (/Another conversation is using the local model|one conversation at a time/i.test(message)) {
      return RequestError('Another question is using the local model. This workspace answers one at a time and holds only a few waiting questions; a full queue is refused rather than growing.', 400, 'locked');
    }
    return RequestError(message || 'The request could not be completed.', status, 'invalid');
  }
  async function call(path, options) {
    const response = await fetch(path, options || {});
    let payload = null;
    try { payload = await response.json(); } catch (error) { payload = null; }
    if (!response.ok) throw classify(response.status, payload);
    if (payload === null) throw RequestError('The workspace returned a response this page could not read.', response.status, 'malformed');
    return payload;
  }
  function newRequestId() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') return window.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, character => {
      const value = Math.floor(Math.random() * 16);
      return (character === 'x' ? value : (value & 0x3) | 0x8).toString(16);
    });
  }
  function jsonRequest(method, body, signal) {
    return { method:method, headers:{ 'Content-Type':'application/json', 'X-WeatherGPT-Token':TOKEN },
             body:JSON.stringify(body), signal:signal };
  }
  function tokenHeader() { return { 'X-WeatherGPT-Token':TOKEN }; }

  /* ---------- transcript ---------- */
  function thread() { return byId('thread'); }
  function scrollToEnd() {
    const box = thread();
    if (!box) return;
    requestAnimationFrame(() => { box.scrollTop = box.scrollHeight; });
  }
  function append(node) { const box = thread(); if (box && node) { box.append(node); scrollToEnd(); } }
  /* Show the reader the top of the newest card: its headline, and for a clarification
     the choices, rather than the end of its evidence disclosures. */
  function revealCard(card) {
    if (!card) return;
    // Two frames: the first lets the browser lay the new card out and finish any
    // pending scroll, the second measures settled geometry and corrects the offset.
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const box = thread();
      if (!box || typeof card.getBoundingClientRect !== 'function') return;
      const delta = card.getBoundingClientRect().top - box.getBoundingClientRect().top;
      box.scrollTop = Math.max(0, box.scrollTop + delta - 2);
    }));
  }
  /* The opening card is a starting point, not part of the conversation, so the
     first question retires it. A restored transcript keeps its own header until
     the next question replaces it the same way. */
  function retireWelcome() {
    const box = thread();
    const card = box && box.querySelector('.welcome');
    if (card) card.remove();
  }
  function firstPoint(packet) {
    const resolved = packet.resolved_points || {};
    const names = Object.keys(resolved);
    for (let index = 0; index < names.length; index += 1) {
      const place = resolved[names[index]];
      if (place && place.coordinates && Number.isFinite(place.coordinates.latitude)) {
        return { latitude:place.coordinates.latitude, longitude:place.coordinates.longitude, label:place.label || names[index] };
      }
    }
    return null;
  }
  function currentQuestion() {
    const input = byId('question');
    return input && input.value.trim() ? input.value.trim() : '';
  }
  function downloadFile(filename, text, kind) {
    const blob = new Blob([text], { type: kind || 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function stampName() { return new Date().toISOString().replace(/[:.]/g, '-'); }
  function downloadPacket(packet) {
    downloadFile('weathergpt-answer-' + stampName() + '.json', JSON.stringify(packet, null, 2), 'application/json');
  }
  function copyTurn(packet, button) {
    const text = answerMarkdown(packet);
    const flash = label => {
      if (!button || !button.textContent) return;
      const original = button.textContent;
      button.textContent = label;
      setTimeout(() => { button.textContent = original; }, 2200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => flash('Copied'), () => showError('The browser did not allow copying. Use Print this answer, or download the JSON, to take this answer elsewhere.', true));
    } else {
      showError('This browser does not allow copying from the page. Use Print this answer, or download the JSON, to take this answer elsewhere.', true);
    }
  }
  function printTurn() {
    // Printing is the portable route for a field or agricultural reader: the
    // stylesheet strips the workspace chrome and keeps the answer, its receipt
    // and its sources on paper.
    if (typeof window.print !== 'function') { showError('This browser does not support printing from the page.', true); return; }
    window.print();
  }
  function exportTurn(packet) {
    downloadFile('weathergpt-answer-' + stampName() + '.md', answerMarkdown(packet), 'text/markdown');
  }
  async function exportTranscript() {
    if (!state.conversationId) { showError('Ask a question first; there is no stored conversation to save yet.', true); return; }
    try {
      const transcript = await call('/api/conversations/' + encodeURIComponent(state.conversationId), { method:'GET', headers:tokenHeader() });
      const item = ((state.ledger || {}).conversations || []).filter(entry => entry.id === transcript.id)[0] || null;
      downloadFile('weathergpt-conversation-' + stampName() + '.md', transcriptMarkdown(transcript, item), 'text/markdown');
    } catch (error) {
      showError(error && error.message ? error.message : 'The stored conversation could not be read.');
    }
  }
  function newConversation() {
    if (state.busy) { showError('Wait for the current turn before starting a new conversation.', true); return; }
    state.conversationId = null;
    state.lastReceipt = null;
    closeRail();
    clearError();
    if (window.location.hash && window.history && window.history.replaceState) window.history.replaceState(null, '', window.location.pathname + '#/assistant');
    const box = thread();
    if (box) box.replaceChildren(renderWelcome(handlers()));
    const input = byId('question');
    if (input) { input.value = ''; input.focus(); }
    loadLedger();
  }
  function rememberAnswer() {
    state.lastSeen = new Date().toISOString();
    try { window.localStorage.setItem('weathergpt.lastAnswer', state.lastSeen); } catch (error) { /* private mode: no persistence */ }
  }
  function updateConnectionBanner(announceReconnect) {
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      renderBanner('This machine reports no network connection. The workspace and its stored evidence still work, but a collection that needs an upstream source cannot complete until the connection returns.');
      return;
    }
    if (announceReconnect && state.lastSeen) {
      renderBanner('Connection restored. The last answer was received ' + istStamp(state.lastSeen) + '. Ask again if you need current evidence.', true);
      setTimeout(() => renderBanner(null), 7000);
      return;
    }
    renderBanner(null);
  }
  function restoreFromHash() {
    const match = /^#\/c\/([0-9a-fA-F-]{36})$/.exec(window.location.hash || '');
    if (!match) return;
    restore({ id: match[1] });
  }
  function wireJump() {
    const box = thread(), jump = byId('jump-latest');
    if (!box || !jump) return;
    const sync = () => { jump.hidden = box.scrollHeight - box.scrollTop - box.clientHeight <= 240; };
    box.addEventListener('scroll', sync);
    jump.addEventListener('click', scrollToEnd);
    sync();
  }
  function handlers() {
    return {
      onChoose: choice => ask({ question:currentQuestion() || 'Which place did you mean?', selection:{ selection_id:choice.selection_id }, showQuestion:false }),
      onRetype: () => { const input = byId('question'); if (input) input.focus(); },
      onExample: text => { const input = byId('question'); if (input) input.value = text; ask({ question:text }); },
      onQuickReply: reply => ask({ question:reply }),
      onPlanChange: () => { const input = byId('question'); if (input) { input.value = 'Make it '; input.focus(); } },
      onPlanUndo: undoPlan,
      onRefresh: refreshFor,
      onDownload: downloadPacket,
      onCopy: copyTurn,
      onPrint: printTurn,
      onExport: exportTurn
    };
  }

  /* ---------- the ask ---------- */
  async function ask(request) {
    if (state.busy) { showError('This workspace answers one question at a time. Wait for the current turn, or stop waiting first.', true); return; }
    const question = String(request.question || '').trim();
    if (!question) { showError('Type a question first.'); return; }
    clearError();
    if (request.showQuestion !== false) { retireWelcome(); append(renderUserTurn(question)); }
    const working = renderWorking(question, state.lastReceipt);
    append(working);
    setBusy(true, 'Interpreting the question, then retrieving evidence…');
    setService('Working', 'is-busy');
    state.controller = new AbortController();
    state.cancelRequested = false;
    state.requestId = newRequestId();
    state.previewSeq += 1;
    askPreview(question, working, state.previewSeq);
    try {
      const body = { question:question, output_language:state.language || '', request_id:state.requestId };
      if (typeof WG !== 'undefined' && typeof WG.personaEntry === 'function' && WG.personaEntry()) body.persona = WG.personaEntry().id;
      if (state.conversationId) body.conversation_id = state.conversationId;
      if (request.selection && request.selection.selection_id) body.selection_id = request.selection.selection_id;
      if (request.selection && request.selection.coordinates) body.coordinates = request.selection.coordinates;
      const packet = await call('/api/chat', jsonRequest('POST', body, state.controller.signal));
      if (packet.conversation_id) state.conversationId = packet.conversation_id;
      if (packet.status === 'answered' || packet.status === 'partial') rememberAnswer();
      rememberReceipt(packet);
      working.remove();
      const card = renderTurn(packet, handlers());
      append(card);
      revealCard(card);
      const planAction = packet.plan_watch && packet.plan_watch.action;
      if ((planAction === 'saved' || planAction === 'changed' || planAction === 'resumed' || planAction === 'deleted') &&
          typeof WG !== 'undefined' && typeof WG.onPlanChanged === 'function') WG.onPlanChanged(packet.plan_watch);
      setService('Ready', 'is-ready');
      loadLedger({ quiet:true });
    } catch (error) {
      working.remove();
      if (error && error.name === 'AbortError') {
        if (!state.cancelRequested) {
          append(el('div', 'You stopped waiting for this turn. The page request was aborted and no cancel request was sent, so the server may still be finishing it; a later question waits in a bounded queue rather than being rejected instantly.', 'notice is-calm'));
        }
        setService(state.cancelRequested ? 'Stopped' : 'Ready', state.cancelRequested ? '' : 'is-ready');
      } else {
        const kind = error && error.kind;
        showError(error && error.message ? error.message : 'The local workspace is unreachable. Restart it and reload this page.');
        setService(kind === 'busy' ? 'Queue full' : kind === 'locked' ? 'One at a time' : kind === 'auth' ? 'Reload needed' : kind === 'down' ? 'Store unavailable' : 'Ready',
                   (kind === 'invalid' || kind === 'busy' || kind === 'locked') ? '' : 'is-down');
      }
    } finally {
      state.controller = null;
      setBusy(false);
      const input = byId('question');
      if (input) input.focus();
    }
  }

  /* ---------- plan watch ---------- */
  async function undoPlan(plan, box) {
    try {
      await call('/api/plans/update', jsonRequest('POST', { id:plan.id, action:'delete' }));
      const tools = box && box.querySelector ? box.querySelector('.plan-tools') : null;
      if (tools) tools.remove();
      if (box) box.append(el('p', 'Plan removed. Nothing will be checked or sent for it.', 'notice is-calm'));
      if (typeof WG !== 'undefined' && typeof WG.onPlanChanged === 'function') WG.onPlanChanged({ action:'deleted', plan:plan });
    } catch (error) {
      showError(error && error.message ? error.message : 'The plan could not be removed.', true);
    }
  }

  /* ---------- bounded collection ---------- */
  async function refreshFor(packet) {
    if (state.busy) { showError('This workspace answers one question at a time. Wait for the current turn first.', true); return; }
    const point = firstPoint(packet);
    if (!point) {
      showError('This answer did not resolve a single place point, so a collection cannot be requested for it. Ask again naming a town, a city or a coordinate.', true);
      return;
    }
    clearError();
    setBusy(true, 'Requesting a bounded collection…');
    setService('Collecting', 'is-busy');
    const controller = new AbortController();
    state.controller = controller;
    try {
      const result = await call('/api/refresh', jsonRequest('POST', { question:packet.question, coordinates:{ latitude:point.latitude, longitude:point.longitude } }, controller.signal));
      const refresh = result.refresh || {};
      const notice = el('div', undefined, 'notice' + (refresh.state === 'succeeded' ? ' is-good' : ' is-calm'));
      notice.append(el('p', refresh.message || 'A collection was requested.'));
      const detail = [refresh.state,
        refresh.claims_this_action !== undefined ? refresh.claims_this_action + ' provider claim(s) this action' : null,
        refresh.job_provider_attempts !== undefined ? refresh.job_provider_attempts + ' claim(s) for the job' : null,
        refresh.retry_due_utc_epoch ? 'next retry ' + istStamp(new Date(refresh.retry_due_utc_epoch * 1000).toISOString()) : null]
        .filter(Boolean).join(' \u00b7 ');
      if (detail) notice.append(el('p', detail, 'field-note'));
      notice.append(el('p', 'Collection for ' + point.label + '. Retry timing, provider budgets and cooldowns stay in force, and no background worker keeps collecting.', 'field-note'));
      append(notice);
      state.controller = null;
      setBusy(false);
      setService('Ready', 'is-ready');
      await ask({ question:packet.question, showQuestion:false });
      loadHealth();
    } catch (error) {
      if (!(error && error.name === 'AbortError')) showError(error && error.message ? error.message : 'The collection could not be requested.');
      else append(el('div', 'You stopped waiting for the collection. The server may still be finishing it; retry timing and budgets still apply.', 'notice is-calm'));
      setService('Ready', 'is-ready');
    } finally {
      state.controller = null;
      if (state.busy) setBusy(false);
    }
  }

  /* ---------- ledger and health ---------- */
  async function loadLedger(options) {
    options = options || {};
    try {
      const ledger = await call('/api/conversations', { method:'GET', headers:tokenHeader() });
      state.ledger = ledger;
      renderLedger(ledger, ledgerHandlers());
    } catch (error) {
      const note = byId('ledger-note');
      if (note && !options.quiet) {
        note.textContent = error && error.kind === 'auth' ? 'Reload the page to read stored conversations.' : 'Stored conversations could not be read, so restore and delete are unavailable.';
      }
    }
  }
  async function restore(item) {
    if (state.busy) { showError('Wait for the current turn before opening another conversation.', true); return; }
    clearError();
    try {
      const transcript = await call('/api/conversations/' + encodeURIComponent(item.id), { method:'GET', headers:tokenHeader() });
      state.conversationId = transcript.id;
      renderRestored(transcript, { onRetype:() => { const input = byId('question'); if (input) input.focus(); } });
      if (window.history && window.history.replaceState) window.history.replaceState(null, '', '#/c/' + transcript.id);
      closeRail();
      loadLedger();
    } catch (error) {
      showError(error && error.message ? error.message : 'That conversation could not be restored.');
    }
  }
  async function remove(item) {
    if (!window.confirm('Delete this stored conversation? Its questions and answers are removed from the local store.')) return;
    try {
      await call('/api/conversations/' + encodeURIComponent(item.id), { method:'DELETE', headers:tokenHeader() });
      if (state.conversationId === item.id) {
        state.conversationId = null;
        const box = thread();
        if (box) box.replaceChildren(renderWelcome(handlers()));
        append(el('div', 'That conversation was deleted from the local store, so the transcript is gone. The sources its answers cited are unaffected, and they were receipts for their own retrieval time.', 'notice is-calm'));
      }
      loadLedger();
    } catch (error) {
      showError(error && error.message ? error.message : 'That conversation could not be deleted.');
    }
  }
  async function loadHealth() {
    try { renderHealth(await call('/api/health', { method:'GET', headers:tokenHeader() })); }
    catch (error) { const box = byId('health'); if (box) box.replaceChildren(el('p', 'Collection health could not be read.', 'block-note')); }
  }

  /* ---------- rail ---------- */
  function setRail(open) {
    const rail = byId('rail'), backdrop = byId('rail-backdrop'), toggle = byId('rail-toggle');
    if (rail) rail.classList.toggle('is-open', open);
    if (backdrop) backdrop.classList.toggle('is-open', open);
    if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  function closeRail() { setRail(false); }
  function toggleRail() { const rail = byId('rail'); setRail(!(rail && rail.classList.contains('is-open'))); }

  /* ---------- fields ---------- */
  function selectionFromFields() {
    const latitude = byId('latitude'), longitude = byId('longitude');
    if (!latitude || !longitude) return null;
    if (!latitude.value.trim() || !longitude.value.trim()) return null;
    const lat = Number(latitude.value), lon = Number(longitude.value);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) { showError('Latitude and longitude must be numbers.'); return null; }
    return { coordinates:{ latitude:lat, longitude:lon } };
  }
  function buildFieldSentence() {
    const measure = byId('measure'), place = byId('place'), day = byId('day');
    const start = byId('start'), end = byId('end'), latitude = byId('latitude'), longitude = byId('longitude');
    const intent = measure ? measure.value : 'How much rain is forecast';
    const pinned = latitude && longitude && latitude.value.trim() && longitude.value.trim();
    const where = pinned ? (latitude.value.trim() + ', ' + longitude.value.trim())
                         : (place && place.value.trim() ? place.value.trim() : '');
    if (!where) { showError('Enter a place name, or both coordinates.'); return null; }
    const when = start && end && start.value && end.value ? ' from ' + start.value + ' to ' + end.value + ' IST' : '';
    return intent + ' for ' + where + ' ' + (day ? day.value : 'tomorrow') + when + '?';
  }

  /* ---------- wiring ---------- */
  function bind() {
    const form = byId('ask-form');
    if (form) form.addEventListener('submit', event => {
      event.preventDefault();
      ask({ question:currentQuestion(), selection:selectionFromFields() });
    });
    const question = byId('question');
    if (question) question.addEventListener('keydown', event => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        ask({ question:currentQuestion(), selection:selectionFromFields() });
      }
    });
    const toggle = null;
    if (toggle) toggle.addEventListener('click', () => {
      const fields = byId('composer-fields');
      if (!fields) return;
      const open = fields.hidden;
      fields.hidden = !open;
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.textContent = open ? 'Hide fields' : 'Ask with fields';
    });
    const useFields = byId('use-fields');
    if (useFields) useFields.addEventListener('click', () => {
      const sentence = buildFieldSentence();
      if (!sentence) return;
      const input = byId('question');
      if (input) { input.value = sentence; input.focus(); }
      clearError();
    });
    const cancel = byId('cancel');
    if (cancel) cancel.addEventListener('click', async () => {
      state.cancelRequested = true;
      const requestId = state.requestId;
      if (state.controller) state.controller.abort();
      if (!requestId) return;
      try {
        const packet = await call('/api/chat/cancel', jsonRequest('POST', { request_id:requestId }));
        const detail = (packet && packet.detail) || '';
        const where = (packet && packet.stage_label) ? ' at ' + packet.stage_label.toLowerCase() : '';
        if (packet && packet.state === 'cancel_requested') {
          append(el('div', 'Stop requested' + where + '. ' + detail, 'notice is-calm'));
        } else if (packet && packet.state === 'not_running') {
          append(el('div', 'That turn had already finished before the stop arrived. ' + detail, 'notice is-calm'));
        } else {
          append(el('div', 'The workspace answered the stop request with state "' + ((packet && packet.state) || 'unknown') + '".', 'notice is-calm'));
        }
      } catch (error) {
        append(el('div', 'The stop request could not reach the workspace; a later question still waits in its bounded queue.', 'notice is-calm'));
      }
    });
    const language = byId('language');
    if (language) language.addEventListener('change', () => { state.language = language.value; });
    const railToggle = byId('rail-toggle');
    if (railToggle) railToggle.addEventListener('click', toggleRail);
    const backdrop = byId('rail-backdrop');
    if (backdrop) backdrop.addEventListener('click', closeRail);
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') closeRail();
      // Command-K belongs to the command palette (shell.js). This handler only adds a
      // single-key shortcut that does not steal typing: "/" focuses the question box.
      const typing = event.target && /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName || '');
      if (event.key === '/' && !typing && !event.metaKey && !event.ctrlKey && !event.altKey) {
        event.preventDefault();
        const input = byId('question');
        if (input) input.focus();
      }
    });
    const newConversationButton = byId('new-conversation');
    if (newConversationButton) newConversationButton.addEventListener('click', newConversation);
    const exportButton = byId('export-transcript');
    if (exportButton) exportButton.addEventListener('click', exportTranscript);
    const search = byId('ledger-search');
    if (search) search.addEventListener('input', () => { if (state.ledger) renderLedger(state.ledger, ledgerHandlers()); });
    if (typeof window.addEventListener === 'function') {
      window.addEventListener('offline', () => updateConnectionBanner(false));
      window.addEventListener('online', () => updateConnectionBanner(true));
    }
  }
  function ledgerHandlers() { return { currentId:() => state.conversationId, onOpen:restore, onDelete:remove }; }

  /* The reading position arrives from its own route after the page paints. If the
     welcome is still on screen, it is repainted so the questions offered match the
     position; a conversation already under way is never disturbed. */
  function refreshWelcome() {
    if (state.busy || state.conversationId) return;
    const box = thread();
    if (!box || !box.querySelector('.welcome')) return;
    box.replaceChildren(renderWelcome(handlers()));
  }

  function start() {
    bind();
    const box = thread();
    if (box) box.replaceChildren(renderWelcome(handlers()));
    try { state.lastSeen = window.localStorage.getItem('weathergpt.lastAnswer'); } catch (error) { state.lastSeen = null; }
    updateConnectionBanner(false);
    wireJump();
    setService('Ready', 'is-ready');
    setBusy(false);
    loadLedger();
    loadHealth();
    restoreFromHash();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();

  window.WeatherGPT = { newConversation:newConversation, ask:ask, state:state, refreshWelcome:refreshWelcome, loadLedger:loadLedger, loadHealth:loadHealth, restore:restore, buildFieldSentence:buildFieldSentence, firstPoint:firstPoint };
})();
