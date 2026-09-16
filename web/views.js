'use strict';
/* Rendering for the conversation packet. Every value shown here comes from the
   packet the engine returned; nothing is inferred, scored or rounded. Source and
   runtime text is inserted as text, never as markup. */

const IST_ZONE = 'Asia/Kolkata';
const STATUS_LABELS = {
  answered:'Evidence retrieved', partial:'Partly answered', needs_selection:'Choose a place',
  needs_clarification:'One more detail', unavailable:'Evidence gap', explanation:'General explanation',
  outside_validity:'Choose an upcoming window', stale:'Evidence expired',
  degraded:'Refresh incomplete', prototype_answer:'Forecast available',
  conversation:'Conversational reply'
};
const HELD_STATUS = ['needs_selection','needs_clarification','unavailable','outside_validity','stale','partial','degraded'];
const EVIDENCE_KINDS = {
  forecast:'Model forecast', observation:'Observation', reanalysis:'Modeled reanalysis',
  air_quality_model:'Modelled air quality',
  advisory:'Source advisory', reference:'Reference only', context:'Source context'
};
const PARAMETER_NAMES = {
  precipitation:'precipitation', precipitation_probability:'rain probability', temperature_2m:'temperature',
  temperature_c:'temperature', relative_humidity_2m:'humidity', wind_speed_10m:'wind speed',
  wind_speed_kt:'wind speed', rainfall:'rainfall', wave_height:'significant wave height',
  wave_direction:'wave direction', wave_period:'wave period', discharge:'river discharge'
};
const LANGUAGE_NAMES = { en:'English', hi:'Hindi', gu:'Gujarati' };

function el(tag, text, cls) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (cls) node.className = cls;
  return node;
}
function dataEl(text) { return el('span', text, 'data'); }
function firstOf(list) { return Array.isArray(list) && list.length ? list[0] : null; }

/* ---------- time, always IST, always explicit ---------- */
function istParts(value) {
  const at = new Date(value);
  if (!value || Number.isNaN(at.getTime())) return null;
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: IST_ZONE, day:'numeric', month:'short', year:'numeric',
    hour:'2-digit', minute:'2-digit', hour12:false
  }).formatToParts(at).reduce((all, part) => (all[part.type] = part.value, all), {});
  return { day: parts.day, month: parts.month, year: parts.year, hour: parts.hour, minute: parts.minute };
}
function istStamp(value) {
  const p = istParts(value);
  if (!p) return 'Time not supplied';
  return p.day + ' ' + p.month + ' ' + p.year + ', ' + p.hour + ':' + p.minute + ' IST';
}
function istClock(value) {
  const p = istParts(value);
  return p ? p.hour + ':' + p.minute : '';
}
function istDay(value) {
  const p = istParts(value);
  return p ? p.day + ' ' + p.month : '';
}
function istWindowText(start, end) {
  if (!start && !end) return null;
  if (!end || start === end) return istDay(start) + ', ' + istClock(start) + ' IST';
  if (istDay(start) === istDay(end)) return istDay(start) + ', ' + istClock(start) + '\u2013' + istClock(end) + ' IST';
  return istDay(start) + ' ' + istClock(start) + ' \u2192 ' + istDay(end) + ' ' + istClock(end) + ' IST';
}
function hourLabel(fact) { return istWindowText(fact.start, fact.end); }

/* ---------- small readers over the packet ---------- */
function citationIndex(packet) {
  const index = new Map();
  (packet.citations || []).forEach(citation => { if (citation.id) index.set(citation.id, citation); });
  return index;
}
function sourceOf(packet, fact) {
  const index = citationIndex(packet);
  return (fact.citation_ids || []).map(id => index.get(id)).find(Boolean) || null;
}
function kindOf(fact) {
  if (fact.evidence_kind && EVIDENCE_KINDS[fact.evidence_kind]) return EVIDENCE_KINDS[fact.evidence_kind];
  if (fact.evidence_kind) return fact.evidence_kind;
  if (fact.observed_at || fact.sample_at) return EVIDENCE_KINDS.observation;
  return null;
}
function findDeep(node, key, found) {
  found = found || [];
  if (Array.isArray(node)) node.forEach(item => findDeep(item, key, found));
  else if (node && typeof node === 'object') {
    Object.keys(node).forEach(name => {
      if (name === key && node[name] !== null && node[name] !== undefined) found.push(node[name]);
      else findDeep(node[name], key, found);
    });
  }
  return found;
}
function coverageFacts(packet) {
  return (packet.facts || []).filter(fact => fact.value !== undefined && fact.value !== null && fact.value !== '');
}
function chartEvidence(charts) {
  const ids = new Set();
  (charts || []).forEach(chart => (chart.points || []).forEach(point => { if (point.evidence_id) ids.add(point.evidence_id); }));
  return ids;
}
const WARNING_PARAMETERS = new Set(['official_district_warning']);
function warningFacts(packet) {
  return coverageFacts(packet).filter(fact => WARNING_PARAMETERS.has(fact.parameter));
}
function sequenceFacts(packet) {
  const plotted = chartEvidence(packet.charts);
  return coverageFacts(packet).filter(fact => !plotted.has(fact.id) && !WARNING_PARAMETERS.has(fact.parameter));
}
function languageRequested(plan, chosen) {
  const declared = plan && plan.language;
  if (chosen) return chosen;
  return declared && declared !== 'en' ? declared : null;
}
function languageDowngradeNote(packet) {
  return (packet.notes || []).find(note => /output language could not be rendered/i.test(note)) || null;
}
function refreshRecords(packet) {
  return (packet.trace && packet.trace.tools ? packet.trace.tools : []).filter(tool => tool && tool.refresh).map(tool => ({ tool: tool.name, refresh: tool.refresh }));
}
function windowFacts(packet) {
  return coverageFacts(packet).filter(fact => fact.start && fact.end && Date.parse(fact.start) < Date.parse(fact.end));
}
function placeOf(packet, fact) {
  if (fact && fact.place) return fact.place;
  const resolved = packet.resolved_points || {};
  const first = Object.keys(resolved)[0];
  return first ? (resolved[first].label || first) : null;
}

/* ---------- the validity ruler ---------- */
function renderRuler(packet) {
  const spans = windowFacts(packet);
  if (!spans.length) return null;
  const starts = spans.map(fact => Date.parse(fact.start));
  const ends = spans.map(fact => Date.parse(fact.end));
  const from = Math.min.apply(null, starts), to = Math.max.apply(null, ends);
  if (!(to > from)) return null;

  const covered = spans.map(fact => [Date.parse(fact.start), Date.parse(fact.end)])
    .sort((a, b) => a[0] - b[0])
    .reduce((merged, span) => {
      const last = merged[merged.length - 1];
      if (last && span[0] <= last[1]) last[1] = Math.max(last[1], span[1]);
      else merged.push(span.slice());
      return merged;
    }, []);

  // The ruler has no value axis, so the track runs almost to the panel edge.
  const width = 640, track = 8, y = 34, height = 15;
  const scale = at => track + (at - from) / (to - from) * (width - track - 12);
  const box = el('div', undefined, 'ruler');
  box.append(el('p', 'Window covered by the evidence', 'ruler-title'));

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 ' + width + ' ' + (y + height + 34));
  svg.setAttribute('role', 'img');
  const seconds = Math.round((to - from) / 1000);
  const hours = Math.round(seconds / 3600 * 10) / 10;
  svg.setAttribute('aria-label', 'Requested window ' + istWindowText(spans[0].start, spans[0].end) +
    ', covering ' + hours + ' hours across ' + spans.length + ' retrieved samples');
  const node = (name, attrs, text) => {
    const created = document.createElementNS('http://www.w3.org/2000/svg', name);
    Object.entries(attrs).forEach(([key, value]) => created.setAttribute(key, String(value)));
    if (text !== undefined) created.textContent = text;
    svg.append(created);
    return created;
  };
  node('rect', { x: track, y: y, width: width - track - 12, height: height, rx: 3, 'class': 'ruler-rail' });
  // Uncovered intervals are drawn as hatched gaps rather than left ambiguous:
  // a rail that simply ends would read as coverage it does not have.
  const segments = [];
  let cursor = from;
  covered.forEach(span => {
    if (span[0] - cursor > 15 * 60 * 1000) {
      const left = scale(cursor), right = scale(span[0]);
      node('rect', { x: left.toFixed(1), y: y, width: Math.max(2, right - left).toFixed(1), height: height, rx: 3, 'class': 'ruler-gap' });
      segments.push({ start: cursor, end: span[0], covered: false });
    }
    cursor = Math.max(cursor, span[1]);
  });
  if (to - cursor > 15 * 60 * 1000) {
    const left = scale(cursor);
    node('rect', { x: left.toFixed(1), y: y, width: Math.max(2, (width - track - 12) - (left - track)).toFixed(1), height: height, rx: 3, 'class': 'ruler-gap' });
    segments.push({ start: cursor, end: to, covered: false });
  }
  covered.forEach(span => {
    const left = scale(span[0]), right = scale(span[1]);
    node('rect', { x: left.toFixed(1), y: y, width: Math.max(2, right - left).toFixed(1), height: height, rx: 3, 'class': 'ruler-covered' });
    node('line', { x1: left.toFixed(1), x2: left.toFixed(1), y1: y - 4, y2: y, 'class': 'ruler-edge' });
    segments.push({ start: span[0], end: span[1], covered: true });
  });
  [0, 0.5, 1].forEach(fraction => {
    const at = from + (to - from) * fraction;
    node('line', { x1: scale(at).toFixed(1), x2: scale(at).toFixed(1), y1: y + height + 3, y2: y + height + 8, 'class': 'ruler-edge' });
    node('text', { x: scale(at).toFixed(1), y: y + height + 22, 'text-anchor': fraction === 0 ? 'middle' : fraction === 1 ? 'end' : 'middle', 'class': 'ruler-tick-label' }, istClock(new Date(at).toISOString()));
  });
  // Source-hour ticks while the window is short enough for them to mean something.
  if (hours <= 36) {
    const step = hours <= 12 ? 3600 * 1000 : 6 * 3600 * 1000;
    for (let at = Math.ceil(from / step) * step; at < to; at += step) {
      node('line', { x1: scale(at).toFixed(1), x2: scale(at).toFixed(1), y1: y + height, y2: y + height + 5, 'class': 'ruler-hour' });
    }
  }
  // The ruler is the answer's window made legible: every part of it is reachable, and a part with
  // no retrieved evidence says so rather than being left as blank space that could read as coverage.
  const readoutLine = el('p', 'Focus a part of the window to read what the evidence covers there.', 'ruler-readout');
  readoutLine.setAttribute('aria-live', 'polite');
  segments.slice().sort((left, right) => left.start - right.start).forEach(segment => {
    const samples = spans.filter(fact => Date.parse(fact.start) < segment.end && Date.parse(fact.end) > segment.start).length;
    const range = istWindowText(new Date(segment.start).toISOString(), new Date(segment.end).toISOString());
    const label = segment.covered
      ? 'Covered by retrieved evidence ' + range + ' \u00b7 ' + samples + ' sample' + (samples === 1 ? '' : 's')
      : 'No retrieved evidence ' + range + ' \u00b7 drawn as a gap and never interpolated';
    const hit = node('rect', { x: scale(segment.start).toFixed(1), y: y - 4, width: Math.max(3, (scale(segment.end) - scale(segment.start))).toFixed(1),
                               height: height + 8, 'class': 'ruler-hit', tabindex: 0, role: 'button', 'aria-label': label });
    const show = () => { readoutLine.textContent = label; };
    hit.addEventListener('focus', show);
    hit.addEventListener('mouseenter', show);
    hit.addEventListener('click', show);
    hit.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); show(); } });
  });
  node('text', { x: track, y: 22, 'class': 'ruler-caption' }, istDay(spans[0].start) + ' \u00b7 ' + Math.round(hours * 10) / 10 + ' h');
  box.append(svg);
  box.append(readoutLine);

  const distances = findDeep(packet, 'grid_distance_km');
  const foot = el('p', undefined, 'ruler-foot');
  foot.append(el('span', spans.length + ' retrieved sample' + (spans.length === 1 ? '' : 's') + ' over ' + hours + ' hours. Source hours start on UTC boundaries, which are :30 in IST. Values are samples, not a continuous trace.'));
  if (distances.length) foot.append(el('span', ' Answering model cell is ' + distances[0] + ' km from the requested point.'));
  box.append(foot);
  return box;
}

