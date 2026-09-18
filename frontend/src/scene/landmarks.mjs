/* The landmarks.
   ============================================================================
   Flat vector silhouettes, one fill each, drawn in a 480 × 340 box whose baseline is y = 340 — the horizon.
   The scene scales and places them; they never carry their own colour, so the palette tints them.

   The register is Firewatch and Overdrop, not clip art: clean geometry, no outlines, no gradients inside the
   shape, no pixel grid. Openings (arches, windows) are cut with fill-rule evenodd rather than painted in the
   sky colour, so a landmark stays correct against any sky.

   Each entry is a famous building for a named city, with regional fallbacks for everywhere else. */

const B = { w: 480, h: 340 };
const base = B.h;

/* ---- shape helpers ------------------------------------------------------------------------------- */

/** A round-headed opening: straight sides, semicircular head. Used as an evenodd cut. */
function arch(cx, baseY, w, h) {
  const r = w / 2;
  const spring = baseY - (h - r);
  return `M ${cx - r} ${baseY} L ${cx - r} ${spring} A ${r} ${r} 0 0 1 ${cx + r} ${spring} L ${cx + r} ${baseY} Z`;
}

/** A pointed (ogee) opening — the Indo-Islamic arch of Charminar, the Gateway and the Taj. */
function ogee(cx, baseY, w, h) {
  const r = w / 2;
  const spring = baseY - h * 0.52;
  return `M ${cx - r} ${baseY} L ${cx - r} ${spring} C ${cx - r} ${spring - h * 0.30} ${cx - r * 0.34} ${spring - h * 0.30} ${cx} ${baseY - h}` +
         ` C ${cx + r * 0.34} ${spring - h * 0.30} ${cx + r} ${spring - h * 0.30} ${cx + r} ${spring} L ${cx + r} ${baseY} Z`;
}

/** An onion dome sitting on baseY, w wide and h tall. */
function onion(cx, baseY, w, h) {
  const r = w / 2;
  return `M ${cx - r} ${baseY} C ${cx - r * 1.16} ${baseY - h * 0.40} ${cx - r * 0.66} ${baseY - h * 0.74} ${cx - r * 0.30} ${baseY - h * 0.90}` +
         ` C ${cx - r * 0.12} ${baseY - h * 0.97} ${cx + r * 0.12} ${baseY - h * 0.97} ${cx + r * 0.30} ${baseY - h * 0.90}` +
         ` C ${cx + r * 0.66} ${baseY - h * 0.74} ${cx + r * 1.16} ${baseY - h * 0.40} ${cx + r} ${baseY} Z`;
}

/** The mast and pot above a dome. */
function finial(cx, topY, h) {
  const t = h * 0.12;
  return `M ${cx - t} ${topY} L ${cx - t} ${topY - h * 0.46} L ${cx - t * 2.2} ${topY - h * 0.56} L ${cx} ${topY - h}` +
         ` L ${cx + t * 2.2} ${topY - h * 0.56} L ${cx + t} ${topY - h * 0.46} L ${cx + t} ${topY} Z`;
}

/** A slim tower with two balcony rings, a dome and a finial. */
function minaret(cx, baseY, w, h) {
  const half = w / 2;
  const shaft = h * 0.74;
  const domeH = h * 0.16;
  const ringOne = baseY - shaft * 0.44;
  const ringTwo = baseY - shaft * 0.80;
  const top = baseY - shaft;
  return [
    `M ${cx - half} ${baseY} L ${cx - half * 0.82} ${top} L ${cx + half * 0.82} ${top} L ${cx + half} ${baseY} Z`,
    `M ${cx - half * 1.5} ${ringOne} L ${cx + half * 1.5} ${ringOne} L ${cx + half * 1.5} ${ringOne + h * 0.035} L ${cx - half * 1.5} ${ringOne + h * 0.035} Z`,
    `M ${cx - half * 1.35} ${ringTwo} L ${cx + half * 1.35} ${ringTwo} L ${cx + half * 1.35} ${ringTwo + h * 0.03} L ${cx - half * 1.35} ${ringTwo + h * 0.03} Z`,
    onion(cx, top, w * 1.5, domeH),
    finial(cx, top - domeH, h * 0.12),
  ].join(' ');
}

const rect = (x, y, w, h) => `M ${x} ${y} L ${x + w} ${y} L ${x + w} ${y + h} L ${x} ${y + h} Z`;

