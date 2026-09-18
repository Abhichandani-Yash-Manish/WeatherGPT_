/* Renders the scene lab: every phase across one hero landmark, then every landmark at one phase.
   Static HTML, no app, no server — open it or capture it. */
import { writeFileSync, mkdirSync } from 'node:fs';
import { sceneSVG } from '../src/scene/scene.mjs';
import { PALETTES, PHASES } from '../src/scene/palettes.mjs';
import { LANDMARKS } from '../src/scene/landmarks.mjs';

const out = new URL('../../research/design/scene-lab/', import.meta.url);
mkdirSync(out, { recursive: true });

const tile = (landmark, phase, w, h, rain = 0, label = '') => `
  <figure class="t" style="--w:${w}px">
    <div class="s" style="height:${h}px">${sceneSVG({ landmark, phase, width: 1600, height: 900, rain, seed: landmark })}</div>
    <figcaption>${label || PALETTES[phase].label}</figcaption>
  </figure>`;

const ids = Object.keys(LANDMARKS);
const page = `<!doctype html><meta charset="utf-8"><title>Scene lab — WeatherGPT</title>
<style>
  :root { color-scheme: light; }
  body { margin:0; background:#0e1116; color:#e8edf5; font:14px/1.5 ui-sans-serif,system-ui,sans-serif; padding:28px 32px 60px; }
  h1 { font-size:20px; margin:0 0 4px; font-weight:650; }
  h2 { font-size:14px; margin:34px 0 12px; font-weight:600; color:#9fb0c6; text-transform:uppercase; letter-spacing:.08em; }
  p.note { margin:0 0 8px; color:#9fb0c6; max-width:80ch; }
  .row { display:flex; gap:14px; flex-wrap:wrap; }
  .t { margin:0; width:var(--w); }
  .s { border-radius:14px; overflow:hidden; box-shadow:0 10px 30px -14px rgba(0,0,0,.8); }
  figcaption { padding-top:6px; font-size:12px; color:#9fb0c6; }
  .glass { position:relative; }
  .glass .panel { position:absolute; left:6%; top:16%; width:52%; padding:18px 20px; border-radius:18px;
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); }
  .panel h3 { margin:0 0 6px; font-size:19px; line-height:1.2; font-weight:650; }
  .panel p { margin:0; font-size:13px; opacity:.85; }
</style>
<h1>Scene lab</h1>
<p class="note">Layered canvas: sky gradient → far range → mid range → flat-vector landmark → ground, plus the life of the hour. Every colour is mixed from the phase palette, so a phase change re-tints the whole scene. Palettes: Daybreak, High Noon and Deep Night are the supplied specification; Golden Hour is derived.</p>

<h2>1 · One landmark, four hours</h2>
<div class="row">${PHASES.map(p => tile('shikhara', p, 380, 214)).join('')}</div>
<div class="row">${PHASES.map(p => tile('india-gate', p, 380, 214)).join('')}</div>

<h2>2 · Every landmark, at golden hour</h2>
<div class="row">${ids.map(id => tile(id, 'golden', 300, 169, 0, LANDMARKS[id].label + ' — ' + LANDMARKS[id].city)).join('')}</div>

<h2>3 · Every landmark, at high noon</h2>
<div class="row">${ids.map(id => tile(id, 'noon', 300, 169, 0, LANDMARKS[id].label)).join('')}</div>

<h2>4 · Every landmark, at night</h2>
<div class="row">${ids.map(id => tile(id, 'night', 300, 169, 0, LANDMARKS[id].label)).join('')}</div>

<h2>5 · Rain — drawn only when a read reports it</h2>
<div class="row">${['daybreak','noon','golden','night'].map(p => tile('gateway', p, 380, 214, 2.4, PALETTES[p].label + ' · rain 2.4 mm')).join('')}</div>

<h2>6 · The welcome, with the glass panel over it</h2>
<div class="row">${PHASES.map(p => `
  <figure class="t" style="--w:560px">
    <div class="s glass" style="height:315px">${sceneSVG({ landmark: 'shikhara', phase: p, width: 1600, height: 900, seed: 'welcome' })}
      <div class="panel" style="background:${PALETTES[p].glass};border:1px solid ${PALETTES[p].glassLine};color:${PALETTES[p].text}">
        <h3>No district is under an orange or red warning today.</h3>
        <p>303 carry a yellow caution, and 439 have nothing flagged.</p>
      </div>
    </div>
    <figcaption>${PALETTES[p].label} — glass ${PALETTES[p].glass}</figcaption>
  </figure>`).join('')}</div>
`;
writeFileSync(new URL('index.html', out), page);
console.log('wrote', new URL('index.html', out).pathname);