/* ---------- the evidence receipt ---------- */
/* Copying a receipt is copying what it shows, in the order it shows it. If the browser refuses the
   clipboard, the button says so rather than reporting a success that did not happen. */
function copyText(text, button) {
  const done = label => {
    if (!button) return;
    const original = button.textContent;
    button.textContent = label;
    if (window.setTimeout) window.setTimeout(() => { button.textContent = original; }, 1800);
  };
  const fallback = () => {
    try {
      const helperNode = document.createElement('textarea');
      helperNode.className = 'copy-helper';
      helperNode.value = text;
      document.body.append(helperNode);
      helperNode.select();
      const copied = document.execCommand && document.execCommand('copy');
      helperNode.remove();
      done(copied ? 'Copied' : 'Copy unavailable here');
    } catch (error) {
      done('Copy unavailable here');
    }
  };
  if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => done('Copied'), fallback);
    return;
  }
  fallback();
}
function receiptRow(list, key, value) {
  if (value === null || value === undefined || value === '') return;
  const row = el('div', undefined, 'receipt-row');
  row.append(el('span', key, 'receipt-key'), value instanceof Node ? value : el('span', value, 'receipt-val'));
  list.append(row);
}
function renderReceipt(packet, fact) {
  if (!fact) return null;
  const source = sourceOf(packet, fact);
  const box = el('section', undefined, 'receipt');
  box.append(el('p', 'Evidence receipt', 'receipt-title'));
  const rows = el('div', undefined, 'receipt-rows');
  receiptRow(rows, 'Measure', (fact.label || PARAMETER_NAMES[fact.parameter] || 'Value') + (fact.parameter ? ' (' + fact.parameter + ')' : ''));
  receiptRow(rows, 'Value', fact.value + (fact.unit ? ' ' + fact.unit : '') + (fact.method ? ' \u00b7 method ' + fact.method : ''));
  receiptRow(rows, 'Place', placeOf(packet, fact));
  receiptRow(rows, 'Entity', fact.entity_id);
  receiptRow(rows, 'Window', hourLabel(fact));
  if (fact.observed_at) receiptRow(rows, 'Observed', istStamp(fact.observed_at));
  receiptRow(rows, 'Evidence', kindOf(fact));
  if (source) {
    const line = el('span', undefined, 'receipt-val');
    const label = [source.source_id, source.provider, source.product].filter(Boolean).join(' \u00b7 ');
    try {
      const url = new URL(source.url);
      if (url.protocol === 'https:') {
        const link = el('a', label);
        link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
        line.append(link);
      } else line.append(document.createTextNode(label));
    } catch (error) { line.append(document.createTextNode(label)); }
    receiptRow(rows, 'Source', line);
  } else {
    receiptRow(rows, 'Source', fact.source_id);
  }
  if (source && source.retrieved_at_utc) receiptRow(rows, 'Retrieved', istStamp(source.retrieved_at_utc));
  if (source && (source.page || source.row || source.column)) {
    receiptRow(rows, 'Locator', [source.page ? 'page ' + source.page : null, source.row ? 'row ' + source.row : null, source.column || null].filter(Boolean).join(' \u00b7 '));
  }
  if (fact.evidence_version) receiptRow(rows, 'Evidence id', String(fact.evidence_version).slice(0, 16) + '\u2026');
  if (fact.task_id) receiptRow(rows, 'Task', fact.task_id);
  box.append(rows);
  if (fact.source_locators && fact.source_locators.length) {
    const locators = el('p', undefined, 'receipt-locators');
    locators.append(el('span', 'Record path' + (fact.source_locators.length === 1 ? ': ' : 's: ') + fact.source_locators.join('  ')));
    box.append(locators);
  }
  // The chain is the receipt's spine in one line: which source, retrieved when,
  // through which contract, supporting which claim. It adds no new fact.
  const chain = el('p', undefined, 'receipt-chain');
  chain.append(el('span', (source && source.source_id) || fact.source_id || 'source', 'data'));
  chain.append(el('span', ' → ', 'receipt-key'));
  chain.append(el('span', 'retrieved ' + (source && source.retrieved_at_utc ? istStamp(source.retrieved_at_utc) : 'time not recorded'), 'receipt-val'));
  chain.append(el('span', ' → ', 'receipt-key'));
  chain.append(el('span', fact.method || kindOf(fact) || 'typed contract', 'receipt-val'));
  chain.append(el('span', ' → ', 'receipt-key'));
  chain.append(el('span', 'claim ' + (fact.id || 'unidentified'), 'data'));
  box.append(chain);
  const actions = el('div', undefined, 'receipt-actions');
  const copy = el('button', 'Copy this receipt', 'ghost');
  copy.type = 'button';
  copy.setAttribute('aria-label', 'Copy the evidence receipt as text');
  copy.addEventListener('click', () => {
    const lines = (rows.children || []).map(row => {
      const key = row.children && row.children[0] ? row.children[0].textContent : '';
      const value = row.children && row.children[1] ? row.children[1].textContent : '';
      return key + ': ' + value;
    });
    copyText('WeatherGPT evidence receipt' + String.fromCharCode(10) + lines.join(String.fromCharCode(10)), copy);
  });
  const print = el('button', 'Print', 'ghost');
  print.type = 'button';
  print.setAttribute('aria-label', 'Print this answer');
  print.addEventListener('click', () => { if (window.print) window.print(); });
  actions.append(copy, print);
  box.append(actions);
  const distances = findDeep(packet, 'grid_distance_km');
  const note = el('p', undefined, 'receipt-note');
  note.append(el('span', 'A receipt for the moment it was retrieved, not a standing fact. ' + (distances.length ? 'The answering cell is ' + distances[0] + ' km from the requested point. ' : '') + 'Model output is not an observation and not a district average.'));
  box.append(note);
  return box;
}

/* ---------- the series receipt ---------- */
function renderSeriesReceipt(packet) {
  const charts = packet.charts || [];
  if (!charts.length) return null;
  const plotted = chartEvidence(charts);
  const series = coverageFacts(packet).filter(fact => plotted.has(fact.id));
  if (!series.length) return null;
  const box = el('section', undefined, 'receipt');
  box.append(el('p', 'Evidence receipt', 'receipt-title'));
  const rows = el('div', undefined, 'receipt-rows');
  const measures = [];
  series.forEach(fact => {
    const name = fact.label || PARAMETER_NAMES[fact.parameter] || 'value';
    if (measures.indexOf(name) < 0) measures.push(name);
  });
  receiptRow(rows, 'Measure', measures.join(', '));
  receiptRow(rows, 'Values', series.length + ' retrieved values, each plotted and inspectable with its own evidence id');
  receiptRow(rows, 'Place', placeOf(packet, series[0]));
  const sources = [];
  series.forEach(fact => { if (fact.source_id && sources.indexOf(fact.source_id) < 0) sources.push(fact.source_id); });
  const citation = sourceOf(packet, series[0]);
  if (citation) {
    const line = el('span', undefined, 'receipt-val');
    const label = [sources.join(', '), citation.provider, citation.product].filter(Boolean).join(' · ');
    try {
      const url = new URL(citation.url);
      if (url.protocol === 'https:') {
        const link = el('a', label);
        link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
        line.append(link);
      } else line.append(document.createTextNode(label));
    } catch (error) { line.append(document.createTextNode(label)); }
    receiptRow(rows, 'Source', line);
  } else {
    receiptRow(rows, 'Source', sources.join(', '));
  }
  if (citation && citation.retrieved_at_utc) receiptRow(rows, 'Retrieved', istStamp(citation.retrieved_at_utc));
  if (citation && (citation.page || citation.row || citation.column)) {
    receiptRow(rows, 'First locator', [citation.page ? 'page ' + citation.page : null, citation.row ? 'row ' + citation.row : null, citation.column || null].filter(Boolean).join(' · '));
  }
  const version = series[0].evidence_version;
  if (version) receiptRow(rows, 'Evidence id', String(version).slice(0, 16) + '…');
  box.append(rows);
  const note = el('p', undefined, 'receipt-note');
  note.append(el('span', 'A receipt for the moment the series was retrieved, not a standing fact. The chart is drawn from these values; a descriptive slope is not a projection, an attribution or a validated trend.'));
  box.append(note);
  return box;
}


