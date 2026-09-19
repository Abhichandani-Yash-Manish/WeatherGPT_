# The flagship overhaul

Working record for the frontend overhaul begun 19 September 2026. Each phase is committed as it lands, with the
capture that justifies it. Companion to the design language documents; this file is the *state* of the work.

## Where the work started

The tree already held a ChatGPT-shaped shell (`frontend/src/gpt/`): a rail, a top bar, a centred column, a
docking composer, and a canvas field whose colour came from the hour. Capture `now-1200.png` shows what it looked
like: a **dark navy** page at midday, no glass panel, and a permanent rail taking a sixth of the sky.

The chosen captures this work is aimed at:

| capture | what it shows |
|---|---|
| `chat-1312ist@1440.png` | bright azure sky over warm sand, the conversation floating in a pale glass panel, chips inside it, a mono legend at the foot |
| `react-gust.png` | the same structure at dusk: violet through rose to amber, dark ink still |
| `gpt4-chat-1200.png` | the running conversation: question bubble, answer column, the work list, the ledger, the composer docked in the panel |

## Phase one — the hour paints the page (committed `6801e04`)

1. **The chrome follows the reader's sun.** `data-mode` is derived from `hourOf()`: a bright page with dark ink by
   day, dark glass with light ink at night, the same panel geometry at every hour so nothing jumps at dusk.
2. **The four hour palettes repainted** in `fieldPaint.ts` from the captures. Midday is no longer dark navy: it is
   a saturated azure falling to sand at the foot. Golden runs violet through rose to amber; night is lifted a little
   so its horizon stays readable.
3. **One frosted sheet** holds the conversation: a faint fill, a 22px blur, a highlight along the top edge. Content
   height at the welcome, tall once there are turns. The sky is visible around it and faintly through it.
4. **The rail became a drawer at every width.** It was a permanent sixth of the sky; it is now something a reader
   opens.
5. **A foot legend** in mono names what painted the field and what stays on this machine, so the decoration is
   declared where it is drawn.

Measured while doing it: at three-quarters opaque the panel read as a grey sheet laid over the sky — the opposite of
the reference — so the light glass settled at `rgba(255,255,255,0.46)` and the night glass at
`rgba(14,17,21,0.44)`.

Captures: `p1c-1200.png`, `p1c-2221.png`.

## Phase two — the conversation inside the glass (first pass)

- A reader turn is a bubble that hugs its words at the right edge (`width: fit-content`, one squared corner),
  not a band across the panel.
- The transcript keeps its own measure inside the sheet (720px) so a long answer does not run the full width.
- The running status is a quiet mono line with a live dot, not a sentence competing with the answer.
- The glass thins to 40% while a conversation is running, because the sheet is tall and the sky should stay present.

Capture: `p2b-chat.png` — the answer with its claims, the `how this was answered` line, task accounting, the folds
and the action chips, all inside the sheet.

## Still to do, in the order I would take it

1. **The claim and the ledger as flagship components.** The claim cards and the evidence receipt are still the
   instrument's: they need the mono key column, the hairline rows, and a hover that reveals the source line.
2. **Motion, one arrival per answer.** The work list ticking, the claims staggering in, the numbers landing on
   exactly the value the tool returned, and all of it collapsing to a plain render under reduced motion.
3. **The fold and the action row.** `What this answer does not cover` is a full-width band; it should be a quiet
   hairline row with a chevron.
4. **The board.** The dashboard is still the old instrument's tiles; it should be the same language as the panel.
5. **The empty state's second beat.** When the reader starts typing, the field should step back and the panel come
   forward, rather than both being static.
6. **The sun and the moon.** The field is a painted gradient; the reference has a disc that travels, which the
   canvas can draw in the same pass.

## Notes for whoever picks this up

- **Pushing is not possible from this sandbox** (the shell has no network). Commits are local and land on `main`;
  `git push` has to run from a machine with credentials.
- The capture tool (`frontend/tools/audit-shot.mjs`) now accepts either composer: the older surface's
  `Your question` label or the flagship composer's placeholder and `Send` button.
- The parallel session's work and this one share the tree: check `git status` before staging, and stage only the
  files this work changed.

## Phase four and five, and what the documents changed

**Phase four — the sky is computed from the sun.** docs/110 asks for an atmosphere computed from the sun at the
reader's place and hour, with the glow placed by its real azimuth and altitude. The shell was bucketing a local
solar *hour* and discarding latitude outright (`void latitude`), so 8°N and 34°N lit identically. Now:

- `flagship/solar.ts` — NOAA/Meeus solar position (declination, the equation of time, hour angle, altitude,
  azimuth), `phaseOf`, `glowPoint`, `glowStrength`;
- five tests in `flagship/solar.test.ts`, each naming its place and instant;
- `fieldPaint.hourOf` derives the phase from that position, so the palettes are phases of the sky;
- the shell publishes `data-phase` plus the sun's point and strength, and a glow layer paints it.

Measured difference: at 18:30 IST in mid-September the sun is below the horizon and the page is dark, where the
clock bucket painted golden until 19:30. Captures `sun-0900.png`, `sun-1830.png`.

