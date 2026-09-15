'use strict';
/* Vector map of the vendored official geometry.

   Equirectangular projection over the India window, one path per feature, pan and
   zoom by transform on a group, and a choropleth driven by the warning table the
   map surface has already read. Warning colour is applied here at render time and
   is never stored in the geometry. A district the warning table does not carry is
   drawn as unmapped and counted, never quietly painted green. */

(function () {
  const WG = window.WG;
  if (!WG) return;
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const WINDOW = { west: 67.0, east: 98.5, south: 5.0, north: 38.5 };
  const LAYERS = [
    { name: 'land', label: 'Land', kind: 'land' },
    { name: 'states', label: 'States', kind: 'states' },
    { name: 'basins', label: 'River sub-basins', kind: 'basins' },
    { name: 'coast-zones', label: 'Coastal zones', kind: 'coast' },
    { name: 'districts', label: 'District warnings', kind: 'districts' },
    { name: 'places', label: 'Cities', kind: 'places' }
  ];

  function node(name, attributes, text) {
    const element = document.createElementNS(SVG_NS, name);
    Object.keys(attributes || {}).forEach(key => element.setAttribute(key, String(attributes[key])));
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function ringPath(rings, project) {
    const parts = [];
    rings.forEach(ring => {
      ring.forEach((point, index) => {
        const projected = project(point[0], point[1]);
        parts.push((index === 0 ? 'M' : 'L') + projected[0].toFixed(2) + ' ' + projected[1].toFixed(2));
      });
      parts.push('Z');
    });
    return parts.join(' ');
  }

  function geometryPath(geometry, project) {
    if (!geometry) return '';
    if (geometry.type === 'Polygon') return ringPath(geometry.coordinates, project);
    if (geometry.type === 'MultiPolygon') return geometry.coordinates.map(polygon => ringPath(polygon, project)).join(' ');
    return '';
  }

  function geometryBounds(geometry, project) {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    const rings = geometry.type === 'Polygon' ? geometry.coordinates
      : geometry.type === 'MultiPolygon' ? geometry.coordinates.flat() : [];
    rings.forEach(ring => ring.forEach(point => {
      const projected = project(point[0], point[1]);
      minX = Math.min(minX, projected[0]); minY = Math.min(minY, projected[1]);
      maxX = Math.max(maxX, projected[0]); maxY = Math.max(maxY, projected[1]);
    }));
    return Number.isFinite(minX) ? [minX, minY, maxX, maxY] : null;
  }

  function render(options) {
    // keyboardKey is the one district in the tab order: a map with 756 districts must not
    // put 756 stops in the way, so the districts act like a grid with a roving tab stop.
    const state = { day: 1, layers: {}, transform: { k: 1, x: 0, y: 0 }, width: 900, height: 820,
                    keyboardKey: null, keyboardUsed: false };
    LAYERS.forEach(layer => { state.layers[layer.name] = layer.kind !== 'basins'; });
    const warningsByKey = {};
    (options.warnings || []).forEach(row => { warningsByKey[row.key] = row; });
    const rows = options.warnings || [];

    const wrapper = el('div', undefined, 'map-wrap');
    const toolbar = el('div', undefined, 'map-toolbar');
    const daySelect = el('select');
    daySelect.setAttribute('aria-label', 'Warning day shown on the map');
    for (let index = 1; index <= 5; index += 1) {
      const option = el('option', 'Day ' + index);
      option.value = String(index);
      daySelect.append(option);
    }
    const zoomIn = el('button', '+', 'chip-button');
    const zoomOut = el('button', '−', 'chip-button');
    const resetView = el('button', 'Reset view', 'chip-button');
    zoomIn.setAttribute('aria-label', 'Zoom in'); zoomOut.setAttribute('aria-label', 'Zoom out');
    [zoomIn, zoomOut, resetView].forEach(button => { button.type = 'button'; });
    const find = el('input');
    find.type = 'search'; find.id = 'map-find'; find.placeholder = 'Find a district'; find.setAttribute('aria-label', 'Find a district on the map');
    find.className = 'map-find';
    toolbar.append(el('span', 'Warning day', 'field-label'), daySelect, zoomOut, zoomIn, resetView, find);
    const legend = el('div', undefined, 'map-legend');
    [['red', 'red'], ['orange', 'orange'], ['yellow', 'yellow'], ['green', 'green'], ['unset', 'colour not supplied']].forEach(pair => {
      const item = el('span', undefined, 'legend-item');
      item.append(WG.colourChip(pair[0] === 'unset' ? null : pair[0], pair[1]));
      legend.append(item);
    });
    const toggles = el('div', undefined, 'map-toggles');
    LAYERS.forEach(layer => {
      const label = el('label', undefined, 'toggle');
      const box = el('input');
      box.type = 'checkbox';
      box.checked = state.layers[layer.name];
      box.addEventListener('change', () => { state.layers[layer.name] = box.checked; paintLayers(); });
      label.append(box, el('span', layer.label));
      toggles.append(label);
    });
    toolbar.append(toggles);
    wrapper.append(toolbar, legend);

    const frame = el('div', undefined, 'map-frame');
    const svg = node('svg', { viewBox: '0 0 ' + state.width + ' ' + state.height, role: 'group',
                              preserveAspectRatio: 'xMidYMid meet', 'aria-label': 'India district warning map' });
    svg.append(node('rect', { x: 0, y: 0, width: state.width, height: state.height, 'class': 'map-sea' }));
    const group = node('g');
    svg.append(group);
    frame.append(svg);
    wrapper.append(frame);

    const status = el('p', undefined, 'map-status');
    wrapper.append(status);
    wrapper.append(el('p', 'Keyboard: Tab reaches the map, arrow keys move between districts, Home and End jump to the first and last, and Enter opens the district the cursor is on. The find box selects a district by name.', 'field-note'));

    const project = (longitude, latitude) => {
      const x = (longitude - WINDOW.west) / (WINDOW.east - WINDOW.west) * state.width;
      const y = (WINDOW.north - latitude) / (WINDOW.north - WINDOW.south) * state.height;
      return [x, y];
    };
    function applyTransform() {
      group.setAttribute('transform', 'translate(' + state.transform.x + ' ' + state.transform.y + ') scale(' + state.transform.k + ')');
    }

    const loaded = {};
    const groups = {};
    LAYERS.forEach(layer => {
      const holder = node('g', { 'class': 'map-layer layer-' + layer.kind });
      groups[layer.name] = holder;
      group.append(holder);
    });

    function warningClass(row) {
      if (!row) return 'w-unmapped';
      const day = row.days[state.day - 1];
      if (!day) return 'w-unmapped';
      return 'w-' + (day.colour || 'unset');
    }
    function districtLabel(row) {
      const day = row.days[state.day - 1] || {};
      const hazards = day.source_text || (day.hazards || []).join(', ') || 'no hazard code supplied';
      return row.district + (row.state ? ', ' + row.state : '') + ': ' + (day.colour || 'colour not supplied') + ' · ' + hazards;
    }

    function paintLayers() {
      LAYERS.forEach(layer => {
        groups[layer.name].setAttribute('display', state.layers[layer.name] ? '' : 'none');
      });
      paintStatus();
    }

    function paintStatus() {
      state.keyboardTotal = (loaded.districts || []).length;
      const mapped = rows.length;
      const unmapped = state.unmapped || 0;
      let text = mapped + ' districts carry a warning row for this bulletin';
      if (unmapped) text += '; ' + unmapped + ' polygons are not in the warning table and are drawn as unmapped';
      if (state.placeholders) text += '; ' + state.placeholders + (state.placeholders === 1 ? ' polygon is' : ' polygons are') + ' drawn as a source bounding box';
      const day = rows.length ? (rows[0].days[state.day - 1] || {}) : {};
      text += '. Showing day ' + state.day + (day.date_utc ? ' (' + day.date_utc + ')' : '') + '.';
      if (state.found) text += ' Selected ' + state.found + '; its polygon outline is emphasised, and its published day is unchanged.';
      if (state.keyboardUsed && state.keyboardKey) {
        text += ' Keyboard cursor on ' + state.keyboardKey + ' of ' + (state.keyboardTotal || 0) + ' districts; Enter opens its published day.';
      }
      status.textContent = text;
    }

    function cursorPosition(districts) {
      if (!districts.length) return 0;
      let position = state.keyboardKey ? districts.findIndex(item => item.key === state.keyboardKey) : -1;
      if (position < 0) position = districts.findIndex(item => item.key === state.found);
      if (position < 0) position = 0;
      state.keyboardKey = districts[position].key;
      return position;
    }

    function moveCursor(districts, position, step) {
      if (!districts.length) return;
      const clamped = Math.max(0, Math.min(districts.length - 1, position + step));
      state.keyboardKey = districts[clamped].key;
      state.keyboardUsed = true;
      const paths = groups.districts.querySelectorAll ? groups.districts.querySelectorAll('path.district') : [];
      for (let index = 0; index < paths.length; index += 1) {
        paths[index].setAttribute('tabindex', index === clamped ? '0' : '-1');
      }
      if (paths[clamped] && paths[clamped].focus) paths[clamped].focus();
      paintStatus();
    }

    function paintDistricts() {
      const holder = groups.districts;
      holder.replaceChildren();
      const districts = loaded.districts || [];
      const cursor = cursorPosition(districts);
      districts.forEach((item, position) => {
        const row = warningsByKey[item.key];
        const classes = 'district ' + warningClass(row) + (item.placeholder ? ' is-placeholder' : '') + (state.found === item.key ? ' is-found' : '');
        const label = (row ? districtLabel(row) : item.name + ': not in the warning table') +
                      (item.placeholder ? ' (the source supplies a bounding box for this district, not a coastline)' : '');
        const path = node('path', { d: item.d, 'class': classes, tabindex: position === cursor ? '0' : '-1',
                                    role: 'button', 'aria-label': label });
        const choose = () => { if (row && options.onSelect) options.onSelect(row); };
        path.addEventListener('click', choose);
        path.addEventListener('keydown', event => {
          if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(); return; }
          if (event.key === 'ArrowRight' || event.key === 'ArrowDown') { event.preventDefault(); moveCursor(districts, position, 1); return; }
          if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') { event.preventDefault(); moveCursor(districts, position, -1); return; }
          if (event.key === 'Home') { event.preventDefault(); moveCursor(districts, 0, 0); return; }
          if (event.key === 'End') { event.preventDefault(); moveCursor(districts, districts.length - 1, 0); }
        });
        const title = node('title', undefined, (row ? districtLabel(row) : (item.name || item.key) + ': no warning row for this bulletin') +
                                   (item.placeholder ? ' · source placeholder geometry (bounding box)' : ''));
        path.append(title);
        holder.append(path);
      });
    }

    function zoom(factor, originX, originY) {
      const next = Math.max(0.8, Math.min(12, state.transform.k * factor));
      const ratio = next / state.transform.k;
      const cx = originX === undefined ? state.width / 2 : originX;
      const cy = originY === undefined ? state.height / 2 : originY;
      state.transform.x = cx - (cx - state.transform.x) * ratio;
      state.transform.y = cy - (cy - state.transform.y) * ratio;
      state.transform.k = next;
      applyTransform();
    }
    zoomIn.addEventListener('click', () => zoom(1.3));
    zoomOut.addEventListener('click', () => zoom(1 / 1.3));
    resetView.addEventListener('click', () => { state.transform = { k: 1, x: 0, y: 0 }; state.found = null; applyTransform(); paintDistricts(); paintStatus(); });
    find.addEventListener('input', () => {
      const needle = find.value.trim().toLowerCase();
      state.found = null;
      if (needle.length >= 2) {
        const match = (loaded.districts || []).find(item => String(item.name || '').toLowerCase().indexOf(needle) >= 0);
        if (match) {
          state.found = match.key;
          if (match.bounds) {
            const [minX, minY, maxX, maxY] = match.bounds;
            const centreX = (minX + maxX) / 2, centreY = (minY + maxY) / 2;
            const extent = Math.max(30, maxX - minX, maxY - minY);
            state.transform.k = Math.max(1, Math.min(9, state.width / extent / 1.6));
            state.transform.x = state.width / 2 - centreX * state.transform.k;
            state.transform.y = state.height / 2 - centreY * state.transform.k;
            applyTransform();
          }
        }
      }
      paintDistricts(); paintStatus();
    });

    let dragging = null;
    svg.addEventListener('pointerdown', event => {
      dragging = { x: event.clientX, y: event.clientY, tx: state.transform.x, ty: state.transform.y };
      svg.setPointerCapture(event.pointerId);
    });
    svg.addEventListener('pointermove', event => {
      if (!dragging) return;
      const box = svg.getBoundingClientRect();
      const scale = state.width / (box.width || state.width);
      state.transform.x = dragging.tx + (event.clientX - dragging.x) * scale;
      state.transform.y = dragging.ty + (event.clientY - dragging.y) * scale;
      applyTransform();
    });
    svg.addEventListener('pointerup', event => { dragging = null; try { svg.releasePointerCapture(event.pointerId); } catch (error) { /* ignore */ } });
    svg.addEventListener('wheel', event => {
      event.preventDefault();
      const box = svg.getBoundingClientRect();
      zoom(event.deltaY < 0 ? 1.15 : 1 / 1.15,
           (event.clientX - box.left) / (box.width || 1) * state.width,
           (event.clientY - box.top) / (box.height || 1) * state.height);
    }, { passive: false });

    daySelect.addEventListener('change', () => { state.day = Number(daySelect.value); paintDistricts(); paintStatus(); });

    async function load() {
      status.textContent = 'Reading the vendored geometry…';
      const paths = {};
      let unmapped = 0;
      for (const layer of LAYERS) {
        if (layer.kind === 'places') continue;
        let data;
        try {
          data = await options.load(layer.name);
        } catch (error) {
          status.textContent = 'A map layer could not be read: ' + error.message;
          continue;
        }
        loaded[layer.name] = data.features || [];
        const holder = groups[layer.name];
        holder.replaceChildren();
        if (layer.kind === 'districts') {
          loaded.districts = (data.features || []).map(feature => {
            const key = feature.properties.k;
            if (!warningsByKey[key]) unmapped += 1;
            return { key, name: feature.properties.n, placeholder: feature.properties.p === 1,
                     d: geometryPath(feature.geometry, project), bounds: geometryBounds(feature.geometry, project) };
          });
          paintDistricts();
          continue;
        }
        (data.features || []).forEach(feature => {
          if (feature.geometry.type === 'Point') {
            const point = project(feature.geometry.coordinates[0], feature.geometry.coordinates[1]);
            const circle = node('circle', { cx: point[0], cy: point[1], r: feature.properties.t === 'PPLC' ? 4 : 3, 'class': 'place', role: 'img', 'aria-label': feature.properties.n });
            circle.append(node('title', undefined, feature.properties.n));
            holder.append(circle);
            return;
          }
          const path = node('path', { d: geometryPath(feature.geometry, project), 'class': 'shape' });
          holder.append(path);
        });
      }
      state.unmapped = unmapped;
      state.placeholders = (loaded.districts || []).filter(item => item.placeholder).length;
      paintLayers();
      applyTransform();
    }

    applyTransform();
    paintLayers();
    load();
    return wrapper;
  }

  WG.map = { render: render };
})();