/* ---------- official district warning panel ---------- */
const WARNING_CHIP = { red:'is-red', orange:'is-orange', yellow:'is-yellow', green:'is-green' };
function warningDaysTable(district) {
  const table = el('table', undefined, 'warning-days');
  const head = el('tr');
  ['Day','IMD colour','Official hazard','Window (IST)'].forEach(name => { const th = el('th', name); th.scope = 'col'; head.append(th); });
  table.append(head);
  (district.days || []).forEach(day => {
    const row = el('tr');
    row.append(el('td', 'Day ' + day.day + ' · ' + day.label));
    const colour = el('td');
    const chip = el('span', day.colour || 'colour not supplied', 'wchip ' + (WARNING_CHIP[day.colour] || 'is-unknown'));
    colour.append(chip);
    row.append(colour);
    row.append(el('td', day.quiet ? 'No warning in this product' : (day.source_text || (day.hazards || []).join(', ') || 'No hazard code supplied')));
    row.append(el('td', istWindowText(day.starts_utc, day.ends_utc) || 'Window not derived'));
    table.append(row);
  });
  return table;
}
function renderWarningPanel(packet) {
  const evidence = packet.warning_evidence || [];
  if (!evidence.length) return null;
  const wrap = el('div', undefined, 'warnings');
  evidence.forEach(entry => {
    (entry.district_warnings || []).forEach(district => {
      const box = el('section', undefined, 'warning-panel');
      const head = el('div', undefined, 'warning-head');
      head.append(el('h3', 'IMD district warning · ' + (district.district || 'district not named'), 'capability-name'));
      head.append(el('span', 'Bulletin ' + istStamp(district.issued_at_utc), 'tag is-quiet'));
      box.append(head);
      box.append(warningDaysTable(district));
      box.append(el('p', 'Read from IMD district-level warning guidance. Day 1 is the bulletin date, and each following day is the next IST calendar day. IMD publishes no per-day validity field in this product, so these windows are derived from the bulletin date and IMD\u2019s own day selector. The colour is IMD\u2019s product colour for that district-day, and the hazard text is IMD\u2019s own wording.', 'field-note'));
      if ((district.days || []).some(day => day.quiet)) {
        box.append(el('p', 'A day marked "No warning in this product" means IMD published no warning hazard for that district-day in this product. It is not an all-clear, and not a statement that nothing will happen.', 'field-note'));
      }
      wrap.append(box);
    });
    (entry.stale_districts || []).forEach(stale => {
      const box = el('div', undefined, 'notice is-calm');
      box.append(el('p', 'The stored IMD district warning for ' + stale.place + ' is dated ' + istStamp(stale.issued_at_utc) + ' and every day it publishes has already passed, so it carries no current facts.'));
      wrap.append(box);
    });
    (entry.points_outside_districts || []).forEach(label => {
      const box = el('div', undefined, 'notice is-calm');
      box.append(el('p', 'The resolved point for ' + label + ' is not inside any district polygon of the IMD district warning product, so no district guidance applies there.'));
      wrap.append(box);
    });
    const cap = el('div', undefined, 'notice is-calm');
    cap.append(el('p', 'CAP relay: ' + (entry.records || []).length + ' retrieved message(s)' +
      (entry.assessment ? ', ' + entry.assessment.eligible_by_lifecycle + ' passing the time/status/reference checks' : '') +
      (entry.latest_sent ? '. Newest sent ' + istStamp(entry.latest_sent) + '.' : '.')));
    cap.append(el('p', 'CAP geographic applicability to this place, origin authentication and feed completeness are unverified, so this is a source assessment and not an alert. Warning material is reported as official product state, not as an instruction.', 'field-note'));
    wrap.append(cap);
  });
  return wrap;
}

/* ---------- parts ---------- */
function renderLead(packet, fact) {
  const lead = el('div', undefined, 'lead');
  const kind = fact ? kindOf(fact) : null;
  lead.append(el('p', (fact && (fact.label || PARAMETER_NAMES[fact.parameter])) || 'Answer', 'lead-parameter'));
  const line = el('p', undefined, 'lead-value');
  if (kind) line.append(el('span', kind, 'tag' + (kind === EVIDENCE_KINDS.observation ? ' is-quiet' : '')));
  if (fact) {
    line.append(el('span', fact.value, 'lead-number'));
    if (fact.unit) line.append(el('span', fact.unit, 'lead-unit'));
  }
  lead.append(line);
  const where = el('p', undefined, 'lead-where');
  const place = placeOf(packet, fact);
  if (place) where.append(document.createTextNode(place));
  const when = fact ? hourLabel(fact) : null;
  if (when) where.append(document.createTextNode((place ? ' \u00b7 ' : '') + when));
  if (where.childNodes.length) lead.append(where);
  return lead;
}
function renderFacts(packet, facts) {
  const grid = el('div', undefined, 'facts');
  facts.forEach(fact => {
    const card = el('div', undefined, 'fact');
    const kind = kindOf(fact);
    if (kind) card.append(el('p', kind + (fact.parameter ? ' \u00b7 ' + (PARAMETER_NAMES[fact.parameter] || fact.parameter) : ''), 'fact-kind'));
    const value = el('p', undefined, 'fact-value');
    value.append(el('span', fact.value));
    if (fact.unit) value.append(el('span', ' ' + fact.unit, 'fact-unit'));
    card.append(value, el('p', fact.label || 'Value', 'fact-label'));
    const when = fact.observed_at ? 'Observed ' + istStamp(fact.observed_at) : hourLabel(fact);
    if (when) card.append(el('p', when, 'fact-when'));
    grid.append(card);
  });
  return grid;
}
const REGISTERS = ['brief', 'conversational', 'full'];
function applyRegister(host, name) {
  // How much of each card is shown. It changes what is displayed and never what a source said:
  // brief hides the evidence apparatus, full opens every disclosure, and every value, unit, date,
  // source identifier, status and caveat stays in the card at every register. The reading order
  // inside a card is the renderer's and does not change with the register.
  if (!host || REGISTERS.indexOf(name) < 0) return null;
  host.setAttribute('data-register', name);
  const boxes = (host.querySelectorAll ? host.querySelectorAll('details') : null) || [];
  Array.prototype.slice.call(boxes).forEach(box => {
    if (!box.dataset) return;
    if (name === 'full') {
      if (box.dataset.registerOpen === undefined) box.dataset.registerOpen = box.open ? '1' : '0';
      box.open = true;
    } else if (box.dataset.registerOpen !== undefined) {
      box.open = box.dataset.registerOpen === '1';
      delete box.dataset.registerOpen;
    }
  });
  return name;
}
function disclosure(summary, build, open) {
  const box = el('details', undefined, 'disclosure');
  if (open) box.open = true;
  box.append(el('summary', summary));
  const body = el('div', undefined, 'disclosure-body');
  build(body);
  box.append(body);
  return box;
}
function renderTasks(packet) {
  const results = packet.task_results || [];
  if (!results.length) return null;
  const answered = results.filter(task => task.status === 'answered').length;
  const incomplete = (packet.task_coverage && packet.task_coverage.incomplete_ids) || [];
  const counts = el('p', undefined, 'coverage');
  counts.append(el('span', 'Asked: ' + results.length));
  counts.append(el('span', 'Answered: ' + answered));
  counts.append(el('span', 'Incomplete: ' + incomplete.length + (incomplete.length ? ' (' + incomplete.join(', ') + ')' : '')));
  counts.append(el('span', 'The engine counts a task answered only when it returned evidence; a clarification or abstention is not counted as answered.'));
  const wrap = el('div');
  wrap.append(counts);
  /* The position the answer was read under travels with the answer, so the framing is
     never mistaken for the finding. */
  if (packet.persona) {
    const read = el('p', undefined, 'coverage');
    read.append(el('span', 'Read as: ' + packet.persona.label));
    read.append(el('span', packet.persona.note));
    wrap.append(read);
  }
  const list = el('div', undefined, 'tasks');
  results.forEach(task => {
    const row = el('div', 'task', 'task' + ' ' + (task.status === 'answered' ? 'is-answered' : 'is-incomplete'));
    const request = task.request || {};
    row.append(el('p', request.request_quote || task.id, 'task-quote'));
    const meta = el('p', undefined, 'task-meta');
    [task.id, request.kind, request.operation, (request.parameters || []).join('/'), task.status].filter(Boolean).forEach(part => meta.append(el('span', part)));
    row.append(meta);
    list.append(row);
  });
  wrap.append(list);
  return wrap;
}
function renderChoices(packet, handlers) {
  if (!packet.choices || !packet.choices.length) return null;
  const wrap = el('div');
  const list = el('div', undefined, 'choices');
  packet.choices.forEach(choice => {
    const button = el('button', undefined, 'choice');
    button.type = 'button';
    button.append(el('span', choice.label, 'choice-label'));
    const meta = [choice.source_id, choice.match_type,
      choice.coordinates ? choice.coordinates.latitude + ', ' + choice.coordinates.longitude : null,
      choice.admin1, choice.admin2].filter(Boolean).join(' \u00b7 ');
    button.append(el('span', meta, 'choice-meta'));
    button.addEventListener('click', () => handlers.onChoose(choice));
    list.append(button);
  });
  wrap.append(list);
  const tools = el('div', undefined, 'choice-tools');
  const retype = el('button', 'Type a different place', 'ghost');
  retype.type = 'button';
  retype.addEventListener('click', () => handlers.onRetype());
  tools.append(retype);
  wrap.append(tools);
  return wrap;
}
const TURN_CHANGE_LABELS = { places:'place', time:'time', parameters:'measure', operation:'operation',
                             language:'language', crop:'crop', growth_stage:'growth stage', topic:'topic', detail:'detail' };
