/* The atmosphere.
   ============================================================================
   The ground under this product used to be a PNG of contour lines, scaled up and translated eight pixels
   on a twenty-four second loop. It was invisible at rest, it could not respond to anything, and at the
   size it had to be drawn the raster showed. This replaces it with the thing it was a picture of.

   WHAT IT DRAWS. A scalar field - a handful of slowly drifting pressure centres, some high, some low, over
   a broad background gradient - contoured at evenly spaced levels by marching squares. That is how a
   synoptic chart is made, and it is why the result reads as weather to somebody who knows weather and as
   quiet abstract linework to everybody else. Closed loops gather around a centre; the lines between two
   centres stretch into a trough. Nothing is randomised per frame: the field is continuous in time, so the
   contours slide and merge and split the way isobars do rather than shimmering.

   WHAT IT IS NOT, and this matters on this product more than the drawing does. It is decoration. It is
   `aria-hidden`, it carries no reading, it is never derived from a retrieved value, and it must never be
   mistaken for a chart. It has no legend because it measures nothing. A reader who takes a lesson from it
   has been misled, so it is kept far below the contrast at which anyone would try.

   WHAT IT ANSWERS TO. Three inputs, all of them real states of this page and none of them invented:

     pace     how fast the centres travel. Resting, the field crosses the screen in about four minutes.
              While the engine is actually working it moves about three times as fast; while the reader is
              composing it slows almost to a stop, because a page that squirms while you type is a page you
              type badly on.
     tension  how far apart the contour levels sit. Tight contours are a strong gradient - in the real
              atmosphere, wind - so the field tightens while a request is in flight and relaxes when the
              answer lands. This is the whole of the "it is working" signal in the background, and it is
              legible without being a progress bar, which is the point: it says busy, it never says how far.
     bearing  which way the weather travels, from the sun's own hour angle. Astronomy the page already
              computes, spent on a decoration rather than on a claim.

   WHAT STOPS IT. `prefers-reduced-motion` draws exactly one frame and never starts the loop. A hidden tab
   stops it at the next visibility change and it resumes where it was. The reader's own atmosphere control
   stops it outright. It never runs when it cannot be seen.

   WHAT IT COSTS. The grid is sized in CSS pixels, not device pixels, so a 2x display does not quadruple the
   work; the field is a single Float32Array reused every frame with no per-frame allocation; each contour
   level accumulates into one Path2D and is stroked once. The loop is capped well under the display's rate
   because the motion is measured in minutes and nothing is gained by drawing it sixty times a second. */

/** The page's own state, read fresh each frame so a change reaches the field without remounting it. */
export type SkyfieldState = {
  /** 0 stops the drift; 1 is resting; above 1 is faster. */
  pace: number;
  /** Contour spacing. 1 is resting; below 1 tightens the gradient. */
  tension: number;
  /** Overall ink strength, 0 to 1. */
  strength: number;
  /** The direction of travel in radians, from the sun's hour angle. */
  bearing: number;
  /**
   * A transient, 0 to 1, that spikes the moment the reader sends a question and decays over a couple of
   * seconds.
   *
   * This is the difference between a background that loops and one that is alive. Everything else here
   * answers to a STATE - resting, working, being typed into - and a state that lasts thirty seconds is
   * not something a reader connects to anything they did. A surge is tied to the press itself: the flow
   * quickens, the light brightens, and both settle. It is the page acknowledging an action, in the same
   * register as a control that depresses when you click it, just very much larger.
   */
  surge: number;
};

export const RESTING: SkyfieldState = { pace: 1, tension: 1, strength: 1, bearing: 0, surge: 0 };

/* Grid resolution in CSS pixels. Coarse enough that the whole field is a few thousand samples at any
   window size, fine enough that a contour reads as a curve rather than as a staircase. */
const CELL = 24;
/* How many contour levels the field is cut at. */
const LEVELS = 11;

