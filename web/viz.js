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

  global.viz = { ensembleFan: ensembleFan, meteogram: meteogram };
  /* In a browser `window` is the global object; in a component harness it is a stand-in, so the
     API is attached to both and `viz` resolves the same way in either. */
  if (typeof globalThis !== 'undefined' && globalThis.viz !== global.viz) globalThis.viz = global.viz;
})(typeof window !== 'undefined' ? window : this);