function renderCarried(packet) {
  // What a continuation inherited and what the person changed, taken from the plan the engine
  // itself settled. It claims nothing about the new values: the facts carry those. A fresh
  // question, and a packet without a settled context action, get no line at all.
  const plan = packet && packet.plan;
  if (!plan || !plan.context_action || plan.context_action === 'new') return null;
  const action = { follow_up:'Continuing from your last message', correction:'Correcting the previous message',
                   clarification_answer:'Answering the question you were asked',
                   explain_previous:'Explaining the previous answer' }[plan.context_action];
  if (!action) return null;
  const changed = (plan.changed_fields || []).map(field => TURN_CHANGE_LABELS[field] || field);
  const line = el('p', undefined, 'carried-line');
  line.append(el('span', changed.length ? action + ' · changed: ' + changed.join(', ') + '.' : action + '.', 'carried-text'));
  line.append(el('span', 'Context the engine kept. Not new evidence.', 'carried-note'));
  return line;
}
/* Quick replies answer the one question a plan still needs. Each sends its reply as the
   person's next message, so a typed answer and a tapped one take the same path. */
function renderQuickReplies(packet, handlers) {
  const replies = packet.quick_replies || [];
  if (!replies.length) return null;
  const wrap = el('div', undefined, 'quick-replies');
  wrap.setAttribute('role', 'group');
  wrap.setAttribute('aria-label', 'Quick replies');
  replies.forEach(reply => {
    const button = el('button', reply.label, 'quick-reply');
    button.type = 'button';
    button.addEventListener('click', () => (handlers.onQuickReply || function () {})(reply.reply));
    wrap.append(button);
  });
  return wrap;
}
const PLAN_CARD_ACTIONS = ['saved', 'changed', 'resumed'];
const INFERRED_LABELS = { activity: 'Activity', hazards: 'Warnings watched', place: 'Place', time: 'Time', when: 'Day' };
function renderPlanCard(packet, handlers) {
  const watch = packet.plan_watch;
  if (!watch || !watch.plan || PLAN_CARD_ACTIONS.indexOf(watch.action) < 0) return null;
  const plan = watch.plan;
  const box = el('section', undefined, 'plan-card');
  box.setAttribute('aria-label', 'Saved plan');
  box.append(el('h3', plan.title, 'plan-title'));
  const meta = el('p', undefined, 'plan-meta');
  [plan.not_connected ? 'Cannot be checked: not connected' : 'Watching ' + plan.hazards,
   plan.district ? 'IMD district ' + plan.district : null,
   plan.state_words].filter(Boolean).forEach(part => meta.append(el('span', part)));
  box.append(meta);
  const inferred = plan.inferred || {};
  if (Object.keys(inferred).length) {
    box.append(disclosure('What I set automatically', into => {
      const list = el('ul', undefined, 'notes');
      Object.keys(inferred).forEach(key => list.append(el('li', (INFERRED_LABELS[key] || key) + ': ' + inferred[key])));
      into.append(list);
    }));
  }
  const tools = el('div', undefined, 'plan-tools');
  const change = el('button', 'Change', 'ghost');
  change.type = 'button';
  change.addEventListener('click', () => (handlers.onPlanChange || function () {})(plan));
  const undo = el('button', watch.action === 'saved' ? 'Undo' : 'Delete plan', 'ghost');
  undo.type = 'button';
  undo.addEventListener('click', () => (handlers.onPlanUndo || function () {})(plan, box));
  tools.append(change);
  tools.append(undo);
  box.append(tools);
  return box;
}
function renderAirportReports(packet) {
  const reports = packet.airport_reports || [];
  if (!reports.length) return null;
  const wrap = el('div');
  reports.forEach(report => {
    const box = el('section', undefined, 'capability');
    const head = el('div', undefined, 'capability-head');
    head.append(el('h3', report.station + ' \u00b7 ' + (report.kind === 'taf' ? 'Forecast (TAF)' : 'Observed report (METAR)'), 'capability-name'));
    head.append(el('span', report.observed_at ? istStamp(report.observed_at) : (report.valid_start ? istStamp(report.valid_start) : 'Time not supplied'), 'tag is-quiet'));
    box.append(head);
    if (report.raw_report) box.append(el('pre', report.raw_report, 'raw-report'));
    const validity = report.valid_start || report.valid_end
      ? 'Valid ' + (report.valid_start ? istStamp(report.valid_start) : 'not stated') + ' to ' + (report.valid_end ? istStamp(report.valid_end) : 'not stated')
      : 'No validity interval was stated in this report.';
    box.append(el('p', validity + ' A report describes its station and its stated validity, not conditions across a whole city, and not a flight status or a clearance.', 'field-note'));
    wrap.append(box);
  });
  return wrap;
}
function renderProductComparison(packet) {
  const items = packet.product_comparison || [];
  if (!items.length) return null;
  // The comparison is part of the answer, not an appendix: it is rendered in the open, with
  // the products, the reading and the refusal to rank them all visible without a click.
  const wrap = el('section', undefined, 'block');
  wrap.append(el('h2', 'Products compared (' + items.length + ')', 'block-title'));
  items.forEach(item => {
    const row = el('div', undefined, 'product-comparison');
    row.append(el('p', (item.place || 'this turn') + ' \u00b7 ' + ((item.window || {}).label || 'window not stated') +
      ' \u00b7 ' + item.reading.replace(/_/g, ' '), 'field-label'));
    (item.products || []).forEach(product => {
      const line = el('p', undefined, 'passage-text');
      line.append(el('span', (product.source_id || 'source not stated') + ' \u00b7 ' + product.product + ' \u00b7 ', 'data'));
      line.append(el('span', product.statement || ''));
      row.append(line);
    });
    if (item.why) row.append(el('p', 'Reading: ' + item.why, 'field-note'));
    if (item.note) row.append(el('p', item.note, 'field-note'));
    wrap.append(row);
  });
  return wrap;
}
function renderEditionDifferences(packet) {
  const items = packet.edition_differences || [];
  if (!items.length) return null;
  const wrap = el('div');
  const box = disclosure('Editions compared (' + items.length + ')', body => {
    items.forEach(item => {
      const row = el('div', undefined, 'edition-difference');
      row.append(el('p', item.section + ' \u00b7 ' + (item.kind === 'section_absent_from_newer'
        ? 'printed in the earlier edition, not in the newer one' : 'materially different text'), 'field-label'));
      [['nearer', 'Newer edition'], ['earlier', 'Earlier edition']].forEach(pair => {
        const side = item[pair[0]] || {};
        const line = el('p', undefined, 'passage-text');
        line.append(el('span', (side.issue_date || 'issue date not stated') +
          (side.page ? ' \u00b7 page ' + side.page : '') + ' \u00b7 ', 'data'));
        line.append(el('span', side.excerpt || 'This edition does not print that section.'));
        row.append(line);
      });
      row.append(el('p', item.note || 'Both editions are named; neither is ranked.', 'field-note'));
      body.append(row);
    });
  });
  wrap.append(box);
  return wrap;
}
function renderPassages(packet) {
  const passages = packet.passages || [];
  if (!passages.length) return null;
  const index = citationIndex(packet);
  const wrap = el('div');
  const whole = packet.whole_document;
  if (whole) {
    wrap.append(el('p', 'Whole edition: ' + whole.passages_served + ' of ' + whole.passages_indexed +
      ' indexed passages, one per printed section in printed order (' + whole.sections_indexed +
      ' sections indexed). A bounded reading of the edition, not its full text; the saved document opens from each passage.',
      'field-note'));
  }
  passages.forEach(passage => {
    const context = passage.evidence_kind === 'published_bulletin_context';
    const label = context ? 'Bulletin context: ' + passage.section : (passage.crop || 'Passage') + ' \u00b7 ' + (passage.stage || 'Stage not stated');
    const head = [label, passage.district, passage.page ? 'Page ' + passage.page : null].filter(Boolean).join(' \u00b7 ');
    const box = disclosure(head, body => {
      const meta = [];
      if (passage.issue_date) meta.push('Published ' + passage.issue_date);
      if (passage.forecast_start || passage.forecast_end) meta.push('Context window ' + (passage.forecast_start || 'not stated') + ' to ' + (passage.forecast_end || 'not stated'));
      if (meta.length) body.append(el('p', meta.join(' \u00b7 '), 'field-note'));
      body.append(el('p', passage.text, 'passage-text'));
      if (context) body.append(el('p', 'Source context only; current warning and individual field applicability remain unverified.', 'field-note'));
      const source = (passage.citation_ids || []).map(id => index.get(id)).find(Boolean);
      if (source) {
        const local = source.local_document_path;
        const archived = typeof local === 'string' && /^\/api\/documents\/[a-f0-9]{64}$/.test(local);
        let url = null;
        try { const candidate = new URL(source.url); if (candidate.protocol === 'https:') url = candidate; } catch (error) { url = null; }
        if (archived || url) {
          const links = el('p');
          if (archived) {
            const open = el('a', 'Open the saved source PDF');
            open.href = local + '#page=' + passage.page; open.target = '_blank'; open.rel = 'noopener noreferrer';
            links.append(open);
            const download = el('a', 'Download saved PDF');
            download.href = local; download.download = 'bulletin-' + local.split('/').pop() + '.pdf';
            links.append(el('span', ' \u00b7 '), download);
            // The viewer is collapsed by default and loads only when asked, so opening
            // the evidence drawer does not fetch a large PDF nobody requested. The
            // frame stays same-origin; the download link is the fallback when the
            // browser has no built-in PDF viewer.
            const viewer = el('div');
            const toggle = el('button', 'View saved PDF here', 'ghost');
            toggle.type = 'button'; toggle.setAttribute('aria-expanded', 'false');
            const frameHost = el('div'); frameHost.hidden = true;
            toggle.addEventListener('click', () => {
              if (!frameHost.hidden) {
                frameHost.hidden = true; toggle.setAttribute('aria-expanded', 'false'); toggle.textContent = 'View saved PDF here';
                return;
              }
              if (!frameHost.children.length) {
                const frame = el('iframe');
                frame.src = local + '#page=' + passage.page;
                frame.title = 'Saved source PDF, page ' + passage.page;
                frame.className = 'pdf-frame';
                frame.setAttribute('loading', 'lazy');
                frameHost.append(frame);
                frameHost.append(el('p', 'Rendered by the browser PDF viewer from this workspace only. If it stays blank, use the download link.', 'field-note'));
              }
              frameHost.hidden = false; toggle.setAttribute('aria-expanded', 'true'); toggle.textContent = 'Hide saved PDF';
            });
            links.append(el('span', ' \u00b7 '), toggle);
            viewer.append(frameHost);
            body.append(viewer);
          } else {
            url.hash = 'page=' + passage.page;
            const open = el('a', 'Open the original bulletin page');
            open.href = url.href; open.target = '_blank'; open.rel = 'noopener noreferrer';
            links.append(open);
          }
          body.append(links);
        }
      }
    });
    wrap.append(box);
  });
  const differences = renderEditionDifferences(packet);
  if (differences) wrap.append(differences);
  return wrap;
}
function calculationKind(calculation) {
  if (calculation.kind === 'source_comparison') return 'Difference between sources';
  if (calculation.operation === 'linear_trend') return 'Descriptive trend';
  if (calculation.method && /sum/i.test(calculation.method)) return 'Deterministic total';
  return calculation.operation || calculation.kind || 'Computed value';
}
function renderCalculations(packet) {
  const calculations = packet.calculations || [];
  if (!calculations.length) return null;
  const wrap = el('div', undefined, 'facts');
  calculations.forEach(calculation => {
    const box = el('div', undefined, 'calc' + (calculation.kind === 'source_comparison' ? ' is-comparison' : ''));
    box.append(el('span', calculation.value + (calculation.unit ? ' ' + calculation.unit : ''), 'calc-value'));
    const detail = el('span', undefined, 'calc-label');
    detail.append(el('span', calculationKind(calculation) + ' \u00b7 ' + calculation.label));
    detail.append(el('span', ' ' + (calculation.input_ids || []).length + ' input value(s)' +
      ((calculation.source_ids || []).length ? ' \u00b7 from ' + calculation.source_ids.join(', ') : '') +
      (calculation.method ? ' \u00b7 ' + calculation.method : '') + '.'));
    if (calculation.kind === 'source_comparison') {
      detail.append(el('span', ' A difference between two sources is not a skill score, an accuracy measure or a confidence value, and agreement between them does not establish correctness.'));
    }
    box.append(detail);
    wrap.append(box);
  });
  return wrap;
}
function renderNotes(packet) {
  const notes = (packet.notes || []).filter(note => !/output language could not be rendered/i.test(note));
  if (!notes.length) return null;
  return disclosure('Scope, assumptions and limits (' + notes.length + ')', body => {
    const list = el('ul', undefined, 'notes');
    notes.forEach(note => list.append(el('li', note)));
    body.append(list);
  });
}
function renderSources(packet) {
  const citations = packet.citations || [];
  if (!citations.length) return null;
  const seen = new Set();
  return disclosure('Sources (' + citations.length + ')', body => {
    const list = el('div', undefined, 'sources');
    citations.forEach(citation => {
      const key = (citation.source_id || '') + '|' + (citation.url || '');
      if (seen.has(key)) return;
      seen.add(key);
      const row = el('div', undefined, 'source');
      const name = [citation.provider || citation.source_id, citation.product].filter(Boolean).join(' \u00b7 ');
      let linked = false;
      try {
        const url = new URL(citation.url);
        if (url.protocol === 'https:') {
          const link = el('a', name); link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
          row.append(link); linked = true;
        }
      } catch (error) { linked = false; }
      if (!linked) row.append(el('span', name));
      const meta = [citation.source_id, citation.retrieved_at_utc ? 'retrieved ' + istStamp(citation.retrieved_at_utc) : null,
        citation.page ? 'page ' + citation.page : null, citation.row ? 'row ' + citation.row : null,
        citation.column || null].filter(Boolean).join(' \u00b7 ');
      if (meta) row.append(el('span', meta, 'source-meta'));
      list.append(row);
    });
    body.append(list);
  });
}
function renderTrace(packet) {
  const trace = packet.trace || {};
  return disclosure('How this answer was produced', body => {
    const planning = trace.planning || {};
    /* The provider is named as the trace records it: deterministic rules, a local model, or a
       routed free model. '(local)' was hard-coded here and would have been wrong for any routed
       model once the provider layer was in. */
    const providerName = planning.provider ? String(planning.provider) : null;
    const facts = [
      ['Interpreter', planning.model ? planning.model + (providerName ? ' (' + providerName + ')' : '') : providerName],
      ['Planner duration', planning.latency_ms ? Math.round(planning.latency_ms / 100) / 10 + ' s' : (planning.duration_seconds ? Math.round(planning.duration_seconds * 10) / 10 + ' s' : null)],
      ['Model calls', planning.model_calls === undefined ? null : String(planning.model_calls)],
      ['Failover', (planning.failover || []).length ? (planning.failover || []).map(item => typeof item === 'string' ? item : JSON.stringify(item)).join('; ') : null],
      ['Structured output', planning.input_tokens ? planning.input_tokens + ' in / ' + planning.output_tokens + ' out tokens' : null],
      ['Answer renderer', trace.generation ? (trace.generation.provider || 'deterministic') : null],
      ['Validation', trace.generation && trace.generation.validation],
      ['Retrieval', trace.duration_seconds ? Math.round(trace.duration_seconds * 10) / 10 + ' s total' : null],
      ['Language recorded by the planner', packet.plan && packet.plan.language ? (LANGUAGE_NAMES[packet.plan.language] || packet.plan.language) : null]
    ].filter(pair => pair[1]);
    const rows = el('div', undefined, 'receipt-rows');
    facts.forEach(pair => receiptRow(rows, pair[0], pair[1]));
    body.append(rows);
    const tools = (trace.tools || []).map(tool => tool.name + (tool.status ? ' (' + tool.status + ')' : '') + (tool.location ? ' \u00b7 ' + tool.location : '')).filter(Boolean);
    if (tools.length) {
      const list = el('ul', undefined, 'notes');
      tools.forEach(name => list.append(el('li', name)));
      body.append(el('p', 'Tools used', 'field-label'), list);
    }
    if (packet.retrieval_plan && packet.retrieval_plan.length) {
      const list = el('ul', undefined, 'notes');
      packet.retrieval_plan.forEach(plan => {
        (plan.candidates || []).forEach(candidate => {
          list.append(el('li', [plan.task_id, candidate.tool, candidate.selected ? 'selected' : 'not selected', candidate.available ? 'available' : 'unavailable', candidate.reason].filter(Boolean).join(' \u00b7 ')));
        });
      });
      if (list.childNodes.length) body.append(el('p', 'Candidates considered', 'field-label'), list);
    }
  });
}
function renderRefreshNote(packet, handlers) {
  const records = refreshRecords(packet);
  const box = el('div');
  records.forEach(record => {
    const refresh = record.refresh;
    const notice = el('div', undefined, 'notice' + ' ' + (refresh.state === 'succeeded' ? 'is-good' : 'is-calm'));
    notice.append(el('p', refresh.message || ('Collection state: ' + refresh.state)));
    const detail = [refresh.state, refresh.claims_this_action !== undefined ? refresh.claims_this_action + ' provider claim(s) this action' : null,
      refresh.job_provider_attempts !== undefined ? refresh.job_provider_attempts + ' claim(s) for the job' : null,
      refresh.retry_due_utc_epoch ? 'next retry ' + istStamp(new Date(refresh.retry_due_utc_epoch * 1000).toISOString()) : null]
      .filter(Boolean).join(' \u00b7 ');
    if (detail) notice.append(el('p', detail, 'field-note'));
    box.append(notice);
  });
  if (records.length) {
    const note = el('p', 'A collection is bounded by the source policy: retry timing, provider budgets and cooldowns all stay in force, and no background worker keeps running after this turn.', 'field-note');
    box.append(note);
  }
  return box;
}
function actionButton(label, handler) {
  const button = el('button', label, 'ghost');
  button.type = 'button';
  button.addEventListener('click', () => handler(button));
  return button;
}

