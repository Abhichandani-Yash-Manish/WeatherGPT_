'use strict';
/* The opening state of the conversation.

   Before you have asked anything, the first thing on screen is the published
   warning state for the place you are working with — the question you would have
   asked anyway. In a product whose theme is disaster management, the opening screen
   should answer "is anything wrong here" without being asked.

   A quiet district is stated as quiet and given the same weight a hazard would get.
   It is never dressed as reassurance: IMD publishes "no warning in this product",
   which is not an all-clear, and this surface says exactly that. */

(function () {
  const TOKEN = (document.querySelector('meta[name="workspace-token"]') || {}).content || '';
  const DAY_LABELS = { 1: 'Today', 2: 'Tomorrow', 3: 'Day 3', 4: 'Day 4', 5: 'Day 5' };
  const COLOURS = ['red', 'orange', 'yellow', 'green'];
  let lastKey = null;

  function el(tag, text, cls) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (cls) node.className = cls;
    return node;
  }

  function read(path, params) {
    const parts = [];
    Object.keys(params || {}).forEach(key => {
      const value = params[key];
      if (value === undefined || value === null || value === '') return;
      parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(value));
    });
    return fetch(path + (parts.length ? '?' + parts.join('&') : ''),
                 { headers: { 'X-WeatherGPT-Token': TOKEN } })
      .then(response => { if (!response.ok) throw new Error('unavailable'); return response.json(); });
  }

  function shortDate(value) {
    if (!value) return 'Date not stated';
    const at = new Date(value);
    if (Number.isNaN(at.getTime())) return String(value);
    return new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short' }).format(at);
  }

  /* The five-day strip is IMD's own published shape, and it carries colour only
     where the source published a hazard. */
  function strip(days) {
    const box = el('div', undefined, 'day-strip');
    (days || []).slice(0, 5).forEach(day => {
      const colour = COLOURS.indexOf(day.colour) >= 0 ? day.colour : '';
      const quiet = !!day.quiet || !colour;
      const line = el('div', undefined, 'day-line' + (colour ? ' ' + colour : '') + (quiet ? ' is-quiet' : ''));
      line.append(el('span', shortDate(day.date_utc || day.date_local), 'day-date'));
      line.append(el('span', DAY_LABELS[day.day] || ('Day ' + day.day), 'day-name'));
      const hazard = day.quiet ? 'No warning in this product'
        : (day.hazard_text || (day.hazards || []).join(', ') || day.colour || 'Not stated');
      line.append(el('span', hazard, 'day-hazard'));
      box.append(line);
    });
    return box;
  }

  function hero(view, placeLabel) {
    const data = (view && view.data) || {};
    const days = data.days || [];
    const severity = data.severity || null;
    const panel = el('section', undefined, 'warning-panel');
    const head = el('div', undefined, 'warning-head');

    const headline = severity
      ? 'A ' + severity + ' warning is published for this district'
      : 'No warning in this product';
    head.append(el('h2', headline));
    head.append(el('span', placeLabel || data.district_label || 'the working place', 'muted'));
    panel.append(head);

    const note = el('p', undefined, 'block-note');
    note.textContent = severity
      ? 'IMD district warning guidance, bulletin of ' + (data.issued_label || shortDate(data.issued_at_utc)) +
        '. This workspace relays the published level; it does not issue warnings and this is not a clearance.'
      : 'IMD publishes no warning for this district in this product. That is not an all-clear, and it is not a statement about hazards other products cover.';
    const wrap = el('div', undefined, 'warning-days');
    wrap.append(note);
    if (days.length) wrap.append(strip(days));
    panel.append(wrap);
    return panel;
  }

  function unavailable(message) {
    const panel = el('section', undefined, 'warning-panel');
    const head = el('div', undefined, 'warning-head');
    head.append(el('h2', 'Warning state not read'));
    panel.append(head);
    const wrap = el('div', undefined, 'warning-days');
    wrap.append(el('p', message, 'block-note'));
    panel.append(wrap);
    return panel;
  }

  async function fill(slot) {
    const place = window.WG && window.WG.state && window.WG.state.place;
    if (!place || !Number.isFinite(place.latitude)) {
      slot.replaceChildren(unavailable('Choose a place to see what is published for it.'));
      return;
    }
    const key = place.latitude + ',' + place.longitude;
    if (slot.dataset.key === key) return;
    slot.dataset.key = key;
    lastKey = key;
    try {
      const view = await read('/api/warnings/place', { lat: place.latitude, lon: place.longitude });
      if (slot.dataset.key !== key) return;
      const status = view && view.status;
      if (status && status !== 'ok' && status !== 'answered') {
        slot.replaceChildren(unavailable(
          (view.message || 'The published warning for this place could not be read.') +
          ' Asking a question still works.'));
        return;
      }
      slot.replaceChildren(hero(view, place.label));
    } catch (error) {
      if (slot.dataset.key !== key) return;
      slot.replaceChildren(unavailable('The published warning for this place could not be read on this workspace. Asking a question still works.'));
    }
  }

  function scan() {
    const slot = document.querySelector('.welcome-hero');
    if (slot) fill(slot);
  }

  function start() {
    const thread = document.getElementById('thread');
    if (thread && window.MutationObserver) {
      new MutationObserver(scan).observe(thread, { childList: true, subtree: true });
    }
    /* The working place is chosen after first paint, so the hero is filled again when
       it changes rather than being left with whatever was first known. */
    window.addEventListener('hashchange', scan);
    document.addEventListener('click', () => window.setTimeout(scan, 400));
    window.setTimeout(scan, 300);
    window.setInterval(() => {
      const place = window.WG && window.WG.state && window.WG.state.place;
      const key = place && Number.isFinite(place.latitude) ? place.latitude + ',' + place.longitude : null;
      if (key && key !== lastKey) scan();
    }, 1500);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
}());
