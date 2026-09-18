/* The layered canvas.
   ============================================================================
   The user's specification, built: a sky gradient at the back, a minimal silhouette range in the middle, a
   flat-vector landmark at the front, and the life of the hour over all of it. One SVG, no image bytes, and
   every colour mixed from the phase palette, so changing the phase re-tints the whole illustration at once —
   which is what makes the transition seamless instead of a cut.

   What the hour draws: the sky, the sun or moon, the depth planes, stars at night, rays at daybreak, birds
   at golden hour, cloud banks by day. What a READ may add, and only when a source actually reported it:
   rain. Nothing here invents a condition. */

import { PALETTES, planes, mix } from './palettes.mjs';
import { LANDMARKS, LANDMARK_BOX } from './landmarks.mjs';

const hash = (seed) => {
  let h = 2166136261 >>> 0;
  const s = String(seed);
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return () => {
    h ^= h << 13; h >>>= 0;
    h ^= h >> 17;
    h ^= h << 5; h >>>= 0;
    return h / 4294967296;
  };
};

/** A soft rolling range across the width, at depth y, drawn as one path. */
function range(width, y, height, amplitude, random, step = 140) {
  let d = `M -40 ${y + height}`;
  let x = -40;
  let prev = y;
  while (x < width + 40) {
    const nx = x + step;
    const ny = y + (random() - 0.5) * amplitude;
    d += ` C ${x + step * 0.4} ${prev} ${nx - step * 0.4} ${ny} ${nx} ${ny}`;
    x = nx;
    prev = ny;
  }
  return d + ` L ${width + 40} ${y + height} Z`;
}

/** A cloud bank: overlapping lozenges, soft and long rather than cartoon puffs. */
function cloud(cx, cy, w, h) {
  const r = h / 2;
  let d = `M ${cx - w / 2} ${cy + r} `;
  d += `A ${r} ${r} 0 0 1 ${cx - w / 2} ${cy - r} `;
  d += `L ${cx + w / 2} ${cy - r} `;
  d += `A ${r} ${r} 0 0 1 ${cx + w / 2} ${cy + r} Z`;
  return d;
}