/* The point an answer was resolved to, if it has one: the drawers need coordinates, never a guess. */
function resolvedPlace(packet) {
  const points = packet.resolved_points || {};
  const names = Object.keys(points);
  const entry = names.length ? (points[names[0]] || {}) : null;
  const coordinates = (entry && entry.coordinates) || {};
  if (coordinates.latitude !== undefined && coordinates.longitude !== undefined) {
    return { label: entry.label || names[0], latitude: coordinates.latitude, longitude: coordinates.longitude };
  }
  /* A warning or corpus turn resolves its district inside the tool and carries no resolved
     point, so the artefact actions fall back to the place this page is working with. The
     drawer names the place it used, so the reader can see which one it was. */
  const working = (window.WG && window.WG.state && window.WG.state.place) || {};
  if (working.latitude === undefined || working.longitude === undefined) return null;
  return { label: working.label || 'the working place', latitude: working.latitude, longitude: working.longitude };
}
/* The published advisory this turn read, as the route that composes a brief wants it. */
function advisoryBriefParams(packet) {
  const tasks = ((packet.plan || {}).tasks) || [];
  const task = tasks.filter(item => item.kind === 'agriculture' && item.document_request)[0]
    || ((packet.task_results || []).filter(item => (item.request || {}).document_request)[0] || {}).request;
  if (!task || !task.document_request) return null;
  const request = task.document_request;
  const passage = (packet.passages || [])[0] || {};
  const evidence = (packet.document_evidence || [])[0] || {};
  const region = passage.district || evidence.district || '';
  if (!region) return null;
  return { region: region, state: passage.state || evidence.state || '', crop: request.crop || '',
           stage: request.growth_stage || '', topic: request.topic || 'general',
           mode: request.mode || 'source_lookup', day: 1 };
}


/* ---------- what was retrieved, and what is still needed ---------- */
/* retrieval_coverage, pending_slots, edition_comparison and document_evidence are records the
   tools produce; until this renderer existed they were only visible in the raw packet. Nothing
   here computes anything: every number is the tool's own, and an absence is shown as an absence. */
const CURRENCY_WORDS = {
  printed_issue_matches_retrieval_date: 'the printed issue date is the retrieval date',
  printed_issue_differs_from_retrieval_date: 'the printed issue is older than the retrieval date',
  printed_issue_not_stated: 'the document states no printed issue date, so its currency is unknown',
  printed_issue_in_the_future: 'the printed issue date is later than the retrieval date'
};
/* views.js builds its own small tables; the shared one lives on WG. The retrieval account
   used a bare `table(...)` call and threw 'table is not defined' in the page, which stopped the
   whole turn from rendering - found in the browser pass on 15 September 2026. */