/** A run of merlons (the toothed crest on a parapet). */
function merlons(x, y, w, count, h) {
  const step = w / count;
  let d = '';
  for (let i = 0; i < count; i += 1) {
    d += rect(x + i * step + step * 0.18, y - h, step * 0.64, h) + ' ';
  }
  return d;
}

/* ---- the buildings -------------------------------------------------------------------------------- */

/** Delhi — India Gate. One great arch, a heavy cornice, a stepped plinth. */
function indiaGate() {
  const cx = 240;
  const body = rect(150, base - 210, 180, 210);
  const cornice = rect(138, base - 232, 204, 22);
  const cap = rect(158, base - 250, 164, 18);
  const plinthOne = rect(120, base - 18, 240, 18);
  const plinthTwo = rect(96, base - 8, 288, 8);
  const opening = arch(cx, base - 18, 84, 150);
  const bowl = `M ${cx - 16} ${base - 250} C ${cx - 16} ${base - 262} ${cx + 16} ${base - 262} ${cx + 16} ${base - 250} Z`;
  return { d: [body, cornice, cap, plinthOne, plinthTwo, bowl, opening].join(' '), rule: 'evenodd' };
}

/** Hyderabad — Charminar. A square of four arches under four minarets. */
function charminar() {
  const cx = 240;
  const bodyTop = base - 150;
  const body = rect(140, bodyTop, 200, 150);
  const deck = rect(126, bodyTop - 20, 228, 20);
  const upper = rect(166, bodyTop - 74, 148, 54);
  const crest = merlons(166, bodyTop - 74, 148, 9, 10);
  const domeSmall = onion(cx, bodyTop - 74, 46, 26);
  const openings = [ogee(cx - 52, base, 56, 104), ogee(cx + 52, base, 56, 104)].join(' ');
  const upperWindows = [rect(188, bodyTop - 62, 16, 30), rect(276, bodyTop - 62, 16, 30)].join(' ');
  const towers = [
    minaret(150, bodyTop - 20, 26, 150),
    minaret(330, bodyTop - 20, 26, 150),
  ].join(' ');
  return { d: [body, deck, upper, crest, domeSmall, towers, openings, upperWindows].join(' '), rule: 'evenodd' };
}

/** Mumbai — the Gateway of India. A central arch between two lower wings, one dome above. */
function gateway() {
  const cx = 240;
  const centre = rect(170, base - 200, 140, 200);
  const wingLeft = rect(96, base - 128, 76, 128);
  const wingRight = rect(308, base - 128, 76, 128);
  const band = rect(158, base - 216, 164, 16);
  const dome = onion(cx, base - 216, 96, 56);
  const tip = finial(cx, base - 272, 20);
  const turrets = [
    onion(120, base - 128, 34, 22), onion(360, base - 128, 34, 22),
    rect(112, base - 150, 16, 22), rect(352, base - 150, 16, 22),
  ].join(' ');
  const plinth = rect(84, base - 10, 312, 10);
  const opening = ogee(cx, base - 10, 78, 150);
  const wingArches = [ogee(134, base - 10, 40, 74), ogee(346, base - 10, 40, 74)].join(' ');
  return { d: [centre, wingLeft, wingRight, band, dome, tip, turrets, plinth, opening, wingArches].join(' '), rule: 'evenodd' };
}

/** Agra — the Taj Mahal. The dome on its drum, the great iwan, four chhatris, two minarets. */
function taj() {
  const cx = 240;
  const plinth = rect(70, base - 22, 340, 22);
  const body = rect(150, base - 150, 180, 128);
  const drum = rect(206, base - 186, 68, 36);
  const dome = onion(cx, base - 186, 112, 84);
  const tip = finial(cx, base - 270, 26);
  const chhatris = [
    onion(168, base - 150, 40, 26), rect(160, base - 176, 16, 26),
    onion(312, base - 150, 40, 26), rect(304, base - 176, 16, 26),
  ].join(' ');
  const minarets = [minaret(104, base - 22, 22, 172), minaret(376, base - 22, 22, 172)].join(' ');
  const iwan = ogee(cx, base - 22, 64, 104);
  const sides = [ogee(180, base - 22, 30, 54), ogee(300, base - 22, 30, 54)].join(' ');
  return { d: [plinth, body, drum, dome, tip, chhatris, minarets, iwan, sides].join(' '), rule: 'evenodd' };
}