export function sceneSVG({
  landmark = 'skyline',
  phase = 'noon',
  width = 1600,
  height = 900,
  rain = 0,
  seed = 'weathergpt',
  horizon = 0.66,
  still = false,
} = {}) {
  const palette = PALETTES[phase] || PALETTES.noon;
  const plane = planes(palette, phase);
  const random = hash(seed + phase + landmark);
  const skyLine = Math.round(height * horizon);
  const entry = LANDMARKS[landmark] || LANDMARKS.skyline;
  const shape = entry.build();

  /* The landmark is drawn in its own 480 × 340 box and placed so its baseline sits on the horizon. */
  const scale = (height * 0.54) / LANDMARK_BOX.h;
  const lw = LANDMARK_BOX.w * scale;
  const lx = width * 0.62 - lw / 2;
  const ly = skyLine - LANDMARK_BOX.h * scale;

  const [sunX, sunY] = palette.sunAt;
  const sx = width * sunX;
  const sy = skyLine * sunY;

  const parts = [];

  /* 1. the sky */
  parts.push(`<rect width="${width}" height="${height}" fill="url(#sky-${phase})"/>`);

  /* 2. stars, only where the sky is dark enough to hold them */
  if (phase === 'night') {
    const stars = [];
    for (let i = 0; i < 90; i += 1) {
      const x = random() * width;
      const y = random() * skyLine * 0.86;
      const r = 0.6 + random() * 1.5;
      const delay = (random() * 6).toFixed(2);
      stars.push(`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(2)}" fill="#ffffff" opacity="${(0.25 + random() * 0.5).toFixed(2)}"${still ? '' : ` class="tw" style="animation-delay:${delay}s"`}/>`);
    }
    parts.push(`<g>${stars.join('')}</g>`);
  }

  /* 3. the sun or the moon, with its glow */
  const discR = phase === 'night' ? height * 0.038 : height * 0.045;
  parts.push(`<circle cx="${sx}" cy="${sy}" r="${height * (phase === 'night' ? 0.17 : 0.34)}" fill="url(#glow-${phase})"/>`);
  if (phase === 'night') {
    parts.push(`<path d="M ${sx} ${sy - discR} A ${discR} ${discR} 0 1 0 ${sx} ${sy + discR} A ${discR * 0.80} ${discR * 0.80} 0 1 1 ${sx} ${sy - discR} Z" fill="${palette.sun}" opacity="0.92"/>`);
  } else {
    parts.push(`<circle cx="${sx}" cy="${sy}" r="${discR}" fill="${palette.sun}" opacity="${phase === 'noon' ? 0.9 : 0.96}"/>`);
  }

  /* 4. rays, at daybreak only: long, soft, and behind everything on the ground */
  if (phase === 'daybreak') {
    const rays = [];
    for (let i = 0; i < 7; i += 1) {
      const a = -1.15 + i * 0.30;
      const len = height * (0.8 + random() * 0.5);
      const spread = 16 + random() * 22;
      rays.push(`<path d="M ${sx} ${sy} L ${sx + Math.cos(a) * len - spread} ${sy + Math.sin(a) * len} L ${sx + Math.cos(a) * len + spread} ${sy + Math.sin(a) * len} Z" fill="#FFF6E2" opacity="${(0.05 + random() * 0.05).toFixed(3)}"/>`);
    }
    parts.push(`<g${still ? '' : ' class="ray"'}>${rays.join('')}</g>`);
  }

  /* 5. cloud banks, by day. Two depths so they read as sky rather than as stickers. */
  if (phase !== 'night') {
    const bank = (depth, opacity, count, scaleY) => {
      const items = [];
      for (let i = 0; i < count; i += 1) {
        const cw = width * (0.16 + random() * 0.22);
        const cx = random() * width;
        const cy = skyLine * (0.16 + random() * 0.44) * scaleY;
        items.push(cloud(cx, cy, cw, cw * 0.14));
        items.push(cloud(cx + cw * 0.22, cy - cw * 0.05, cw * 0.6, cw * 0.11));
      }
      return `<g${still ? '' : ` class="drift d${depth}"`} opacity="${opacity}"><path d="${items.join(' ')}" fill="${depth === 1 ? '#ffffff' : mix('#ffffff', palette.mid, 0.18)}"/></g>`;
    };
    parts.push(bank(2, phase === 'noon' ? 0.26 : 0.18, 4, 1.05));
    parts.push(bank(1, phase === 'noon' ? 0.52 : 0.30, 3, 0.8));
  }

  /* 5b. a night needs light on its horizon or the silhouette has nothing to stand against: the settled
     glow of a place, low and wide, behind every plane. It is atmosphere, not a reading. */
  if (phase === 'night') {
    parts.push(`<ellipse cx="${width * 0.62}" cy="${skyLine + height * 0.02}" rx="${width * 0.55}" ry="${height * 0.20}" fill="url(#citylight)"/>`);
  }

  /* 6. the depth planes: two ranges behind the landmark, then the ground it stands on */
  parts.push(`<path d="${range(width, skyLine - height * 0.085, height * 0.5, height * 0.05, random, 200)}" fill="${plane.far}" opacity="0.75"/>`);
  parts.push(`<path d="${range(width, skyLine - height * 0.035, height * 0.5, height * 0.032, random, 160)}" fill="${plane.mid}" opacity="0.9"/>`);

  /* 7. the landmark */
  const snow = shape.snow ? `<path d="${shape.snow}" fill="${mix(plane.near, '#ffffff', 0.55)}"/>` : '';
  parts.push(`<g transform="translate(${lx} ${ly}) scale(${scale})"><path d="${shape.d}" fill="${plane.near}" fill-rule="${shape.rule}"/>${snow}</g>`);

  /* 8. the ground, graded so it recedes from the horizon instead of sitting there as a slab */
  parts.push(`<path d="${range(width, skyLine + height * 0.010, height * 0.5, height * 0.012, random, 260)}" fill="url(#ground-${phase})"/>`);

  /* 9. birds at golden hour — three arcs, the smallest mark that reads as a bird */
  if (phase === 'golden') {
    const birds = [];
    for (let i = 0; i < 6; i += 1) {
      const bx = width * (0.12 + random() * 0.4);
      const by = skyLine * (0.24 + random() * 0.34);
      const s = 7 + random() * 7;
      birds.push(`<path d="M ${bx} ${by} q ${s} ${-s * 0.62} ${s * 2} 0 M ${bx + s * 2.3} ${by + s * 0.3} q ${s * 0.8} ${-s * 0.5} ${s * 1.6} 0" fill="none" stroke="${plane.near}" stroke-width="${(1.4 + random()).toFixed(1)}" stroke-linecap="round" opacity="0.5"/>`);
    }
    parts.push(`<g${still ? '' : ' class="fly"'}>${birds.join('')}</g>`);
  }

  /* 10. rain — drawn only when a read reported it, never to decorate a dry hour */
  if (rain > 0) {
    const lines = [];
    const count = Math.min(120, Math.round(28 + rain * 34));
    for (let i = 0; i < count; i += 1) {
      const x = random() * width * 1.1 - width * 0.05;
      const y = random() * (skyLine + height * 0.1);
      const len = height * (0.02 + random() * 0.03);
      lines.push(`<line x1="${x.toFixed(0)}" y1="${y.toFixed(0)}" x2="${(x - len * 0.30).toFixed(0)}" y2="${(y + len).toFixed(0)}" stroke="${mix(palette.horizon, '#ffffff', 0.6)}" stroke-width="1.2" opacity="${(0.16 + random() * 0.22).toFixed(2)}" stroke-linecap="round"/>`);
    }
    parts.push(`<g${still ? '' : ' class="rain"'}>${lines.join('')}</g>`);
  }

  /* 11. the grain that stops a big gradient banding on a projector */
  parts.push(`<rect width="${width}" height="${height}" fill="url(#grain)" opacity="0.03"/>`);

  const animation = still ? '' : `
    .tw { animation: tw 4.5s ease-in-out infinite; }
    @keyframes tw { 0%,100% { opacity: .22 } 50% { opacity: .95 } }
    .drift { animation: drift 120s linear infinite; }
    .drift.d2 { animation-duration: 210s; }
    @keyframes drift { from { transform: translateX(-8%) } to { transform: translateX(8%) } }
    .ray { animation: ray 14s ease-in-out infinite; transform-origin: ${sx}px ${sy}px; }
    @keyframes ray { 0%,100% { opacity: .75 } 50% { opacity: 1 } }
    .fly { animation: fly 46s linear infinite; }
    @keyframes fly { from { transform: translate(-6%, 2%) } to { transform: translate(24%, -6%) } }
    .rain { animation: rain 0.9s linear infinite; }
    @keyframes rain { from { transform: translateY(-4%) } to { transform: translateY(4%) } }
    @media (prefers-reduced-motion: reduce) { .tw,.drift,.ray,.fly,.rain { animation: none } }`;

  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
  <defs>
    <linearGradient id="sky-${phase}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${palette.zenith}"/>
      <stop offset="52%" stop-color="${palette.mid}"/>
      <stop offset="100%" stop-color="${palette.horizon}"/>
    </linearGradient>
    <radialGradient id="glow-${phase}">
      <stop offset="0%" stop-color="${palette.sunGlow}"/>
      <stop offset="100%" stop-color="${palette.sunGlow.replace(/[\d.]+\)$/, '0)')}"/>
    </radialGradient>
    <linearGradient id="ground-${phase}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${plane.groundFar}"/>
      <stop offset="100%" stop-color="${plane.ground}"/>
    </linearGradient>
    <radialGradient id="citylight">
      <stop offset="0%" stop-color="rgba(160,190,255,0.30)"/>
      <stop offset="60%" stop-color="rgba(120,150,220,0.10)"/>
      <stop offset="100%" stop-color="rgba(120,150,220,0)"/>
    </radialGradient>
    <filter id="grain-f"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/></filter>
    <pattern id="grain" width="180" height="180" patternUnits="userSpaceOnUse">
      <rect width="180" height="180" filter="url(#grain-f)"/>
    </pattern>
  </defs>
  <style>${animation}</style>
  ${parts.join('\n  ')}
</svg>`;
}

export { PALETTES, LANDMARKS };