function accountTable(head, rows) {
  const maker = (window.WG && window.WG.table) || null;
  if (maker) return maker(head, rows);
  const node = el('table', undefined, 'account-table');
  const headRow = el('tr');
  head.forEach(cell => headRow.append(el('th', cell)));
  node.append(headRow);
  (rows || []).forEach(row => { const tr = el('tr'); row.forEach(cell => tr.append(el('td', cell))); node.append(tr); });
  return node;
}

function renderRetrievalAccount(packet) {
  const slots = packet.pending_slots || [];
  const coverage = packet.retrieval_coverage || [];
  const comparison = packet.edition_comparison || null;
  const editions = packet.document_evidence || [];
  if (!slots.length && !coverage.length && !comparison && !editions.length) return null;
  const box = el('section', undefined, 'receipt');
  box.append(el('p', 'What was retrieved, and what is missing', 'receipt-title'));
  if (slots.length) {
    box.append(el('p', 'Still needed before this can be answered', 'field-label'));
    const list = el('ul', undefined, 'notes');
    slots.forEach(slot => list.append(el('li', String(slot.field || 'a field') + ': ' + String(slot.reason || 'not stated')
      + (slot.task_id ? ' (task ' + String(slot.task_id) + ')' : ''))));
    box.append(list);
  }
  if (coverage.length) {
    coverage.forEach(entry => {
      const filters = entry.filters || {};
      const rows = [
        ['Search mode', String(entry.mode || 'not stated'), 'the retriever this turn used'],
        ['Candidates → returned', String(entry.candidates === undefined ? 'not stated' : entry.candidates) + ' → ' + String(entry.returned === undefined ? 'not stated' : entry.returned),
          entry.lexical_overlap_required ? 'a passage must share words with the question to be returned' : 'no lexical overlap required'],
        ['Product filters', [filters.family, filters.scope, filters.region].filter(Boolean).join(' · ') || 'none', 'family, scope and region as stored'],
        ['Whole document asked for', entry.whole_document ? 'yes' : 'no', 'a whole-edition read returns the document as a record'],
        ['Editions indexed for this product', String(entry.editions_indexed_for_this_product === undefined ? 'not stated' : entry.editions_indexed_for_this_product),
          'a single indexed edition cannot be compared with another']
      ];
      if (entry.query_translation) {
        const translation = entry.query_translation;
        rows.push(['Question translated for retrieval', String(translation.text || 'not stated'),
          'read as ' + String(translation.source_language || 'an Indian script') + ' from its script, through ' +
          String(translation.service || 'the language service') + ' (' + String(translation.model || 'model not stated') + ')' +
          (translation.used_for_retrieval ? '; used to find passages only, never to state anything' : '; not used for this retrieval')]);
      }
      if (entry.topic_tokens) {
        rows.push(['Words that name the topic', entry.topic_tokens.length ? entry.topic_tokens.join(', ') : 'none beyond the product and the place',
          entry.topic_matched === false
            ? 'no returned passage contains them: these passages share the question\u2019s other words only'
            : 'at least one returned passage contains them']);
      }
      const BASES = {
        semantic_only_indic_script_disclosed: 'no exact word from the question appears in these passages: top semantic matches, wording support unverified',
        lexical_overlap_without_the_topic_word: 'the topic word is absent from this product and region: not an answer to the question',
        translated_query_lexical_overlap: 'the question was translated to English to find these passages: they are the source\u2019s own words, matched on that translation',
        translated_query_without_the_topic_word: 'the translation found no passage containing the topic word: these passages share the question\u2019s other words only, and the reading is not an answer to it'
      };
      if (BASES[entry.match_basis]) rows.push(['Wording support', String(entry.match_basis), BASES[entry.match_basis]]);
      box.append(accountTable(['Field', 'Value', 'Provenance'], rows));
    });
  }
  if (comparison) {
    box.append(el('p', 'Editions in the index', 'field-label'));
    box.append(accountTable(['Field', 'Value', 'Provenance'], [
      ['Editions indexed', String(comparison.editions_indexed === undefined ? 'not stated' : comparison.editions_indexed), String(comparison.state || 'state not stated')],
      ['Newest printed issue', String(comparison.newest_issue || 'not stated'), 'read from the document, never from the retrieval instant'],
      ['Previous printed issue', String(comparison.previous_issue || 'none indexed'), 'differences are labelled and never ranked']
    ]));
  }
  if (editions.length) {
    box.append(el('p', 'Editions read', 'field-label'));
    box.append(accountTable(['Edition', 'Region', 'Printed issue', 'Currency and age'], editions.map(item => [
      String(item.family_label || item.family || 'document') + ' (' + String(item.source_id || 'source not stated') + ')',
      [item.region, item.state].filter(Boolean).join(', ') || String(item.scope || 'not stated'),
      String(item.issue_date || 'not stated') + (item.issue_date && item.issue_date_basis ? ' (' + String(item.issue_date_basis) + ')' : ''),
      (CURRENCY_WORDS[item.currency] || String(item.currency || 'currency not stated')) +
        (item.age_days === undefined || item.age_days === null ? '' : ', ' + String(item.age_days) + ' day(s) old at retrieval')
    ])));
  }
  return box;
}

function renderActions(packet, handlers) {
  const actions = el('div', undefined, 'actions');
  const refreshable = windowFacts(packet).length && (packet.resolved_points && Object.keys(packet.resolved_points).length);
  if (refreshable && handlers.onRefresh) actions.append(actionButton('Collect fresh evidence', () => handlers.onRefresh(packet)));
  if (handlers.onCopy) actions.append(actionButton('Copy the answer', button => handlers.onCopy(packet, button)));
  if (handlers.onPrint) actions.append(actionButton('Print this answer', () => handlers.onPrint(packet)));
  if (handlers.onExport) actions.append(actionButton('Save this turn as Markdown', () => handlers.onExport(packet)));
  if (handlers.onDownload) actions.append(actionButton('Download this answer as JSON', () => handlers.onDownload(packet)));
  /* The artefacts this reader can ask for next, where the answer makes them reachable. */
  const WGx = window.WG || {};
  const drawers = WGx.briefDrawers;
  if (drawers) {
    const place = resolvedPlace(packet);
    if (place) {
      actions.append(actionButton('Right now here', () => drawers.now(WGx, place)));
      const warningTurn = ((packet.plan || {}).intent === 'warning') || warningFacts(packet).length > 0;
      if (warningTurn) actions.append(actionButton('Write the alert brief', () => drawers.alert(WGx, place, 1)));
      actions.append(actionButton('Write a briefing', () => drawers.briefing(WGx, place)));
    }
    const advisory = advisoryBriefParams(packet);
    if (advisory) actions.append(actionButton('Write the advisory brief', () => drawers.advisory(WGx, advisory)));
  }
  actions.append(actionButton('Inspect the raw packet', () => {
    const pretty = JSON.stringify(packet, null, 1);
    const bounded = pretty.length > 60000 ? pretty.slice(0, 60000) + '\n… truncated for display; the download action holds the full packet.' : pretty;
    const WG = window.WG;
    if (!WG || !WG.openDrawer) return;
    WG.openDrawer('Raw packet', body => {
      const pre = el('pre', bounded);
      body.append(pre);
      body.append(el('p', 'This is the exact packet the page rendered, not a summary. Question text and evidence stay on this machine.', 'field-note'));
    });
  }));
  return actions;
}
function renderExpiry(packet) {
  if (!packet.expires_at_utc) return null;
  const expiry = Date.parse(packet.expires_at_utc);
  const note = el('p', 'Evidence serving lifetime ends ' + istStamp(packet.expires_at_utc) + '. Ask again before relying on this answer.', 'field-note');
  note.dataset.expiresAt = packet.expires_at_utc;
  if (!Number.isNaN(expiry) && expiry - Date.now() < 2147483647) {
    setTimeout(() => {
      const tag = note.closest('.turn');
      const status = tag && tag.querySelector('.status-line');
      if (status) status.insertBefore(el('span', 'Receipt expired', 'tag is-held'), status.firstChild);
      note.textContent = 'This receipt has expired. Ask again to retrieve current evidence; the values above are what was retrieved at the time stamped on this card.';
    }, Math.max(0, expiry - Date.now()));
  }
  return note;
}