**Phase five — the module surfaces in the panel language.** One finding first: **`#/board` does not exist any
more**, and that is a decision rather than a break — docs/110 line 91 records that "the register, the rail, the
topbar and the conversation rail stay deleted". The dashboard work is therefore the module surfaces, which do
render inside the same glass frame (`#/overview`, `#/climate`, …), with a sheet header naming the surface and two
ways back to the conversation.

In that frame the modules were assembling their own chrome: heavier borders than the panel, labels at body
weight. Now the ledger language reaches them — mono small capitals for what a number is, mono tabular figures for
the number, hairlines between rows, tables without zebra bands.

One defect found by looking, not by reasoning: the mono labels are wider than the KPI tiles were built for, and a
four-digit number at the inherited size ran out of its box and overlapped its neighbour (`mod2-overview.png`).
The tiles now reserve their label, cap their number and wrap to fewer columns (`mod3-overview.png`).

## Verification for these phases

| Gate | Result |
|---|---|
| `tsc --noEmit` | clean |
| `vitest run` | **57 files, 317 checks passing** |
| axe, every surface at 1440 | **20 passed, 0 failed** (57 s) |
| frames delivered | **60 fps at 1440, 61 at 390** |
| captures | `sun-0900`, `sun-1830`, `p3d-chat`, `mod-overflow` series, `mod3-overview` |

## Still open, in the documents' own terms

1. **HeroUI v3 as the chrome.** docs/110 records it as adopted; the top bar still uses plain `<select>`s, so the
   controls are the one place the adopted library is not in use.
2. **The 90-second drift and the grain.** The grain is in the canvas; the drift should be checked against the doc.
3. **Watch** as the second of the three surfaces — the panel opens, but the surface itself is the old one.
4. Re-run the capture set for the record after each phase (done here) and keep `git push` to a machine with
   network: the sandbox has none.


## Phase eight — the layered scene, wired in at last

The objective asks for "a layered canvas (CSS sky gradient + mid silhouette + front landmark) with location-aware
morphing". The tree already held that library — `frontend/src/scene/`: eleven landmarks with city and regional
matching, a palette per phase, plane tints derived from it — and **nothing in the app imported it**. That is a
capability built and left behind, and it is now wired:

- `gpt/Scene.tsx` renders the two layers the reference is about: a stretched ridge tinted by `planes().mid` and the
  place's own landmark tinted by `planes().near`, with the landmark chosen by `landmarkFor(place)` — city first,
  then region, then a skyline. No colour is invented: the tints come from the scene's palette for the phase.
- Two defects the captures caught, not reasoning: the builders return `{ d, rule }` and the rule is `evenodd` —
  that is what cuts a landmark's arches and windows, so a plain string left the path as `[object Object]` and
  nothing drew at all. And the near plane at 0.64 toward ink is right against a dark sky and far too dark against
  a bright one, so the day hours take the middle plane.
- The composition took three passes against the capture: at 54vh the scene fought the panel and the legend for the
  foot of the page. At 30vh with a smaller landmark it reads as depth behind the conversation.

Open for the next pass: the legend still crosses the skyline band and wants more ground of its own.


## Phase ten — the chrome library, actually used

The design record says HeroUI v3 was adopted as the chrome. In the tree it was not: `@import "@heroui/styles"`
sat in `styles/app.css` and **no component imported `@heroui/react`** — the stylesheet was being loaded for
nothing. That is a documented capability left behind, and it is now used: the top bar’s Watch and Owner controls
are HeroUI `Button`s with their accessible names unchanged, so the gates that check those names still mean
something.

Three API differences cost three round trips, and each is worth recording so the next reader does not fight a
fork of the library: v3’s `Button` takes **no `radius`**, **no `startContent`** and **no `isIconOnly`** — the shape
comes from the class, and an icon is a child. `variant` and `size` are real; the variant names are
`primary | ghost | danger | outline | danger-soft | secondary | tertiary`, so `light` and `flat` do not exist.

Open and recorded: the icon-only Owner control is nearly invisible against a bright sky because a `ghost` variant
leaves it to our own class, which was written for a plain `<button>`. It wants a real treatment next round.


## Phase eleven — a defect found by probing, and a wrong diagnosis corrected

Checking whether Watch works as the third surface, the probe showed the plan/watch panel does not open when the
Watch control is clicked. My first reading was that phase ten’s HeroUI swap had killed it (React Aria’s `onPress`
under a synthetic click), so I rolled the swap back — and **the panel still did not open**. The rollback changed
nothing, which means the defect is in the shell’s own wiring and pre-dates the swap.

Two lessons, both kept in the code comment:

1. **Correlation is not cause.** A library swap and a broken control appeared together, so I blamed the swap.
   The counter-test — revert and re-probe — took one run and disproved it.
2. **A probe can be wrong before the thing it probes is.** The first probe grepped for panel text; the second the
   same; both reported "not open" for a component whose heading is present in the source. The structural probe
   (host element, role, class count) is the right instrument and is what the next round should use.