/** Kolkata — Howrah Bridge. Two portal towers, the through truss, the deck. */
function howrah() {
  const deckY = base - 56;
  const topY = base - 214;
  const leftX = 118;
  const rightX = 362;
  const deck = rect(10, deckY, 460, 11);
  const towers = [rect(leftX, topY, 26, deckY - topY), rect(rightX - 26, topY, 26, deckY - topY)].join(' ');
  const caps = [rect(leftX - 7, topY - 13, 40, 13), rect(rightX - 33, topY - 13, 40, 13)].join(' ');
  /* The suspended span: a straight top chord between the towers, verticals, and one zigzag of diagonals. */
  const chordY = topY + 22;
  const chord = rect(leftX + 26, chordY, rightX - leftX - 52, 9);
  const bays = 6;
  const bayW = (rightX - leftX - 52) / bays;
  const web = [];
  for (let i = 0; i <= bays; i += 1) {
    const x = leftX + 26 + i * bayW;
    web.push(rect(x - 3, chordY + 9, 6, deckY - chordY - 9));
  }
  for (let i = 0; i < bays; i += 1) {
    const x0 = leftX + 26 + i * bayW;
    const x1 = x0 + bayW;
    const [ax, ay, bx, by] = i % 2 === 0 ? [x0, deckY, x1, chordY + 9] : [x0, chordY + 9, x1, deckY];
    web.push(`M ${ax} ${ay} L ${ax + 5} ${ay} L ${bx + 5} ${by} L ${bx} ${by} Z`);
  }
  /* The side spans run from each tower out to the bank, sloping down to the approach. */
  const sides = [
    `M 10 ${deckY} L ${leftX} ${deckY} L ${leftX} ${topY + 54} L 10 ${deckY - 14} Z`,
    `M 470 ${deckY} L ${rightX} ${deckY} L ${rightX} ${topY + 54} L 470 ${deckY - 14} Z`,
  ].join(' ');
  const piers = [rect(leftX - 8, deckY + 11, 42, 45), rect(rightX - 34, deckY + 11, 42, 45)].join(' ');
  const water = rect(0, base - 6, 480, 6);
  return { d: [sides, deck, towers, caps, chord, ...web, piers, water].join(' '), rule: 'nonzero' };
}

/** Jaipur — Hawa Mahal. Five tiers of jharokhas stepping back to a crest. */
function hawaMahal() {
  const tiers = [
    { x: 92, w: 296, y: base - 62, h: 62, windows: 9 },
    { x: 106, w: 268, y: base - 116, h: 54, windows: 8 },
    { x: 122, w: 236, y: base - 166, h: 50, windows: 7 },
    { x: 140, w: 200, y: base - 210, h: 44, windows: 6 },
    { x: 162, w: 156, y: base - 248, h: 38, windows: 4 },
  ];
  const solids = tiers.map(t => rect(t.x, t.y, t.w, t.h));
  const crests = tiers.map(t => merlons(t.x, t.y, t.w, Math.round(t.w / 26), 7));
  const cuts = [];
  tiers.forEach(t => {
    const step = t.w / t.windows;
    for (let i = 0; i < t.windows; i += 1) {
      cuts.push(arch(t.x + step * (i + 0.5), t.y + t.h - 9, step * 0.44, t.h * 0.62));
    }
  });
  const domes = [onion(200, base - 248, 30, 18), onion(280, base - 248, 30, 18)].join(' ');
  const plinth = rect(76, base - 10, 328, 10);
  return { d: [...solids, ...crests, domes, plinth, ...cuts].join(' '), rule: 'evenodd' };
}

/** Madurai / Chennai — a gopuram. A tapering tower of tiers under a row of kalashas. */
function gopuram() {
  const tiers = 7;
  const solids = [];
  const cuts = [];
  for (let i = 0; i < tiers; i += 1) {
    const inset = i * 15;
    const y = base - 40 - i * 30;
    const w = 300 - inset * 2;
    solids.push(rect(90 + inset, y - 26, w, 26));
    solids.push(rect(84 + inset, y - 32, w + 12, 8));
    const cells = Math.max(2, 7 - i);
    const step = w / cells;
    for (let c = 0; c < cells; c += 1) {
      cuts.push(rect(90 + inset + step * c + step * 0.30, y - 20, step * 0.40, 14));
    }
  }
  const crestY = base - 40 - tiers * 30 + 4;
  const crest = [];
  for (let i = 0; i < 5; i += 1) {
    const cx = 175 + i * 32;
    crest.push(onion(cx, crestY, 20, 14));
    crest.push(finial(cx, crestY - 14, 12));
  }
  const gate = rect(78, base - 40, 324, 40);
  const doorway = arch(240, base, 56, 92);
  const plinth = rect(66, base - 8, 348, 8);
  return { d: [gate, ...solids, ...crest, plinth, doorway, ...cuts].join(' '), rule: 'evenodd' };
}