type Centre = {
  /** Where it sits, in field units (0..1 across the long edge), and how it travels. */
  x: number; y: number; ax: number; ay: number; px: number; py: number;
  /** Positive is a high, negative is a low. */
  weight: number;
  /** How wide the centre's influence reaches. */
  spread: number;
};

/* Six centres: enough that the field is never symmetrical and never obviously periodic, few enough that
   evaluating it at every grid point stays trivial. The numbers are chosen, not random, so the field is the
   same composition on every machine and in every screenshot - a background that differs between two
   captures is a background that cannot be reviewed. */
const CENTRES: Centre[] = [
  { x: 0.18, y: 0.24, ax: 0.115, ay: 0.085, px: 0.00, py: 1.13, weight: 1.00, spread: 0.30 },
  { x: 0.74, y: 0.16, ax: 0.090, ay: 0.110, px: 2.31, py: 0.44, weight: -0.86, spread: 0.26 },
  { x: 0.52, y: 0.62, ax: 0.140, ay: 0.070, px: 4.02, py: 2.77, weight: 0.74, spread: 0.34 },
  { x: 0.92, y: 0.72, ax: 0.075, ay: 0.125, px: 1.18, py: 5.01, weight: -0.68, spread: 0.29 },
  { x: 0.06, y: 0.82, ax: 0.100, ay: 0.095, px: 3.44, py: 3.60, weight: 0.58, spread: 0.24 },
  { x: 0.40, y: 0.02, ax: 0.130, ay: 0.060, px: 5.27, py: 1.90, weight: -0.52, spread: 0.32 },
];

/* The period of the slowest centre, in seconds, at pace 1. Everything else is a multiple of it, so the
   whole field returns to its starting composition rather than drifting away from it forever. */
const PERIOD = 240;

/** The field at one point. A sum of Gaussians over a broad tilt - the tilt is what keeps the contours from
    being nothing but concentric rings, and the bearing is what turns it.

    Exported for the test that holds the flow perpendicular to it: that relationship is the whole claim
    this layer makes about being weather-shaped rather than decorative-shaped, and it is checkable. */
export function fieldAt(x: number, y: number, phase: number, bearing: number): number {
  let total = Math.cos(bearing) * (x - 0.5) * 0.55 + Math.sin(bearing) * (y - 0.5) * 0.55;
  for (let i = 0; i < CENTRES.length; i += 1) {
    const c = CENTRES[i];
    const cx = c.x + c.ax * Math.sin(phase + c.px);
    const cy = c.y + c.ay * Math.cos(phase * 0.78 + c.py);
    const dx = (x - cx) / c.spread;
    const dy = (y - cy) / c.spread;
    total += c.weight * Math.exp(-(dx * dx + dy * dy));
  }
  return total;
}

/** Where a contour at `level` crosses the segment between two corner values, as a fraction of it. */
function cut(a: number, b: number, level: number): number {
  const span = b - a;
  return span === 0 ? 0.5 : (level - a) / span;
}

/**
 * Draw the field once onto a 2D context.
 *
 * Exported so a test can render a frame and assert on what was stroked without standing up a browser, and
 * so a still can be produced for a reader who has asked for no motion at all.
 */