/* ---------- the turn ---------- */
function turnTitle(packet) {
  if (packet.status === 'conversation') return 'Conversation';
  if (packet.status === 'needs_selection') return 'Which place do you mean?';
  if (packet.status === 'needs_clarification') return 'One more detail needed';
  if (packet.status === 'unavailable') return 'No verified evidence for this';
  if (packet.status === 'outside_validity') return 'That window is not available';
  if (packet.status === 'explanation') return 'General explanation';
  if ((packet.airport_reports || []).length) return 'Airport report';
  if ((packet.charts || []).length) return 'Retrieved series';
  return 'Answer';
}
function renderTurn(packet, handlers) {
  handlers = handlers || {};
  const card = el('article', undefined, 'turn');
  const head = el('div', undefined, 'turn-head');
  head.append(el('h2', turnTitle(packet)));
  const status = el('div', undefined, 'status-line');
  const label = STATUS_LABELS[packet.status] || packet.status;
  status.append(el('span', label, 'tag' + (HELD_STATUS.indexOf(packet.status) >= 0 ? ' is-held' : '')));
  if (packet.plan && packet.plan.language && packet.plan.language !== 'en') {
    status.append(el('span', 'Requested output: ' + (LANGUAGE_NAMES[packet.plan.language] || packet.plan.language), 'tag is-quiet'));
  }
  /* A conversational turn read no source. The tag says so beside the answer, not only in a
     disclosure, so the reply can never be mistaken for retrieved evidence. */
  if (packet.answer_basis === 'conversation') status.append(el('span', 'No source read', 'tag is-quiet'));
  status.append(el('span', packet.answered_at_utc ? istStamp(packet.answered_at_utc) : 'Time not recorded', 'tag is-quiet'));
  head.append(status);
  card.append(head);

  const body = el('div', undefined, 'turn-body');
  const facts = sequenceFacts(packet);
  // Only a value that is not already drawn may headline the card, so a series answer
  // cannot present one arbitrary member of the series as its answer.
  const primary = firstOf(facts);
  const downgrade = languageDowngradeNote(packet);
  if (downgrade) {
    const notice = el('div', undefined, 'notice');
    notice.append(el('p', 'The answer below is not in the language you asked for.'));
    notice.append(el('p', downgrade, 'field-note'));
    body.append(notice);
  }
  const carried = renderCarried(packet);
  if (carried) body.append(carried);
  const calculations = renderCalculations(packet);
  if (packet.status === 'needs_selection' || packet.status === 'needs_clarification') {
    body.append(el('p', packet.answer, 'answer-copy'));
  } else {
    if (primary) {
      body.append(renderLead(packet, primary));
      const ruler = renderRuler(packet);
      if (ruler) body.append(ruler);
    }
    if (calculations) body.append(calculations);
    body.append(el('p', packet.answer, 'answer-copy'));
  }
  const choices = renderChoices(packet, {
    onChoose: handlers.onChoose || function () {},
    onRetype: handlers.onRetype || function () {}
  });
  if (choices) body.append(choices);
  const quickReplies = renderQuickReplies(packet, handlers);
  if (quickReplies) body.append(quickReplies);
  const planCard = renderPlanCard(packet, handlers);
  if (planCard) body.append(planCard);
  (packet.charts || []).forEach(chart => body.append(historicalChart(chart)));
  const airport = renderAirportReports(packet);
  if (airport) body.append(airport);
  const passages = renderPassages(packet);
  if (passages) body.append(passages);
  const comparison = renderProductComparison(packet);
  if (comparison) body.append(comparison);
  const rest = facts.filter(fact => fact !== primary);
  if (rest.length) body.append(renderFacts(packet, rest));
  if (packet.follow_up) body.append(el('p', packet.follow_up, 'notice is-calm'));
  const warnings = renderWarningPanel(packet);
  if (warnings) body.append(warnings);
  const warning = warningFacts(packet);
  const receipt = renderReceipt(packet, primary) || (warning.length ? renderReceipt(packet, warning[0]) : null) || renderSeriesReceipt(packet);
  if (receipt) body.append(receipt);
  const tasks = renderTasks(packet);
  if (tasks) body.append(disclosure('Requested tasks (' + (packet.task_results || []).length + ')', into => into.append(tasks)));
  const refreshNote = renderRefreshNote(packet, handlers);
  if (refreshNote.childNodes.length) body.append(refreshNote);
  const notes = renderNotes(packet);
  if (notes) body.append(notes);
  const sources = renderSources(packet);
  if (sources) body.append(sources);
  const retrievalAccount = renderRetrievalAccount(packet);
  if (retrievalAccount) body.append(retrievalAccount);
  body.append(renderTrace(packet));
  const actions = renderActions(packet, handlers);
  if (actions.childNodes.length) body.append(actions);
  const expiry = renderExpiry(packet);
  if (expiry) body.append(expiry);
  if (rest.length || packet.charts) {
    body.append(disclosure('Machine record (raw response)', into => {
      into.append(el('p', 'The complete response this card was rendered from, for audit.', 'field-note'));
      into.append(el('pre', JSON.stringify(packet, null, 2), 'raw-json'));
    }));
  }
  card.append(body);
  return card;
}

/* ---------- welcome and in-flight ---------- */
function renderWelcome(handlers) {
  const box = el('article', undefined, 'welcome');
  const place = (typeof WG !== 'undefined' && WG.state.place && WG.state.place.label) || 'Ahmedabad, Gujarat';
  box.append(el('h1', 'Ask about a place and a time.'));
  box.append(el('p', 'Ask in your own words and follow up in the same conversation. WeatherGPT resolves the place, retrieves the evidence, and keeps the source, the window and the retrieval time attached to every value. When a name is shared between places it asks you which one you mean.'));
  const starters = el('div', undefined, 'starters');
  /* The openings lead with what this build does best: a right-now reading, today's published
     warning, the district farm advisory, a trend from the record, and an airport report. */
  const examples = [
    ['What is it like right now in ' + place + '?', 'Ask what it is like right now'],
    ['Is any warning in force for ' + place + ' today?', 'Check today\u2019s published warnings'],
    ['What does the district agromet advisory for ' + place + ' say for cotton?', 'Read the farm advisory'],
    ['Show the annual rainfall trend for ' + place + ' district from 1981 to 2010.', 'Look at a trend'],
    ['What is the current weather at VOBL?', 'Ask for an airport report']
  ];
  /* The reading position changes which questions are offered first. It changes nothing
     about how they are answered. */
  const reading = (typeof WG !== 'undefined' && WG.personaEntry) ? WG.personaEntry() : null;
  if (reading) {
    (reading.starters || []).slice(0, 3).forEach(question => examples.unshift([question, 'Ask as ' + reading.label.toLowerCase()]));
    box.append(el('p', 'Reading as ' + reading.label + ': ' + reading.who + ' ' + reading.note, 'welcome-limit'));
  }
  examples.slice(0, reading ? 6 : 4).forEach(pair => {
    const button = el('button', pair[1], 'ghost');
    button.type = 'button';
    button.addEventListener('click', () => handlers.onExample(pair[0]));
    starters.append(button);
  });
  box.append(starters);
  box.append(el('p', 'It will not invent a warning, an observation, a water level or a forecast, and it says when evidence is missing rather than filling the gap. Radar and satellite imagery, official sea-area bulletins and flood extent are not connected. Plans and their inbox work only while this local workspace is running.', 'welcome-limit'));
  const home = el('a', 'Explore all tools in the workspace →', 'workspace-link');
  home.href = '#/workspace';
  box.append(home);
  return box;
}
function renderWorking(question, receipt) {
  const box = el('div', undefined, 'working');
  box.append(el('span', undefined, 'working-dot'));
  const body = el('div', undefined, 'working-body');
  body.append(el('p', 'Working on it', 'working-title'));
  body.append(el('p', 'Resolving the place and window, then retrieving evidence. A local model is interpreting your question, so this can take up to about a minute.', 'working-note'));
  /* The engine's own first reading of this question lands here while the turn works. It arrives
     carrying provisional:true, it repeats no value, and the answer card replaces this whole box. */
  const reading = el('p', undefined, 'working-reading');
  reading.hidden = true;
  body.append(reading);
  if (receipt && receipt.place && receipt.at) {
    body.append(el('p', 'This conversation last read ' + receipt.place + ' at ' + receipt.at + '; that receipt stands until this turn replaces it.', 'working-receipt'));
  }
  const clock = el('p', undefined, 'working-clock');
  clock.dataset.since = String(Date.now());
  body.append(clock);
  box.append(body);
  return box;
}
function renderUserTurn(text) { return el('div', text, 'turn-user'); }

/* ---------- rail ---------- */
let ledgerExpanded = false;
function ledgerItem(item, current, handlers) {
  const row = el('li', undefined, 'ledger-item' + (item.id === current ? ' is-current' : ''));
  const question = item.opening_question || 'Conversation';
  const open = el('button', undefined, 'ledger-open');
  open.type = 'button';
  open.setAttribute('aria-label', 'Open the stored conversation: ' + question);
  open.append(el('span', question, 'ledger-text'));
  const meta = el('span', undefined, 'ledger-meta');
  meta.append(el('span', item.asked + ' asked'));
  meta.append(el('span', item.updated ? istStamp(item.updated) : 'time not recorded'));
  open.append(meta);
  open.addEventListener('click', () => handlers.onOpen(item));
  row.append(open);
  const tools = el('div', undefined, 'ledger-tools');
  const remove = el('button', 'Delete', 'ghost danger');
  remove.type = 'button';
  remove.setAttribute('aria-label', 'Delete the stored conversation: ' + question);
  remove.addEventListener('click', () => handlers.onDelete(item));
  tools.append(remove);
  row.append(tools);
  return row;
}
function renderLedger(ledger, handlers) {
  const list = document.getElementById('ledger');
  const note = document.getElementById('ledger-note');
  if (!list) return;
  list.replaceChildren();
  const all = (ledger && ledger.conversations) || [];
  const search = document.getElementById('ledger-search');
  const query = search && search.value ? search.value.trim().toLowerCase() : '';
  const items = query ? all.filter(item => (item.opening_question || '').toLowerCase().indexOf(query) >= 0) : all;
  if (!all.length) {
    if (note) note.textContent = 'No stored conversations yet. The first question creates one.';
    return;
  }
  if (!items.length) {
    if (note) note.textContent = 'No stored conversation matches this search. It covers the questions held on this machine.';
    return;
  }
  // The ledger is a bounded read of the store, and the note says so rather than
  // implying that every stored conversation is searchable here.
  if (note) note.textContent = query
    ? items.length + ' of the ' + all.length + ' most recent conversations match. Older stored conversations are not loaded into this view.'
    : ledger.total + ' stored on this machine; the ' + all.length + ' most recent are listed. Open one to restore its transcript, or delete it.';
  const limit = 6;
  const shown = ledgerExpanded ? items : items.slice(0, limit);
  shown.forEach(item => list.append(ledgerItem(item, handlers.currentId(), handlers)));
  const hidden = items.length - shown.length;
  if (hidden > 0) {
    const more = el('button', 'Show ' + hidden + ' older conversation' + (hidden === 1 ? '' : 's'), 'ghost');
    more.type = 'button';
    more.addEventListener('click', () => { ledgerExpanded = true; renderLedger(ledger, handlers); });
    const row = el('li');
    row.append(more);
    list.append(row);
  } else if (ledgerExpanded && items.length > limit) {
    const fewer = el('button', 'Show fewer', 'ghost');
    fewer.type = 'button';
    fewer.addEventListener('click', () => { ledgerExpanded = false; renderLedger(ledger, handlers); });
    const row = el('li');
    row.append(fewer);
    list.append(row);
  }
}
/* The slow layers are read once at startup; the page says so instead of leaving a first ask
   to be the wait. Measured 15 September 2026: a first right-now ask fell from 146 s to 1.4 s. */
function renderWarmState(health, box) {
  const warm = (health || {}).warm;
  if (!warm) return;
  const lines = (warm.layers || []).map(layer => layer.layer + ': ' + layer.state
    + (layer.seconds === undefined ? '' : ' in ' + layer.seconds + ' s')
    + (layer.detail ? ' — ' + layer.detail : ''));
  box.append(el('p', 'Slow layers at startup: ' + String(warm.state || 'not started')
    + (lines.length ? ' — ' + lines.join('; ') : ''), 'health-val'));
}