/** Ahmedabad / Gujarat — a shikhara over its mandapa, the Somnath silhouette. */
function shikhara() {
  const cx = 240;
  const spireBase = base - 96;
  const spireTop = base - 268;
  const spire = `M ${cx - 46} ${spireBase} C ${cx - 44} ${spireBase - 80} ${cx - 26} ${spireTop + 42} ${cx - 15} ${spireTop + 16}` +
                ` L ${cx + 15} ${spireTop + 16} C ${cx + 26} ${spireTop + 42} ${cx + 44} ${spireBase - 80} ${cx + 46} ${spireBase} Z`;
  const amalaka = `M ${cx - 20} ${spireTop + 16} C ${cx - 22} ${spireTop + 2} ${cx + 22} ${spireTop + 2} ${cx + 20} ${spireTop + 16} Z`;
  const kalasha = finial(cx, spireTop + 2, 22);
  const urushringa = [
    `M ${cx - 66} ${spireBase} C ${cx - 64} ${spireBase - 48} ${cx - 54} ${spireBase - 74} ${cx - 46} ${spireBase - 92} L ${cx - 46} ${spireBase} Z`,
    `M ${cx + 66} ${spireBase} C ${cx + 64} ${spireBase - 48} ${cx + 54} ${spireBase - 74} ${cx + 46} ${spireBase - 92} L ${cx + 46} ${spireBase} Z`,
  ].join(' ');
  const sanctum = rect(cx - 68, spireBase, 136, 60);
  const mandapaRoof = `M 112 ${base - 100} L 176 ${base - 150} L 304 ${base - 150} L 368 ${base - 100} Z`;
  const eave = rect(104, base - 100, 272, 10);
  const mandapa = rect(124, base - 90, 232, 62);
  const bays = [arch(180, base - 28, 34, 48), arch(240, base - 28, 34, 48), arch(300, base - 28, 34, 48)].join(' ');
  const steps = [rect(96, base - 28, 288, 11), rect(78, base - 17, 324, 10), rect(60, base - 7, 360, 7)].join(' ');
  return { d: [spire, amalaka, kalasha, urushringa, sanctum, mandapaRoof, eave, mandapa, steps, bays].join(' '), rule: 'evenodd' };
}

/** Anywhere with a skyline — a quiet modern city. */
function skyline() {
  const blocks = [
    [20, 84, 46], [70, 132, 40], [114, 104, 54], [172, 190, 44], [220, 150, 38],
    [262, 240, 50], [316, 126, 42], [362, 168, 36], [402, 96, 58],
  ];
  const solids = blocks.map(([x, h, w]) => rect(x, base - h, w, h));
  const caps = [
    rect(280, base - 268, 14, 28), rect(186, base - 214, 10, 24), rect(418, base - 122, 8, 26),
  ].join(' ');
  const cuts = [];
  blocks.forEach(([x, h, w]) => {
    const cols = Math.max(2, Math.round(w / 16));
    const rows = Math.max(2, Math.round(h / 26));
    for (let c = 0; c < cols; c += 1) {
      for (let r = 0; r < rows; r += 1) {
        if ((c * 7 + r * 13 + x) % 5 === 0) continue;
        cuts.push(rect(x + 6 + c * ((w - 12) / cols), base - h + 12 + r * ((h - 20) / rows), 5, 7));
      }
    }
  });
  return { d: [...solids, caps, ...cuts].join(' '), rule: 'evenodd' };
}

/** The north — a Himalayan ridge. No windows, no arches, only rock. */
function himalaya() {
  const ridge = `M -20 ${base} L 40 ${base - 96} L 78 ${base - 60} L 130 ${base - 180} L 168 ${base - 128}` +
                ` L 214 ${base - 232} L 252 ${base - 166} L 300 ${base - 262} L 344 ${base - 150} L 392 ${base - 206}` +
                ` L 436 ${base - 110} L 500 ${base} Z`;
  const snow = `M 300 ${base - 262} L 282 ${base - 224} L 294 ${base - 230} L 304 ${base - 216} L 316 ${base - 232} L 328 ${base - 224} Z` +
               ` M 214 ${base - 232} L 200 ${base - 200} L 210 ${base - 206} L 220 ${base - 196} L 230 ${base - 208} Z`;
  return { d: ridge, rule: 'nonzero', snow };
}