export function drawSkyfield(
  ctx: CanvasRenderingContext2D, width: number, height: number,
  state: SkyfieldState, seconds: number, ink: string,
): void {
  ctx.clearRect(0, 0, width, height);
  if (width <= 0 || height <= 0) return;
  const cols = Math.max(2, Math.ceil(width / CELL));
  const rows = Math.max(2, Math.ceil(height / CELL));
  const phase = (seconds / PERIOD) * Math.PI * 2;
  /* The field is sampled in a square space and stretched to the window, so a wide window shows more of the
     same weather rather than the same weather squashed. */
  const values = new Float32Array((cols + 1) * (rows + 1));
  let low = Infinity;
  let high = -Infinity;
  for (let j = 0; j <= rows; j += 1) {
    for (let i = 0; i <= cols; i += 1) {
      const v = fieldAt(i / cols, j / rows, phase, state.bearing);
      values[j * (cols + 1) + i] = v;
      if (v < low) low = v;
      if (v > high) high = v;
    }
  }
  if (!(high > low)) return;
  /* Contour levels sit inside the field's own range rather than at fixed values, so the drawing keeps the
     same density as the centres wander instead of emptying out when they happen to line up. Tension pulls
     the levels toward the middle of the range, which is what tightens them. */
  const mid = (low + high) / 2;
  const half = ((high - low) / 2) * Math.max(0.2, state.tension);
  const scaleX = width / cols;
  const scaleY = height / rows;

  /* THE WASH, under the linework.
     ----------------------------------------------------------------------------------------------------
     Contours alone are a drawing. They give the field structure and no mass, and a page whose only moving
     element is a 1px line reads as a diagram with a screensaver on it rather than as a surface with
     weather over it. What was missing is TONE: something large and soft and slow that changes the value of
     the ground itself as it passes, so the page is lighter in one corner than the other and that keeps
     changing.

     Each centre lays down one huge radial pool at its current position. A high is warm and slightly
     lighter - sun on paper; a low is cool and slightly darker - shade. Both are within a few per cent of
     the ground, and crucially both are in the SAME family, a warm grey and a cool grey. That is a taste
     decision and also a safety one: two saturated tints on a weather product would be read as a legend -
     blue means rain - by exactly the readers this product is for. Light and shade cannot be read that way.

     It is drawn before the contours so the lines sit on top of their own field rather than under it. */
  /* PARALLAX. The wash runs at a little over half the contours' rate, so the two layers separate and the
     ground reads as having depth rather than as one drawing sliding about. It is the cheapest depth cue
     there is and the only one that survives being this low-contrast. */
  const phaseWash = phase * 0.55;
  const reach = Math.hypot(width, height);
  for (let i = 0; i < CENTRES.length; i += 1) {
    const c = CENTRES[i];
    const cx = (c.x + c.ax * Math.sin(phaseWash + c.px)) * width;
    const cy = (c.y + c.ay * Math.cos(phaseWash * 0.78 + c.py)) * height;
    const radius = c.spread * 2.35 * reach * 0.5;
    const warm = c.weight > 0;
    const a = Math.min(0.5, Math.abs(c.weight) * 0.085 * state.strength);
    const pool = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    pool.addColorStop(0, warm ? 'rgba(214, 196, 166, ' + a.toFixed(3) + ')' : 'rgba(96, 124, 150, ' + a.toFixed(3) + ')');
    pool.addColorStop(0.55, warm ? 'rgba(214, 196, 166, ' + (a * 0.42).toFixed(3) + ')' : 'rgba(96, 124, 150, ' + (a * 0.42).toFixed(3) + ')');
    pool.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = pool;
    ctx.fillRect(0, 0, width, height);
  }

  /* THE TRAVELLING LIGHT, and it is the single element doing most of the work of making this page feel
     awake. One very large, very soft warm pool on its own slow path across the ground - about seventy-five
     seconds corner to corner - so the room is brighter in one place than another and that keeps changing.
     A reader never catches it moving and always notices that it has.

     It brightens on a surge. That is the whole acknowledgement: press send, and the light comes up. */
  const lightPhase = (seconds / 75) * Math.PI * 2;
  const lx = (0.5 + 0.42 * Math.cos(lightPhase)) * width;
  const ly = (0.42 + 0.34 * Math.sin(lightPhase * 0.73)) * height;
  const lightAlpha = Math.min(0.5, (0.10 + 0.11 * state.surge) * state.strength);
  const beam = ctx.createRadialGradient(lx, ly, 0, lx, ly, reach * 0.62);
  beam.addColorStop(0, 'rgba(255, 246, 224, ' + lightAlpha.toFixed(3) + ')');
  beam.addColorStop(0.45, 'rgba(255, 246, 224, ' + (lightAlpha * 0.38).toFixed(3) + ')');
  beam.addColorStop(1, 'rgba(255, 246, 224, 0)');
  ctx.fillStyle = beam;
  ctx.fillRect(0, 0, width, height);

  ctx.lineWidth = 1;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = ink;
  for (let l = 0; l < LEVELS; l += 1) {
    const t = (l + 0.5) / LEVELS;
    const level = mid - half + t * half * 2;
    const path = new Path2D();
    for (let j = 0; j < rows; j += 1) {
      for (let i = 0; i < cols; i += 1) {
        const v00 = values[j * (cols + 1) + i];
        const v10 = values[j * (cols + 1) + i + 1];
        const v11 = values[(j + 1) * (cols + 1) + i + 1];
        const v01 = values[(j + 1) * (cols + 1) + i];
        let code = 0;
        if (v00 > level) code |= 8;
        if (v10 > level) code |= 4;
        if (v11 > level) code |= 2;
        if (v01 > level) code |= 1;
        if (code === 0 || code === 15) continue;
        const x0 = i * scaleX;
        const y0 = j * scaleY;
        /* The four edge crossings, named for the side they sit on. */
        const top = [x0 + cut(v00, v10, level) * scaleX, y0];
        const right = [x0 + scaleX, y0 + cut(v10, v11, level) * scaleY];
        const bottom = [x0 + cut(v01, v11, level) * scaleX, y0 + scaleY];
        const left = [x0, y0 + cut(v00, v01, level) * scaleY];
        const line = (a: number[], b: number[]) => { path.moveTo(a[0], a[1]); path.lineTo(b[0], b[1]); };
        switch (code) {
          case 1: case 14: line(left, bottom); break;
          case 2: case 13: line(bottom, right); break;
          case 3: case 12: line(left, right); break;
          case 4: case 11: line(top, right); break;
          case 6: case 9: line(top, bottom); break;
          case 7: case 8: line(left, top); break;
          /* The two saddles. Resolved the same way every time rather than by the cell's own centre value:
             a consistent choice keeps a contour continuous between frames, and an inconsistent one makes
             the line flicker between two valid readings as the field drifts past the ambiguity. */
          case 5: line(left, top); line(bottom, right); break;
          case 10: line(top, right); line(left, bottom); break;
          default: break;
        }
      }
    }
    /* Every third level is drawn heavier, the way a synoptic chart bolds an isobar every few millibars. It
       is the one detail that makes the linework read as an instrument rather than as a gradient. */
    const heavy = l % 3 === 1;
    ctx.globalAlpha = Math.max(0, Math.min(1, state.strength * (heavy ? 0.13 : 0.06)));
    ctx.stroke(path);
  }
  ctx.globalAlpha = 1;
}

