'use strict';
/* A place-centred product workspace. Every section reads the existing governed
   product API independently. No headline infers a quiet warning from missing data. */
(function () {
  const W = window.WG;
  if (!W) return;
  const TOOLS = [
    { id: 'now', group: 'Daily weather', title: 'Understand right now', detail: 'Nearby station reports, the published warning day and the next model hours.', output: 'Current-condition reading', question: p => 'What is it like right now in ' + p + '?' },
    { id: 'forecast', group: 'Daily weather', title: 'Plan a weather window', detail: 'Rain, temperature, humidity and wind for a place and part of the day.', output: 'Forecast with exact hours', question: (p, f) => 'What is the weather forecast for ' + p + ' ' + f.day + ' ' + f.period + '?' },
    { id: 'air-quality', group: 'Daily weather', title: 'Read modelled air quality', detail: 'CAMS pollutant concentrations and the source’s own indices. Model output, not a ground monitor or health assessment.', output: 'Hourly air-quality evidence', question: (p, f) => 'Show PM2.5 and US AQI for ' + p + ' ' + f.day + '.' },
    { id: 'compare', group: 'Models & history', title: 'Compare forecast models', detail: 'Put GFS and the best-match product side by side. Their model lineage can overlap.', output: 'Source comparison', question: (p, f) => 'Compare the GFS and best-match forecast for rain in ' + p + ' ' + f.day + ' ' + f.period + '.' },
    { id: 'ensemble', group: 'Models & history', title: 'Explore ensemble spread', detail: 'Read the range and spread of model members. Spread is not confidence or forecast skill.', output: 'Member statistics', question: (p, f) => 'Show the ensemble spread for temperature in ' + p + ' ' + f.day + '.' },
    { id: 'warning', group: 'Warnings & plans', title: 'Read the warning brief', detail: 'The district day, published hazards, issue time and what the product does not establish.', output: 'Brief to save or export', action: p => W.alertBriefDrawer(W, p, 1) },
    { id: 'watch', group: 'Warnings & plans', title: 'Watch a plan', detail: 'Describe an activity and when it happens. Check official district guidance while the workspace runs.', output: 'Plan and local inbox', question: (p, f) => 'Notify me about official weather warning changes for my ' + f.activity + ' in ' + p + ' ' + f.day + ' ' + f.period + '.' },
    { id: 'farm', group: 'Published advice', title: 'Read a crop advisory', detail: 'Find published passages for your district and crop, with their issue date and original PDF.', output: 'Cited advisory passages', question: (p, f) => 'What does the district agromet advisory for ' + p + ' say for ' + f.crop + (f.stage ? ' at ' + f.stage + ' stage' : '') + '?' },
    { id: 'bulletin', group: 'Published advice', title: 'Search published bulletins', detail: 'Read the indexed national weather bulletin by topic. Published wording stays reference material.', output: 'Passages and source pages', question: (p, f) => 'What does the latest all India weather bulletin say about ' + f.topic + '?' },
    { id: 'history', group: 'Models & history', title: 'Explore rainfall history', detail: 'Read the published district series and its descriptive trend, within the available years.', output: 'Chart and source records', question: (p, f) => 'Show the annual rainfall trend for ' + p + ' district from ' + f.fromYear + ' to ' + f.toYear + '.' },
    { id: 'reanalysis', group: 'Models & history', title: 'Look back at a weather week', detail: 'Ask for daily modelled reanalysis for a chosen past date. This is not a station record.', output: 'Historical daily series', question: (p, f) => 'Show daily ERA5 temperature and rainfall for ' + p + ' from ' + f.from + ' to ' + f.to + '.' },
    { id: 'aviation', group: 'Specialist weather', title: 'Read an airport report', detail: 'METAR observations or a TAF forecast for the airport code you choose.', output: 'Station report and explanation', question: (p, f) => 'Show the latest ' + f.report + ' for ' + f.icao + ' and explain it.' },
    { id: 'marine', group: 'Specialist weather', title: 'Explore waves offshore', detail: 'Modelled wave height, direction and period, with the answering cell and distance.', output: 'Wave forecast', question: (p, f) => 'What are the wave conditions off ' + p + ' ' + f.day + '?' },
    { id: 'river', group: 'Specialist weather', title: 'Explore river discharge', detail: 'Modelled discharge near a point. No observed water level, danger level or flood extent.', output: 'Discharge forecast', question: (p, f) => 'Show the modelled river discharge near ' + p + ' ' + f.day + '.' },
    { id: 'briefing', group: 'Warnings & plans', title: 'Compose a place briefing', detail: 'Keep a dated reading of warnings and forecast context, including what changed since the previous run.', output: 'Dated local briefing', action: p => W.writeBriefing(W, p) }
  ];
  function button(text, fn, cls) {
    const b = el('button', text, cls || 'ghost'); b.type = 'button'; b.addEventListener('click', fn); return b;
  }
  function link(text, view) { const a = el('a', text, 'workspace-link'); a.href = '#/' + view; return a; }
  function field(form, label, name, value, options) {
    const wrap = el('label', undefined, 'journey-field'); wrap.append(el('span', label));
    const input = el(options ? 'select' : 'input'); input.name = name; input.id = 'journey-' + name;
    if (options) options.forEach(pair => { const o = el('option', pair[1]); o.value = pair[0]; input.append(o); });
    else { input.type = ['from', 'to'].includes(name) ? 'date' : 'text'; input.maxLength = 150; }
    input.value = value; input.required = name !== 'stage'; wrap.append(input); form.append(wrap); return input;
  }
  function launch(tool, place) {
    // Snapshot the chosen place: a later topbar change must not relabel this draft.
    const p = Object.assign({}, place);
    if (tool.action) { tool.action(p); return; }
    W.openDrawer(tool.title, host => {
      host.append(el('p', tool.detail, 'block-note'));
      const form = el('form', undefined, 'journey-form');
      const fields = {};
      if (!['aviation', 'bulletin'].includes(tool.id)) fields.place = field(form, 'Place or district', 'place', p.queryLabel || [...new Set((p.label || '').split(', ').map(part => part.replace(/^State of /, '')))].join(', '));
      if (['forecast', 'compare', 'ensemble', 'watch', 'marine', 'river', 'air-quality'].includes(tool.id)) {
        fields.day = field(form, 'Day', 'day', 'tomorrow', [['today', 'Today'], ['tomorrow', 'Tomorrow']]);
      }
      if (['forecast', 'compare', 'watch'].includes(tool.id)) fields.period = field(form, 'Time (IST)', 'period', 'morning', [['morning', 'Morning · 09:30–12:30'], ['afternoon', 'Afternoon · 12:30–18:30'], ['evening', 'Evening · 18:30–22:30']]);
      if (tool.id === 'watch') fields.activity = field(form, 'Activity to watch', 'activity', 'outdoor event', [['outdoor event', 'Outdoor event'], ['travel', 'Travel'], ['cotton spraying', 'Cotton spraying'], ['harvest', 'Harvest'], ['irrigation', 'Irrigation']]);
      if (tool.id === 'farm') {
        fields.crop = field(form, 'Crop', 'crop', 'cotton'); fields.stage = field(form, 'Growth stage (optional)', 'stage', '');
      }
      if (tool.id === 'bulletin') fields.topic = field(form, 'Topic to find', 'topic', 'heavy rainfall');
      if (tool.id === 'aviation') {
        fields.icao = field(form, 'Airport ICAO code', 'icao', 'VOBL');
        fields.icao.pattern = '[A-Za-z]{4}';
        fields.report = field(form, 'Report', 'report', 'METAR', [['METAR', 'METAR · observed'], ['TAF', 'TAF · forecast']]);
      }
      if (tool.id === 'history') {
        fields.fromYear = field(form, 'First year (1901–2010)', 'fromYear', '1981');
        fields.toYear = field(form, 'Last year (1901–2010)', 'toYear', '2010');
        [fields.fromYear, fields.toYear].forEach(i => { i.type = 'number'; i.min = '1901'; i.max = '2010'; i.step = '1'; });
      }
      if (tool.id === 'reanalysis') {
        fields.from = field(form, 'From', 'from', '2025-07-01'); fields.to = field(form, 'Until (at most 7 days)', 'to', '2025-07-07');
      }
      const preview = el('p', undefined, 'journey-preview'); preview.setAttribute('aria-live', 'polite');
      const values = () => Object.fromEntries(Object.entries(fields).map(([key, input]) => [key, input.value.trim()]));
      const question = () => { const f = values(); return tool.question(f.place || p.label, f); };
      const update = () => { preview.textContent = question(); };
      form.addEventListener('input', update); form.addEventListener('change', update); update();
      form.append(el('p', 'Your question', 'field-label'), preview);
      const note = el('p', 'Opens a new conversation. Review the question there, then ask; follow-ups keep its context.', 'field-note'); form.append(note);
      const go = el('button', 'Open in Ask →', 'primary'); go.type = 'submit'; form.append(go);
      form.addEventListener('submit', event => {
        event.preventDefault();
        if (tool.id === 'history' && Number(values().fromYear) > Number(values().toYear)) { note.textContent = 'The first year must come before the last year.'; return; }
        if (tool.id === 'reanalysis') {
          const f = values(), days = (Date.parse(f.to) - Date.parse(f.from)) / 86400000;
          if (!Number.isFinite(days) || days < 0 || days > 6) { note.textContent = 'Choose an inclusive range of 1 to 7 days.'; return; }
        }
        if (W.prepareQuestion(question(), tool.title + ' · ' + (values().place || (values().icao ? values().icao.toUpperCase() : 'All India')))) W.closeDrawer();
        else note.textContent = 'A question is still running. Finish or stop it before opening this task.';
      });
      host.append(form);
    });
  }
  // Keep source identity, retrieval time, coverage and limitations in each section.
  function receipt(host, view) {
    const sources = (view.sources || []).map(s => s.source_id + ' · ' + (s.product || '')).join(' / ');
    host.append(el('p', sources || 'Source identity not returned', 'desk-source'));
    host.append(el('p', (view.sources || []).map(s => 'Retrieved ' + (s.retrieved_at_utc ? istStamp(s.retrieved_at_utc) : 'time not stated')).join(' · '), 'desk-source'));
    host.append(W.sourceDisclosure(view), W.disclosure('Coverage and limits', body => body.append(W.limitationList(view))));
  }
  function warningSummary(host, view) {
    const data = view.data || {};
    host.append(el('p', (data.district || 'District not resolved') + (data.state ? ', ' + data.state : ''), 'desk-entity'));
    host.append(el('p', 'Issued ' + (data.issued_at_utc ? istStamp(data.issued_at_utc) : 'time not stated'), 'desk-source'));
    const days = data.days || [];
    const today = days.find(d => d.is_today && !d.is_past);
    // The API has no `severity` property. Missing it cannot mean no warning.
    if (!today) host.append(el('p', 'Today is not covered by this edition.', 'desk-reading'));
    else {
      host.append(el('p', today.quiet === true ? 'No warning in this product' : (today.source_text || (today.hazards || []).join(', ') || 'Hazard wording not stated'), 'desk-reading'));
      if (today.colour) host.append(W.colourChip(today.colour, today.colour));
    }
    const strip = el('div', undefined, 'desk-days');
    days.filter(d => !d.is_past).forEach(d => {
      const row = el('div', undefined, 'desk-day');
      row.append(el('span', d.label || d.date_local || 'Date not stated'));
      if (d.colour) row.append(W.colourChip(d.colour, d.colour));
      row.append(el('span', d.quiet === true ? 'No warning in this product' : d.source_text || (d.hazards || []).join(', ') || 'Not stated'));
      strip.append(row);
    });
    host.append(strip, el('p', 'District guidance from one product. Not an all-clear or a point-level warning.', 'field-note'));
  }
  function observationSummary(host, view) {
    const data = view.data || {};
    const stations = data.stations || Object.values(data.networks || {}).flat();
    // Prefer a usable report, then the freshest reported instant; never label it
    // as a measurement at the selected point.
    const station = stations.slice().sort((a, b) => Number(a.stale === true) - Number(b.stale === true) || (Date.parse(b.observed_at_utc) || 0) - (Date.parse(a.observed_at_utc) || 0))[0];
    if (!station) { host.append(el('p', 'No station report returned within 150 km.', 'desk-reading')); return; }
    host.append(el('p', (station.name || station.station_code || station.station_id || 'Station name not stated') + (station.kind ? ' · ' + station.kind.toUpperCase() : ''), 'desk-entity'));
    host.append(el('p', 'Reported ' + (station.observed_at_utc ? istStamp(station.observed_at_utc) : 'time not stated') + ' · ' + (station.distance_km == null ? 'distance not stated' : station.distance_km + ' km away'), 'desk-source'));
    host.append(el('p', (station.stale === true ? 'Stale report' : station.stale === false ? 'Within the prototype age limit' : 'Freshness not stated') + (station.age_minutes == null ? '' : ' · ' + station.age_minutes + ' min old'), 'field-note'));
    const weather = (station.parameters || []).find(p => p.field === 'weather' && typeof p.value === 'string');
    if (weather) host.append(el('p', weather.value, 'desk-reading'));
    const labels = { temp: 'Temperature', dewtemp: 'Dew point', mslp: 'Pressure', winddir: 'Wind direction', windsp: 'Wind speed', rainfall: 'Rainfall' };
    const rows = (station.parameters || []).slice(0, 3).map(p => [labels[p.field] || p.field, p.value == null ? 'Not stated' : String(p.value), p.unit || 'Unit not stated by source']);
    if (rows.length) host.append(W.table(['Reported field', 'Value', 'Unit'], rows));
    (station.time_notes || []).forEach(note => host.append(el('p', note, 'field-note')));
    host.append(el('p', 'This is a station report, not a measurement at your selected point.', 'field-note'));
  }
  function forecastSummary(host, view) {
    const data = view.data || {}, buckets = data.parameters || {};
    const grid = data.grid || {};
    host.append(el('p', 'Answering cell: ' + (grid.latitude == null ? 'not stated' : grid.latitude + ', ' + grid.longitude), 'desk-entity'));
    const rows = [];
    Object.entries(buckets).slice(0, 4).forEach(([name, b]) => {
      const point = (b.points || []).find(p => Date.parse(p.t) >= Date.now());
      if (point) rows.push([name.replace(/_/g, ' '), point.v == null ? 'Missing' : String(point.v), b.unit || 'Not stated', point.start && point.end ? istStamp(point.start) + ' – ' + istStamp(point.end) : istStamp(point.t)]);
    });
    if (rows.length) host.append(W.table(['Next value', 'Value', 'Unit', 'Window (IST)'], rows));
    else host.append(el('p', 'No upcoming source hours were returned.', 'desk-reading'));
    host.append(el('p', 'Model: ' + Array.from(new Set(Object.values(buckets).map(b => b.model || 'not stated'))).join(', '), 'desk-source'));
    host.append(el('p', 'Model output. Each value uses its own valid hour; it is not an observation.', 'field-note'));
  }
  async function readSection(card, path, params, paint, title) {
    const body = el('div', undefined, 'desk-card-body'); card.append(body); body.tabIndex = 0; body.setAttribute('aria-label', title + ' — reading and evidence'); body.setAttribute('role', 'region');
    async function read() {
      body.replaceChildren(W.loading('Reading this source…'));
      const slow = setTimeout(() => {
        if (body.querySelector('.state-loading')) body.append(el('p', 'This source is taking longer. Other sections and tools remain usable.', 'field-note'));
      }, 12000);
      try {
        const view = await W.api(path, params);
        body.replaceChildren();
        if (view.status && !['ok', 'answered'].includes(view.status)) {
          body.append(el('p', 'Not available from this source', 'desk-reading'));
          if (view.message) body.append(el('p', view.message, 'field-note'));
        } else paint(body, view);
        if (view.sources) receipt(body, view);
        body.append(button('Read this source again', read, 'ghost desk-retry'));
      } catch (error) {
        body.replaceChildren(el('p', 'This source could not be read', 'desk-reading'), el('p', error.message, 'field-note'), button('Retry this source', read, 'secondary'));
      } finally { clearTimeout(slow); }
    }
    return read();
  }
  W.panels.workspace = async function (host) {
    const place = Object.assign({}, W.state.place || {});
    const displayPlace = place.queryLabel || Array.from(new Set((place.label || '').split(', ').map(part => part.replace(/^State of /, '')))).join(', ');
    const head = el('header', undefined, 'desk-head');
    const intro = el('div'); intro.append(el('p', 'YOUR WEATHER WORKSPACE', 'desk-eyebrow'), el('h1', displayPlace || 'Choose your place'));
    intro.append(el('p', 'Understand the weather. Make a plan. Keep the evidence.', 'desk-subtitle'));
    head.append(intro, button('Change place', () => document.getElementById('place-input').focus(), 'secondary'));
    host.append(head);
    const command = el('form', undefined, 'desk-command');
    const label = el('label', 'What would you like to find out?', 'sr'); label.htmlFor = 'workspace-question';
    const input = el('input'); input.id = 'workspace-question'; input.required = true; input.maxLength = 1500;
    input.placeholder = 'Ask about ' + (displayPlace || 'a place') + '…';
    const ask = el('button', 'Open in Ask →', 'primary'); ask.type = 'submit'; command.append(label, input, ask);
    command.addEventListener('submit', event => { event.preventDefault(); W.prepareQuestion(input.value.trim(), 'New question from your workspace. Name the place in your question.'); });
    host.append(command);
    const sectionHead = el('div', undefined, 'desk-section-head'); sectionHead.append(el('h2', 'The picture at your place'), el('span', 'Each source has its own time and coverage.', 'field-note')); host.append(sectionHead);
    const grid = el('div', undefined, 'desk-live-grid'); host.append(grid);
    const specs = [
      ['Published warnings', 'warnings', '/api/warnings/place', {}, warningSummary],
      ['Nearby observation', 'observations', '/api/observations/near', { limit: 1, radius_km: 150 }, observationSummary],
      ['Next forecast hours', 'forecast', '/api/forecast', { days: 2 }, forecastSummary]
    ];
    const reads = [];
    specs.forEach(([title, route, path, extra, paint]) => {
      const card = el('section', undefined, 'desk-live-card'); const top = el('div', undefined, 'desk-card-head');
      top.append(el('h3', title), link('Explore →', route)); card.append(top); grid.append(card);
      if (Number.isFinite(place.latitude) && Number.isFinite(place.longitude)) reads.push(readSection(card, path, Object.assign({ lat: place.latitude, lon: place.longitude }, extra), paint, title));
      else card.append(el('p', 'Choose a place to read this source.', 'field-note'));
    });
    const toolHead = el('div', undefined, 'desk-section-head'); toolHead.append(el('h2', 'What do you want to do?'));
    const searchLabel = el('label', 'Find a tool', 'sr'); searchLabel.htmlFor = 'tool-search';
    const search = el('input'); search.type = 'search'; search.id = 'tool-search'; search.placeholder = 'Find a tool, topic or output'; toolHead.append(searchLabel, search); host.append(toolHead);
    const filters = el('div', undefined, 'desk-filters'); filters.setAttribute('role', 'group'); filters.setAttribute('aria-label', 'Filter tools');
    const toolGrid = el('div', undefined, 'desk-tools'); let group = 'All tools';
    const count = el('p', undefined, 'field-note'); count.setAttribute('aria-live', 'polite');
    function paintTools() {
      toolGrid.replaceChildren();
      const query = search.value.trim().toLowerCase();
      const found = TOOLS.filter(t => (group === 'All tools' || t.group === group) && [t.title, t.detail, t.output].join(' ').toLowerCase().includes(query));
      filters.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.textContent === group)));
      found.forEach(tool => {
        const card = el('article', undefined, 'desk-tool'); card.append(el('p', tool.group, 'desk-eyebrow'), el('h3', tool.title), el('p', tool.detail, 'block-note'));
        const foot = el('div', undefined, 'desk-tool-foot'); foot.append(el('span', tool.output, 'field-note'), button('Open →', () => launch(tool, place), 'secondary'));
        foot.querySelector('button').setAttribute('aria-label', tool.title); card.append(foot); toolGrid.append(card);
      });
      count.textContent = found.length ? found.length + ' tools · results keep their source and limits.' : 'No tools match. Try “rain”, “bulletin” or “airport”.';
    }
    ['All tools', ...new Set(TOOLS.map(t => t.group))].forEach(name => filters.append(button(name, () => { group = name; paintTools(); }, 'chip-button')));
    search.addEventListener('input', paintTools); host.append(filters, toolGrid, count); paintTools();
    const keepHead = el('div', undefined, 'desk-section-head'); keepHead.append(el('h2', 'Pick up where you left off')); host.append(keepHead);
    const kept = el('div', undefined, 'desk-kept'); host.append(kept);
    const briefs = el('section', undefined, 'desk-live-card'); briefs.append(el('h3', 'Saved briefs'), link('Open briefcase →', 'briefcase')); kept.append(briefs);
    const plans = el('section', undefined, 'desk-live-card'); plans.append(el('h3', 'Plans & inbox'), button('Open plans & inbox →', () => document.getElementById('notify-toggle').click())); kept.append(plans);
    reads.push(readSection(briefs, '/api/briefs', {}, (body, view) => {
      const entries = view.briefs || [];
      if (!entries.length) body.append(el('p', 'Your first brief starts with a warning or place briefing above. Save it, then reopen or export it here.', 'block-note'));
      entries.slice(0, 3).forEach(e => body.append(el('p', e.title || 'Saved brief', 'desk-entity'), el('p', 'Saved ' + (e.saved_at ? istStamp(e.saved_at) : 'time not stated'), 'field-note')));
    }, 'Saved briefs'));
    reads.push(readSection(plans, '/api/plans', {}, (body, view) => {
      const items = view.plans || [];
      if (!items.length) body.append(el('p', 'No plans saved. Start with “Watch a plan” above.', 'block-note'));
      items.slice(0, 3).forEach(p => body.append(el('p', p.title, 'desk-entity'), el('p', (p.state_words || p.state || 'State not stated') + ' · checked ' + (p.last_checked_at ? istStamp(p.last_checked_at) : 'not yet'), 'field-note')));
      body.append(el('p', 'Checks and browser notifications require the local workspace to be running. Open the inbox for delivery status.', 'field-note'));
    }, 'Plans and inbox'));
    host.append(el('p', 'Local prototype · Radar imagery, tide, observed river levels and operational clearance are not available. Source, language and coverage limits remain visible with each result.', 'desk-boundary'));
    await Promise.allSettled(reads);
  };
  W.workspaceTools = TOOLS;
  W.workspaceWarningSummary = warningSummary;
  W.workspaceObservationSummary = observationSummary;
})();