Recorded for the next round: **the Watch control does not open the panel in either variant** — HeroUI or plain —
with the evidence in `watch-open.png` and `watch-open2.png`. This is the concrete reason Watch cannot yet count as
the third surface.


## Phase twelve — the Watch defect, narrowed to a handoff

Round eight recorded that the Watch control does not open its panel. This round narrowed it with the structural
probe the earlier rounds should have used:

| Check | Result |
|---|---|
| `Workspace` renders the control | yes — a plain `<button onClick={() => onPlans?.()}>` |
| `App` passes the handler | yes — `onPlans={() => setPlansOpen(true)}` |
| `App` renders the panel | yes — `{plansOpen ? <div className="planwatch-host"><PlanWatch …/></div> : null}`, in the same return as the shell |
| panel component intact | yes — `plans/PlanWatch.tsx:495` carries its heading and its `data-testid` |
| after a real click | **neither `.planwatch-host` nor `[data-testid="planwatch"]` is in the DOM** |

So the click lands (Playwright completes it, which it only does when the element receives the event), the handler
and the state and the render block all exist, and the panel still never mounts. The suspect is therefore the
**handoff between the control and the state** — the one link in the chain that has not been observed directly.
The next probe is to log from inside `onPlans` rather than to change anything: three rounds have now been spent
on a defect that a single instrumented click would localise.

Not fixed this round: the context budget went on establishing that the panel component and the wiring are both
intact, which is itself the useful result — the fix is small once the break is observed.


## Phase thirteen — the instrumented click, and what it rules out

Round nine said the next probe was to instrument the handoff rather than change anything. Done: a `console.log`
inside `onPlans`, then a real click.

| Observation | Value |
|---|---|
| element clicked | `<button type="button" class="g-tool">` with our bell svg — the right control |
| `[watch] onPlans fired` in the console | **never printed** |
| `.planwatch-host` after the click | absent |

So the pointer reaches the control, and **React never runs the handler**. That rules out everything below the
handler — the state, the render block, the panel component — and moves the suspect above it: the event never
reaches React, which points at either a second, stale copy of the shell in the tree being the one under the
pointer, or React’s delegated listener not being attached for this subtree.

The instrumentation was removed before committing: a probe is an instrument, not a feature. The next probe is to
count how many `Watch` controls exist in the DOM and how many React roots are mounted, which distinguishes those
two hypotheses in one run.

Honest note on cost: this defect has now taken three rounds. The first round I spent on a fix, the second on
elimination, and only the third on the instrument that produced a decisive observation. The instrument should
have come first.


## Phase fourteen — two hypotheses disproved, and a contrast that matters

Round ten left two candidates: a duplicate stale shell under the pointer, or React's delegated listener not attached for this subtree. Both are disproved by measurement.

- Watch controls in the DOM: **1** (no duplicate).
- The control is inside the React root: true.
- Mounted roots: one (`#root`).
- Element under the pointer at the button centre: `BUTTON.g-tool` — nothing intercepting.

A second probe then measured whether any handler in the app fires, and produced the contrast that matters:

- Clicking **Owner** works — the address moves to `#/signin` — and its native event target is the icon `<svg>` inside it.
- Clicking **Watch** targets the `<button>` element itself, and the handler never runs.

React is alive and delegating: a click that lands on the icon inside a control bubbles to that control. On Watch the pointer lands on the button element instead and nothing happens. That is a reproducible difference between two controls built the same way.

Next: instrument node identity across `pointerdown` and `click`, and click the icon rather than the button centre.

Cost, again because it is the lesson: three rounds went on fixes and elimination before one probe measured two candidates in a single run.

## Phase fifteen — the closing observation, and the handover

The promised instrumented click, on the icon rather than the button centre, with the event log watched:

| Observation | Value |
|---|---|
| `pointerdown` | on the icon `svg` inside the button |
| `click` | on the same `svg`, `defaultPrevented=false` |
| `.planwatch-host` afterwards | absent |
| the sibling Owner control, same bar, same markup pattern | **works** |

So the control receives both a pointer event and an unprevented click on a child, inside the React root, with nothing over it, and the handler on the button never runs — while the control beside it does. Every hypothesis that can be checked from outside React is now spent; the next instrument has to be inside it: a render counter on the bar, a handler that logs, and a check of whether the two controls differ in what they receive.

What is *not* in doubt: the panel component, the state, the render block and the App handler were each verified intact in earlier rounds. This is one control, one handler, and one unexplained gap between them.

## Handover at the end of the goal rounds

The objective's items (1) conversation-with-motion, (2) layered canvas with the travelling disc and crossfades, (3) the dashboard surfaces in the same language, and (4) per-phase verification are implemented, gated and recorded — seventeen commits, each with the capture that justifies it, each phase's gates run and written down.

Open, with evidence rather than adjectives:

1. **The Watch control's handler never runs** — this section, and phases eleven to fourteen. Not a wiring defect in the three places that were checked; it is the gap between the click and the handler.
2. **The landmark's midday framing** — visible since phase seven, still low in the frame.
3. **Push** — impossible from this sandbox: the shell has no network. Seventeen commits sit on local `main` for a machine with credentials.
