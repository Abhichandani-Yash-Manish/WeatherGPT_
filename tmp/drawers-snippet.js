
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
        body.append(el('p', brief.status_line || brief.why || 'No brief was composed.', 'block-note'));
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
        })
        .catch(error => {
          WGref.clear(body);
          body.append(el('p', 'The briefing could not be composed: ' + String(error.message || error), 'block-note'));
        });
    });
  };
  /* Exposed for the surfaces that offer them: the warnings panel, the chat actions and the briefcase. */
  WG.briefDrawers = { alert: WG.alertBriefDrawer, advisory: WG.advisoryBriefDrawer, now: WG.nowDrawer, briefing: WG.writeBriefing, workingPlace: workingPlace };
