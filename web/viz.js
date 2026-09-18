'use strict';
/* Chart engine v2 — signature visualisations for an evidence-first instrument.
   ============================================================================
   The chart language has four rules, and every primitive here obeys them:
   1. A mark exists only where the engine returned a value. A missing hour splits a line,
      leaves a bar out and stays a gap in the readout — nothing is interpolated or zero-filled.
   2. Every drawn point carries its source_locator into the exact-value readout and table.
   3. Model output and member statistics are drawn with the viz tokens; hazard colour is
      never used here, because a spread or a probability is not a warning.
   4. The drawing is the summary; the exact source values are always one disclosure away.
   ========================================================================== */
(function (global) {
  const NS = 'http://www.w3.org/2000/svg';
  const VIEW = { width: 660, height: 320 };
  const PAD = { left: 58, right: 16, top: 24, bottom: 28 };

  function make(tag, text, cls) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  }

  function svgChild(svg, name, attrs, text) {
    const child = document.createElementNS(NS, name);
    Object.keys(attrs || {}).forEach(key => child.setAttribute(key, String(attrs[key])));
    if (text !== undefined) child.textContent = text;
    return svg.append(child) || child;
  }

  function number(value) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function series(key, title, unit, points) {
    return { key: key, title: title, unit: unit || '', points: (points || []).map(point => ({
      x: point.x === undefined ? Date.parse(point.t) : point.x,
      label: point.label === undefined ? point.t : point.label,
      value: number(point.value),
      raw: point.value,
      evidence_id: point.evidence_id || point.source_locator || ''
    })).filter(point => Number.isFinite(point.x)) };
  }

  /* Contiguous runs of present values: the only shape a line or a band may take. */
  function runs(points) {
    const out = [];
    let current = [];
    points.forEach(point => {
      if (point.value === null) { if (current.length) out.push(current); current = []; return; }
      if (current.length && point.x - current[current.length - 1].x > stepOf(points) * 1.5) {
        out.push(current); current = [];
      }
      current.push(point);
    });
    if (current.length) out.push(current);
    return out;
  }

  function stepOf(points) {
    if (points.length < 2) return 0;
    const gaps = [];
    for (let index = 1; index < points.length; index += 1) gaps.push(points[index].x - points[index - 1].x);
    gaps.sort((left, right) => left - right);
    return gaps[Math.floor(gaps.length / 2)] || 0;
  }

  function extentOf(lists, key) {
    const values = [];
    lists.forEach(list => (list.points || list).forEach(point => {
      const value = number(point.value);
      if (value !== null) values.push(value);
    }));
    if (!values.length) return null;
    let low = Math.min(...values);
    let high = Math.max(...values);
    if (key === 'rain') low = Math.min(0, low);
    if (high === low) { low -= 1; high += 1; }
    return { low: low, high: high };
  }

  function ticks(low, high, count) {
    const out = [];
    for (let index = 0; index <= count; index += 1) out.push(low + (high - low) * (index / count));
    return out;
  }

  function format(value) {
    if (value === null) return 'missing';
    if (Math.abs(value) >= 100) return String(Math.round(value));
    if (Math.abs(value) >= 10) return value.toFixed(1).replace(/\.0$/, '');
    return value.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
  }

  function frame(title, note) {
    const box = make('section', undefined, 'viz');
    box.append(make('h3', title, 'viz-title'));
    if (note) box.append(make('p', note, 'viz-note'));
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + VIEW.width + ' ' + VIEW.height);
    svg.setAttribute('role', 'group');
    svg.setAttribute('aria-label', title);
    svg.setAttribute('class', 'viz-frame');
    svg.addEventListener('mousemove', event => {
      const rect = svg.getBoundingClientRect ? svg.getBoundingClientRect() : null;
      if (!rect || !rect.width) return;
      const ratio = (event.clientX - rect.left) / rect.width;
      const x = (ratio * VIEW.width - PAD.left) / (VIEW.width - PAD.left - PAD.right);
      if (box.dataset) box.dataset.hover = String(x);
      if (typeof box.onHover === 'function') box.onHover(x);
    });
    return { box: box, svg: svg };
  }

  function axis(svg, low, high, toY, unit) {
    ticks(low, high, 4).forEach(value => {
      svgChild(svg, 'line', { x1: PAD.left, x2: VIEW.width - PAD.right, y1: toY(value), y2: toY(value), 'class': 'viz-grid' });
      svgChild(svg, 'text', { x: PAD.left - 8, y: toY(value) + 4, 'text-anchor': 'end', 'class': 'viz-axis' }, format(value));
    });
    svgChild(svg, 'text', { x: PAD.left, y: 14, 'class': 'viz-unit' }, unit);
  }

  function timeAxis(svg, points, toX) {
    if (!points.length) return;
    const at = [points[0], points[Math.floor(points.length / 2)], points[points.length - 1]];
    at.forEach((point, index) => {
      svgChild(svg, 'text', { x: toX(point.x), y: VIEW.height - 8, 'class': 'viz-axis',
                              'text-anchor': index === 0 ? 'start' : (index === at.length - 1 ? 'end' : 'middle') }, point.label);
    });
  }

  function readout(box, label) {
    const line = make('p', label || 'Hover or focus a mark to read its exact source value.', 'viz-readout');
    line.setAttribute('aria-live', 'polite');
    box.append(line);
    return line;
  }

  function exactTable(box, headers, rows, summary) {
    const detail = make('details', undefined, 'viz-values');
    detail.append(make('summary', summary || 'Exact values and evidence'));
    const table = make('table');
    const head = make('tr');
    headers.forEach(name => { const cell = make('th', name); cell.scope = 'col'; head.append(cell); });
    table.append(head);
    rows.forEach(values => {
      const row = make('tr');
      values.forEach(value => row.append(make('td', value === null || value === undefined ? 'missing' : String(value))));
      table.append(row);
    });
    detail.append(table);
    box.append(detail);
    return detail;
  }

  /* ---- ensemble plume ----------------------------------------------------- */
  function ensembleFan(chart) {
    const band = { low: series('p10', 'p10', chart.unit, chart.p10), high: series('p90', 'p90', chart.unit, chart.p90) };
    const median = series('p50', 'median', chart.unit, chart.p50);
    const mean = series('mean', 'mean', chart.unit, chart.mean);
    const floor = series('min', 'min', chart.unit, chart.min);
    const ceiling = series('max', 'max', chart.unit, chart.max);
    const support = median.points.length ? median.points : band.high.points;
    const added = [band.low, band.high, median, mean, floor, ceiling];
    const box = frame(chart.title || 'Ensemble spread', chart.note ||
      'The returned members as a distribution: the shaded band is p10 to p90, the heavy line the median, the thin whiskers min to max. Spread is not a probability or a skill score.');
    const legend = make('p', undefined, 'viz-legend');
    [['band', 'p10–p90'], ['median', 'median (p50)'], ['mean', 'mean'], ['whisker', 'min–max']].forEach(pair => {
      const item = make('span', undefined, 'viz-legend-item');
      item.append(make('i', undefined, 'viz-swatch is-' + pair[0]));
      item.append(make('span', pair[1]));
      legend.append(item);
    });
    box.box.append(legend);
    box.box.append(box.svg);
    const scale = extentOf(added, 'spread');
    if (!scale || !support.length) {
      box.box.append(make('p', 'No member statistics were returned for this window, so there is nothing to draw.', 'viz-empty'));
      return box.box;
    }
    const first = support[0].x, last = support[support.length - 1].x;
    const toX = value => PAD.left + (value - first) / Math.max(1, last - first) * (VIEW.width - PAD.left - PAD.right);
    const toY = value => VIEW.height - PAD.bottom - (value - scale.low) / (scale.high - scale.low) * (VIEW.height - PAD.top - PAD.bottom);
    axis(box.svg, scale.low, scale.high, toY, chart.unit || '');
    timeAxis(box.svg, support, toX);
    /* The band, drawn only across contiguous pairs of present values. */
    runs(band.low.points.map((point, index) => ({ x: point.x, label: point.label, value: point.value,
        high: (band.high.points[index] || {}).value, evidence_id: point.evidence_id })))
      .forEach(run => {
        const usable = run.filter(point => point.value !== null && number(point.high) !== null);
        if (usable.length < 2) return;
        const upper = usable.map(point => toX(point.x) + ',' + toY(number(point.high))).join(' ');
        const lower = usable.slice().reverse().map(point => toX(point.x) + ',' + toY(point.value)).join(' ');
        svgChild(box.svg, 'polygon', { points: upper + ' ' + lower, 'class': 'viz-band' });
        svgChild(box.svg, 'polyline', { points: usable.map(point => toX(point.x) + ',' + toY(number(point.high))).join(' '), 'class': 'viz-band-line' });
        svgChild(box.svg, 'polyline', { points: usable.map(point => toX(point.x) + ',' + toY(point.value)).join(' '), 'class': 'viz-band-line' });
      });
    /* min–max whiskers: one thin rule per hour where both ends are present. */
    floor.points.forEach((point, index) => {
      const top = number((ceiling.points[index] || {}).value);
      if (point.value === null || top === null) return;
      svgChild(box.svg, 'line', { x1: toX(point.x), x2: toX(point.x), y1: toY(top), y2: toY(point.value), 'class': 'viz-whisker' });
    });
    const draw = (seriesObject, className) => {
      runs(seriesObject.points).forEach(run => {
        if (className === 'viz-mean') return;
        if (run.length > 1) svgChild(box.svg, 'polyline', { points: run.map(point => toX(point.x) + ',' + toY(point.value)).join(' '), 'class': className });
      });
    };
    draw(median, 'viz-median');
    runs(mean.points).forEach(run => {
      if (run.length > 1) svgChild(box.svg, 'polyline', { points: run.map(point => toX(point.x) + ',' + toY(point.value)).join(' '), 'class': 'viz-mean' });
    });
    const line = readout(box.box);
    /* Focusable hours: keyboard and pointer reach the same numbers. */
    support.slice(0, 96).forEach((point, index) => {
      const hit = svgChild(box.svg, 'rect', { x: toX(point.x) - 6, y: PAD.top, width: 12, height: VIEW.height - PAD.top - PAD.bottom,
                                             'class': 'viz-hit', tabindex: 0, role: 'button' });
      const parts = [
        ['p10', (band.low.points[index] || {}).raw], ['median', (median.points[index] || {}).raw],
        ['p90', (band.high.points[index] || {}).raw], ['mean', (mean.points[index] || {}).raw],
        ['min', (floor.points[index] || {}).raw], ['max', (ceiling.points[index] || {}).raw]
      ].filter(pair => pair[1] !== null && pair[1] !== undefined);
      const text = point.label + ' · ' + (parts.length ? parts.map(pair => pair[0] + ' ' + pair[1]).join(' · ') : 'no member value') +
        (point.evidence_id ? ' · ' + point.evidence_id : '');
      hit.setAttribute('aria-label', text);
      const show = () => { line.textContent = text; };
      hit.addEventListener('focus', show);
      hit.addEventListener('mouseenter', show);
      hit.addEventListener('click', show);
      hit.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); show(); } });
    });
    const hours = support.length;
    exactTable(box.box,
      ['Hour (source label)', 'p10', 'median (p50)', 'p90', 'mean', 'min', 'max', 'Evidence'],
      support.map((point, index) => [point.label,
        (band.low.points[index] || {}).raw, (median.points[index] || {}).raw, (band.high.points[index] || {}).raw,
        (mean.points[index] || {}).raw, (floor.points[index] || {}).raw, (ceiling.points[index] || {}).raw,
        point.evidence_id || 'not recorded']),
      'Exact member statistics for all ' + hours + ' hour(s)');
    if (chart.member_total !== undefined) box.box.append(make('p', 'Members returned: ' + chart.member_total + '. ' +
      (chart.statistics ? Object.keys(chart.statistics).map(key => key + ': ' + chart.statistics[key]).join(' · ') : ''), 'viz-method'));
    return box.box;
  }

  /* ---- meteogram ---------------------------------------------------------- */
  function meteogram(chart) {
    const hours = (chart.hours || []).map(hour => ({
      x: Date.parse(hour.t),
      label: hour.label || hour.t,
      temperature: number(hour.temperature), rain: number(hour.rain),
      wind_speed: number(hour.wind_speed), wind_direction: number(hour.wind_direction),
      humidity: number(hour.humidity),
      evidence: hour.evidence || {},
      night: hour.night === true
    })).filter(hour => Number.isFinite(hour.x));
    const box = frame(chart.title || 'Meteogram', chart.note ||
      'Temperature, precipitation and wind on one time axis. A gap is a source gap: nothing is interpolated, and a zero bar is a returned zero.');
    if (!hours.length) {
      box.box.append(make('p', 'No hourly values were returned for this window, so there is nothing to draw.', 'viz-empty'));
      return box.box;
    }
    box.box.append(box.svg);
    const first = hours[0].x, last = hours[hours.length - 1].x;
    const toX = value => PAD.left + (value - first) / Math.max(1, last - first) * (VIEW.width - PAD.left - PAD.right);
    const panels = [
      { key: 'temperature', label: chart.temperature_unit || 'temperature', top: 30, height: 120 },
      { key: 'rain', label: chart.rain_unit || 'precipitation', top: 168, height: 58 },
      { key: 'wind_speed', label: chart.wind_unit || 'wind', top: 244, height: 44 }
    ];
    /* Day and night shading from the source timestamps, so an overnight gap is visible. */
    const stepPx = hours.length > 1 ? (VIEW.width - PAD.left - PAD.right) / (hours.length - 1) : 14;
    hours.forEach(hour => {
      if (!hour.night) return;
      svgChild(box.svg, 'rect', { x: Math.max(PAD.left, toX(hour.x) - stepPx / 2), y: PAD.top, width: stepPx,
                                  height: VIEW.height - PAD.top - PAD.bottom, 'class': 'viz-night' });
    });
    const temperature = series('temperature', 'Temperature', chart.temperature_unit, hours.map(hour => ({ x: hour.x, label: hour.label, value: hour.temperature, evidence_id: hour.evidence.temperature })));
    const rain = series('rain', 'Precipitation', chart.rain_unit, hours.map(hour => ({ x: hour.x, label: hour.label, value: hour.rain, evidence_id: hour.evidence.rain })));
    const wind = series('wind_speed', 'Wind speed', chart.wind_unit, hours.map(hour => ({ x: hour.x, label: hour.label, value: hour.wind_speed, evidence_id: hour.evidence.wind })));
    const scale = extentOf([temperature], null);
    panels.forEach(panel => {
      const range = panel.key === 'temperature' ? scale : extentOf([panel.key === 'rain' ? rain : wind], panel.key);
      if (!range) return;
      const toY = value => panel.top + panel.height - (value - range.low) / (range.high - range.low) * panel.height;
      svgChild(box.svg, 'line', { x1: PAD.left, x2: VIEW.width - PAD.right, y1: panel.top + panel.height, y2: panel.top + panel.height, 'class': 'viz-grid' });
      svgChild(box.svg, 'text', { x: PAD.left - 8, y: panel.top + 6, 'text-anchor': 'end', 'class': 'viz-axis' }, format(range.high));
      svgChild(box.svg, 'text', { x: PAD.left - 8, y: panel.top + panel.height, 'text-anchor': 'end', 'class': 'viz-axis' }, format(panel.key === 'rain' ? 0 : range.low));
      svgChild(box.svg, 'text', { x: PAD.left, y: panel.top - 4, 'class': 'viz-unit' }, panel.label);
      if (panel.key === 'temperature') {
        runs(temperature.points).forEach(run => {
          if (run.length > 1) svgChild(box.svg, 'polyline', { points: run.map(point => toX(point.x) + ',' + toY(point.value)).join(' '), 'class': 'viz-line' });
        });
      }
      if (panel.key === 'rain') {
        rain.points.forEach(point => {
          if (point.value === null || point.value <= 0) return;
          const width = Math.max(2, (VIEW.width - PAD.left - PAD.right) / Math.max(1, hours.length) - 2);
          svgChild(box.svg, 'rect', { x: toX(point.x) - width / 2, y: toY(point.value), width: width,
                                     height: Math.max(1, panel.top + panel.height - toY(point.value)), 'class': 'viz-bar' });
        });
      }
      if (panel.key === 'wind_speed') {
        wind.points.forEach((point, index) => {
          if (point.value === null || index % Math.max(1, Math.round(hours.length / 16)) !== 0) return;
          const direction = number(hours[index].wind_direction);
          const arrow = svgChild(box.svg, 'text', { x: toX(point.x), y: toY(point.value) + 4, 'text-anchor': 'middle',
                                                   'class': 'viz-arrow' }, direction === null ? '·' : '↑');
          if (direction !== null) arrow.setAttribute('transform', 'rotate(' + direction + ' ' + toX(point.x) + ' ' + (toY(point.value) + 4) + ')');
          arrow.setAttribute('aria-label', point.label + ' wind ' + point.value + ' ' + (panel.label === 'wind' ? '' : ''));
        });
      }
    });
    const line = readout(box.box);
    hours.slice(0, 96).forEach(hour => {
      const hit = svgChild(box.svg, 'rect', { x: toX(hour.x) - 5, y: PAD.top, width: 10, height: VIEW.height - PAD.top - PAD.bottom,
                                             'class': 'viz-hit', tabindex: 0, role: 'button' });
      const parts = [
        ['temperature', hour.temperature, hour.evidence.temperature],
        ['precipitation', hour.rain, hour.evidence.rain],
        ['wind', hour.wind_speed, hour.evidence.wind],
        ['humidity', hour.humidity, hour.evidence.humidity]
      ].filter(pair => pair[1] !== null && pair[1] !== undefined);
      const text = hour.label + ' · ' + (parts.length
        ? parts.map(pair => pair[0] + ' ' + pair[1] + (pair[2] ? ' (' + pair[2] + ')' : '')).join(' · ')
        : 'no value returned for this hour');
      hit.setAttribute('aria-label', text);
      const show = () => { line.textContent = text; };
      hit.addEventListener('focus', show);
      hit.addEventListener('mouseenter', show);
      hit.addEventListener('click', show);
      hit.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); show(); } });
    });
    timeAxis(box.svg, hours, toX);
    exactTable(box.box,
      ['Hour (source label)', 'Temperature', 'Precipitation', 'Wind speed', 'Humidity', 'Evidence'],
      hours.map(hour => [hour.label, hour.temperature, hour.rain, hour.wind_speed, hour.humidity,
                         [hour.evidence.temperature, hour.evidence.rain, hour.evidence.wind].filter(Boolean).join(' ') || 'not recorded']),
      'Exact hourly values for all ' + hours.length + ' hour(s)');
    return box.box;
  }


  /* ---- district × day warning matrix -------------------------------------- */
  /* The national product as a colour grid. Every cell is one district-day exactly as the source
     published it: the colour word the product printed, the hazard wording read verbatim in the
     readout, and an explicit state for a day that carried no colour or an unknown hazard code.
     The engine does not rank or score a district; the caller decides the row order and says how. */
  function warningMatrix(chart) {
    const days = chart.days || [];
    const rows = chart.rows || [];
    const box = make('section', undefined, 'viz viz-matrix-block');
    box.setAttribute('data-days', String(days.length));
    box.append(make('h3', chart.title || 'District warning matrix', 'viz-title'));
    box.append(make('p', chart.note ||
      'One row per district, one column per day of the published product. The cell shows the colour the source printed; the hazard wording is read verbatim when a cell is focused.', 'viz-note'));
    const readoutLine = make('p', 'Focus a cell to read its district, day, colour and hazard wording.', 'viz-readout');
    readoutLine.setAttribute('aria-live', 'polite');
    box.append(readoutLine);
    const grid = make('div', undefined, 'viz-matrix');
    grid.setAttribute('role', 'table');
    grid.setAttribute('aria-label', chart.title || 'District warning matrix');
    const head = make('div', undefined, 'viz-matrix-row is-head');
    head.setAttribute('role', 'row');
    const corner = make('span', chart.corner || 'District', 'viz-matrix-corner');
    corner.setAttribute('role', 'columnheader');
    head.append(corner);
    days.forEach(day => {
      const cell = make('span', day.label || String(day.key || ''), 'viz-matrix-head');
      cell.setAttribute('role', 'columnheader');
      cell.setAttribute('title', day.date || day.label || '');
      head.append(cell);
    });
    grid.append(head);
    rows.forEach(row => {
      const line = make('div', undefined, 'viz-matrix-row');
      line.setAttribute('role', 'row');
      const name = make('span', (row.district || 'district not stated') + (row.state ? ' · ' + row.state : ' · state not stated'), 'viz-matrix-name');
      name.setAttribute('role', 'rowheader');
      line.append(name);
      days.forEach((day, index) => {
        const entry = (row.days || [])[index] || {};
        const known = ['red', 'orange', 'yellow', 'green'].indexOf(entry.colour) >= 0;
        const unknown = (entry.unknown_hazard_codes || []).length > 0;
        const cell = make('button', known ? String(entry.colour).toUpperCase() : 'NOT STATED',
          'viz-cell ' + (known ? 'is-' + entry.colour : 'is-unknown') + (unknown ? ' is-unverified' : ''));
        cell.type = 'button';
        /* The cell role belongs to a wrapper, not to the button: a button does not allow role=cell
           (measured 18 September 2026, axe reported aria-allowed-role on every matrix cell). The wrapper
           is display:contents, so the grid layout and the keyboard behaviour are unchanged. */
        const holder = make('div', undefined, 'viz-cell-holder');
        holder.setAttribute('role', 'cell');
        const hazard = entry.source_text || (entry.hazards && entry.hazards.length ? entry.hazards.join(', ') : '');
        const label = (row.district || 'district not stated') + (row.state ? ', ' + row.state : '') +
          ' · ' + (day.label || ('Day ' + (index + 1))) + (day.date ? ' (' + day.date + ')' : '') +
          ' · ' + (known ? 'colour ' + entry.colour : 'no colour stated by the product') +
          (hazard ? ' · ' + hazard : ' · no hazard wording printed') +
          (unknown ? ' · contains an unknown hazard code' : '');
        cell.setAttribute('aria-label', label);
        cell.append(make('span', known ? String(entry.colour).toUpperCase() : 'NOT STATED', 'viz-cell-word'));
        const show = () => { readoutLine.textContent = label; };
        cell.addEventListener('focus', show);
        cell.addEventListener('mouseenter', show);
        if (typeof chart.onOpen === 'function') {
          cell.addEventListener('click', () => chart.onOpen(row, index));
        }
        holder.append(cell);
        line.append(holder);
      });
      grid.append(line);
    });
    box.append(grid);
    if (chart.footnote) box.append(make('p', chart.footnote, 'viz-method'));
    exactTable(box,
      ['District', 'State'].concat(days.map(day => day.label || String(day.key || ''))),
      rows.map(row => [row.district || 'district not stated', row.state || 'state not stated']
        .concat(days.map((day, index) => {
          const entry = (row.days || [])[index] || {};
          const hazard = entry.source_text || (entry.hazards && entry.hazards.length ? entry.hazards.join(', ') : 'no hazard wording printed');
          return (entry.colour || 'not stated') + ' — ' + hazard;
        }))),
      'Every shown district-day as text (' + (rows.length * days.length) + ' cell(s))');
    return box;
  }

  /* ---- corpus library cards ------------------------------------------------ */
  /* Each indexed edition as a card: what it is, when it was printed, how much text it carries and
     whether the saved body is still held. The card never implies the edition still applies to
     anything — that is the corpus's own stated limit, printed on every card's rail. */
  function libraryCards(chart) {
    const documents = chart.documents || [];
    const box = make('section', undefined, 'viz viz-library');
    box.append(make('h3', chart.title || 'The library', 'viz-title'));
    box.append(make('p', chart.note ||
      'Every edition this machine has indexed. A stored document is the record of one printed edition, never a current warning.', 'viz-note'));
    const grid = make('div', undefined, 'viz-cards');
    documents.forEach(document => {
      const card = make('article', undefined, 'viz-card');
      const rail = make('div', undefined, 'viz-card-rail');
      rail.append(make('span', document.family_label || document.family || 'family not stated', 'viz-card-family'));
      rail.append(make('span', document.scope || 'scope not stated', 'viz-card-scope'));
      card.append(rail);
      const bodyState = document.body || 'unknown';
      const chip = make('span', bodyState === 'available' ? 'body held' : (bodyState === 'pruned' ? 'body pruned' : 'body location unrecorded'),
        'viz-card-chip is-' + bodyState);
      card.append(chip);
      const title = make('h4', document.region || document.district || document.state || 'region not stated', 'viz-card-title');
      const opener = make('button', document.region || document.district || document.state || 'region not stated', 'viz-card-open');
      opener.type = 'button';
      opener.setAttribute('aria-label', 'Open ' + (document.family_label || document.family) + ' for ' + (document.region || 'a region not stated'));
      if (typeof chart.onOpen === 'function') opener.addEventListener('click', () => chart.onOpen(document));
      else opener.disabled = true;
      title.textContent = '';
      title.append(opener);
      card.append(title);
      const facts = make('dl', undefined, 'viz-card-facts');
      [['Printed issue', document.issue_date || 'not stated'],
       ['Retrieved', document.retrieved_at_utc ? document.retrieved_at_utc.slice(0, 10) : 'not recorded'],
       ['Currency', (document.age_days === null || document.age_days === undefined)
          ? (document.currency_recorded_at_intake || 'unknown')
          : document.age_days + ' day(s) after the printed issue date'],
       ['Pages / passages', String(document.pages === null || document.pages === undefined ? 'not stated' : document.pages) + ' / ' + String(document.passages || 0)],
       ['Source', document.source_id || 'not stated']].forEach(pair => {
        facts.append(make('dt', pair[0], 'viz-card-key'));
        facts.append(make('dd', pair[1], 'viz-card-value'));
      });
      card.append(facts);
      if (bodyState === 'available') {
        const open = make('a', 'Open the saved PDF');
        open.href = '/api/documents/' + document.sha256;
        open.target = '_blank';
        open.rel = 'noopener noreferrer';
        const download = make('a', 'Download');
        download.href = '/api/documents/' + document.sha256;
        download.download = 'source-' + (document.sha_prefix || '') + '.pdf';
        const links = make('p', undefined, 'viz-card-links');
        links.append(open, make('span', ' \u00b7 ', 'field-note'), download);
        card.append(links);
      } else {
        card.append(make('p', bodyState === 'pruned'
          ? 'The saved body is outside the retention window; the hash, pages and passages above remain indexed and citable.'
          : 'No saved-body location is recorded for this edition, so no file is offered.', 'viz-card-note'));
      }
      grid.append(card);
    });
    box.append(grid);
    if (!documents.length) box.append(make('p', 'No edition is listed for this filter, so there is nothing to show.', 'viz-empty'));
    return box;
  }

  /* ---- the 'now' band ------------------------------------------------------ */
  /* One band, three lanes, three products kept apart: what a station observed, what the published
     district product says, and what the model holds next. A lane is drawn only from the timestamps
     the engine returned; an instant is a tick and a window is a span, and the read-at marker comes
     from the payload's own generated_at_utc rather than from the reader's clock. */
  function nowBand(chart) {
    const lanes = (chart.lanes || []).filter(lane => lane && lane.from);
    const box = make('section', undefined, 'viz viz-now');
    const head = make('div', undefined, 'viz-now-head');
    head.append(make('h3', chart.title || 'Right now', 'viz-title'));
    if (chart.place) head.append(make('span', chart.place, 'viz-now-place'));
    if (chart.read_at) head.append(make('span', 'read ' + chart.read_at.slice(11, 16) + ' UTC', 'viz-now-read'));
    box.append(head);
    if (chart.note) box.append(make('p', chart.note, 'viz-note'));
    if (!lanes.length) {
      box.append(make('p', 'No lane of this reading carried a timestamp, so there is nothing to place on the band.', 'viz-empty'));
      return box;
    }
    const starts = lanes.map(lane => Date.parse(lane.from));
    const ends = lanes.map(lane => Date.parse(lane.to || lane.from));
    const readAt = chart.read_at ? Date.parse(chart.read_at) : null;
    const first = Math.min.apply(null, starts.concat(readAt ? [readAt] : []));
    const last = Math.max.apply(null, ends.concat(readAt ? [readAt] : []));
    const width = 660, height = 132, pad = { left: 96, right: 18 };
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    svg.setAttribute('role', 'group');
    svg.setAttribute('class', 'viz-frame viz-now-frame');
    svg.setAttribute('aria-label', (chart.title || 'Right now') + ', lanes kept apart');
    const scale = at => pad.left + (at - first) / Math.max(1, last - first) * (width - pad.left - pad.right);
    const readoutLine = make('p', 'Focus a lane to read what it is and where it came from.', 'viz-readout');
    readoutLine.setAttribute('aria-live', 'polite');
    lanes.forEach((lane, index) => {
      const y = 26 + index * 30;
      const start = Date.parse(lane.from);
      const end = Date.parse(lane.to || lane.from);
      const span = end - start > 60 * 1000;
      // An SVG <text> must be created in the SVG namespace: an HTML element inside <svg> is
      // created but never painted, which the first live browser render showed plainly.
      svgChild(svg, 'text', { x: pad.left - 10, y: y + 4, 'text-anchor': 'end', 'class': 'viz-axis' }, lane.label || lane.key || 'lane');
      svgChild(svg, 'line', { x1: pad.left, x2: width - pad.right, y1: y + 14, y2: y + 14, 'class': 'viz-grid' });
      const colour = lane.colour && ['red', 'orange', 'yellow', 'green'].indexOf(lane.colour) >= 0 ? lane.colour : null;
      const mark = svgChild(svg, colour ? 'rect' : (span ? 'rect' : 'line'), colour || span ? {
        x: scale(start).toFixed(1), y: y - 2, width: Math.max(span ? 3 : 3, (scale(end) - scale(start))).toFixed(1), height: span ? 16 : 4,
        'class': 'viz-now-mark is-' + (colour || lane.kind || 'lane')
      } : {
        x1: scale(start).toFixed(1), x2: scale(start).toFixed(1), y1: y - 6, y2: y + 18,
        'class': 'viz-now-mark is-' + (lane.kind || 'lane')
      });
      const detail = [lane.detail, lane.source ? 'source ' + lane.source : 'source not stated'].filter(Boolean).join(' · ');
      const text = (lane.label || lane.key || 'lane') + ' · ' + (span
        ? fmt(fromIso(start)) + ' to ' + fmt(fromIso(end))
        : fmt(fromIso(start))) + (detail ? ' · ' + detail : '');
      mark.setAttribute('tabindex', 0);
      mark.setAttribute('role', 'button');
      mark.setAttribute('aria-label', text);
      const show = () => { readoutLine.textContent = text; };
      mark.addEventListener('focus', show);
      mark.addEventListener('mouseenter', show);
      mark.addEventListener('click', show);
      mark.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); show(); } });
    });
    if (readAt !== null && readAt >= first && readAt <= last) {
      svgChild(svg, 'line', { x1: scale(readAt).toFixed(1), x2: scale(readAt).toFixed(1), y1: 12, y2: height - 20, 'class': 'viz-now-readat' });
      svgChild(svg, 'text', { x: scale(readAt).toFixed(1), y: height - 8, 'text-anchor': 'middle', 'class': 'viz-axis' }, 'read at');
    }
    // The lanes are placed by timestamp, so the band has to say which timestamp each end is: without
    // it a reader cannot tell how far ahead the model hours reach.
    [first, (first + last) / 2, last].forEach((at, index) => {
      svgChild(svg, 'text', { x: scale(at).toFixed(1), y: height - 6, 'class': 'viz-axis',
                              'text-anchor': index === 0 ? 'start' : (index === 2 ? 'end' : 'middle') },
        fmt(fromIso(at)).slice(5, 16));
    });
    box.append(svg, readoutLine);
    exactTable(box, ['Lane', 'From', 'To', 'Detail', 'Source'],
      lanes.map(lane => [lane.label || lane.key || 'lane', fmt(fromIso(Date.parse(lane.from))),
        lane.to && Date.parse(lane.to) - Date.parse(lane.from) > 60000 ? fmt(fromIso(Date.parse(lane.to))) : 'an instant, not a window',
        lane.detail || 'no detail returned', lane.source || 'not stated']),
      'Every lane as text (' + lanes.length + ')');
    return box;
  }

  function fromIso(at) { return new Date(at).toISOString(); }

  function fmt(iso) {
    const at = Date.parse(iso);
    if (!Number.isFinite(at)) return 'not stated';
    return new Date(at).toISOString().replace('T', ' ').slice(0, 16) + 'Z';
  }

  /* ---- the unified day timeline -------------------------------------------- */
  /* One column per published day, overlaid with the model hours counted into the IST day their
     timestamp falls in and the station observation on the day it was reported. Day windows are the
     product's own IST calendar days, so this never invents a boundary; model hours are counted, and
     no value is combined across days. */
  function istClockText(iso) {
    const at = Date.parse(iso);
    if (!Number.isFinite(at)) return null;
    const shifted = new Date(at + 5.5 * 3600 * 1000);
    return String(shifted.getUTCHours()).padStart(2, '0') + ':' + String(shifted.getUTCMinutes()).padStart(2, '0');
  }

  function istDayKey(iso) {
    const at = Date.parse(iso);
    if (!Number.isFinite(at)) return null;
    return new Date(at + 5.5 * 3600 * 1000).toISOString().slice(0, 10);
  }

  function dayTimeline(chart) {
    const days = (chart.days || []).filter(day => day && day.date_utc);
    const hours = chart.hours || [];
    const observed = chart.observed || null;
    const box = make('section', undefined, 'viz viz-dayline');
    box.setAttribute('data-days', String(days.length));
    box.append(make('h3', chart.title || 'The published days', 'viz-title'));
    box.append(make('p', chart.note ||
      'One column per published day, with the model hours counted into the IST day their timestamp falls in. Day windows are the product own calendar days; no value is combined across days.', 'viz-note'));
    if (!days.length) {
      box.append(make('p', 'The district product returned no day for this place, so there is nothing to lay out.', 'viz-empty'));
      return box;
    }
    const hourCounts = {};
    hours.forEach(row => { const key = istDayKey(row.at || row.t); if (key) hourCounts[key] = (hourCounts[key] || 0) + 1; });
    const observedKey = observed && observed.at ? istDayKey(observed.at) : null;
    // Measured 15 September 2026: the district product's five rows all carry the bulletin date, and
    // the place read path returns no date at all. A repeated date is printed once, on the first day
    // that carries it; the following days say the source states no separate date rather than
    // repeating one date five times as though five days had been dated.
    const dateOccurrences = {};
    const firstIndexOfDate = {};
    days.forEach((day, index) => {
      dateOccurrences[day.date_utc] = (dateOccurrences[day.date_utc] || 0) + 1;
      if (firstIndexOfDate[day.date_utc] === undefined) firstIndexOfDate[day.date_utc] = index;
    });
    const datesRepeated = Object.keys(dateOccurrences).some(date => dateOccurrences[date] > 1);
    let observedPlaced = false;
    const readoutLine = make('p', 'Focus a day to read the colour, the hazard wording and the hours counted into it.', 'viz-readout');
    readoutLine.setAttribute('aria-live', 'polite');
    box.append(readoutLine);
    const grid = make('div', undefined, 'viz-daygrid');
    days.forEach((day, position) => {
      const known = ['red', 'orange', 'yellow', 'green'].indexOf(day.colour) >= 0;
      const hazard = day.source_text || (day.hazards && day.hazards.length ? day.hazards.join(', ') : '');
      const count = hourCounts[day.date_utc] || 0;
      const unknown = (day.unknown_hazard_codes || []).length > 0;
      const repeats = datesRepeated && dateOccurrences[day.date_utc] > 1;
      const showDate = !repeats || firstIndexOfDate[day.date_utc] === position;
      const dateText = day.label || day.date_utc || null;
      const headline = 'Day ' + day.day + ' \u00b7 ' + (showDate && dateText ? dateText : 'date not stated by the source');
      const column = make('button', undefined, 'viz-daycol ' + (known ? 'is-' + day.colour : 'is-unknown') + (unknown ? ' is-unverified' : ''));
      column.type = 'button';
      column.append(make('span', headline, 'viz-daycol-head'));
      column.append(make('span', known ? String(day.colour).toUpperCase() : 'NOT STATED', 'viz-daycol-colour'));
      column.append(make('span', hazard || 'no hazard wording printed', 'viz-daycol-hazard'));
      const meta = make('span', count + ' model hour(s) returned here', 'viz-daycol-meta');
      column.append(meta);
      if (day.starts_utc && day.ends_utc) {
        const opens = istClockText(day.starts_utc);
        const rawClose = istClockText(day.ends_utc);
        // A 24-hour IST day ends at the next midnight, which reads as 24:00 rather than 00:00.
        const closes = (opens === '00:00' && rawClose === '00:00') ? '24:00' : rawClose;
        if (opens && closes) column.append(make('span', 'IST window ' + opens + '\u2013' + closes + ' (derived from the bulletin date)', 'viz-daycol-window'));
      }
      if (day.is_today) column.append(make('span', 'today in IST', 'viz-daycol-today'));
      if (day.quiet) column.append(make('span', 'the product states no warning for this day', 'viz-daycol-quiet'));
      const observedDay = observedKey === day.date_utc && observed && !observedPlaced;
      if (observedDay) { column.append(make('span', (observed.label || 'station') + ' reported here', 'viz-daycol-observed')); observedPlaced = true; }
      if (unknown) column.append(make('span', 'contains an unknown hazard code', 'viz-daycol-flag'));
      const label = 'Day ' + day.day + ' (' + day.date_utc + ') \u00b7 ' + (known ? 'colour ' + day.colour : 'no colour stated by the product') +
        ' \u00b7 ' + (hazard || 'no hazard wording printed') + ' \u00b7 ' + count + ' model hour(s) returned in this IST day' +
        (observedDay ? ' \u00b7 ' + (observed.label || 'a station') + ' reported on this day' : '') +
        (unknown ? ' \u00b7 contains an unknown hazard code' : '');
      column.setAttribute('aria-label', label);
      const show = () => { readoutLine.textContent = label; };
      column.addEventListener('focus', show);
      column.addEventListener('mouseenter', show);
      column.addEventListener('click', show);
      grid.append(column);
    });
    box.append(grid);
    exactTable(box, ['Day', 'Date', 'Colour', 'Hazard wording', 'Model hours returned', 'Markers'],
      days.map(day => {
        const markers = [];
        if (day.quiet) markers.push('product states no warning');
        if (observedKey === day.date_utc && observed) markers.push((observed.label || 'station') + ' reported');
        if ((day.unknown_hazard_codes || []).length) markers.push('unknown hazard code');
        return [String(day.day), day.date_utc, day.colour || 'not stated',
                day.source_text || (day.hazards || []).join(', ') || 'no hazard wording printed',
                String(hourCounts[day.date_utc] || 0), markers.join(' \u00b7 ') || '\u2014'];
      }),
      'Every day as text (' + days.length + ')');
    if (chart.read_at) box.append(make('p', 'Read at ' + chart.read_at + '. Model hours are counted, never combined into a daily value here.', 'viz-method'));
    return box;
  }
  global.viz = { ensembleFan: ensembleFan, meteogram: meteogram, warningMatrix: warningMatrix, libraryCards: libraryCards, nowBand: nowBand, dayTimeline: dayTimeline };
  /* In a browser `window` is the global object; in a component harness it is a stand-in, so the
     API is attached to both and `viz` resolves the same way in either. */
  if (typeof globalThis !== 'undefined' && globalThis.viz !== global.viz) globalThis.viz = global.viz;
})(typeof window !== 'undefined' ? window : this);