/** The coast — a lighthouse and two palms. */
function coast() {
  const towerX = 330;
  const tower = `M ${towerX - 22} ${base - 28} L ${towerX - 13} ${base - 172} L ${towerX + 13} ${base - 172} L ${towerX + 22} ${base - 28} Z`;
  const gallery = rect(towerX - 20, base - 186, 40, 14);
  const lamp = rect(towerX - 12, base - 208, 24, 22);
  const roof = `M ${towerX - 16} ${base - 208} L ${towerX} ${base - 226} L ${towerX + 16} ${base - 208} Z`;
  const hut = rect(towerX - 52, base - 56, 40, 28);
  const rock = `M 240 ${base} C 268 ${base - 26} 300 ${base - 30} 330 ${base - 28} C 360 ${base - 30} 392 ${base - 26} 420 ${base} Z`;
  const palms = [];
  [110, 168].forEach((x, index) => {
    const h = index ? 132 : 158;
    palms.push(`M ${x - 5} ${base} C ${x - 3} ${base - h * 0.5} ${x + 3} ${base - h * 0.8} ${x + 9} ${base - h} L ${x + 15} ${base - h * 0.98} C ${x + 8} ${base - h * 0.78} ${x + 3} ${base - h * 0.48} ${x + 4} ${base} Z`);
    for (let f = 0; f < 5; f += 1) {
      const a = -0.9 + f * 0.45;
      const tipX = x + 9 + Math.cos(a) * 52;
      const tipY = base - h - Math.sin(a) * 30;
      palms.push(`M ${x + 9} ${base - h} C ${x + 9 + Math.cos(a) * 26} ${base - h - Math.sin(a) * 26} ${tipX - 12} ${tipY - 6} ${tipX} ${tipY}` +
                 ` C ${tipX - 14} ${tipY + 6} ${x + 12 + Math.cos(a) * 24} ${base - h - Math.sin(a) * 14} ${x + 9} ${base - h + 6} Z`);
    }
  });
  return { d: [rock, tower, gallery, lamp, roof, hut, ...palms].join(' '), rule: 'nonzero' };
}

export const LANDMARKS = {
  'india-gate': { label: 'India Gate', city: 'Delhi', build: indiaGate },
  charminar: { label: 'Charminar', city: 'Hyderabad', build: charminar },
  gateway: { label: 'Gateway of India', city: 'Mumbai', build: gateway },
  taj: { label: 'Taj Mahal', city: 'Agra', build: taj },
  howrah: { label: 'Howrah Bridge', city: 'Kolkata', build: howrah },
  'hawa-mahal': { label: 'Hawa Mahal', city: 'Jaipur', build: hawaMahal },
  gopuram: { label: 'Gopuram', city: 'Madurai', build: gopuram },
  shikhara: { label: 'Shikhara', city: 'Ahmedabad', build: shikhara },
  skyline: { label: 'City skyline', city: 'anywhere with a skyline', build: skyline },
  himalaya: { label: 'Himalayan ridge', city: 'the north', build: himalaya },
  coast: { label: 'Lighthouse coast', city: 'the coast', build: coast },
};

export const LANDMARK_BOX = B;

/** Which scene a place gets. A named city wins; otherwise the region decides; otherwise a skyline. */
export function landmarkFor(place) {
  const name = String(place || '').toLowerCase();
  const byCity = [
    [/delhi|new delhi|gurgaon|gurugram|noida/, 'india-gate'],
    [/hyderabad|secunderabad|telangana/, 'charminar'],
    [/mumbai|bombay|thane|navi mumbai/, 'gateway'],
    [/agra/, 'taj'],
    [/kolkata|calcutta|howrah/, 'howrah'],
    [/jaipur|rajasthan/, 'hawa-mahal'],
    [/madurai|chennai|madras|tamil|trichy|coimbatore/, 'gopuram'],
    [/ahmedabad|gandhidham|gujarat|surat|vadodara|rajkot|bhuj|somnath/, 'shikhara'],
    [/shimla|manali|leh|ladakh|srinagar|dehradun|himachal|uttarakhand|sikkim|gangtok|darjeeling/, 'himalaya'],
    [/kochi|cochin|goa|kerala|vizag|visakhapatnam|puri|kanyakumari|mangalore|udupi|ratnagiri/, 'coast'],
  ];
  for (const [pattern, id] of byCity) if (pattern.test(name)) return id;
  return 'skyline';
}