/* ---- the array -----------------------------------------------------------------------------------------
   Three attempts at a living background have now failed for the same reason, and it is worth naming
   because the third one only looked like it was different. Contours: honest, invisible. Wind trails: read
   as woodgrain. A halftone lattice with the cursor dragging it about: that was a LENS, not a behaviour -
   it moved when the mouse moved and did absolutely nothing the rest of the time, which is the definition
   of a decoration with an event handler bolted on.

   THE POINTER REACTION IS GONE, deliberately. Two versions of it were built - a positional drag, then a
   glow - and both were the same mistake: a background that does nothing until you wave a mouse at it is a
   decoration with an event handler on it, and on a page whose subject is a paragraph of text the cursor is
   usually nowhere near the background anyway. What is left is the part that was always doing the work.

   What reads as an intelligent system is not smooth drift. It is LOCAL ACTIVITY: a surface where
   individual cells fire, brightly and briefly, in patterns that are not uniform and not periodic, and
   where the rate of that firing changes with what the system is actually doing. A sensor array. That is
   what this is.

     the base      every cell's resting size is the pressure field sampled at that point, so the synoptic
                   surface is still what is being drawn and it still swells and thins in slow waves
     firing        cells light sharply and decay over about half a second. Where they fire is biased
                   toward a steep field gradient, so activity gathers where the weather is doing something
                   instead of scattering evenly - which is the difference between an array and static
     the sweep     a wavefront crosses the field every twenty seconds or so, lighting what it passes
     the surge     a ring leaves the centre when a question is sent and lights everything it crosses
     WORKING       and this is the one that matters: while the engine is retrieving, the firing rate goes
                   up roughly fivefold and the whole array gets busy. A reader can see the system thinking
                   without a single invented percentage

   DETERMINISTIC. Nothing here calls Math.random. A cell fires when a hash of its index and the current
   tick falls under the rate, so the same second of field time produces the same frame on every machine -
   the background stays reviewable, diffable and screenshottable, which a random one never is. */

