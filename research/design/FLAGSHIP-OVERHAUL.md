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

