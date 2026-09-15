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