/** How much of the atmosphere's resolution the slow layer is rendered at. */
const SLOW_SCALE = 0.5;

/** Grid spacing in CSS pixels. */
const GRID = 24;
/** The largest a cell gets at rest, before activation. */
const DOT = 4.2;
/** How long a fired cell takes to fall back, in seconds. */
const DECAY = 0.52;
/** Ticks per second at which cells may fire. */
const TICK = 22;

export type Pointer = { x: number; y: number; on: boolean };

/** The pointer's glow: hardest at the cursor, exactly zero at the edge of its reach. */
export function matrixPull(distance: number, reach: number): number {
  if (distance >= reach || distance <= 0) return 0;
  const t = 1 - distance / reach;
  return t * t;
}

/** A deterministic 0..1 from two integers. No Math.random: the same tick must draw the same frame. */
export function spark(cell: number, tick: number): number {
  const n = Math.sin(cell * 127.1 + tick * 311.7) * 43758.5453;
  return n - Math.floor(n);
}

/** The array's own state, which persists between frames because activation is a decay, not a value. */
export type Array2D = { activation: Float32Array; cols: number; rows: number; tick: number };

export function makeArray(): Array2D {
  return { activation: new Float32Array(0), cols: 0, rows: 0, tick: -1 };
}

function drawArray(
  ctx: CanvasRenderingContext2D, width: number, height: number,
  state: SkyfieldState, seconds: number, dt: number, ink: string, live: Array2D,
): void {
  const phase = (seconds / PERIOD) * Math.PI * 2;
  const cols = Math.ceil(width / GRID) + 1;
  const rows = Math.ceil(height / GRID) + 1;
  if (live.cols !== cols || live.rows !== rows) {
    live.cols = cols;
    live.rows = rows;
    live.activation = new Float32Array(cols * rows);
  }
  const a = live.activation;

  /* Everything falls back toward nothing; what follows decides what is lifted this frame. */
  const fade = Math.exp(-dt / DECAY);
  for (let i = 0; i < a.length; i += 1) a[i] *= fade;

  /* The field, and its gradient, which is where firing gathers. */
  const values = new Float32Array(cols * rows);
  let low = Infinity;
  let high = -Infinity;
  for (let j = 0; j < rows; j += 1) {
    for (let i = 0; i < cols; i += 1) {
      const v = fieldAt((i * GRID) / width, (j * GRID) / height, phase, state.bearing);
      values[j * cols + i] = v;
      if (v < low) low = v;
      if (v > high) high = v;
    }
  }
  const span = high - low || 1;

  /* FIRING. One pass per tick rather than per frame, so the rate is the same at 30fps and at 144. */
  const tick = Math.floor(seconds * TICK);
  if (tick !== live.tick) {
    live.tick = tick;
    /* Busy is the whole point of this layer: while the engine retrieves, the array gets visibly busy. */
    const rate = 0.006 + 0.030 * Math.min(1, state.pace / 3) + 0.05 * state.surge;
    for (let j = 1; j < rows - 1; j += 1) {
      for (let i = 1; i < cols - 1; i += 1) {
        const k = j * cols + i;
        /* Steeper field here means likelier to fire: the array is busiest where the weather is. */
        const gx = values[k + 1] - values[k - 1];
        const gy = values[k + cols] - values[k - cols];
        const steep = Math.min(1, Math.hypot(gx, gy) / (span * 0.5));
        if (spark(k, tick) < rate * (0.35 + 1.5 * steep)) a[k] = 1;
      }
    }
  }

  /* THE SWEEP: a wavefront every twenty seconds, lighting what it crosses. */
  const sweepAt = ((seconds % 20) / 20) * (width + 420) - 210;
  /* THE SURGE: a ring leaving the centre when a question was sent. */
  const ringR = state.surge > 0 ? (1 - state.surge) * Math.hypot(width, height) * 0.62 : -1;

  const near = new Path2D();
  const mid = new Path2D();
  const far = new Path2D();
  for (let j = 0; j < rows; j += 1) {
    for (let i = 0; i < cols; i += 1) {
      const k = j * cols + i;
      const x = i * GRID;
      const y = j * GRID;

      const sweep = 1 - Math.min(1, Math.abs(x - sweepAt) / 150);
      if (sweep > 0) a[k] = Math.max(a[k], sweep * 0.55);

      if (ringR > 0) {
        const distance = Math.hypot(x - width / 2, y - height / 2);
        const band = 1 - Math.min(1, Math.abs(distance - ringR) / 110);
        if (band > 0) a[k] = Math.max(a[k], band * state.surge);
      }

      const v = (values[k] - low) / span;
      const lit = a[k];
      const size = DOT * (0.16 + 0.70 * v + 0.95 * lit);
      const half = size / 2;
      (lit > 0.45 ? near : lit > 0.14 ? mid : far).rect(x - half, y - half, size, size);
    }
  }

  /* Three fills, not fourteen hundred: every cell is a rect appended to one of three paths, and each path
     is filled once. That is what keeps this at sixty frames with a couple of thousand cells on screen. */
  ctx.fillStyle = ink;
  ctx.globalAlpha = Math.max(0, Math.min(1, 0.30 * state.strength));
  ctx.fill(far);
  ctx.globalAlpha = Math.max(0, Math.min(1, 0.52 * state.strength));
  ctx.fill(mid);
  ctx.globalAlpha = Math.max(0, Math.min(1, 0.85 * state.strength));
  ctx.fill(near);
  ctx.globalAlpha = 1;
}

