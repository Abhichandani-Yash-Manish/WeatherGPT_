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
    stateSelect.append(el('option', 'All states'));
    stateSelect.firstChild.value = '';
    const states = Array.from(new Set(view.data.districts.map(row => row.state).filter(Boolean))).sort();
    states.forEach(name => { const option = el('option', name); option.value = name; stateSelect.append(option); });
    const search = el('input');
    search.type = 'search';
    search.placeholder = 'Filter districts';
    controls.append(stateSelect, search);
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
    [1, 2, 3, 5, 7].forEach(value => { const option = el('option', value + ' day' + (value > 1 ? 's' : '')); option.value = String(value); if (value === 3) option.selected = true; daysSelect.append(option); });
    const parameterSelect = el('select');
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
    index.data.states.forEach(entry => { const option = el('option', entry.state); option.value = entry.state; stateSelect.append(option); });
    const districtSelect = el('select');
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

  WG.panels.assistant = async function () { /* the conversation is owned by app.js */ };
})();