function renderHealth(health) {
  const box = document.getElementById('health');
  if (!box) return;
  box.replaceChildren();
  if (!health) { box.append(el('p', 'Collection health is unavailable.', 'block-note')); return; }
  if (!health.available) { box.append(el('p', health.note || 'No collection history.', 'block-note')); return; }
  renderWarmState(health, box);
  (health.products || []).forEach(product => {
    const row = el('div', undefined, 'health-stream');
    row.append(el('span', product.product, 'health-key'));
    row.append(el('span', product.jobs + ' job' + (product.jobs === 1 ? '' : 's') + ' \u00b7 ' + productStates(product.states), 'health-val'));
    row.append(el('span', product.newest_commit_utc ? 'newest evidence ' + istStamp(product.newest_commit_utc) : 'no committed evidence yet', 'health-val'));
    box.append(row);
  });
  const leases = el('div', undefined, 'health-row');
  leases.append(el('span', 'Requests in flight', 'health-key'));
  leases.append(el('span', String(health.active_leases), 'health-val'));
  box.append(leases);
  if ((health.cooldowns || []).length) {
    const cooldown = el('div', undefined, 'health-row');
    cooldown.append(el('span', 'Provider cooldowns', 'health-key'));
    cooldown.append(el('span', health.cooldowns.map(item => item.provider + ' until ' + istClock(item.until_utc)).join(' \u00b7 '), 'health-val'));
    box.append(cooldown);
  }
  box.append(el('p', health.note, 'block-note'));
}
function productStates(states) {
  const keys = Object.keys(states || {});
  return keys.length ? keys.sort().map(key => key + ' ' + states[key]).join(' \u00b7 ') : 'no jobs';
}
function renderRestored(transcript, handlers) {
  const thread = document.getElementById('thread');
  if (!thread) return;
  thread.replaceChildren();
  const box = el('article', undefined, 'welcome');
  box.append(el('span', 'Restored conversation', 'eyebrow'));
  box.append(el('h2', 'Continuing from your stored transcript'));
  box.append(el('p', transcript.note || 'Earlier answers are timestamped receipts; ask again before relying on one.'));
  thread.append(box);
  (transcript.turns || []).forEach(turn => {
    thread.append(turn.role === 'user' ? renderUserTurn(turn.content) : el('div', turn.content, 'answer-copy notice is-calm'));
  });
  if (handlers && handlers.onRetype) {
    const actions = el('div', undefined, 'actions');
    const ask = el('button', 'Ask a follow-up', 'primary');
    ask.type = 'button';
    ask.addEventListener('click', handlers.onRetype);
    actions.append(ask);
    thread.append(actions);
  }
  thread.scrollTop = thread.scrollHeight;
}

/* ---------- service banner ---------- */
function renderBanner(text, calm) {
  const box = document.getElementById('banner');
  if (!box) return;
  if (!text) { box.hidden = true; box.textContent = ''; return; }
  box.textContent = text;
  box.className = 'banner' + (calm ? ' is-calm' : '');
  box.hidden = false;
}

/* ---------- portable exports ---------- */
function markdownTable(rows) {
  if (!rows.length) return '';
  const head = '| ' + rows[0].join(' | ') + ' |';
  const rule = '| ' + rows[0].map(() => '---').join(' | ') + ' |';
  const body = rows.slice(1).map(row => '| ' + row.join(' | ') + ' |');
  return [head, rule].concat(body).join(String.fromCharCode(10));
}
function answerMarkdown(packet) {
  const newline = String.fromCharCode(10);
  const lines = [];
  const cell = value => String(value === undefined || value === null ? '' : value).split('|').join('/');
  lines.push('# WeatherGPT answer');
  lines.push('');
  lines.push('- Question: ' + (packet.question || 'not recorded'));
  lines.push('- Status: ' + (STATUS_LABELS[packet.status] || packet.status));
  lines.push('- Answered: ' + (packet.answered_at_utc ? istStamp(packet.answered_at_utc) : 'time not recorded'));
  if (packet.expires_at_utc) lines.push('- Serving lifetime ends: ' + istStamp(packet.expires_at_utc));
  lines.push('');
  lines.push('## Answer');
  lines.push('');
  lines.push(String(packet.answer || '').trim());
  const facts = coverageFacts(packet);
  if (facts.length) {
    lines.push('');
    lines.push('## Retrieved values (' + facts.length + ')');
    lines.push('');
    const rows = [['Measure', 'Value', 'Unit', 'Place', 'Time', 'Source', 'Evidence id']];
    facts.slice(0, 60).forEach(fact => rows.push([
      cell(fact.label || fact.parameter),
      cell(fact.value),
      cell(fact.unit),
      cell(fact.place),
      cell(fact.observed_at ? 'observed ' + istStamp(fact.observed_at) : hourLabel(fact)),
      cell(fact.source_id),
      cell(String(fact.evidence_version || '').slice(0, 12))
    ]));
    lines.push(markdownTable(rows));
    if (facts.length > 60) {
      lines.push('');
      lines.push('_' + (facts.length - 60) + ' further retrieved values are in the JSON export._');
    }
  }
  const calculations = packet.calculations || [];
  if (calculations.length) {
    lines.push('');
    lines.push('## Computed values');
    lines.push('');
    calculations.forEach(calculation => lines.push('- ' + calculation.label + ': ' + calculation.value + ' ' +
      (calculation.unit || '') + ' (' + calculationKind(calculation) + (calculation.method ? '; ' + calculation.method : '') + ')'));
  }
  const citations = packet.citations || [];
  if (citations.length) {
    lines.push('');
    lines.push('## Sources');
    lines.push('');
    const seen = {};
    citations.forEach(citation => {
      const key = (citation.source_id || '') + (citation.url || '');
      if (seen[key]) return;
      seen[key] = true;
      const label = [citation.source_id, citation.provider, citation.product].filter(Boolean).join(' - ');
      lines.push('- ' + label + (citation.url ? ' <' + citation.url + '>' : '') +
        (citation.page ? ' (page ' + citation.page + ')' : '') +
        (citation.retrieved_at_utc ? ' retrieved ' + istStamp(citation.retrieved_at_utc) : ''));
    });
  }
  const notes = (packet.notes || []).filter(note => !/output language could not be rendered/i.test(note));
  if (notes.length) {
    lines.push('');
    lines.push('## Limits and assumptions');
    lines.push('');
    notes.forEach(note => lines.push('- ' + note));
  }
  const tasks = packet.task_results || [];
  if (tasks.length) {
    lines.push('');
    lines.push('## Requested tasks');
    lines.push('');
    tasks.forEach(task => lines.push('- ' + task.id + ' ' + ((task.request || {}).kind || '') + '/' +
      ((task.request || {}).operation || '') + ' - ' + task.status));
  }
  lines.push('');
  lines.push('_Model forecasts and published records, each with source and retrieval time. Not an official warning and not field, marine or travel clearance. Produced by a local prototype._');
  return lines.join(newline);
}
function transcriptMarkdown(transcript, ledgerItem) {
  const newline = String.fromCharCode(10);
  const lines = ['# WeatherGPT conversation', ''];
  lines.push('- Started by: ' + ((ledgerItem && ledgerItem.opening_question) || ((transcript.turns || [])[0] || {}).content || 'not recorded'));
  lines.push('- Last stored: ' + istStamp(transcript.updated));
  lines.push('- Turns: ' + (transcript.turns || []).length);
  lines.push('');
  lines.push(transcript.note || '');
  lines.push('');
  (transcript.turns || []).forEach(turn => {
    lines.push(turn.role === 'user' ? '## You' : '## WeatherGPT');
    lines.push('');
    lines.push(String(turn.content || '').trim());
    lines.push('');
  });
  lines.push('_Earlier answers are receipts for the moment they were retrieved; ask again before relying on one._');
  return lines.join(newline);
}
function stageLine(progress) {
  // The engine's own checkpoints and the queue's own counters. Facts only: no
  // percentage, no ETA, no confidence. A waiting turn says so instead.
  if (!progress || progress.state !== 'running') return null;
  const queue = progress.queue || {};
  const waiting = Number(queue.waiting || 0);
  const wrap = el('span', undefined, 'stage-readout');
  if (waiting > 0) {
    wrap.append(el('span', '⧗', 'stage-glyph'));
    wrap.append(el('span', 'Waiting for the engine · ' + waiting + (waiting === 1 ? ' question ahead' : ' questions ahead'), 'stage-text'));
    const bound = (queue.capacity === null || queue.capacity === undefined) ? 'a fixed size' : queue.capacity;
    wrap.append(el('span', 'The wait queue is bounded at ' + bound + '; the wait ends when the running turn finishes. Not a completion estimate.', 'stage-note'));
    return wrap;
  }
  if (!progress.stage) return null;
  wrap.append(el('span', '▸', 'stage-glyph'));
  wrap.append(el('span', progress.stage_label || progress.stage, 'stage-text'));
  const seconds = Number(progress.stage_seconds);
  if (isFinite(seconds) && seconds >= 2) wrap.append(el('span', Math.round(seconds) + ' s in this stage', 'stage-note'));
  if ((progress.stages_seen || []).length > 1) wrap.append(el('span', progress.stages_seen.join(' → '), 'stage-note'));
  wrap.append(el('span', progress.stage_note || 'A stage names work in progress; it is not a completion estimate.', 'stage-note'));
  return wrap;
}
function readingLine(packet) {
  // The engine's own first reading of the question, shown while the answer is still being
  // retrieved. It is provisional by contract: it repeats no value, cites nothing and is never
  // saved, and the card that replaces it carries the evidence. A carried reading is what the
  // conversation already holds; it is not a claim about the new message.
  const reading = packet && packet.reading;
  if (!reading || !reading.line) return null;
  const wrap = el('span', undefined, 'reading-readout');
  wrap.append(el('span', '\u25c7', 'reading-glyph'));
  wrap.append(el('span', reading.line, 'reading-text'));
  wrap.append(el('span', reading.basis === 'carried'
    ? 'What the conversation is still carrying. Not a new reading, not evidence.'
    : (packet.note || 'A first reading, not evidence.'), 'reading-note'));
  return wrap;
}
