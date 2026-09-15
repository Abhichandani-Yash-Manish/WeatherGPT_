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
  /* The product's own colour words, in the order the product itself escalates them. This is a
     reading order for a grid, not a score and not a severity claim of ours. */
  const COLOUR_RANK = { green: 1, yellow: 2, orange: 3, red: 4 };
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
  /* The meteogram needs three independent series on one axis, so it is built only from what the
     source returned. A missing series is simply absent from the drawing and the exact-value table
     — never estimated from another parameter or from the previous hour. */
  function meteogramFor(parameters) {
    if (typeof viz === 'undefined' || !viz.meteogram) return null;
    const temperature = parameters.temperature_2m || parameters.apparent_temperature || null;
    const rain = parameters.precipitation || parameters.rain || null;
    const wind = parameters.wind_speed_10m || parameters.wind_speed || null;
    const humidity = parameters.relative_humidity_2m || parameters.relative_humidity || null;
    if (!temperature && !rain && !wind) return null;
    const hours = [];
    const index = new Map();
    const collect = (bucket, field, evidenceKey) => {
      ((bucket || {}).points || []).forEach(point => {
        if (!point.t) return;
        let entry = index.get(point.t);
        if (!entry) { entry = { t: point.t, label: istStamp(point.t), evidence: {} }; index.set(point.t, entry); hours.push(entry); }
        entry[field] = point.v;
        if (point.source_locator) entry.evidence[evidenceKey] = point.source_locator;
      });
    };
    collect(temperature, 'temperature', 'temperature');
    collect(rain, 'rain', 'rain');
    collect(wind, 'wind_speed', 'wind');
    collect(humidity, 'humidity', 'humidity');
    const wind_direction = parameters.wind_direction_10m || parameters.wind_direction || null;
    ((wind_direction || {}).points || []).forEach(point => {
      const entry = index.get(point.t);
      if (entry) entry.wind_direction = point.v;
    });
    if (!hours.length) return null;
    hours.sort((left, right) => Date.parse(left.t) - Date.parse(right.t));
    hours.forEach(hour => {
      const ist = new Date(Date.parse(hour.t) + 5.5 * 3600 * 1000);
      const localHour = ist.getUTCHours();
      hour.night = localHour < 6 || localHour >= 19;
    });
    return viz.meteogram({
      title: 'Meteogram \u00b7 ' + hours.length + ' hour(s)',
      temperature_unit: (temperature || {}).unit, rain_unit: (rain || {}).unit, wind_unit: (wind || {}).unit,
      hours: hours
    });
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
    /* The Now band is the command-centre reading: one row per product, placed on the same time
       axis, so a reader can see what is observed, what is published and what is modelled, and
       where each of them starts. Every lane comes from the payload; nothing is placed by hand. */
    let nowReading = null;
    try { nowReading = await WGref.api('/api/now', { lat: placeQuery(WGref).lat, lon: placeQuery(WGref).lon }); }
    catch (error) { nowReading = null; }
    if (nowReading && typeof viz !== 'undefined' && viz.nowBand) {
      const reading = nowReading.data || {};
      const station = (((reading.observed || {}).stations) || [])[0] || null;
      const day = reading.in_force || {};
      const hours = ((reading.next_hours || {}).rows) || [];
      const lanes = [];
      if (station && station.observed_at_utc) {
        lanes.push({ key: 'observed', label: 'Observed', kind: 'observed', from: station.observed_at_utc,
          detail: [station.name || station.station_code, station.distance_km === null || station.distance_km === undefined ? null : Math.round(station.distance_km * 10) / 10 + ' km away',
            (station.parameters || []).slice(0, 2).map(parameter => parameter.field + ' ' + parameter.value).join(', ')].filter(Boolean).join(' \u00b7 '),
          source: station.source_id || 'S63' });
      }
      if (day.status === 'ok' && day.starts_utc && day.ends_utc) {
        lanes.push({ key: 'published', label: 'Published', kind: 'published', from: day.starts_utc, to: day.ends_utc,
          colour: day.colour, detail: day.status_line || 'the product stated a colour without wording', source: day.source_id || 'S63' });
      }
      if (hours.length) {
        const firstHour = hours[0].at, lastHour = hours[hours.length - 1].at;
        const firstTemp = hours[0].temperature_2m, lastTemp = hours[hours.length - 1].temperature_2m;
        lanes.push({ key: 'model', label: 'Model next', kind: 'model', from: firstHour, to: lastHour,
          detail: hours.length + ' hour(s) returned, ' + (firstTemp === undefined ? 'temperature not returned' : firstTemp + ' \u00b0C at the first hour') +
            ' and ' + (lastTemp === undefined ? 'temperature not returned' : lastTemp + ' \u00b0C at the last'),
          source: (reading.next_hours || {}).source_id || 'source not stated' });
      }
      host.append(viz.nowBand({
        title: 'Now',
        place: WGref.state.place ? WGref.state.place.label : null,
        read_at: reading.generated_at_utc || nowReading.generated_at_utc,
        note: 'Three products on one axis, kept apart: an observation is an instant, the published day is a district window, and the model hours are model output.',
        lanes: lanes
      }));
    }
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
    /* The right-now reading: what a station reported, what the published district product says
       for today, and what the model holds for the next hours - three products kept apart. Radar
       and satellite imagery, sub-hourly refresh and push are not connected and say so here. */
    const nowCard = WG.block('Right now at this place', 'Station observations, the published day and the next model hours, kept apart.');
    try {
      const now = (nowReading || {}).data;
      if (!now) throw new Error('the right-now reading could not be read');
      const stations = ((now.observed || {}).stations) || [];
      if (stations.length) {
        nowCard.append(WG.table(['Station', 'Network', 'Distance', 'Reported', 'Age'],
          stations.map(station => [station.name || station.station_code || 'station', String(station.network || '').toUpperCase(),
            station.distance_km === null || station.distance_km === undefined ? 'not stated' : String(Math.round(station.distance_km * 100) / 100) + ' km',
            station.observed_at_utc || 'not stated',
            station.age_minutes === null || station.age_minutes === undefined ? 'not stated' : String(Math.round(station.age_minutes)) + ' min'])));
        const reported = el('ul', undefined, 'notes');
        (stations[0].parameters || []).forEach(parameter => reported.append(el('li', parameter.field + ': ' + parameter.value +
          (parameter.unit ? ' ' + parameter.unit : (parameter.unit_stated_by_source === false ? ' (no unit stated by the source)' : '')))));
        nowCard.append(el('p', 'As reported by the nearest station', 'field-label'));
        nowCard.append(reported);
      } else {
        nowCard.append(el('p', 'No station in the connected METAR or AWS layers reported within 150 km of this point. That is an absence of station evidence here, not a statement that nothing is happening.', 'block-note'));
      }
      const day = now.in_force || {};
      if (day.status === 'ok') {
        const line = el('p', undefined, 'block-note');
        line.append(WG.colourChip(day.colour || 'unknown', day.colour || 'colour not supplied'));
        line.append(el('span', ' ' + String(day.status_line || '')));
        nowCard.append(line);
        nowCard.append(el('p', 'Published for ' + String(day.district || 'this point') + ' by ' + String(day.source_id || 'the district product') +
          ', issued ' + String(day.issued_at_utc || 'instant not stated') + '. A quiet day in this product is not an all-clear.', 'field-note'));
      } else {
        nowCard.append(el('p', 'The official district product could not be read for this point: ' + String(day.why || 'no published day matched') + '.', 'block-note'));
      }
      const rows = ((now.next_hours || {}).rows) || [];
      if (rows.length) {
        nowCard.append(el('p', 'Model hours next (' + String((now.next_hours || {}).source_id || 'source not stated') + ')', 'field-label'));
        nowCard.append(WG.table(['Hour', 'Temperature', 'Rain chance'], rows.map(row => [row.at,
          row.temperature_2m === undefined ? 'not returned' : row.temperature_2m + ' °C',
          row.precipitation_probability === undefined ? 'not returned' : row.precipitation_probability + ' %'])));
      } else {
        nowCard.append(el('p', 'No model hours were returned for this point.', 'block-note'));
      }
      nowCard.append(el('p', 'Not connected here: ' + ((now.not_connected || []).join('; ') || 'nothing listed') + '.', 'field-note'));
      nowCard.append(el('p', now.summary || '', 'block-note'));
    } catch (error) {
      nowCard.append(el('p', 'The right-now reading could not be read: ' + String(error.message || error), 'block-note'));
    }
    grid.append(nowCard);
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
    // The matrix is the scan view of the same product. Rows are ordered by the product's own
    // colour rank — never a score — and every cell carries the colour the source printed.
    if (typeof viz !== 'undefined' && viz.warningMatrix && (view.data.districts || []).length) {
      const worstOf = row => (row.days || []).reduce((best, day) => Math.max(best, COLOUR_RANK[day.colour] || 0), 0);
      const ranked = view.data.districts.slice().sort((left, right) =>
        (worstOf(right) - worstOf(left)) || String(left.district).localeCompare(String(right.district)));
      const header = (view.data.districts[0].days || []).map(day => ({ key: day.day, label: 'Day ' + day.day, date: day.date_utc }));
      const matrixCard = WG.block('District \u00d7 day matrix',
        'The published product as a grid. A cell shows the colour the source printed for that district-day; focus one to read its hazard wording verbatim.');
      matrixCard.append(viz.warningMatrix({
        title: 'Colour printed per district-day',
        days: header,
        rows: ranked.slice(0, 60),
        onOpen: row => openDistrict(row),
        footnote: 'Showing the ' + Math.min(60, ranked.length) + ' district(s) with the strongest published colour first, then by name. The table below lists every district. A cell is a colour, not a verdict: the product publishes district-day guidance and this page never turns it into an all-clear.'
      }));
      matrixCard.append(WG.limitationList(view));
      host.append(matrixCard);
    }
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
    briefButton.addEventListener('click', () => {
      const W = window.WG;
      if (W && W.briefDrawers) W.briefDrawers.alert(W, place, 1);
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
    // One row renderer for both station reads: the nearby cards and the single-network inventory
    // read the same governed rows and must not drift apart.
    function stationRow(station) {
      const name = el('span', station.name || station.station_code || 'unnamed station');
      const stateChip = station.stale === true ? WG.chip('stale', 'is-stale')
        : station.stale === false ? WG.chip('current', 'is-current') : WG.chip('no instant', 'is-unknown');
      return [name, station.distance_km + ' km',
              station.observed_at_utc ? istStamp(station.observed_at_utc) : (station.observed_date_utc || 'not supplied'),
              station.age_minutes === null ? '\u2014' : station.age_minutes + ' min', stateChip];
    }

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
            card.append(WG.table(['Station', 'Distance', 'Observed', 'Age', 'State'], stations.map(stationRow)));
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

    // The layer inventory: one network at a time, the same governed route, a wider radius and a
    // longer list. The layer's own station count is printed beside the list so a longer list can
    // never read as better coverage.
    const networkCard = WG.block('Station network inventory',
      'One network at a time, wider than the nearby cards above. The count is the layer\u2019s own station count, not a coverage claim.');
    const networkControls = el('div', undefined, 'controls');
    const kindSelect = el('select');
    kindSelect.setAttribute('aria-label', 'Station network to list');
    [['metar', 'Airport reports (METAR)'], ['aws', 'Automatic weather stations (AWS)']].forEach(pair => {
      const option = el('option', pair[1]); option.value = pair[0]; kindSelect.append(option);
    });
    const networkRadius = el('select');
    networkRadius.setAttribute('aria-label', 'Station network search radius in kilometres');
    [50, 150, 300, 600].forEach(value => {
      const option = el('option', value + ' km'); option.value = String(value); if (value === 600) option.selected = true;
      networkRadius.append(option);
    });
    const networkLimit = el('select');
    networkLimit.setAttribute('aria-label', 'Stations to list');
    [10, 25, 50].forEach(value => {
      const option = el('option', 'up to ' + value + ' stations'); option.value = String(value); if (value === 25) option.selected = true;
      networkLimit.append(option);
    });
    const networkRefresh = el('button', 'Refresh from the source', 'ghost');
    networkRefresh.type = 'button';
    networkControls.append(kindSelect, networkRadius, networkLimit, networkRefresh);
    networkCard.append(networkControls);
    const networkHost = el('div');
    networkCard.append(networkHost);
    host.append(networkCard);

    async function paintNetwork(force) {
      WG.clear(networkHost);
      networkHost.append(WG.loading('Reading the station network\u2026'));
      try {
        const view = await WGref.api('/api/observations/network', placeQuery(WGref, {
          kind: kindSelect.value, radius_km: networkRadius.value, limit: networkLimit.value, refresh: force ? '1' : '' }));
        WG.clear(networkHost);
        const stations = view.data.stations || [];
        const coverage = view.coverage || {};
        networkHost.append(el('p', (coverage.stations_in_layer === undefined ? 'The layer did not state its station count'
          : 'The layer carries ' + coverage.stations_in_layer + ' station(s)') + ' \u00b7 ' + stations.length +
          ' listed inside ' + networkRadius.value + ' km for ' + kindSelect.value.toUpperCase() + '.', 'block-note'));
        if (!stations.length) {
          networkHost.append(WG.stateBlock('plain',
            'No ' + kindSelect.value.toUpperCase() + ' station reported inside ' + networkRadius.value +
            ' km of this place. That means none is connected at this radius, not that no weather occurred.'));
        } else {
          networkHost.append(WG.table(['Station', 'Distance', 'Observed', 'Age', 'State'], stations.map(stationRow)));
        }
        if (view.data.rejected && view.data.rejected.length) {
          networkHost.append(el('p', view.data.rejected.length + ' feature(s) were rejected by the reader and are not listed: ' +
            view.data.rejected.map(rejected => rejected.reason).join('; '), 'field-note'));
        }
        networkHost.append(WG.limitationList(view));
        networkHost.append(WG.sourceDisclosure(view));
      } catch (error) {
        WG.clear(networkHost);
        networkHost.append(WG.stateBlock('error', error.message));
      }
    }

    // The radar board is the network reporting on itself. Status codes and remarks are shown as
    // published and are never read as rainfall, a nowcast or a warning.
    const radarCard = WG.block('Radar network status',
      'The national radar layer reporting on itself. A status code is shown verbatim; it is not rainfall, a nowcast or a warning.');
    const radarControls = el('div', undefined, 'controls');
    const radarRefresh = el('button', 'Refresh from the source', 'ghost');
    radarRefresh.type = 'button';
    radarControls.append(radarRefresh);
    radarCard.append(radarControls);
    const radarHost = el('div');
    radarCard.append(radarHost);
    host.append(radarCard);

    async function paintRadar(force) {
      WG.clear(radarHost);
      radarHost.append(WG.loading('Reading the radar layer\u2026'));
      try {
        const view = await WGref.api('/api/radar', { refresh: force ? '1' : '' });
        WG.clear(radarHost);
        const data = view.data || {};
        const stations = data.stations || [];
        if (!stations.length) {
          radarHost.append(WG.stateBlock('plain',
            'The radar layer returned no station. That is not a statement about radar coverage or about rainfall.'));
        } else {
          radarHost.append(el('p', stations.length + ' station(s) in the layer \u00b7 ' +
            (data.reported === undefined ? 'a status count the layer did not state' : data.reported + ' report a status') + ' \u00b7 ' +
            (data.not_reported === undefined ? 'the rest unknown' : data.not_reported + ' do not') + '.', 'block-note'));
          radarHost.append(WG.table(['Station', 'Code', 'Status as published', 'Source remarks', 'Last updated'],
            stations.map(station => [
              station.name || station.code || 'unnamed station',
              station.code || '\u2014',
              station.status === null || station.status === undefined || station.status === '' ? 'not reported' : String(station.status),
              station.remarks || '\u2014',
              [station.last_updated_date, station.last_updated_time].filter(Boolean).join(' ') || 'not stated'])));
        }
        if (data.rejected && data.rejected.length) {
          radarHost.append(el('p', data.rejected.length + ' feature(s) were rejected by the reader and are not listed: ' +
            data.rejected.map(rejected => rejected.reason).join('; '), 'field-note'));
        }
        radarHost.append(WG.limitationList(view));
        radarHost.append(WG.sourceDisclosure(view));
      } catch (error) {
        WG.clear(radarHost);
        radarHost.append(WG.stateBlock('error', error.message));
      }
    }

    [kindSelect, networkRadius, networkLimit].forEach(node => node.addEventListener('change', () => paintNetwork(false)));
    networkRefresh.addEventListener('click', () => paintNetwork(true));
    radarRefresh.addEventListener('click', () => paintRadar(true));
    await Promise.all([paintNetwork(false), paintRadar(false)]);
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
      const meteogram = meteogramFor(view.data.parameters);
      if (meteogram) host2.append(meteogram);
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
      WGref.state.surfaceContexts = WGref.state.surfaceContexts || {};
      WGref.state.surfaceContexts.climate = { question: 'Show the annual rainfall trend for ' + districtSelect.value + ' district, ' + stateSelect.value + ' from ' + fromInput.value + ' to ' + toInput.value + '.', summary: districtSelect.value + ', ' + stateSelect.value };
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
            WGref.prepareQuestion('What does the district agromet bulletin say for ' + (district.label || district.id) + ', ' + stateSelect.value + '?', 'Farm advisories · ' + (district.label || district.id) + ', ' + stateSelect.value);
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
    input.setAttribute('aria-label', 'Airport ICAO code');
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
      WGref.state.surfaceContexts = WGref.state.surfaceContexts || {};
      WGref.state.surfaceContexts.aviation = { question: 'Show the latest ' + kindSelect.value.toUpperCase() + ' for ' + input.value.trim().toUpperCase() + ' and explain it.', summary: input.value.trim().toUpperCase() };
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
    // The published sub-basin layer is national, so it is listed independently of the point above.
    // The layer does not document what its day fields mean, so they are shown exactly as published
    // and no flood class, severity or warning level is derived from them.
    const basinsCard = WG.block('River sub-basins (national layer)',
      'The source\u2019s own sub-basin list with its own day fields, kept verbatim. The meaning of a day field is not documented by the layer.');
    const basinsControls = el('div', undefined, 'controls');
    const basinsFilter = el('input', undefined, 'palette-input');
    basinsFilter.setAttribute('aria-label', 'Filter sub-basins by name');
    basinsFilter.placeholder = 'Filter by sub-basin or basin name';
    const basinsRefresh = el('button', 'Refresh from the source', 'ghost');
    basinsRefresh.type = 'button';
    basinsControls.append(basinsFilter, basinsRefresh);
    basinsCard.append(basinsControls);
    const basinsHost = el('div');
    basinsCard.append(basinsHost);
    host.append(basinsCard);
    let basinsView = null;
    const SHOWN_BASINS = 25;

    function paintBasins() {
      WG.clear(basinsHost);
      const view = basinsView;
      const rows = (view && view.data && view.data.basins) || [];
      if (!rows.length) {
        basinsHost.append(WG.stateBlock('plain',
          'The sub-basin layer returned no sub-basin. That is not a statement about river levels anywhere.'));
      } else {
        const needle = String(basinsFilter.value || '').trim().toLowerCase();
        const matching = rows.filter(row => !needle ||
          String(row.name || '').toLowerCase().indexOf(needle) >= 0 ||
          String(row.basin || '').toLowerCase().indexOf(needle) >= 0);
        const shown = matching.slice(0, SHOWN_BASINS);
        basinsHost.append(el('p', matching.length + ' of ' + rows.length + ' sub-basin(s) match' +
          (needle ? ' "' + basinsFilter.value + '"' : '') + '; showing ' + shown.length + '. ' +
          'The layer states ' + ((view.data.with_day_fields === undefined) ? 'no count of' : view.data.with_day_fields) +
          ' sub-basin(s) carrying day fields.', 'block-note'));
        if (!shown.length) {
          basinsHost.append(WG.stateBlock('plain', 'No sub-basin name matches that filter. The layer is unchanged; only this list is filtered.'));
        } else {
          const cell = (row, key) => {
            const value = (row.day_fields || {})[key];
            return (value === null || value === undefined || value === '') ? 'not stated' : String(value);
          };
          basinsHost.append(WG.table(['Sub-basin', 'Basin', 'Area (km\u00b2)', 'Field office', 'Day 1', 'Day 2', 'Day 3'],
            shown.map(row => [row.name || 'unnamed sub-basin', row.basin || '\u2014', row.area_sqkm || 'not stated',
                              row.fmo || '\u2014', cell(row, 'day1'), cell(row, 'day2'), cell(row, 'day3')])));
        }
        if (view.data.rejected && view.data.rejected.length) {
          basinsHost.append(el('p', view.data.rejected.length + ' feature(s) were rejected by the reader and are not listed: ' +
            view.data.rejected.map(rejected => rejected.reason).join('; '), 'field-note'));
        }
        basinsHost.append(WG.limitationList(view));
        basinsHost.append(WG.sourceDisclosure(view));
      }
    }

    async function loadBasins(force) {
      WG.clear(basinsHost);
      basinsHost.append(WG.loading('Reading the sub-basin layer\u2026'));
      try {
        basinsView = await WGref.api('/api/basins', { refresh: force ? '1' : '' });
        paintBasins();
      } catch (error) {
        WG.clear(basinsHost);
        basinsHost.append(WG.stateBlock('error', error.message));
      }
    }

    basinsFilter.addEventListener('input', paintBasins);
    basinsRefresh.addEventListener('click', () => loadBasins(true));
    await loadBasins(false);
    host.append(WG.disclosure('Why neither of these is an official marine or flood product', body => {
      const list = el('ul', undefined, 'notes');
      ['A wave height is model output for a sea grid cell, not an official sea-area bulletin and not a measured buoy observation.',
       'A discharge value is modeled volume flow, not an observed water level, a gauge reading, a danger level, an inundation extent or an official flood warning.',
       'No tide, current or sea-surface temperature is retrieved here.'].forEach(note => list.append(el('li', note)));
      body.append(list);
    }));
  };

  WG.panels['air-quality'] = async function (host, WGref) {
    const card = WG.block('Modelled air quality',
      'CAMS modelled concentrations and the source\u2019s own indices at a grid cell. Not a monitor measurement, not a health assessment and not an official warning.');
    const controls = el('div', undefined, 'controls');
    const daysSelect = el('select');
    daysSelect.setAttribute('aria-label', 'Air-quality days to retrieve');
    [1, 2, 3].forEach(value => {
      const option = el('option', value + ' day' + (value > 1 ? 's' : '')); option.value = String(value);
      if (value === 1) option.selected = true; daysSelect.append(option);
    });
    const parameterSelect = el('select');
    parameterSelect.setAttribute('aria-label', 'Air-quality parameter to plot');
    const refresh = el('button', 'Refresh from the source', 'ghost');
    refresh.type = 'button';
    controls.append(daysSelect, parameterSelect, refresh);
    card.append(controls);
    const host2 = el('div');
    card.append(host2);
    host.append(card);
    let view = null;

    function paint() {
      WG.clear(host2);
      const parameters = (view.data && view.data.parameters) || {};
      const names = Object.keys(parameters);
      if (!names.length) {
        host2.append(WG.stateBlock('plain', 'No air-quality parameter was returned for this cell.', 'That is a missing reading, not clean air.'));
        return;
      }
      const chosen = parameters[parameterSelect.value] ? parameterSelect.value : names[0];
      const chart = seriesChart(parameters, chosen, chosen + ' \u00b7 ' + (parameters[chosen].unit || 'unit not stated'));
      if (chart) host2.append(chart);
      const current = (view.data && view.data.current) || {};
      const rows = names.filter(name => current[name] !== undefined && current[name] !== null)
        .map(name => [name, String(current[name]), parameters[name].unit || 'not stated by the source']);
      if (rows.length) {
        host2.append(el('p', 'The source\u2019s own current instant, kept apart from this window:', 'field-note'));
        host2.append(WG.table(['Parameter', 'Value at the source current hour', 'Unit'], rows));
      }
      const grid = view.data.grid;
      host2.append(el('p', 'Answering cell ' + (grid ? grid.latitude + ', ' + grid.longitude : 'not stated') +
        ' \u00b7 domain ' + (view.data.domain || 'not stated') + '.', 'block-note'));
      host2.append(WG.disclosure('Which values are concentrations and which are the source\u2019s own indices', body => {
        const list = el('ul', undefined, 'notes');
        const concentrations = names.filter(name => !/_aqi$/.test(name));
        const indices = names.filter(name => /_aqi$/.test(name));
        ['Concentrations are modelled mass per volume in the source\u2019s own units: ' + (concentrations.join(', ') || 'none returned') + '.',
         'Indices are the source\u2019s own scale: ' + (indices.join(', ') || 'none returned') + '. An index is not a concentration, and neither is a health assessment.',
         'No ground monitor, no health advice, no protective action, no risk score and no official air-quality warning is produced here.'].forEach(note => list.append(el('li', note)));
        body.append(list);
      }));
      host2.append(WG.limitationList(view));
      host2.append(WG.sourceDisclosure(view));
    }

    async function load(force) {
      WG.clear(host2);
      host2.append(WG.loading('Reading the air-quality model\u2026'));
      try {
        view = await WGref.api('/api/air-quality', placeQuery(WGref, { days: daysSelect.value, refresh: force ? '1' : '' }));
        WGref.state.freshness = WG.freshness(view);
        const names = Object.keys((view.data && view.data.parameters) || {});
        const previous = parameterSelect.value;
        WG.clear(parameterSelect);
        names.forEach(name => { const option = el('option', name); option.value = name; parameterSelect.append(option); });
        if (names.indexOf(previous) >= 0) parameterSelect.value = previous;
        paint();
      } catch (error) {
        WG.clear(host2);
        host2.append(WG.stateBlock('error', error.message));
      }
    }

    daysSelect.addEventListener('change', () => load(false));
    parameterSelect.addEventListener('change', paint);
    refresh.addEventListener('click', () => load(true));
    await load(false);
  };
  WG.panels.ensemble = async function (host, WGref) {
    const card = WG.block('Ensemble spread',
      'One model\u2019s returned members at a grid cell: mean, population spread, range and nearest-rank p10/p50/p90. Spread is not a probability, confidence, risk or skill measure.');
    const controls = el('div', undefined, 'controls');
    const variableSelect = el('select');
    variableSelect.setAttribute('aria-label', 'Ensemble variable');
    [['temperature_2m', 'Temperature'], ['precipitation', 'Precipitation'], ['wind_speed_10m', 'Wind speed']].forEach(pair => {
      const option = el(pair[1]); option.value = pair[0]; variableSelect.append(option);
    });
    const modelSelect = el('select');
    modelSelect.setAttribute('aria-label', 'Ensemble model');
    ['gfs025', 'ecmwf_ifs025', 'icon_seamless'].forEach(name => { const option = el(name); option.value = name; modelSelect.append(option); });
    const daysSelect = el('select');
    daysSelect.setAttribute('aria-label', 'Ensemble days to retrieve');
    [1, 2, 3].forEach(value => {
      const option = el('option', value + ' day' + (value > 1 ? 's' : '')); option.value = String(value);
      if (value === 1) option.selected = true; daysSelect.append(option);
    });
    const refresh = el('button', 'Refresh from the source', 'ghost');
    refresh.type = 'button';
    controls.append(variableSelect, modelSelect, daysSelect, refresh);
    card.append(controls);
    const host2 = el('div');
    card.append(host2);
    host.append(card);
    let view = null;
    const KINDS = ['mean', 'spread', 'min', 'max', 'p10', 'p50', 'p90', 'control'];

    function paint() {
      WG.clear(host2);
      const data = view.data || {};
      const parameters = data.parameters || {};
      const names = Object.keys(parameters);
      if (!names.length) {
        host2.append(WG.stateBlock('plain', 'No ensemble member series was returned for this cell.', 'That is a missing reading, not a calm forecast.'));
        return;
      }
      const families = Array.from(new Set(names.map(name => name.replace(new RegExp('_(' + KINDS.join('|') + ')$'), ''))));
      const chosen = families.indexOf(variableSelect.value) >= 0 ? variableSelect.value : (families[0] || '');
      const members = (data.member_total || {})[chosen];
      host2.append(el('p', 'Model ' + (data.model || 'not stated') + ' \u00b7 ' +
        (members === undefined ? 'member count not stated for this variable' : members + ' member(s) returned') +
        ' \u00b7 nearest-rank percentiles on the sorted members.', 'block-note'));
      const pointsOf = key => ((parameters[key] || {}).points || []).map(point => ({
        t: point.t, label: istStamp(point.t), value: point.v, source_locator: point.source_locator }));
      const fanSeries = ['p10', 'p50', 'p90', 'mean', 'min', 'max'].some(kind => parameters[chosen + '_' + kind]);
      if (fanSeries && typeof viz !== 'undefined' && viz.ensembleFan) {
        const unit = ((parameters[chosen + '_p50'] || parameters[chosen + '_mean'] || {}).unit) || '';
        host2.append(viz.ensembleFan({
          title: chosen.replace(/_/g, ' ') + ' member distribution \u00b7 ' + (data.model || 'model not stated'),
          note: 'The returned members as a distribution: the shaded band is p10 to p90, the heavy line the median, the thin whiskers min to max. Spread is not a probability or a skill score.',
          unit: unit,
          p10: pointsOf(chosen + '_p10'), p50: pointsOf(chosen + '_p50'), p90: pointsOf(chosen + '_p90'),
          mean: pointsOf(chosen + '_mean'), min: pointsOf(chosen + '_min'), max: pointsOf(chosen + '_max'),
          member_total: members, statistics: data.statistics
        }));
      }
      let drawn = 0;
      KINDS.forEach(kind => {
        const key = chosen + '_' + kind;
        if (!parameters[key]) return;
        const chart = seriesChart(parameters, key, chosen + ' ' + kind + ' \u00b7 ' + (parameters[key].unit || 'unit not stated'));
        if (chart) { host2.append(chart); drawn += 1; }
      });
      if (!drawn) {
        host2.append(el('p', 'The source returned member statistics for another variable; choose one of: ' +
          families.join(', ') + '.', 'field-note'));
      }
      const statistics = data.statistics || {};
      const definitions = Object.keys(statistics);
      if (definitions.length) {
        host2.append(WG.disclosure('How each statistic is computed', body => {
          body.append(WG.table(['Statistic', 'Method as computed'], definitions.map(key => [key, statistics[key]])));
        }));
      }
      const grid = data.grid;
      host2.append(el('p', 'Answering cell ' + (grid ? grid.latitude + ', ' + grid.longitude : 'not stated') +
        (data.grid_distance_km !== undefined ? ' \u00b7 ' + data.grid_distance_km + ' km from the requested point' : '') + '.', 'block-note'));
      host2.append(WG.limitationList(view));
      host2.append(WG.sourceDisclosure(view));
    }

    async function load(force) {
      WG.clear(host2);
      host2.append(WG.loading('Reading the ensemble members\u2026'));
      try {
        view = await WGref.api('/api/ensemble', placeQuery(WGref, { variable: variableSelect.value, model: modelSelect.value, days: daysSelect.value, refresh: force ? '1' : '' }));
        WGref.state.freshness = WG.freshness(view);
        paint();
      } catch (error) {
        WG.clear(host2);
        host2.append(WG.stateBlock('error', error.message));
      }
    }

    [variableSelect, modelSelect, daysSelect].forEach(node => node.addEventListener('change', () => load(false)));
    refresh.addEventListener('click', () => load(true));
    await load(false);
  };
  // The published corpus gets a front door of its own. Every column is a state the intake already
  // measured: a printed issue date, the retrieval instant, the passage count and whether the saved
  // body is still held. A stored document is the record of one edition, never a current warning and
  // never a claim that it applies to a place or a decision.
  WG.panels.documents = async function (host, WGref) {
    const card = WG.block('Published documents',
      'What this machine has indexed, one row per edition. The printed issue date is not a current warning and a stored passage is not applicability.');
    const summary = el('p', undefined, 'block-note');
    summary.textContent = 'Reading the local corpus index\u2026';
    const controls = el('div', undefined, 'controls');
    const familySelect = el('select');
    familySelect.setAttribute('aria-label', 'Document family');
    const filter = el('input', undefined, 'palette-input');
    filter.setAttribute('aria-label', 'Filter published documents');
    filter.placeholder = 'Filter by region, state or district';
    const limitSelect = el('select');
    limitSelect.setAttribute('aria-label', 'Documents to list');
    [25, 50, 100].forEach(value => {
      const option = el('option', 'up to ' + value + ' documents'); option.value = String(value);
      if (value === 50) option.selected = true;
      limitSelect.append(option);
    });
    const refresh = el('button', 'Refresh from the source', 'ghost');
    refresh.type = 'button';
    controls.append(familySelect, filter, limitSelect, refresh);
    card.append(summary, controls);
    const resultHost = el('div');
    card.append(resultHost);
    host.append(card);
    const BODY_LABELS = { available: 'body held', pruned: 'body pruned', unknown: 'body location unrecorded' };
    const BODY_CLASSES = { available: 'is-current', pruned: 'is-stale', unknown: 'is-unknown' };
    let view = null;
    let familiesBuilt = false;

    /* One edition in detail: the drawer is a record of what this machine holds, with the saved file
       offered only when the body is still inside the retention window. */
    function openDocument(document) {
      WG.openDrawer(document.family_label || document.family || 'Published document', body => {
        body.append(el('p', (document.region || document.district || document.state || 'region not stated') +
          ' \u00b7 printed issue ' + (document.issue_date || 'not stated') +
          ' \u00b7 retrieved ' + (document.retrieved_at_utc ? istStamp(document.retrieved_at_utc) : 'not recorded'), 'block-note'));
        body.append(WG.table(['Field', 'Value'], [
          ['Document sha256', document.sha256],
          ['Family', document.family_label || document.family || 'not stated'],
          ['Scope', document.scope || 'not stated'],
          ['Source', document.source_id || 'not stated'],
          ['Address', document.address || 'not stated'],
          ['Pages', document.pages === null || document.pages === undefined ? 'not stated' : String(document.pages)],
          ['Passages', String(document.passages || 0)],
          ['Currency', (document.age_days === null || document.age_days === undefined)
            ? (document.currency_recorded_at_intake || 'unknown')
            : document.age_days + ' day(s) after the printed issue date'],
          ['Saved body', document.body === 'available' ? 'held' : (document.body === 'pruned' ? 'pruned: only the hash, pages and passages remain' : 'location unrecorded')],
          ['Quarantined passages', String(document.quarantined_passages || 0)]
        ]));
        if (document.body === 'available') {
          const links = el('p');
          const open = el('a', 'Open the saved PDF');
          open.href = '/api/documents/' + document.sha256; open.target = '_blank'; open.rel = 'noopener noreferrer';
          const download = el('a', 'Download');
          download.href = '/api/documents/' + document.sha256; download.download = 'source-' + document.sha_prefix + '.pdf';
          links.append(open, el('span', ' \u00b7 ', 'field-note'), download);
          body.append(links);
        } else {
          body.append(el('p', document.body === 'pruned'
            ? 'The saved body is outside the local retention window. The hash, the extracted pages and the passages remain indexed and citable, which is why this edition is still listed.'
            : 'No saved-body location is recorded for this edition, so no file can be offered.', 'field-note'));
        }
        body.append(el('p', 'A stored document is the record of one printed edition: not a current warning, not an all-clear and not a statement that it applies to a place or a decision.', 'field-note'));
      });
    }
    function buildFamilies(families) {
      if (familiesBuilt) return;
      const all = el('option', 'Every family'); all.value = ''; familySelect.append(all);
      (families || []).forEach(entry => {
        const option = el('option', entry.label + ' (' + entry.documents + ')');
        option.value = entry.family; familySelect.append(option);
      });
      familiesBuilt = true;
    }

    function savedFile(document) {
      const open = el('a', 'Open the saved PDF');
      open.href = '/api/documents/' + document.sha256;
      open.target = '_blank'; open.rel = 'noopener noreferrer';
      const download = el('a', 'Download');
      download.href = '/api/documents/' + document.sha256;
      download.download = 'source-' + document.sha_prefix + '.pdf';
      const wrap = el('span');
      wrap.append(open, el('span', ' \u00b7 ', 'field-note'), download);
      return wrap;
    }

    function paint() {
      WG.clear(resultHost);
      const data = view.data || {};
      const counts = data.counts || {};
      const documents = data.documents || [];
      buildFamilies(data.families);
      summary.textContent = (counts.documents || 0) + ' document(s) \u00b7 ' + (counts.passages || 0) + ' passage(s) \u00b7 ' +
        (data.families || []).length + ' family(ies) \u00b7 ' + (counts.regions || 0) + ' region(s) \u00b7 ' +
        (counts.bodies_available || 0) + ' with a saved body, ' + (counts.pruned || 0) + ' pruned \u00b7 ' +
        (counts.documents_without_a_printed_issue_date || 0) + ' without a printed issue date.';
      if (view.status !== 'ok' || !documents.length) {
        resultHost.append(WG.stateBlock('plain', data.reason || 'No published document is indexed here.',
          'The local corpus is built by scripts/ingest_documents.py; this page reads the index and downloads nothing.'));
        if (view.limitations) resultHost.append(WG.limitationList(view));
        return;
      }
      if (typeof viz !== 'undefined' && viz.libraryCards) {
        resultHost.append(viz.libraryCards({
          title: 'The library',
          note: 'The editions on this page as cards: what it is, when it was printed, how much text it carries and whether the saved body is still held.',
          documents: documents.slice(0, 24),
          onOpen: document => openDocument(document)
        }));
      }
      resultHost.append(WG.table(['Family', 'Region', 'Printed issue', 'Retrieved', 'Pages', 'Passages', 'Currency', 'Saved body', 'Source file'],
        documents.map(document => {
          const region = document.region || [document.district, document.state].filter(Boolean).join(', ') || 'not stated';
          const currency = (document.age_days === null || document.age_days === undefined)
            ? (document.currency_recorded_at_intake || 'unknown')
            : document.age_days + ' day(s) after the printed issue date';
          const body = WG.chip(BODY_LABELS[document.body] || 'body state unrecorded', BODY_CLASSES[document.body] || 'is-unknown');
          return [document.family_label || document.family, region,
                  document.issue_date || 'not stated',
                  document.retrieved_at_utc ? istStamp(document.retrieved_at_utc) : 'not recorded',
                  (document.pages === null || document.pages === undefined) ? '\u2014' : String(document.pages),
                  String(document.passages || 0), currency, body,
                  document.body === 'available' ? savedFile(document) : el('span', 'not held', 'field-note')];
        })));
      documents.slice(0, 20).forEach(document => {
        resultHost.append(WG.disclosure('Provenance \u00b7 ' + (document.family_label || document.family) + ' \u00b7 ' + (document.sha_prefix || ''), body => {
          body.append(WG.table(['Field', 'Value'], [
            ['Document sha256', document.sha256],
            ['Source', document.source_id || 'not stated'],
            ['Address', document.address || 'not stated'],
            ['Retrieved', document.retrieved_at_utc || 'not recorded'],
            ['Checked', document.checked_at_utc || 'not recorded'],
            ['Language', document.language || 'not stated'],
            ['Scope', document.scope || 'not stated'],
            ['Physical pages', (document.first_page === null || document.first_page === undefined) ? 'not stated' : document.first_page + ' to ' + document.last_page],
            ['Extraction status', document.extraction_status || 'not stated'],
            ['Quarantined passages', String(document.quarantined_passages || 0)],
          ]));
          if (document.quarantined_passages) body.append(el('p', 'A quarantined passage is counted here and is never served as evidence.', 'field-note'));
        }));
      });
      resultHost.append(WG.limitationList(view));
      resultHost.append(WG.sourceDisclosure(view));
    }

    async function load(force) {
      WG.clear(resultHost);
      resultHost.append(WG.loading('Reading the published corpus\u2026'));
      try {
        view = await WGref.api('/api/corpus', { family: familySelect.value, q: filter.value, limit: limitSelect.value, refresh: force ? '1' : '' });
        WGref.state.freshness = WG.freshness(view);
        paint();
      } catch (error) {
        WG.clear(resultHost);
        summary.textContent = 'The corpus index could not be read.';
        resultHost.append(WG.stateBlock('error', error.message));
      }
    }

    refresh.addEventListener('click', () => load(true));
    familySelect.addEventListener('change', () => load(false));
    limitSelect.addEventListener('change', () => load(false));
    filter.addEventListener('change', () => load(false));
    await load(false);
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

    /* Which model answers, what it may spend, and where the key goes: the page states it rather
       than leaving the reader to read a config file. Nothing here prints or stores the key. */
    const provider = (view.data && view.data.provider) || null;
    if (provider) {
      const card = WG.block('Model providers',
        provider.openrouter.configured
          ? 'OpenRouter is configured; only free-tier model ids are routed, most capable first.'
          : 'No OpenRouter key is configured yet. The rules floor and any local model still answer.');
      card.append(WG.table(['Provider', 'State', 'Detail'], [
        ['Rules floor', 'always available', String((provider.rules_floor || {}).model || 'rule-planner') + ' — ' + String((provider.rules_floor || {}).detail || '')],
        ['OpenRouter', provider.openrouter.configured ? 'configured' : 'not configured',
          'key source: ' + String(provider.openrouter.key_source || 'not configured') + ' · ' + String((provider.openrouter.routing_order || []).length) + ' free model id(s) ranked'],
        ['Key handling', 'local only', String(provider.key_note || '')]
      ]));
      if ((provider.openrouter.routing_order || []).length) {
        card.append(el('p', 'Free models, most capable first (a workload judgement, not a provider statement)', 'field-label'));
        const order = el('ol', undefined, 'notes');
        (provider.openrouter.routing_order || []).forEach(model => order.append(el('li', String(model))));
        card.append(order);
      }
      if ((provider.openrouter.refused || []).length) {
        const refused = el('ul', undefined, 'notes');
        (provider.openrouter.refused || []).forEach(item => refused.append(el('li', String(item.model_id || 'an id') + ' — ' + String(item.reason || 'refused'))));
        card.append(el('p', 'Refused, and why (a paid id is never routed)', 'field-label'));
        card.append(refused);
      }
      card.append(el('p', 'To provide a key, run this on the machine that serves this workspace, then restart the server:', 'field-note'));
      card.append(el('pre', String(provider.set_key_command || 'python3 scripts/models.py --set-key'), 'brief-markdown'));
      card.append(el('p', 'To measure what the account can actually reach, with the key configured:', 'field-note'));
      card.append(el('pre', String(provider.probe_command || 'python3 scripts/models.py --probe-free'), 'brief-markdown'));
      card.append(el('p', String((provider.openrouter || {}).note || ''), 'field-note'));
      host.append(card);
    }

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
    const briefingTools = el('div', undefined, 'brief-tools');
    const writeBriefing = el('button', 'Write a briefing for the working place', 'ghost');
    writeBriefing.type = 'button';
    writeBriefing.setAttribute('aria-label', 'Compose a briefing for the working place and write it into the local series');
    writeBriefing.addEventListener('click', () => { const W = window.WG; if (W && W.briefDrawers) W.briefDrawers.briefing(W, null); });
    briefingTools.append(writeBriefing);
    block.append(briefingTools);

    block.append(el('p', view.note || 'Nothing kept here is delivered or pushed.', 'block-note'));
    if (!entries.length) {
      block.append(WGref.stateBlock('plain', 'Nothing is kept yet.',
        'Open Warnings and write the alert brief for the working place, then keep it here. A brief is composed from its sources by the server: this page cannot save a brief the workspace did not compose.'));
    }
    if (entries.length) {
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
    }
    host.append(block);
    /* The briefing series is a local file series, not a service. The page reads the newest run
       and says plainly when nothing has run yet, rather than showing an empty panel. */
    try {
      const briefing = await WGref.api('/api/briefing/latest');
      const block = WGref.block('Latest briefing on this machine',
        briefing.present ? ('Run ' + String((briefing.run || {}).generated_at_utc || 'instant not recorded') +
                            ' · ' + String((briefing.run || {}).place_count || 0) + ' place(s) · change since the previous run: ' +
                            String((briefing.run || {}).change || 'not recorded'))
                          : 'No briefing has been written to this workspace yet');
      block.append(el('p', 'A briefing reads the connected products for named places at the instant it ran: the official district warning day, the CAP relay kept separate, and the forecast window as retrieved. It is not a warning, not an all-clear and not advice.', 'block-note'));
      if (briefing.present) {
        const run = briefing.run || {};
        block.append(WGref.table(['Field', 'Value', 'Provenance'], [
          ['Run instant', run.generated_at_utc, run.runner_note || 'written by scripts/briefing.py'],
          ['Briefing identity', 'sha256 ' + String(run.briefing_id || '').slice(0, 16), 'the content hash of this briefing'],
          ['Places read', String(run.place_count), (run.sources || []).join(', ') || 'no source identifiers recorded'],
          ['Official day', 'day ' + String(run.day_number) + ' of the published product', 'forecast days retrieved: ' + String(run.forecast_days)],
          ['Interval', run.interval_seconds ? String(run.interval_seconds) + ' s between runs in that invocation' : 'a single run', 'a foreground interval, not a service'],
          ['Latency', run.latency_seconds === null || run.latency_seconds === undefined ? 'not recorded' : String(run.latency_seconds) + ' s', 'measured for this run only'],
          ['Written to', run.record_path || 'path not recorded', run.markdown_path || '']
        ]));
        if ((briefing.series || []).length > 1) {
          const list = el('ul', undefined, 'notes');
          briefing.series.slice().reverse().forEach(item => list.append(el('li', 'run ' + String(item.run) + ' · ' + String(item.generated_at_utc) +
            ' · ' + String(item.place_count) + ' place(s) · ' + String(item.latency_seconds) + ' s · change: ' + String(item.change))));
          block.append(el('p', 'Runs in this series', 'field-label'));
          block.append(list);
        }
        if (briefing.markdown) {
          block.append(WGref.disclosure('Read the briefing as written', body => body.append(el('pre', briefing.markdown, 'brief-markdown'))));
        }
        const limits = el('ul', undefined, 'notes');
        (((briefing.briefing || {}).not_established) || []).forEach(limit => limits.append(el('li', limit)));
        if (limits.childNodes.length) { block.append(el('p', 'What this briefing says is not established', 'field-label')); block.append(limits); }
      } else {
        block.append(WGref.stateBlock('plain', 'Nothing has been scheduled or delivered.', briefing.detail || 'No briefing record was found in this workspace series directory.'));
      }
      host.append(block);
    } catch (error) {
      host.append(WGref.block('Latest briefing on this machine', 'This view could not be read from the workspace: ' + String(error.message || error)));
    }
  };


  /* ---------- briefs and the right-now reading, as drawers any surface can open ---------- */
  /* The warnings panel composed the alert brief inside its own renderer, so the conversation
     could not offer the same artefact. These live here and take the working place, so the chat
     actions, the warnings surface and the briefcase all open the same composition. */
  function workingPlace(WGref) {
    const place = (WGref && WGref.state && WGref.state.place) || {};
    return { label: place.label || 'the working place', latitude: place.latitude, longitude: place.longitude };
  }
  function saveToBriefcase(WGref, kind, params, body, note) {
    const tools = el('div', undefined, 'brief-tools');
    const save = el('button', 'Save to briefcase', 'ghost');
    save.type = 'button';
    save.setAttribute('aria-label', 'Keep this brief in the local briefcase');
    save.addEventListener('click', () => {
      save.disabled = true;
      save.textContent = 'Saving…';
      WGref.post('/api/briefs/save', Object.assign({ kind: kind }, params || {}))
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
    tools.append(save);
    if (note) tools.append(el('span', note, 'field-note'));
    return tools;
  }
  WG.alertBriefDrawer = function (WGref, place, day) {
    const where = place || workingPlace(WGref);
    if (where.latitude === undefined || where.longitude === undefined) {
      WGref.openDrawer('Alert brief', body => body.append(el('p', 'Choose a working place first: a brief is composed for one point, and the workspace will not guess which.', 'field-note')));
      return;
    }
    const chosenDay = day || 1;
    WGref.openDrawer('Alert brief · ' + (where.label || 'selected point'), body => {
      body.append(el('p', 'Composing from the official district warning product and the CAP relay, reported separately…', 'field-note'));
      WGref.api('/api/warnings/alert-brief', { lat: where.latitude, lon: where.longitude, day: chosenDay }).then(view => {
        const brief = view.data || {};
        WGref.clear(body);
        body.append(el('p', brief.status_line || brief.why || 'No brief was composed.', 'block-note'));
        body.append(WGref.table(['Field', 'Value', 'Provenance'], [
          ['District', (brief.place || {}).district || 'not stated', (brief.place || {}).state || ''],
          ['Day', (brief.day || {}).label || 'not stated', (brief.day || {}).starts_utc ? (brief.day.starts_utc + ' to ' + brief.day.ends_utc) : ''],
          ['Hazards as published', ((brief.day_status || {}).hazards || []).join(', ') || 'none listed', (brief.day_status || {}).official_wording || (brief.day_status || {}).wording_note || ''],
          ['Issuer', (brief.issuer || {}).source_id + ' · ' + (brief.issuer || {}).product, 'issued ' + ((brief.issuer || {}).issued_at_utc || 'not stated') + ' · retrieved ' + ((brief.issuer || {}).retrieved_at_utc || 'not stated')],
          ['CAP relay (separate)', ((brief.relay || {}).source_id || 'S06') + ' · ' + ((brief.relay || {}).messages === undefined ? 'not read' : brief.relay.messages + ' message(s)'), (brief.relay || {}).note || ''],
          ['Brief identity', 'sha256 ' + String(brief.brief_id || '').slice(0, 16), 'the content hash of this brief']
        ]));
        const limits = el('ul', undefined, 'notes');
        (brief.not_established || []).forEach(item => limits.append(el('li', item)));
        body.append(el('p', 'What is not established here', 'field-label'));
        body.append(limits);
        body.append(saveToBriefcase(WGref, 'alert_brief', { lat: where.latitude, lon: where.longitude, day: chosenDay }, body));
        body.append(el('p', 'A brief records what a product published. It is not a warning issued here, not a forecast and not an all-clear.', 'field-note'));
      }).catch(error => {
        WGref.clear(body);
        body.append(el('p', 'The brief could not be composed: ' + String(error.message || error), 'block-note'));
      });
    });
  };
  WG.advisoryBriefDrawer = function (WGref, params) {
    const request = params || {};
    if (!request.region) {
      WGref.openDrawer('Advisory brief', body => body.append(el('p', 'A published advisory is read for a named district or region. Ask about a district first, or name one.', 'field-note')));
      return;
    }
    WGref.openDrawer('Advisory brief · ' + String(request.region) + (request.crop ? ' · ' + String(request.crop) : ''), body => {
      body.append(el('p', 'Composing from the indexed published advice, with the model forecast kept apart as context…', 'field-note'));
      WGref.api('/api/advisories/brief', request).then(brief => {
        WGref.clear(body);
        const region = String(((brief.published_advice || {}).region) || request.region);
        body.append(el('p', brief.status === 'ok'
          ? ('Published advice for ' + region + ' quoted below, with the model forecast kept apart as context.')
          : String(brief.why || brief.status_line || 'No brief was composed.'), 'block-note'));
        if (brief.forecast_status) body.append(el('p', 'Forecast context: ' + String(brief.forecast_status), 'field-note'));
        if ((brief.conditions_named_by_the_source || []).length) {
          const conditions = el('ul', undefined, 'notes');
          (brief.conditions_named_by_the_source || []).forEach(item => conditions.append(el('li', String(item))));
          body.append(el('p', 'Conditions the source itself names', 'field-label'));
          body.append(conditions);
        }
        if (brief.published_advice) {
          body.append(WGref.table(['Field', 'Value', 'Provenance'], [
            ['Edition read', brief.published_advice.family + ' (' + brief.published_advice.scope + ')', String(brief.published_advice.region || '')],
            ['Passages quoted', String((brief.published_advice.passages || []).length), 'each with its page and printed issue date'],
            ['Forecast context', ((brief.forecast || {}).status || 'not retrieved'), (brief.forecast || {}).note || 'context, never instruction'],
            ['Sources named', (brief.sources || []).join(', ') || 'none named', 'source identifiers as stored']
          ]));
        }
        const notes = el('ul', undefined, 'notes');
        (brief.notes || []).forEach(note => notes.append(el('li', note)));
        if (notes.childNodes.length) { body.append(el('p', 'What this brief discloses', 'field-label')); body.append(notes); }
        const limits = el('ul', undefined, 'notes');
        (brief.not_established || []).forEach(item => limits.append(el('li', item)));
        if (limits.childNodes.length) { body.append(el('p', 'What is not established here', 'field-label')); body.append(limits); }
        if (brief.status === 'ok') body.append(saveToBriefcase(WGref, 'advisory_brief', request, body));
        body.append(el('p', 'Published advice is written for a district and a season; it is not a prescription for one field, and no dose, diagnosis or go/no-go decision is made here.', 'field-note'));
      }).catch(error => {
        WGref.clear(body);
        body.append(el('p', 'The advisory brief could not be composed: ' + String(error.message || error), 'block-note'));
      });
    });
  };
  WG.nowDrawer = function (WGref, place) {
    const where = place || workingPlace(WGref);
    if (where.latitude === undefined || where.longitude === undefined) {
      WGref.openDrawer('Right now', body => body.append(el('p', 'Choose a working place first: observations are read for a point.', 'field-note')));
      return;
    }
    WGref.openDrawer('Right now · ' + (where.label || 'selected point'), body => {
      body.append(el('p', 'Reading the station layers, the published district day and the model hours…', 'field-note'));
      WGref.api('/api/now', { lat: where.latitude, lon: where.longitude }).then(view => {
        const now = view.data || {};
        WGref.clear(body);
        const stations = ((now.observed || {}).stations) || [];
        if (stations.length) {
          body.append(WGref.table(['Station', 'Network', 'Distance', 'Reported', 'Age'], stations.map(station => [station.name || station.station_code || 'station', String(station.network || '').toUpperCase(), station.distance_km === null || station.distance_km === undefined ? 'not stated' : String(Math.round(station.distance_km * 100) / 100) + ' km', station.observed_at_utc || 'not stated', station.age_minutes === null || station.age_minutes === undefined ? 'not stated' : String(Math.round(station.age_minutes)) + ' min'])));
        } else {
          body.append(el('p', 'No station in the connected METAR or AWS layers reported within 150 km. That is an absence of station evidence, not a statement that nothing is happening.', 'block-note'));
        }
        const day = now.in_force || {};
        if (day.status === 'ok') {
          const line = el('p', undefined, 'block-note');
          line.append(WGref.colourChip(day.colour || 'unknown', day.colour || 'colour not supplied'));
          line.append(el('span', ' ' + String(day.status_line || '')));
          body.append(line);
        }
        const rows = ((now.next_hours || {}).rows) || [];
        if (rows.length) {
          body.append(el('p', 'Model hours next (' + String((now.next_hours || {}).source_id || 'source not stated') + ')', 'field-label'));
          body.append(WGref.table(['Hour', 'Temperature', 'Rain chance'], rows.map(row => [row.at, row.temperature_2m === undefined ? 'not returned' : row.temperature_2m + ' °C', row.precipitation_probability === undefined ? 'not returned' : row.precipitation_probability + ' %'])));
        }
        body.append(el('p', 'Not connected here: ' + ((now.not_connected || []).join('; ') || 'nothing listed') + '.', 'field-note'));
        body.append(el('p', now.summary || '', 'block-note'));
      }).catch(error => {
        WGref.clear(body);
        body.append(el('p', 'The right-now reading could not be read: ' + String(error.message || error), 'block-note'));
      });
    });
  };
  WG.writeBriefing = function (WGref, place) {
    const where = place || workingPlace(WGref);
    if (where.latitude === undefined || where.longitude === undefined) {
      WGref.openDrawer('Briefing', body => body.append(el('p', 'Choose a working place first: a briefing is composed for a point.', 'field-note')));
      return;
    }
    WGref.openDrawer('Briefing · ' + (where.label || 'selected point'), body => {
      body.append(el('p', 'Composing a briefing and writing it into this machine’s series…', 'field-note'));
      WGref.post('/api/briefing/run', { lat: where.latitude, lon: where.longitude, label: where.label, hours: 6 })
        .then(result => {
          WGref.clear(body);
          const entry = result.entry || {};
          body.append(WGref.table(['Field', 'Value', 'Provenance'], [
            ['Run', 'run ' + String(entry.run) + ' at ' + String(entry.generated_at_utc), 'a foreground run: nothing is scheduled'],
            ['Briefing identity', 'sha256 ' + String(entry.briefing_id || '').slice(0, 16), 'the content hash of this briefing'],
            ['Places', String(entry.place_count), 'named place(s)'],
            ['Change since the previous run', String(entry.change), 'read against the previous run record'],
            ['Latency', String(entry.latency_seconds) + ' s', 'measured for this run only'],
            ['Written to', String(entry.record_path), String(entry.markdown_path)]
          ]));
          body.append(el('p', result.note || '', 'field-note'));
          const uses = el('div', undefined, 'brief-tools');
          const open = el('button', 'Read the briefing', 'ghost');
          open.type = 'button';
          open.addEventListener('click', () => { WGref.closeDrawer(); window.location.hash = '#/briefcase'; });
          const download = el('button', 'Export Markdown', 'ghost');
          download.type = 'button';
          download.addEventListener('click', () => WGref.download('briefing-' + String(entry.generated_at_utc || '').replace(/[^0-9]/g, '').slice(0, 12) + '.md', result.markdown || '', 'text/markdown'));
          uses.append(open, download);
          body.append(uses);
          if (typeof WGref.render === 'function') WGref.render();
        })
        .catch(error => {
          WGref.clear(body);
          body.append(el('p', 'The briefing could not be composed: ' + String(error.message || error), 'block-note'));
        });
    });
  };
  /* Exposed for the surfaces that offer them: the warnings panel, the chat actions and the briefcase. */
  WG.briefDrawers = { alert: WG.alertBriefDrawer, advisory: WG.advisoryBriefDrawer, now: WG.nowDrawer, briefing: WG.writeBriefing, workingPlace: workingPlace };
  WG.panels.assistant = async function () { /* the conversation is owned by app.js */ };
})();
