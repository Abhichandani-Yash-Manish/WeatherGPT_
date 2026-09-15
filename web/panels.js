'use strict';
/* Surface renderers. Each one reads a product-view payload and paints it,
   including the payload's own limitations. Series values are passed through as
   exact source text so the chart's inspector shows the source value. */

(function () {
  const WG = window.WG;
  if (!WG) return;
  const DAY_LABELS = { 1: 'Day 1', 2: 'Day 2', 3: 'Day 3', 4: 'Day 4', 5: 'Day 5' };

  function placeQuery(WGref, extra) {
    const place = WGref.state.place || { latitude: 23.02579, longitude: 72.58727 };
    const params = { lat: place.latitude, lon: place.longitude };
    Object.keys(extra || {}).forEach(key => { params[key] = extra[key]; });
    return params;
  }
  function dayChip(day) {
    const label = day.colour || 'colour not supplied';
    return WG.colourChip(day.colour, label);
  }
  function hazardText(day) {
    if (day.source_text) return day.source_text;
    if (day.hazards && day.hazards.length) return day.hazards.join(', ');
    if (day.hazard_codes && day.hazard_codes.length) return 'codes ' + day.hazard_codes.join(', ');
    return 'no hazard code supplied';
  }
  function dayStrip(days) {
    const strip = el('div', undefined, 'day-strip');
    (days || []).forEach(day => {
      const cell = el('div', undefined, 'day-cell' + (day.is_today ? ' is-today' : '') + (day.quiet ? ' is-quiet' : ''));
      cell.append(el('span', DAY_LABELS[day.day] || ('Day ' + day.day), 'day-name'));
      if (day.label) cell.append(el('span', day.label, 'day-date'));
      cell.append(dayChip(day));
      cell.append(el('span', hazardText(day), 'day-hazard'));
      if (day.is_today) cell.append(el('span', 'Today', 'day-today'));
      strip.append(cell);
    });
    return strip;
  }
  function sourceLine(view, host) {
    host.append(WG.sourceDisclosure(view));
  }
  function seriesChart(parameters, key, title, unitLabel) {
    const bucket = parameters[key];
    if (!bucket) return null;
    const points = (bucket.points || []).map(point => ({
      x: Date.parse(point.t),
      label: istStamp(point.t),
      value: point.v === null || point.v === undefined ? null : String(point.v),
      evidence_id: point.source_locator
    }));
    return historicalChart({ title: title, unit: bucket.unit || unitLabel || '', points: points, axis_label: 'Time (IST)' });
  }

  WG.panels.overview = async function (host, WGref) {
    const view = await WGref.api('/api/overview', { place: placeQuery(WGref).lat + ',' + placeQuery(WGref).lon });
    WGref.state.freshness = WG.freshness(view);
    const data = view.data;
    const tally = el('div', undefined, 'metric-row');
    Object.keys(data.national.tally || {}).sort().forEach(colour => {
      const card = el('div', undefined, 'metric');
      card.append(WG.colourChip(colour, colour));
      card.append(el('strong', String(data.national.tally[colour]), 'metric-value'));
      card.append(el('small', 'district-days at this colour', 'metric-note'));
      tally.append(card);
    });
    const grid = el('div', undefined, 'overview-grid');
    const nationalCard = WG.block('National warning picture',
      'Official IMD district warning guidance, bulletin ' + (data.national.bulletin_date || 'date not stated') + '.');
    nationalCard.append(tally);
    nationalCard.append(el('p', data.national.districts + ' districts carry a row; ' + data.national.skipped +
      ' source features carry no district name and are listed in the warnings view.', 'block-note'));
    grid.append(nationalCard);

    const radarCard = WG.block('Radar network', 'How many stations report a state to the source.');
    radarCard.append(el('p', data.radar.reported + ' of ' + data.radar.stations + ' stations report a state.', 'block-note'));
    grid.append(radarCard);
    host.append(grid);

    (data.places || []).forEach(strip => {
      const card = WG.block(strip.label || 'Place', strip.district
        ? 'District ' + strip.district + (strip.state ? ', ' + strip.state : '') + ' · bulletin ' + (strip.bulletin_date || 'date not stated')
        : 'No district applies to this point.');
      if (strip.days && strip.days.length) card.append(dayStrip(strip.days));
      if (strip.note) card.append(el('p', strip.note, 'block-note'));
      host.append(card);
    });

    host.append(WG.disclosure('How this overview was assembled', body => {
      const list = el('ul', undefined, 'notes');
      ['The district table is read as attributes only, so the overview does not download district geometry.',
       'A place is resolved to its district by point-in-polygon on the vendored official geometry.',
       'A district day marked quiet is not an all-clear, and the CAP relay is reported separately in the warnings view.'].forEach(note => list.append(el('li', note)));
      body.append(list);
    }));
    sourceLine(view, host);
  };

  WG.panels.warnings = async function (host, WGref) {
    const caps = await WGref.api('/api/warnings/cap').catch(error => null);
    const plan = WG.block('Your place', 'Resolved against the official district geometry.');
    host.append(plan);
    const placeButton = el('button', 'Check my place against the warning product', 'secondary');
    placeButton.type = 'button';
    plan.append(placeButton);
    const placeResult = el('div', undefined, 'place-result');
    plan.append(placeResult);
    placeButton.addEventListener('click', async () => {
      WG.clear(placeResult);
      placeResult.append(WG.loading('Resolving the district…'));
      try {
        const view = await WGref.api('/api/warnings/place', placeQuery(WGref));
        WG.clear(placeResult);
        WGref.state.freshness = WG.freshness(view);
        if (view.status !== 'ok' || !view.data.district) {
          placeResult.append(el('p', 'No district polygon of this product contains that point, so no district guidance applies there.', 'block-note'));
        } else {
          placeResult.append(el('p', view.data.district + (view.data.state ? ', ' + view.data.state : '') +
            ' · bulletin ' + istStamp(view.data.issued_at_utc), 'block-note'));
          placeResult.append(dayStrip(view.data.days));
          placeResult.append(el('p', view.data.day_boundary_basis || '', 'field-note'));
        }
        placeResult.append(WG.sourceDisclosure(view));
      } catch (error) {
        WG.clear(placeResult);
        placeResult.append(WG.stateBlock('error', error.message));
      }
    });

    const capCard = WG.block('CAP relay', 'Reported on its own and never merged with district guidance.');
    if (!caps) {
      capCard.append(WG.stateBlock('plain', 'The CAP relay state could not be read.'));
    } else {
      const data = caps.data;
      capCard.append(el('p', data.messages + ' retrieved messages; ' + data.eligible_by_lifecycle +
        ' pass the time, status and reference checks.' + (data.latest_sent ? ' Newest sent ' + istStamp(data.latest_sent) + '.' : ''), 'block-note'));
      if (data.records && data.records.length) {
        capCard.append(WG.disclosure('Retrieved CAP messages (' + data.records.length + ')', body => {
          body.append(WG.table(['Sent', 'Event', 'Severity', 'Status', 'Expires'],
            data.records.map(record => [record.sent ? istStamp(record.sent) : '—', record.event || '—',
                                        record.severity || '—', record.status || '—',
                                        record.expires ? istStamp(record.expires) : '—'])));
        }));
      }
      capCard.append(WG.limitationList(caps));
    }
    host.append(capCard);

    const view = await WGref.api('/api/warnings/national');
    WGref.state.freshness = WG.freshness(view);
    const card = WG.block('National district warning table',
      view.data.districts.length + ' districts · ' + (view.data.skipped || []).length + ' source features without a district name');
    const controls = el('div', undefined, 'controls');
    const stateSelect = el('select');
    stateSelect.setAttribute('aria-label', 'Filter districts by state');
    stateSelect.append(el('option', 'All states'));
    stateSelect.firstChild.value = '';
    const states = Array.from(new Set(view.data.districts.map(row => row.state).filter(Boolean))).sort();
    states.forEach(name => { const option = el('option', name); option.value = name; stateSelect.append(option); });
    const search = el('input');
    search.type = 'search';
    search.placeholder = 'Filter districts';
    const briefButton = el('button', 'Write the alert brief', 'ghost');
    briefButton.type = 'button';
    briefButton.setAttribute('aria-label', 'Write the alert brief for the working place');
    const place = WGref.state.place || {};
    briefButton.addEventListener('click', async () => {
      if (place.latitude === undefined || place.longitude === undefined) {
        WG.openDrawer('Alert brief', body => body.append(el('p', 'Choose a working place first: a brief is composed for one point, and the workspace will not guess which.', 'field-note')));
        return;
      }
      WG.openDrawer('Alert brief · ' + (place.label || 'selected point'), body => {
        const note = el('p', 'Composing from the official district warning product and the CAP relay, reported separately…', 'field-note');
        body.append(note);
        WGref.api('/api/warnings/alert-brief', { lat: place.latitude, lon: place.longitude, day: 1 }).then(view => {
          const brief = view.data || {};
          WG.clear(body);
          body.append(el('p', brief.status_line || brief.why || 'No brief was composed.', 'block-note'));
          const rows = [
            ['District', (brief.place || {}).district || 'not stated', (brief.place || {}).state || ''],
            ['Day', (brief.day || {}).label || 'not stated', (brief.day || {}).starts_utc ? (brief.day.starts_utc + ' to ' + brief.day.ends_utc) : ''],
            ['Hazards as published', ((brief.day_status || {}).hazards || []).join(', ') || 'none listed', (brief.day_status || {}).official_wording || (brief.day_status || {}).wording_note || ''],
            ['Issuer', (brief.issuer || {}).source_id + ' · ' + (brief.issuer || {}).product, 'issued ' + ((brief.issuer || {}).issued_at_utc || 'not stated') + ' · retrieved ' + ((brief.issuer || {}).retrieved_at_utc || 'not stated')],
            ['CAP relay (separate)', ((brief.relay || {}).source_id || 'S06') + ' · ' + ((brief.relay || {}).messages === undefined ? 'not read' : brief.relay.messages + ' message(s), ' + brief.relay.eligible_by_lifecycle + ' eligible'), (brief.relay || {}).note || ''],
            ['Brief identity', 'sha256 ' + String(brief.brief_id || '').slice(0, 16), 'the content hash of this brief']
          ];
          body.append(WG.table(['Field', 'Value', 'Provenance'], rows));
          body.append(el('p', 'What would change this', 'field-label'));
          const changes = el('ul', undefined, 'notes');
          (brief.what_would_change_this || []).forEach(item => changes.append(el('li', item)));
          body.append(changes);
          body.append(el('p', 'What is not established here', 'field-label'));
          const limits = el('ul', undefined, 'notes');
          (brief.not_established || []).forEach(item => limits.append(el('li', item)));
          body.append(limits);
          const keep = el('div', undefined, 'brief-tools');
          const save = el('button', 'Save to briefcase', 'ghost');
          save.type = 'button';
          save.setAttribute('aria-label', 'Keep this brief in the local briefcase');
          save.addEventListener('click', () => {
            save.disabled = true;
            save.textContent = 'Saving…';
            WGref.post('/api/briefs/save', { kind: 'alert_brief', lat: place.latitude, lon: place.longitude, day: 1 })
              .then(result => {
                save.textContent = 'Kept';
                body.append(el('p', 'Kept as “' + String((result.entry || {}).title || 'a brief') + '”. Nothing was delivered: open the Briefcase to reopen or export it.', 'block-note'));
              })
              .catch(error => {
                save.disabled = false;
                save.textContent = 'Save to briefcase';
                body.append(el('p', 'This brief was not kept: ' + String(error.message || error), 'block-note'));
              });
          });
          keep.append(save);
          body.append(keep);
          body.append(el('p', 'A brief records what a product published. It is not a warning issued here, not a forecast and not an all-clear.', 'field-note'));
        }).catch(error => {
          WG.clear(body);
          body.append(el('p', 'The brief could not be composed: ' + String(error.message || error), 'block-note'));
        });
      });
    });
    controls.append(stateSelect, search, briefButton);
    card.append(controls);
    const tableHost = el('div');
    card.append(tableHost);
    function paint() {
      const needle = search.value.trim().toUpperCase();
      const chosen = stateSelect.value;
      const rows = view.data.districts.filter(row => (!chosen || row.state === chosen) &&
        (!needle || String(row.district).toUpperCase().indexOf(needle) >= 0)).slice(0, 400);
      WG.clear(tableHost);
      tableHost.append(WG.table(['District', 'State', 'Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'],
        rows.map(row => {
          const button = el('button', row.district, 'link-button');
          button.type = 'button';
          button.addEventListener('click', () => openDistrict(row));
          return [button, row.state || '—'].concat(row.days.map(day => dayChip(day)));
        }), { cls: 'warnings-table' }));
      if (rows.length === 400) tableHost.append(el('p', 'Showing the first 400 matching districts. Narrow the filter to see others.', 'block-note'));
    }
    function openDistrict(row) {
      WG.openDrawer(row.district + (row.state ? ', ' + row.state : ''), body => {
        body.append(el('p', 'Bulletin ' + (row.bulletin_date || 'date not stated') +
          (row.updated_at ? ' · updated ' + istStamp(row.updated_at) : ''), 'block-note'));
        const list = el('div', undefined, 'day-list');
        row.days.forEach(day => {
          const line = el('div', undefined, 'day-line');
          line.append(el('span', DAY_LABELS[day.day] + ' · ' + (day.date_utc || 'date not stated'), 'day-name'));
          line.append(dayChip(day));
          line.append(el('span', hazardText(day), 'day-hazard'));
          list.append(line);
        });
        body.append(list);
        body.append(el('p', 'Day 1 is the bulletin date and each following day is the next IST calendar day. The colour is the product colour for that district-day and the hazard wording is the source wording.', 'field-note'));
      });
    }
    stateSelect.addEventListener('change', paint);
    search.addEventListener('input', paint);
    paint();
    card.append(WG.limitationList(view));
    host.append(card);
    host.append(WG.disclosure('Why some districts are missing', body => {
      body.append(el('p', 'Of ' + view.coverage.features_returned + ' source features, ' +
        view.coverage.skipped_without_a_name + ' carry no district name and cannot be keyed. They are listed here rather than dropped silently.', 'field-note'));
      if ((view.data.skipped || []).length) {
        body.append(WG.table(['Source object id', 'Reason'],
          view.data.skipped.map(item => [String(item.obj_id || '—'), item.reason])));
      }
    }));
    sourceLine(view, host);
  };

  WG.panels.map = async function (host, WGref) {
    const manifest = await WGref.api('/api/map/layers');
    WGref.state.freshness = WG.freshness(manifest);
    if (!WG.map) { host.append(WG.stateBlock('error', 'The map renderer is not loaded.')); return; }
    const warningsView = await WGref.api('/api/warnings/national');
    host.append(WG.map.render({
      manifest: manifest.data,
      warnings: warningsView.data.districts,
      place: WGref.state.place,
      load: name => WGref.apiJsonFile('/api/map/static/' + name),
      onSelect: row => WG.openDrawer(row.district + (row.state ? ', ' + row.state : ''), body => {
        body.append(el('p', 'Bulletin ' + (row.bulletin_date || 'date not stated'), 'block-note'));
        const list = el('div', undefined, 'day-list');
        row.days.forEach(day => {
          const line = el('div', undefined, 'day-line');
          line.append(el('span', DAY_LABELS[day.day] + ' · ' + (day.date_utc || 'date not stated'), 'day-name'));
          line.append(dayChip(day));
          line.append(el('span', hazardText(day), 'day-hazard'));
          list.append(line);
        });
        body.append(list);
        body.append(el('p', 'Drawn from the vendored official district geometry. Warning colour is applied at render time and is never stored in the geometry.', 'field-note'));
      })
    }));
    host.append(WG.sourceDisclosure(manifest));
    host.append(WG.sourceDisclosure(warningsView));
  };

  WG.panels.observations = async function (host, WGref) {
    const controls = WG.block('Search radius', 'Stations are found by great-circle distance from your working place.');
    const row = el('div', undefined, 'controls');
    const select = el('select');
    select.setAttribute('aria-label', 'Station search radius in kilometres');
    [50, 150, 300, 600].forEach(value => { const option = el('option', value + ' km'); option.value = String(value); if (value === 150) option.selected = true; select.append(option); });
    const button = el('button', 'Refresh from the source', 'ghost');
    button.type = 'button';
    row.append(select, button);
    controls.append(row);
    host.append(controls);
    const resultHost = el('div');
    host.append(resultHost);

    async function paint(force) {
      WG.clear(resultHost);
      resultHost.append(WG.loading('Reading the station networks…'));
      try {
        const view = await WGref.api('/api/observations/near', placeQuery(WGref, { radius_km: select.value, limit: 8, refresh: force ? '1' : '' }));
        WGref.state.freshness = WG.freshness(view);
        WG.clear(resultHost);
        const networks = view.data.networks || {};
        Object.keys(networks).forEach(kind => {
          const card = WG.block(kind === 'metar' ? 'Airport reports (METAR)' : 'Automatic weather stations (AWS)',
            kind === 'metar' ? 'Reports from the aviation network nearest your place.' : 'Automated station readings nearest your place.');
          const stations = networks[kind] || [];
          if (!stations.length) {
            card.append(WG.stateBlock('plain', 'No ' + kind.toUpperCase() + ' station reported inside ' + select.value + ' km. That means none is connected here, not that no weather occurred.'));
          } else {
            card.append(WG.table(['Station', 'Distance', 'Observed', 'Age', 'State'],
              stations.map(station => {
                const name = el('span', station.name || station.station_code || 'unnamed station');
                const stateChip = station.stale === true ? WG.chip('stale', 'is-stale')
                  : station.stale === false ? WG.chip('current', 'is-current') : WG.chip('no instant', 'is-unknown');
                return [name, station.distance_km + ' km',
                        station.observed_at_utc ? istStamp(station.observed_at_utc) : (station.observed_date_utc || 'not supplied'),
                        station.age_minutes === null ? '—' : station.age_minutes + ' min', stateChip];
              })));
            stations.slice(0, 3).forEach(station => {
              if (!station.parameters || !station.parameters.length) return;
              card.append(WG.disclosure('Reported values · ' + (station.name || station.station_code), body => {
                body.append(WG.table(['Field', 'Value as reported', 'Unit'],
                  station.parameters.map(parameter => [parameter.field, String(parameter.value),
                                                       parameter.unit || 'not stated by the source'])));
                if (station.time_notes && station.time_notes.length) {
                  const list = el('ul', undefined, 'notes');
                  station.time_notes.forEach(note => list.append(el('li', note)));
                  body.append(el('p', 'Time field notes', 'field-label'), list);
                }
                if (station.unusable_time_field) body.append(el('p', 'Rejected time field: ' + station.unusable_time_field, 'field-note'));
              }));
            });
          }
          resultHost.append(card);
        });
        resultHost.append(WG.disclosure('What an observation is not', body => {
          const list = el('ul', undefined, 'notes');
          (view.limitations || []).forEach(note => list.append(el('li', note)));
          body.append(list);
        }));
        resultHost.append(WG.sourceDisclosure(view));
      } catch (error) {
        WG.clear(resultHost);
        resultHost.append(WG.stateBlock('error', error.message));
      }
    }
    select.addEventListener('change', () => paint(false));
    button.addEventListener('click', () => paint(true));
    await paint(false);
  };

  WG.panels.forecast = async function (host, WGref) {
    const card = WG.block('Point forecast', 'Model output, not an observation.');
    const controls = el('div', undefined, 'controls');
    const daysSelect = el('select');
    daysSelect.setAttribute('aria-label', 'Forecast days to retrieve');
    [1, 2, 3, 5, 7].forEach(value => { const option = el('option', value + ' day' + (value > 1 ? 's' : '')); option.value = String(value); if (value === 3) option.selected = true; daysSelect.append(option); });
    const parameterSelect = el('select');
    parameterSelect.setAttribute('aria-label', 'Forecast parameter');
    const refresh = el('button', 'Refresh from the source', 'ghost');
    refresh.type = 'button';
    controls.append(daysSelect, parameterSelect, refresh);
    card.append(controls);
    const host2 = el('div');
    card.append(host2);
    host.append(card);
    let view = null;
    async function load(force) {
      WG.clear(host2);
      host2.append(WG.loading('Reading the forecast…'));
      try {
        view = await WGref.api('/api/forecast', placeQuery(WGref, { days: daysSelect.value, refresh: force ? '1' : '' }));
        WGref.state.freshness = WG.freshness(view);
        const names = Object.keys(view.data.parameters || {});
        WG.clear(parameterSelect);
        names.forEach(name => { const option = el('option', name); option.value = name; parameterSelect.append(option); });
        if (names.length && !parameterSelect.value) parameterSelect.value = names[0];
        paint();
      } catch (error) {
        WG.clear(host2);
        host2.append(WG.stateBlock('error', error.message));
      }
    }
    function paint() {
      WG.clear(host2);
      if (!view || view.status !== 'ok') { host2.append(WG.stateBlock('plain', 'No forecast series was returned for this point.')); return; }
      const bucket = (view.data.parameters || {})[parameterSelect.value];
      if (!bucket) { host2.append(WG.stateBlock('plain', 'Select a parameter.')); return; }
      const chart = seriesChart(view.data.parameters, parameterSelect.value, parameterSelect.value);
      if (chart) host2.append(chart);
      const facts = WG.block('Answering grid');
      facts.append(el('p', 'Requested ' + (view.data.requested ? view.data.requested.latitude + ', ' + view.data.requested.longitude : '—') +
        ' · model grid ' + (view.data.grid ? view.data.grid.latitude + ', ' + view.data.grid.longitude : '—') +
        ' · time basis ' + (view.data.time_basis || 'not stated'), 'block-note'));
      facts.append(el('p', 'Model: ' + (bucket.model || 'not stated') +
        (bucket.quality_flags && bucket.quality_flags.length ? ' · quality flags ' + bucket.quality_flags.join(', ') : ' · no quality flags reported'), 'field-note'));
      host2.append(facts);
      host2.append(WG.limitationList(view));
      host2.append(WG.sourceDisclosure(view));
    }
    parameterSelect.addEventListener('change', paint);
    daysSelect.addEventListener('change', () => load(false));
    refresh.addEventListener('click', () => load(true));
    await load(false);
  };

  WG.panels.climate = async function (host, WGref) {
    const index = await WGref.api('/api/climate/index');
    WGref.state.freshness = WG.freshness(index);
    const card = WG.block('Published district rainfall', 'Transcribed from the supplied IMD district tables, 1901 to 2010.');
    const controls = el('div', undefined, 'controls');
    const stateSelect = el('select');
    stateSelect.setAttribute('aria-label', 'State for the published record');
    index.data.states.forEach(entry => { const option = el('option', entry.state); option.value = entry.state; stateSelect.append(option); });
    const districtSelect = el('select');
    districtSelect.setAttribute('aria-label', 'District for the published record');
    const fromInput = el('input'); fromInput.type = 'number'; fromInput.value = '1981'; fromInput.min = '1901'; fromInput.max = '2010';
    const toInput = el('input'); toInput.type = 'number'; toInput.value = '2010'; toInput.min = '1901'; toInput.max = '2010';
    const go = el('button', 'Read the record', 'secondary');
    go.type = 'button';
    controls.append(stateSelect, districtSelect, fromInput, toInput, go);
    if (index.data.states.length) stateSelect.value = stateSelect.value || index.data.states[0].state;
    card.append(controls);
    const resultHost = el('div');
    card.append(resultHost);
    host.append(card);
    function fillDistricts() {
      const entry = index.data.states.find(item => item.state === stateSelect.value);
      WG.clear(districtSelect);
      const items = (entry && entry.districts) || [];
      items.forEach(item => {
        const option = el('option', item.district + ' (' + item.first_year + '–' + item.last_year + ')');
        option.value = item.district;
        districtSelect.append(option);
      });
      if (items.length) districtSelect.value = districtSelect.value || items[0].district;
    }
    async function read() {
      WG.clear(resultHost);
      resultHost.append(WG.loading('Reading the published record…'));
      try {
        const view = await WGref.api('/api/climate/series', { district: districtSelect.value, state: stateSelect.value, from: fromInput.value, to: toInput.value });
        WG.clear(resultHost);
        if (view.status !== 'ok') { resultHost.append(WG.stateBlock('plain', 'The stored record does not carry this district spelling.')); return; }
        const points = view.data.points.map(point => ({ year: point.year, value: point.value, evidence_id: point.series_id + ' p' + (point.source_page || '?') }));
        resultHost.append(historicalChart({ title: view.data.district + ' · annual rainfall · ' + view.data.first_year + '–' + view.data.last_year,
                                            unit: 'mm', points: points }));
        resultHost.append(WG.disclosure('Per-year provenance (' + view.data.points.length + ')', body => {
          body.append(WG.table(['Year', 'Annual (mm)', 'Source page', 'Source row', 'Table label', 'Asset'],
            view.data.points.map(point => [String(point.year), point.value === null ? 'missing' : String(point.value),
                                           point.source_page || '—', String(point.source_row), point.label || '—',
                                           point.asset_sha256_prefix || '—'])));
          body.append(el('p', 'The chart reports exact source text; a descriptive reading of this record is not a projection or an attribution.', 'field-note'));
        }, true));
        resultHost.append(WG.limitationList(view));
        resultHost.append(WG.sourceDisclosure(view));
      } catch (error) {
        WG.clear(resultHost);
        resultHost.append(WG.stateBlock('error', error.message));
      }
    }
    stateSelect.addEventListener('change', fillDistricts);
    go.addEventListener('click', read);
    fillDistricts();
    await read();
  };

  WG.panels.advisories = async function (host, WGref) {
    const states = await WGref.api('/api/advisories/states');
    WGref.state.freshness = WG.freshness(states);
    const card = WG.block('District farmer bulletins', 'Directory entries published by the source. A listing is not proof of a current bulletin.');
    const controls = el('div', undefined, 'controls');
    const stateSelect = el('select');
    stateSelect.setAttribute('aria-label', 'State for farmer bulletins');
    states.data.states.forEach(entry => { const option = el('option', entry.label || entry.id); option.value = entry.id; stateSelect.append(option); });
    controls.append(stateSelect);
    card.append(controls);
    if (states.data.states.length) stateSelect.value = stateSelect.value || states.data.states[0].id;
    const listHost = el('div');
    card.append(listHost);
    host.append(card);
    async function loadDistricts() {
      WG.clear(listHost);
      listHost.append(WG.loading('Reading the district directory…'));
      try {
        const view = await WGref.api('/api/advisories/districts', { state: stateSelect.value });
        WG.clear(listHost);
        const districts = view.data.districts || [];
        listHost.append(el('p', districts.length + ' districts listed for ' + stateSelect.value + '.', 'block-note'));
        const grid = el('div', undefined, 'chip-grid');
        districts.forEach(district => {
          const button = el('button', district.label || district.id, 'chip-button');
          button.type = 'button';
          button.addEventListener('click', () => {
            const input = document.getElementById('question');
            if (input) input.value = 'What does the district bulletin say for ' + (district.label || district.id) + '?';
            const note = document.getElementById('assistant-context');
            if (note) note.textContent = 'Asked from advisories: ' + (district.label || district.id) + ' bulletin';
            window.location.hash = '#/assistant';
          });
          grid.append(button);
        });
        listHost.append(grid);
        listHost.append(el('p', 'Choosing a district asks the assistant for its passages, which keeps the crop, stage, page and saved archive attached to each quotation.', 'field-note'));
        listHost.append(WG.sourceDisclosure(view));
      } catch (error) {
        WG.clear(listHost);
        listHost.append(WG.stateBlock('error', error.message));
      }
    }
    stateSelect.addEventListener('change', loadDistricts);
    await loadDistricts();
    host.append(WG.disclosure('What this surface does not do', body => {
      const list = el('ul', undefined, 'notes');
      ['It does not present a listing as a current advisory.',
       'It does not extend a source recommendation into a field decision, a dosage or a go or no-go call.',
       'Whole-document recall across every edition is still partial: four district editions were inspected, not the national corpus.'].forEach(note => list.append(el('li', note)));
      body.append(list);
    }));
    host.append(WG.sourceDisclosure(states));
  };

  WG.panels.aviation = async function (host, WGref) {
    const card = WG.block('Airport reports', 'Station observations and terminal forecasts by ICAO code.');
    const controls = el('div', undefined, 'controls');
    const input = el('input');
    input.type = 'text';
    input.value = 'VAAH';
    input.placeholder = 'VAAH';
    const kindSelect = el('select');
    kindSelect.setAttribute('aria-label', 'Station report kind');
    [['metar', 'Observation (METAR)'], ['taf', 'Terminal forecast (TAF)']].forEach(pair => {
      const option = el('option', pair[1]); option.value = pair[0]; kindSelect.append(option);
    });
    const go = el('button', 'Read the report', 'secondary');
    go.type = 'button';
    controls.append(input, kindSelect, go);
    card.append(controls);
    const presets = el('div', undefined, 'chip-grid');
    [['VAAH', 'Ahmedabad'], ['VABB', 'Mumbai'], ['VIDP', 'Delhi'], ['VOBL', 'Bengaluru'], ['VECC', 'Kolkata'], ['VOMM', 'Chennai']].forEach(pair => {
      const button = el('button', pair[0] + ' · ' + pair[1], 'chip-button');
      button.type = 'button';
      button.addEventListener('click', () => { input.value = pair[0]; read(); });
      presets.append(button);
    });
    card.append(presets);
    const resultHost = el('div');
    card.append(resultHost);
    host.append(card);
    async function read() {
      WG.clear(resultHost);
      resultHost.append(WG.loading('Reading the airport report…'));
      try {
        const view = await WGref.api('/api/aviation', { icao: input.value.trim(), kind: kindSelect.value });
        WGref.state.freshness = WG.freshness(view);
        WG.clear(resultHost);
        (view.data.stations || []).forEach(station => {
          const box = WG.block(station.station_id || 'station');
          if (station.observed_at_utc) {
            box.append(el('p', 'Observed ' + istStamp(station.observed_at_utc) +
              (station.age_seconds !== undefined ? ' · ' + Math.round(station.age_seconds / 60) + ' minutes old' : '') +
              ' · ' + (station.freshness || 'freshness not stated'), 'block-note'));
          }
          if (station.raw_report) box.append(el('pre', station.raw_report, 'raw-report'));
          const rows = [];
          if (station.temperature_c !== undefined && station.temperature_c !== null) rows.push(['Temperature', String(station.temperature_c), '°C']);
          if (station.dewpoint_c !== undefined && station.dewpoint_c !== null) rows.push(['Dewpoint', String(station.dewpoint_c), '°C']);
          if (station.wind_speed_kt !== undefined && station.wind_speed_kt !== null) rows.push(['Wind speed', String(station.wind_speed_kt), 'kt']);
          if (station.wind_direction_native !== undefined && station.wind_direction_native !== null) rows.push(['Wind direction', String(station.wind_direction_native), 'degrees']);
          if (rows.length) box.append(WG.table(['Field', 'Value', 'Unit'], rows));
          resultHost.append(box);
        });
        if ((view.data.missing || []).length) resultHost.append(el('p', 'No report was returned for: ' + view.data.missing.join(', '), 'block-note'));
        if (!(view.data.stations || []).length && !(view.data.missing || []).length) resultHost.append(WG.stateBlock('plain', 'No report was returned for that code.'));
        resultHost.append(WG.limitationList(view));
        resultHost.append(WG.sourceDisclosure(view));
      } catch (error) {
        WG.clear(resultHost);
        resultHost.append(WG.stateBlock('error', error.message));
      }
    }
    go.addEventListener('click', read);
    input.addEventListener('keydown', event => { if (event.key === 'Enter') read(); });
    await read();
  };

  WG.panels.marine = async function (host, WGref) {
    const place = WGref.state.place;
    const card = WG.block('Coastal and river point', 'Modeled waves and modeled discharge near ' + (place ? place.label : 'your place') + '.');
    host.append(card);
    const wavesHost = el('div');
    card.append(wavesHost);
    wavesHost.append(WG.loading('Reading the wave model…'));
    try {
      const view = await WGref.api('/api/marine', placeQuery(WGref, { days: 2 }));
      WGref.state.freshness = WG.freshness(view);
      WG.clear(wavesHost);
      if (view.status !== 'ok') {
        wavesHost.append(WG.stateBlock('plain', 'No sea grid cell was returned for this place. Marine values are served only for a coastal point with a nearby sea cell; an inland place is not answered with a distant cell.'));
        if (view.limitations) wavesHost.append(WG.limitationList(view));
      } else {
        Object.keys(view.data.parameters).forEach(name => {
          const chart = seriesChart(view.data.parameters, name, name);
          if (chart) wavesHost.append(chart);
        });
        wavesHost.append(el('p', 'Answering cell ' + (view.data.grid ? view.data.grid.latitude + ', ' + view.data.grid.longitude : 'not stated') +
          (view.data.grid_distance_km !== undefined ? ' · ' + view.data.grid_distance_km + ' km from the requested point' : ''), 'block-note'));
        wavesHost.append(WG.limitationList(view));
      }
      wavesHost.append(WG.sourceDisclosure(view));
    } catch (error) {
      WG.clear(wavesHost);
      wavesHost.append(WG.stateBlock('error', error.message));
    }
    const riverHost = el('div');
    card.append(riverHost);
    riverHost.append(WG.loading('Reading the river model…'));
    try {
      const view = await WGref.api('/api/river', placeQuery(WGref, { days: 3 }));
      WG.clear(riverHost);
      if (view.status !== 'ok') {
        riverHost.append(WG.stateBlock('plain', 'No river model cell was returned for this place.'));
      } else {
        Object.keys(view.data.parameters).forEach(name => {
          const chart = seriesChart(view.data.parameters, name, 'Modeled river discharge');
          if (chart) riverHost.append(chart);
        });
        riverHost.append(el('p', 'Answering cell ' + (view.data.grid ? view.data.grid.latitude + ', ' + view.data.grid.longitude : 'not stated') +
          (view.data.grid_distance_km !== undefined ? ' · ' + view.data.grid_distance_km + ' km from the requested point' : ''), 'block-note'));
        riverHost.append(WG.limitationList(view));
      }
      riverHost.append(WG.sourceDisclosure(view));
    } catch (error) {
      WG.clear(riverHost);
      riverHost.append(WG.stateBlock('error', error.message));
    }
    host.append(WG.disclosure('Why neither of these is an official marine or flood product', body => {
      const list = el('ul', undefined, 'notes');
      ['A wave height is model output for a sea grid cell, not an official sea-area bulletin and not a measured buoy observation.',
       'A discharge value is modeled volume flow, not an observed water level, a gauge reading, a danger level, an inundation extent or an official flood warning.',
       'No tide, current or sea-surface temperature is retrieved here.'].forEach(note => list.append(el('li', note)));
      body.append(list);
    }));
  };

  WG.panels.settings = async function (host, WGref) {
    const view = await WGref.api('/api/settings/capabilities');
    WGref.state.freshness = WG.freshness(view);
    const card = WG.block('What this suite can answer',
      view.data.capabilities.length + ' connected capabilities over ' + view.data.connected_sources + ' tested adapters, from ' + view.data.registered_sources + ' registered sources.');
    card.append(WG.table(['Capability', 'Kind', 'Answers', 'Stated purpose'],
      view.data.capabilities.map(capability => [capability.tool, capability.kind,
        (capability.operations || []).join(', '), capability.purpose])));
    host.append(card);
    const sourceCard = WG.block('Sources in use', 'Integration status and unresolved terms as the registry records them.');
    sourceCard.append(WG.table(['Source', 'Product', 'Integration', 'Review', 'Selection'],
      view.data.sources.map(source => [source.source_id, source.product || '—', source.integration_status || '—',
        source.user_review || '—', source.selection || '—'])));
    const terms = el('ul', undefined, 'notes');
    view.data.sources.filter(source => source.usage_terms).forEach(source => {
      terms.append(el('li', source.source_id + ': ' + source.usage_terms));
    });
    sourceCard.append(el('p', 'Usage terms', 'field-label'), terms);
    sourceCard.append(el('p', 'A registered source is not a serving approval, and a tested adapter is not operational readiness.', 'field-note'));
    host.append(sourceCard);
    host.append(WG.limitationList(view));
    const mapCard = WG.block('Vendored basemap', 'Display geometry built once from official layers.');
    host.append(mapCard);
    try {
      const manifest = await WGref.api('/api/map/layers');
      mapCard.append(el('p', 'Build ' + manifest.data.build_id + ' · ' + manifest.data.layers.length + ' layers · ' +
        manifest.data.district_polygons + ' district polygons · ' + manifest.data.skipped_without_a_name + ' source features without a name.', 'block-note'));
      const join = manifest.data.state_attribution || {};
      mapCard.append(el('p', 'State attribution: ' + (join.attributed || 0) + ' of ' + (join.districts || 0) +
        ' districts, ' + (join.exact_name_matches || 0) + ' by exact name and the rest geometrically.', 'field-note'));
      mapCard.append(WG.sourceDisclosure(manifest));
    } catch (error) {
      mapCard.append(WG.stateBlock('plain', error.message));
    }
  };

  /* What changed: stored retrieval vintages compared for the same valid hour.
     This surface reports vintage variance and never presents it as skill,
     calibration or confidence, because no observation is matched here. */
  WG.panels.changes = async function (host, WGref) {
    const place = WGref.state.place || { latitude: 23.02579, longitude: 72.58727 };
    const view = await WGref.api('/api/forecast/changes', placeQuery(WGref, { limit: 40 }));
    WGref.state.freshness = WG.freshness(view);

    const head = el('section', undefined, 'block');
    head.append(el('p', 'Vintage variance · not a forecast score', 'eyebrow'));
    const title = el('h2', 'How the stored retrievals differ for the same valid hour', 'block-title');
    head.append(title);
    const status = view.status;
    const data = view.data || {};
    const summary = el('div', undefined, 'metric-row');
    [['Stored retrievals', String(data.retrieval_count || 0)],
     ['Valid hours compared', String(data.overlapping_valid_hours || 0)],
     ['Parameters', String(Object.keys(data.parameters || {}).length)],
     ['View status', status]].forEach(pair => {
      const metric = el('div', undefined, 'metric');
      metric.append(el('span', pair[0], 'metric-note'));
      metric.append(el('span', pair[1], 'metric-value'));
      summary.append(metric);
    });
    head.append(summary);
    head.append(el('p', 'A change between retrievals is not an error and neither retrieval is validated here. Upstream model run identity is not exposed, so a change cannot be attributed to a rerun; retrieval time is not issue time.', 'block-note'));
    if (data.point) head.append(el('p', 'Stored point ' + Number(data.point.latitude).toFixed(4) + ', ' + Number(data.point.longitude).toFixed(4) + (data.requested_point && (data.point.latitude !== data.requested_point.latitude || data.point.longitude !== data.requested_point.longitude) ? ' — nearest stored retrieval to ' + Number(data.requested_point.latitude).toFixed(4) + ', ' + Number(data.requested_point.longitude).toFixed(4) : ''), 'field-note'));
    host.append(head);

    const parameters = data.parameters || {};
    if (Object.keys(parameters).length) {
      const table = WG.table(['Parameter', 'Unit', 'Hours compared', 'Mean change', 'Largest change', 'Example'], Object.keys(parameters).map(name => {
        const entry = parameters[name] || {};
        const example = entry.example
          ? entry.example.first_value + ' → ' + entry.example.last_value + ' at ' + istStamp(entry.example.valid_time_utc) + ' IST, retrieved ' + istStamp(entry.example.first_retrieved_utc) + ' → ' + istStamp(entry.example.last_retrieved_utc)
          : 'no overlapping pair';
        return [name, entry.unit || '—', String(entry.valid_hours || 0), entry.mean_abs_change === undefined ? '—' : String(entry.mean_abs_change),
                entry.max_abs_change === undefined ? '—' : String(entry.max_abs_change), example];
      }));
      const block = el('section', undefined, 'block');
      block.append(el('h2', 'By parameter', 'block-title'));
      block.append(el('p', 'Mean and largest absolute change between the earliest and latest stored retrieval that covers a valid hour. Units are the source units.', 'block-note'));
      block.append(table);
      host.append(block);
    } else if (status !== 'unavailable') {
      const block = el('section', undefined, 'block');
      block.append(el('h2', 'No overlapping valid hours', 'block-title'));
      block.append(el('p', 'Stored retrievals exist for this place, but no valid hour was retrieved more than once, so nothing can be compared. This is an absence of comparison, not a statement that the forecast did not change.', 'block-note'));
      host.append(block);
    }

    if ((data.retrievals || []).length) {
      const block = el('section', undefined, 'block');
      block.append(el('h2', 'Retrievals compared', 'block-title'));
      const list = el('ul', undefined, 'notes');
      data.retrievals.slice(-8).reverse().forEach(row => list.append(el('li', istStamp(row.retrieved_at_utc) + ' · ' + (row.product || 'forecast') + (row.request_date ? ' · requested ' + row.request_date : '') + ' · response ' + (row.response_sha256_prefix || 'not recorded'))));
      block.append(list);
      host.append(block);
    }

    sourceLine(view, host);
  };


  /* ---------- the briefcase ---------- */
  /* Briefs the workspace composed and kept. The page can save, reopen, export and delete
     one; it cannot post a brief of its own, because the server composes from sources. */
  function briefTitle(entry) { return String(entry.title || 'Brief'); }
  function briefRows(entry) {
    return [
      ['Kind', entry.kind, entry.delivery || 'local_only_no_delivery'],
      ['Place', (entry.place || {}).label || (entry.place || {}).district || 'not stated', (entry.place || {}).state || ''],
      ['Window', (entry.window || {}).label || 'not stated', (entry.window || {}).starts_utc ? entry.window.starts_utc + ' to ' + entry.window.ends_utc : ''],
      ['Sources named', (entry.sources || []).join(', ') || 'none named in this brief', 'source identifiers as stored'],
      ['Content hash', 'sha256 ' + String(entry.content_sha256 || '').slice(0, 16), 'the content hash recorded when it was composed'],
      ['Kept', entry.saved_at, 'entry ' + String(entry.id).slice(0, 8)]
    ];
  }
  WG.panels.briefcase = async function (host, WGref) {
    const view = await WGref.api('/api/briefs');
    WGref.state.freshness = WGref.freshness(view);
    const entries = view.briefs || [];
    const block = WGref.block('Kept briefs', entries.length + ' kept in the local store · ' + (view.delivery || 'local_only_no_delivery'));
    block.append(el('p', view.note || 'Nothing kept here is delivered or pushed.', 'block-note'));
    if (!entries.length) {
      block.append(WGref.stateBlock('plain', 'Nothing is kept yet.',
        'Open Warnings and write the alert brief for the working place, then keep it here. A brief is composed from its sources by the server: this page cannot save a brief the workspace did not compose.'));
      host.append(block);
      return;
    }
    const list = el('ul', undefined, 'brief-list');
    entries.forEach(entry => {
      const item = el('li', undefined, 'brief-item');
      item.append(el('p', briefTitle(entry), 'brief-title'));
      item.append(el('p', 'Kept ' + entry.saved_at + ' · ' + ((entry.place || {}).label || (entry.place || {}).district || 'place not stated') + ' · sources ' + ((entry.sources || []).join(', ') || 'none named'), 'brief-meta'));
      const tools = el('div', undefined, 'brief-tools');
      const open = el('button', 'Open', 'ghost');
      open.type = 'button';
      open.setAttribute('data-brief-open', entry.id);
      open.addEventListener('click', () => {
        WGref.openDrawer(briefTitle(entry), body => {
          const note = el('p', 'Reading the kept entry from the local store…', 'field-note');
          body.append(note);
          WGref.api('/api/briefs/get', { id: entry.id }).then(saved => {
            WGref.clear(body);
            body.append(WGref.table(['Field', 'Value', 'Provenance'], briefRows(saved.entry || entry)));
            body.append(el('p', 'Export as written', 'field-label'));
            body.append(el('pre', saved.markdown || '', 'brief-markdown'));
            const limits = el('ul', undefined, 'notes');
            (((saved.entry || entry).evidence || {}).not_established || []).forEach(limit => limits.append(el('li', limit)));
            if (limits.childNodes.length) { body.append(el('p', 'What this brief says is not established', 'field-label')); body.append(limits); }
          }).catch(error => { WGref.clear(body); body.append(el('p', 'This entry could not be read: ' + String(error.message || error), 'block-note')); });
        });
      });
      const exportButton = el('button', 'Export Markdown', 'ghost');
      exportButton.type = 'button';
      exportButton.setAttribute('data-brief-export', entry.id);
      exportButton.addEventListener('click', async () => {
        try {
          const text = await WGref.apiText('/api/briefs/export?id=' + encodeURIComponent(entry.id));
          WGref.download(String(entry.title || 'brief').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) + '-' + String(entry.id).slice(0, 8) + '.md', text, 'text/markdown');
        } catch (error) {
          WGref.openDrawer('Export failed', body => body.append(el('p', 'The export could not be read from the local store: ' + String(error.message || error), 'block-note')));
        }
      });
      const remove = el('button', 'Delete', 'ghost danger');
      remove.type = 'button';
      remove.setAttribute('data-brief-delete', entry.id);
      remove.addEventListener('click', async () => {
        try {
          await WGref.post('/api/briefs/delete', { id: entry.id });
          WGref.render();
        } catch (error) {
          WGref.openDrawer('Delete failed', body => body.append(el('p', 'This entry was not removed: ' + String(error.message || error), 'block-note')));
        }
      });
      tools.append(open, exportButton, remove);
      item.append(tools);
      list.append(item);
    });
    block.append(list);
    block.append(el('p', 'Deleting removes the entry from this machine\'s local store. An exported file stays where you saved it.', 'block-note'));
    host.append(block);
  };
  WG.panels.assistant = async function () { /* the conversation is owned by app.js */ };
})();