/** True when this reader has asked for no decorative motion. */
function stillnessWanted(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Start the atmosphere and return the function that stops it.
 *
 * TWO CADENCES, AND THAT IS THE WHOLE PERFORMANCE STORY.
 *
 * The slow layer - the tonal wash and the contours - costs real work: six radial gradients and a beam
 * filled over the whole canvas, plus marching squares across a few thousand cells at eleven levels. None
 * of it moves fast enough to need sixty frames a second. So it is rendered into an offscreen canvas about
 * twelve times a second and blitted, which is one drawImage per frame.
 *
 * The array runs every frame, because it is the layer a reader can actually see moving, and it is cheap by
 * construction: a decay pass over a Float32Array and three Path2D fills.
 *
 * `read` is called once per frame rather than captured, so the page's state reaches the atmosphere without
 * the canvas being torn down - remounting mid-drift restarts the composition, which a reader sees as a jump.
 */
export function mountSkyfield(canvas: HTMLCanvasElement, read: () => SkyfieldState): () => void {
  const ctx = canvas.getContext('2d');
  if (!ctx) return () => { /* no 2D context: the ground is the gradient alone, still a complete page */ };
  const slow = document.createElement('canvas');
  const slowCtx = slow.getContext('2d');
  let frame = 0;
  let stopped = false;
  /* Field time, which is not wall time: pace scales how fast it advances, so slowing the drift slows it
     from where it is rather than snapping it to a different point in the loop. */
  let clock = 0;
  let last = 0;
  let slowAt = -Infinity;
  let width = 0;
  let height = 0;
  let ratio = 1;
  let ink = 'rgba(32, 45, 58, 1)';
  let inkReadAt = -Infinity;
  const live = makeArray();

  const measure = () => {
    /* THE ATMOSPHERE DOES NOT NEED THE READER'S FULL PIXEL RATIO, and paying it is the single largest
       cost in this loop. Nothing on this layer has a hard edge: gradients, hairlines and small squares.
       Capped at 1.5, a 1440-wide panel backs onto 2.2 megapixels instead of 5.2, and on a retina display
       the difference is not findable by eye. The text above it is unaffected - that is the DOM's own
       rasterisation and it still gets every pixel the device has. */
    ratio = Math.min(1.5, window.devicePixelRatio || 1);
    const box = canvas.getBoundingClientRect();
    width = Math.max(1, Math.round(box.width));
    height = Math.max(1, Math.round(box.height));
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    /* The slow layer is rendered at HALF of that again and scaled up on the blit. It is six radial
       gradients and a set of very faint hairlines; there is nothing in it that a half-resolution buffer
       loses, and it cuts both the gradient fills and the per-frame blit to a quarter of the pixels. */
    slow.width = Math.max(1, Math.round(width * ratio * SLOW_SCALE));
    slow.height = Math.max(1, Math.round(height * ratio * SLOW_SCALE));
    if (slowCtx) slowCtx.setTransform(ratio * SLOW_SCALE, 0, 0, ratio * SLOW_SCALE, 0, 0);
    slowAt = -Infinity;
  };

  /* The ink follows the spectrum, which drifts once a minute, so it is re-read on a slow timer rather than
     every frame - getComputedStyle is the single most expensive thing this loop could do. */
  const readInk = () => {
    const value = getComputedStyle(canvas).getPropertyValue('--g-mark-2').trim();
    if (value) ink = value;
  };

  const paint = (now: number) => {
    if (stopped) return;
    const state = read();
    if (last === 0) last = now;
    const elapsed = Math.min(250, now - last);
    last = now;
    const dt = elapsed / 1000;
    clock += dt * Math.max(0, state.pace);
    if (now - inkReadAt > 4000) { inkReadAt = now; readInk(); }

    /* Every 150ms, not every 80. The rebuild is the one expensive thing left in this loop - marching
       squares plus seven full-canvas gradient fills - and it lands entirely on whichever frame it happens
       on, which is what the p95 spike in the measurement was. The wash and the contours move in minutes;
       rebuilding them six times a second is already far finer than anything a reader can perceive. */
    if (slowCtx && now - slowAt >= 150) {
      slowAt = now;
      slowCtx.clearRect(0, 0, width, height);
      drawSkyfield(slowCtx, width, height, state, clock, ink);
    }
    ctx.clearRect(0, 0, width, height);
    if (slowCtx) ctx.drawImage(slow, 0, 0, width, height);
    drawArray(ctx, width, height, state, clock, dt, ink, live);
    frame = requestAnimationFrame(paint);
  };

  const start = () => {
    if (stopped || frame) return;
    last = 0;
    frame = requestAnimationFrame(paint);
  };
  const halt = () => {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
  };

  measure();
  if (stillnessWanted()) {
    /* One frame, at a fixed point in the loop so it is the same still every time, no loop, no firing and
       and no firing. */
    readInk();
    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      const state = read();
      drawSkyfield(ctx, width, height, state, PERIOD * 0.25, ink);
      drawArray(ctx, width, height, { ...state, surge: 0, pace: 0 }, PERIOD * 0.25, 0, ink, live);
    };
    draw();
    const onResize = () => { measure(); draw(); };
    window.addEventListener('resize', onResize);
    return () => { stopped = true; window.removeEventListener('resize', onResize); };
  }

  const onVisibility = () => { if (document.hidden) halt(); else start(); };
  const onResize = () => measure();
  document.addEventListener('visibilitychange', onVisibility);
  window.addEventListener('resize', onResize);
  if (!document.hidden) start();

  return () => {
    stopped = true;
    halt();
    document.removeEventListener('visibilitychange', onVisibility);
    window.removeEventListener('resize', onResize);
  };
}
