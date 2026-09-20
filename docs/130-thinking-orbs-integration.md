# 130 — The orb in the wait: thinking-orbs, integrated

20 September 2026. The wait between a question and its answer now carries a dotted orb that animates the stage the
engine says it is in. This is what it is, the two of its defaults that had to be wired rather than accepted, and
what it costs.

## What the library is

thinking-orbs by Jakub Antalik, version 0.3.1, **MIT**, zero dependencies, peer React >= 18 (this app is on 19).
Nine hand-tuned states, two tuned sizes (64 for a chat avatar, 20 for inline text), drawn on a plain 2D canvas:
no WebGL, no filters, device-pixel-ratio capped at 2. It carries disciplines this product already keeps, which is
most of the reason it belongs here:

- a per-state aria-label out of the box, and the role of an image rather than a decorative div;
- prefers-reduced-motion: reduce draws a static representative frame, not a frozen animation;
- every instance pauses when the tab is hidden or the orb scrolls out of view, and all instances share one clock.

## The two defaults that were wrong here

**1. Its state is a verb, and this product may not show a verb the engine did not state.** So the orb's state is
read from the engine's own stage vocabulary and never invented. The mapping is in `frontend/src/gpt/orb.ts` and
each pairing is the animation's own meaning rather than a synonym hunt:

| The engine's stage | The orb | Why that drawing |
| --- | --- | --- |
| started | working | particles on tilted orbits: the question is being read |
| planned | solving | bands scramble and click back: tasks are being chosen |
| resolving | connecting | a constellation wires itself: a name is being fixed to a point |
| retrieving | searching | a scan meridian sweeps a globe: published evidence is being reached for |
| assembling | weaving | three strands plait into one: several tools are being worked into one answer |
| finalising | shaping | a dotted outline morphs until it holds a form: the last check |
| task boundary | breathing | a ring morphing slowly: the engine stopped at a boundary, and that is not working |

A stage this build does not recognise shows the neutral state, which says something is running without claiming
what. **The table is held by a check that can fail**: every key of `STAGE_LABELS` must be answered, and the
mapping is asserted against the library's own registry (`STATE_TO_MODE`) so a state with no drawing behind it
fails here rather than rendering an empty canvas in somebody's browser. Removing one row from the table fails two
tests, and that was measured rather than assumed.

**2. Its theme defaults to the operating system, and this product's ground is the hour's.** The two disagree
exactly when it matters: a reader whose OS is dark, at daybreak, would get light dots on a near-white page.
`tokens.css` keys two light hours — `[data-hour='daybreak']` and `[data-hour='noon']` — so the theme is passed
explicitly from the attribute that painted the ground, which also means the orb cannot drift from the page it is
drawn on in the minutes either side of an hour change. Pinning the theme to light unconditionally fails a test;
that was measured too.

## What it replaced, and what it does not do

It replaced three hand-rolled pulsing dots (`.g-dots`, three `<i>` elements and a keyframe). Those could say only
that something was happening. The orb says which thing, in the engine's own vocabulary, and it freezes the moment
the reader asks the turn to stop — a stopped turn is not a turn at work.

Three things it deliberately does not do:

- **It is not ambient.** This is not the background experiment docs/111 rejected seven times over: the orb exists
  only while a turn is running, it starts when the reader asks and stops when the answer lands, and nothing about
  it continues after the wait. The rule "motion answers actions only and nothing loops" is about the ground; a
  status indicator that answers an action is what that rule leaves room for, and the wait already moved — a clock
  ticking once a second, and the stage word lighting up.
- **It does not measure progress.** No percentage, no fraction, no ETA — the rule the wait already kept, held where
  it was: in the stage word beside the orb, not in the drawing.
- **It is not announced.** The canvas is aria-hidden because the stage word beside it is a live region: a reader
  using a screen reader hears the stage once, not twice.

## Evidence

| Check | Result |
| --- | --- |
| `npx vitest run src/gpt/orb.test.tsx` | **9 tests, 9 passed** |
| the mapping with one stage removed | **2 failed** — the completeness test names the stage |
| the theme pinned to light | **1 failed** — the hour test |
| `npx vitest run` (whole frontend suite) | **74 files, 471 tests, 0 failed** |
| `python3 scripts/audit_react_frontend.py` | **19 checks, 0 failed** |
| `npm run build` | main JS **728.79 -> 744.39 kB** (+15.6 kB, gzip 223.82 -> 230.60 kB) |
| live turn, default preference, 1440 and 390 | orb **20x20**, consecutive frames **differ**, axe **clean**, no console errors |
| live turn, prefers-reduced-motion, 1440 and 390 | orb **20x20**, consecutive frames **identical**, axe **clean** |

The last two rows are the point of `frontend/tools/capture-working-turn.mjs`: a working turn is not a route, so
the route capture tool could never see it. This one asks a real question, waits for the wait, and then *checks* the
library's two opposite promises instead of trusting them — under the default preference the orb must move between
two frames 450 ms apart, and under reduce it must not. It also runs axe during the turn, because no route-level
accessibility pass covers a state that exists only mid-turn.

## Attribution

MIT (c) Jakub Antalik. The licence ships with the package and the repository keeps it; the dependency is declared
in `frontend/package.json`, so anyone rebuilding this workspace gets the same code and the same licence. Nothing
was copied into the tree and nothing was modified in the library.

## What is still not covered

- **Nobody has looked at it on a device.** Every measurement above is a headless browser at two widths on one
  machine.
- **Only the first stage has been seen running.** The captures caught the turn before the server reported a stage,
  so the orb drew the neutral state. The other seven pairings are asserted, not watched.
- **The voice path is not wired.** `listening` is the right state for the composer's own recogniser, and the
  composer belongs to another lane.
- **The 64px preset is unused.** The wait uses the inline 20px preset; the avatar-scale preset is a second design
  this product has no home for yet.
- **No visual baseline.** The wait has no stored screenshot baseline, and a baseline must be reviewed before it is
  committed.
- **The bundle grew.** +15.6 kB raw and +6.8 kB gzipped on a main chunk that was already 728 kB and already carries
  a build warning. That is a real cost for a status indicator, and it is stated here rather than rounded away.
