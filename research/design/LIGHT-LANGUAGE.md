# The light language — proposal and first build

18 September 2026. Standing intent: the user asked for a redesign from scratch, ruled out the three probe
directions as generic, and asked for a root language that is contextual to the problem statement, technically
sound, and dynamic. The probes in `probes/` are kept as references; the implementation is React.

## The thesis

**This product's only unique property is that every value has a chain of custody, and every reading knows its
place and hour.** So the language is built from the two things the product actually owns:

1. **Where and when.** The ground is computed from the reader's own sun — altitude sets the palette, azimuth
   sets the side the light enters from. It is astronomy: true everywhere, verifiable, and it cannot fabricate a
   weather condition. A board whose tiles describe five places is lit five different ways because each tile is
   lit by the hour of the place it describes.
2. **Nothing unattributed.** A value without a source is not drawn. Missing has a texture (hatch), refusal is
   monochrome and struck through, and the machine's own work is openable rather than hidden behind a spinner.

## The four parts

| Part | What it is | Where it lives |
|---|---|---|
| **The light** | A pure function of place and instant → ground, ink, hazard-safe accent, horizon, light side, star and emissive levels. Seven complete grounds keyed on solar altitude, interpolated continuously. | `frontend/src/light/solar.ts` |
| **The claim** | One value, one window, one source, one state. The same atom in an answer, a board tile, a comparison. Carries a window ruler where covered spans are drawn and gaps stay hatched. | `frontend/src/light/Claim.tsx` |
| **The work** | The engine's own task list, openable: named steps, real durations, and failed steps kept with their reason. | `frontend/src/light/Work.tsx` |
| **The door** | The front door: the country's weather as this machine read it, lit by the reader's own hour, with the reader's own question box as the only way in. | `frontend/src/home/Home.tsx` |

Typographic roles: **Martian Mono** for everything a tool owns (values, units, place names the resolver
returned, ids, timestamps, states); **Anek Latin** for everything a model wrote. Both self-hosted, both now
real dependencies of the frontend.

## The rules this layer enforces

1. **Hazard colour arrives only through a published value.** It appears on a chip or a strip only where a
   source printed that colour, and it always carries the source's own words. Interface state never borrows it:
   a failed step is monochrome and struck through, because a red glyph beside a red hazard chip is a lie about
   severity.
2. **A number with no read is not printed.** An absent `today` block says the read did not state today; a
   failed read says so in the server's words and draws no board at all, because a tile carries a source line
   and would attribute numbers nobody returned. A zero the source stated *is* printed — that is an answer.
3. **The sky is never a reading.** The readout prints the computed sun altitude, azimuth and compass point, and
   says out loud that the light is computed from a place and hour and is never a condition report.
4. **A gap is not a calm hour.** Windows are drawn: covered spans solid, everything else hatched.

## What is verified

| Check | Result |
|---|---|
| `frontend/src/light/solar.test.ts` | 11 checks: a real sunset (Surat, 18 Sep 2026), a solstice noon, a night, a rising morning, azimuth bounds, the three light modes, the light side, emissive/star behaviour, and two places lit differently at one instant |
| `frontend/src/home/home.test.tsx` | 5 checks: today's own column leads; a stated zero prints; a pending read prints no numeral; an absent today block is unstated; a failed read prints no count and no board; the light names its place |
| `npx vitest run` (frontend) | **64 files, 365 checks, all passing** (63 files / 356 before this batch) |
| `npx tsc --noEmit` | clean |
| `playwright a11y -g "front door"` | passes under axe (wcag2a/aa, 21a/aa, best-practice). It failed first with two real defects — no `main` landmark and unlandmarked content — which were repaired, and the front door is now a named test in the gate because the empty address is not in the route registry |
| Captures | `research/design/ui-audit-20260918/home-*.png` — live clock, and dawn / noon / night with the page clock pinned. A pinned capture is a design render, not a claim about what the page looked like at that hour |
| Served app | built to `web/dist` and served on 8765; the captures are of the served build |

## What is not done, and should not be implied

- **The board is not built.** The five tiles on the front door are claims rendered from one national read, not
  the modular customisable area. No library, no resize, no arrange, no per-place boards, no relevance model.
- **The district field is not built** — the national mosaic of district cells is designed and unrendered.
- **The work panel is not wired to the conversation.** The component exists and is tested by construction, but
  the answer surface still uses the old shell.
- **Eighteen surfaces still carry the previous language.** Only the front door has moved, which is why the
  layer is scoped to `.light` and prefixed `--l-`: a half-applied palette cannot leak into a surface that
  has not moved.
- **Two recorded defects are untouched**: an unknown deep link still renders Ask silently (a test now asserts
  the current behaviour, not the desired one), and seven built routes are still called by no UI.
- **No reader other than this machine's owner has used it.** A capture is one render on one machine.

## Open questions

1. Is the light the right root — should the ground follow the reader's sun in *every* surface, or is the front
   door its home?
2. The board: what does "intelligent" mean concretely — a relevance order with a *why these?* disclosure, or
   something more active (it proposes a tile when a warning enters force for a place you watch)?
3. Should the machine's work be openable on the answer surface itself, or does it belong to a diagnostics view?


---

# The stage layout, 18 September 2026

The user supplied an AI-chat reference (Omago AI, Dribbble 26622820) and asked to make **its layout** work
for WeatherGPT, taking the vibe and background philosophy from the pixel-art weather widgets already in
`research/design-references/`, which is no longer in this repository. Those were third-party product
screenshots kept as visual reference while the light language was being worked out; the language itself
is written down here and in the spectrum's own source, so the borrowed imagery had done its job and
shipping other people's interface art in a public repository is not something this project should do.

## What was measured in the reference

Dominant field `#E5DAEA` → `#F3E8F9` (47.6% / 9.8%), with `#C9AEE6` violet and the composer glass sitting on
`#D2B8EF`. Layout: one large rounded stage inset in the page, a quiet top bar (mark left, nav centre, search
and avatar right), a centred greeting above a large glass composer with chips in its lower row, a row of mode
pills underneath, one floating action button.

## What was taken, and what was refused

| Taken | Refused |
|---|---|
| One rounded stage as the whole surface | The greeting that says nothing: a weather product's first screen must show weather. Our hero sentence **is** the reading. |
| A centred conversation with one input | A fixed lavender brand wash. Our field is computed from the reader's own sun, so it is dawn at dawn. |
| Chips in the composer's lower row | Decorative chips. Every chip is a control the product already has (register, answer language, reading position), reading the same catalogues and keys as the top bar. |
| Generous space around the hero | Low-contrast light-on-light text. The light engine guarantees ink against its own ground, and the veil hands the field over to a calm ground before any sentence is read. |

## The material: the sky is printed

`DitherSky` renders the computed sky to a canvas and quantises it through an ordered Bayer matrix with a
reduced amplitude, then scales it up with `image-rendering: pixelated`. Two measured corrections during the
batch: 232 × 132 cells at five levels read as a chessboard fighting the text, so the grid is now 620 × 348 at
seven levels with 0.55 amplitude; and the colour now fills the stage while only the *grain* is banded to the
sky, because the ground under the board is the same sky the answer is read in.

The sun's disc is drawn only when the sun is above the horizon. There is no drawn moon: this build does not
read the moon's position, and an invented one would be a fabricated fact on a page that refuses them.

## Evidence added in this batch

| Check | Result |
|---|---|
| `npx vitest run` | **64 files, 365 checks, all passing** |
| `npx tsc --noEmit` | clean |
| axe, front door | passes |
| Captures | `research/design/ui-audit-20260918/stage-*.png` — live, dawn (05:52 IST) and noon (13:12 IST), desktop and phone |

## A repair this batch made, and why it was needed

`useConversation` read the stored register once, when its module was imported: `const initial = { … register:
readRegister() … }`. A reader who chose *Full evidence* on the front door and then asked a question got the
register the module happened to load with, not the one they had just chosen. The register is now read when the
conversation surface mounts (`useReducer(reducer, undefined, freshConversation)`), and the register vocabulary
moved into `chat/model.ts` so the rail and the front door cannot drift apart.

## Still not built

The board remains a single row of claims from one national read: no library, no resize, no arrange, no
per-place boards, no relevance model, no *why these?*. The district field is designed and unrendered. The Work
panel is not wired to the answer surface. Eighteen surfaces still carry the previous language.



---

# The living sky and the chat-only face, 18 September 2026

The user asked for three things: a dynamic, soothing background that plays for each time or phase (inspired by a
golden-hour weather shot), the whole face of the site to be the chat interface alone, and a genuine
differentiator rather than a better dashboard.

## The differentiator: the background is the answer

Every weather product animates a *decoration* that pretends to be weather — an SVG cloud that means nothing. Here
the field is composited from the same reads that answer questions, and a legend names every input:

| Layer | Painted from | Allowed because |
|---|---|---|
| Light | computed solar altitude and azimuth | astronomy: true at that place and hour, and unfakeable |
| God rays | the sun's own position, strongest near the horizon | they exist because the sun is there, not because a source said "sunny" |
| Haze | the forecast's visibility for the hour covering now | a reading, labelled |
| Rain | the forecast's precipitation for that hour; wind sets the slant | a reading, labelled — the sky rains only when a source says rain |
| The published day | the district bulletin's colour for today | reached only through a published colour; the words stay in the legend |
| Stars | how far the sun is below the horizon | astronomy |
| The print | an ordered Bayer dither over everything | it is one product, not a render |

**Clouds are deliberately absent.** The hourly forecast this build reads carries temperature, humidity,
precipitation, probability, wind, gusts and visibility — and no cloud fraction. A cloud drawn without one would
be exactly the invented condition the rest of the product refuses. The sky has texture instead, and the legend
says so.

The live legend on the served build, 21:21 IST: `sun −41.6° · rain 0.4 mm/h · visibility 1.2 km · wind 5 km/h ·
published day yellow · Open-Meteo best match; variable-specific upstream model/run unspecified · read 21:21 IST`.

## The face is the conversation

`#/` is now the chat and nothing else: the country's picture opens the conversation as the machine's first line,
the openings under it are the registry's own questions (so a suggestion cannot ask for something no surface
answers), and the composer is the page's one input. The tiles moved to **`#/board`**, a registered surface with
its own module, its own nav entry and its own tests.

The stored-conversation column was taken off this face: it still carries the previous language, including a
destructive action drawn at content weight in hazard red, which is the defect the design philosophy already
recorded. It is reachable at `#/assistant` until it is rebuilt as a drawer.

## What was measured, not asserted

| Check | Result |
|---|---|
| `npx vitest run` | **65 files, 369 checks, all passing** |
| `npx tsc --noEmit` | clean |
| axe, front door | passes |
| axe, `#/board` | passes — after it caught a real defect: the board had no level-one heading |
| The animation | two frames 1.8 s apart differ by **0.35%** of pixels with motion allowed and **0.00%** under `prefers-reduced-motion` |
| Captures | `chat-*.png`, `board@1440.png`, motion and still pairs, in `research/design/ui-audit-20260918/` |

Two rendering defects were found by looking at captures rather than by reasoning:
1. a fixed 240 × 135 cell grid stretched over a wide band turned grain into vertical stripes and the sun's disc
   into an ellipse — the grid is now measured from the element, one cell ≈ 2.5 CSS px;
2. the band's height was a percentage of a stage that grows with the transcript, so the grain flooded the page —
   it is now measured against the viewport.

## Research that fed this

Broad rather than weather-app specific: *Komorebi-mediated ambient notifications for calm technology* (ACM) for
the idea that an interface can be lit rather than labelled; Framer's BayerDithering component for confirmation
that ordered dithering is a current design language rather than a nostalgia play; Equinox and macOS dynamic
wallpapers for a desktop that changes with the sun; god-ray and volumetric-light shader techniques for the
shafts; and domain-warped noise for what a cloud layer would need — which is exactly the layer this build cannot
draw honestly yet.

## Still not built

The board is still five national tiles: no library, no resize, no arrange, no per-place boards, no relevance
order, no *why these?*. The Work panel is not wired to the answer surface. Eighteen surfaces still carry the
previous language, and the chat face's conversation interior — transcript cards, the register switch, the
stored-conversation rail — is the next thing to migrate.



---

# The pocket sky, 18 September 2026

The brief: make the chat interface carry micro-animations — rain falling, cloud grazing at noon, morning rays,
evening birds, night stars twinkling — and give the page a central artefact, with the pixel language pushed as
far as it goes.

## The rule that made it possible

Every drawn thing in this product is one of exactly two kinds, and the caption and the legend say which:

| | What it is | Examples |
|---|---|---|
| **Painted from something** | astronomy, or a value a source returned | the sky bands, the sun or moon disc and its rays, the stars, the rain (only from the forecast's own millimetres for the hour covering now), the band along the ridge (only from a colour a district bulletin printed for today) |
| **Declared ambient** | decoration, named as decoration wherever it appears | the drifting cloud, and the birds of dawn and dusk |

The birds do not mean fair weather and a drifting cloud does not mean cloud cover — because no read this build
makes carries a cloud fraction for the hour being drawn. They are drawn because a person looking at a sky at
dusk sees birds, and the caption says *ambient: drifting cloud and birds at dusk (decoration)*.

The dawn and dusk windows are found from the sun, not from a clock, so the same rule holds in every season and
at every longitude: birds appear when the altitude is between −7° and 14° on the rising or setting side, and
never at noon.

## The artefact

**The pocket sky** (`src/light/Diorama.tsx`, rules in `src/light/scene.ts`): a place and an hour, eighty-four
pixels wide, drawn from the same scene rules as the field and stepped at eight frames a second. Every sprite
moves by whole pixels; the stars blink on a two-frame cycle and the birds flap on one, because that stepping is
what makes a drawn thing read as drawn rather than as a small render.

It sits **beside** the answer and never in front of it: the reading is first in reading order at every width, and
the artefact is a column beside it on a wide screen and a block below it on a phone. Clicking it asks the
conversation about that place; the chips under it point the whole field — sky, light and scene — at any place the
reader keeps.

`scene.ts` is a pure function of place, instant and reading, so the scene is tested without a canvas: eight
checks pin the stars to a low sun, the disc to the horizon, the birds to the dawn and dusk windows, the rain to
a read (and "no rain read" when there is none), the cloud drift to the wind, the published colour to the reading,
and the whole scene to determinism.

## Measured

| Check | Result |
|---|---|
| `npx vitest run` | **63 files, 361 checks, all passing** |
| scene rules | 8 checks, including "a drifting cloud is never read as cloud cover" |
| axe, front door | passes |
| Delivered frames | **59 fps at 1440, 60 fps at 390**, with both loops running (`tools/motion-probe.mjs`) |
| Captures | `pocket-0552ist.png`, `pocket-1312ist.png`, `pocket-1815ist.png`, `pocket-2221ist.png`, `pocket-now@390.png` |

## Still to do on this face

The transcript cards, the register switch and the stored-conversation drawer are still the previous language;
the artefact does not yet cycle through the reader's places on its own; and hovering a board tile does not yet
re-light the stage for that place.



---

# The living world, 18 September 2026

The instruction: keep the pocket sky, and make **the whole background** that. Every hour of the day should have
its own character, the field should be reactive to the second and to the reader, and the page should carry a
written line for the hour.

## What the page is now

One scene, drawn at three pixels to the cell, filling the stage:

| Layer | Where it comes from | How it moves |
|---|---|---|
| Sky bands | the light engine's four computed stops, quantised through a Bayer matrix to six levels | static; the whole palette changes with the sun |
| Sun or moon disc | the sun's computed altitude and azimuth; **the real moon**, with its own illuminated fraction from the elongation between sun and moon | the disc's position is astronomy, so it crosses the sky by itself |
| Star field | how far the sun is below the horizon — none above −6° | two-frame twinkle, per star phase |
| Shafts | the sun's position, strongest below 26° altitude | length steps on a four-frame cycle |
| Cloud | ambient, drifting on the wind read when one covers this hour | speed is a fraction of the sky per frame, so a wider sky drifts in the same wall-clock time |
| Birds | the two windows the **sun** decides (altitude −7° to 14°, rising or setting side) | three-pixel wings on a two-frame flap |
| Ridges, three deep | seeded per place, so two places are two places | parallax: the far layer moves six cells to the near layer's twelve |
| Valley haze | the visibility read | thicker as visibility falls |
| Heat dashes | the temperature read | only above 30 °C |
| Rain | the forecast's millimetres for the hour covering now | slant from the wind read |
| The published day | the colour a district bulletin printed for today | tinted along the far ridge line, never ruled across the picture |
| The reader | none — this one is decoration, and the legend says so | pointer parallax, a ring travelling out from a press |

**Eight phases, decided by the sun rather than by a clock**: late night, night, first light, morning, noon,
afternoon, golden hour, dusk. `phaseOf` uses altitude bands with a rising/setting side, so the same rule holds
in June and December, in Kutch and in Kohima. The foot legend names the phase, the sun, the rain, the
visibility, the wind, the published day and the read time.

## The line for the hour

`src/light/phrases.ts`, set in the human face because it is written, not sourced. Three rules keep it honest:

1. **No line contains a numeral.** A sentence with a number in it would need a source; this one has an author.
2. **A line never states a condition.** It talks about light, hours and the day's shape; where it touches the
   weather — rain, a published colour, real heat, real cold — it is the *reading* that selected the pool.
3. It is chosen by FNV-1a over the place and the quarter hour, so it holds still while you read and is different
   when you come back. (The first hash, `hash * 31`, was poorly spread modulo a small pool: four consecutive
   quarter hours all landed on the same line.)

It is withheld entirely when the read failed, because a pleasant sentence under a failed read is the page
enjoying itself at the reader's expense.

## Four faults that looking found, not reasoning

1. **The equation of time was missing from `solarPosition`.** A test written from an earlier readout disagreed
   with the engine, and the engine was wrong: up to sixteen minutes, which near the horizon is four degrees of
   altitude. The readout publishes that number and the disc is drawn from it, so the engine now carries it. The
   probe that shipped the wrong value said −1.4° where the sun was about +2.5°.
2. **The hazard band read as a chart.** Drawn along a ridge crest or straight across the sky it looked like a
   plotted series; it is now a tint on the furthest ridge *line* — light lying on land.
3. **The presence glow sat lit at the centre of the page before the reader moved**, washing the sky out from
   behind the sentence. It now waits for the first pointer movement.
4. **The sun's halo was an antialiased arc**, which on a three-pixel grid drew a fuzzy flower. It is
   whole-pixel and dithered now.

## Measured

| Check | Result |
|---|---|
| `npx vitest run` | **66 files, 374 checks, all passing** |
| `tsc --noEmit` | clean |
| axe, front door | passes |
| Delivered frames | **60 fps at 1440, 61 fps at 390** with the landscape at nine frames a second, the pocket sky at eight and the presence layer at the browser's rate |
| Captures | `world-0330`, `world-0535`, `world-0730`, `world-1200`, `world-1740`, `world-1830`, `world-2221`, `world-1200@390` |

`LivingSky` was deleted in this batch: the landscape is the same idea at the size of the page, and two
implementations of one sky would drift apart.



---

# Removing the pocket sky and refining the world, 18 September 2026

The instruction: take the framed artefact out, and make the whole background elegant rather than merely working.

## What was removed, and what took over its job

The pocket sky (`Diorama.tsx`, its frame, its caption and its row of place chips) is gone. It was a picture of
the same thing the page had already become, and a frame inside the picture was one frame too many.

Two of its jobs were real, and both were kept:

- **Choosing the place.** It is now a **plate** in the right-hand column: a place selector, the local time in
  the machine face, the phase of the day in words, and the published colour when one is in force. Set as a
  caption, not boxed as a widget.
- **Saying what is decoration.** The caption that named the drifting cloud and the birds as decoration lived
  under the pocket sky. That disclosure moved into the foot legend, where the pointer's light was already
  named. A local guardrail: the ambient layer must be named wherever it is drawn.

## What "elegant" turned out to require

Six measurements, each taken by looking at a capture rather than by reasoning about the code:

1. **Dither at the step, not over the field.** Six levels at amplitude 0.45 made the whole sky a dot mesh, which
   reads as a screen door. Eight levels at 0.16 means a pixel only flips where the gradient is about to change
   level: large calm areas, a fine stitched seam between them.
2. **Air between the ridges.** The furthest ridge now keeps most of the sky in it (74% at light, 60% dark), the
   middle keeps half, the near one keeps none. With the three tones closer than that they merged into one shape.
3. **Ridges that cannot cross.** The middle ridge was painting *upward* wherever its line rose above the near
   one, leaving a band unpainted and letting the dithered far layer show through as speckle at noon. The three
   lines are now clamped apart per column, and every fill is height-safe.
4. **No striped texture.** A hillside lightens towards its crest and darkens as it falls away. Every seventh
   column lightened — the previous texture — read as green speckle across the whole band in daylight.
5. **Grain scaled by brightness**, because a fixed grain on a night sky of value ten is a light show; and a
   **real integer hash** instead of `sin(x·k)`, which aliases into vertical stripes when sampled per pixel.
6. **A halo, not a flood.** The sun's glow reached half the sky at full strength and turned noon into a white
   bloom that swallowed the ridges. It is a sixteenth of the sky now, at 0.42.

Also tuned: haze is capped and cooler after dark; the published colour is two rows on the ridge line rather than
one saturated wire across the hill; shafts and cloud puffs were rebuilt (five rows, widest in the middle, lit on
top and shaded underneath) so cloud reads as cloud rather than as bars.

## Measured

| Check | Result |
|---|---|
| `npx vitest run` | **66 files, 374 checks, all passing** |
| `tsc --noEmit` | clean |
| axe, front door | passes |
| Delivered frames | **61 fps at 1440 and at 390** with the landscape at nine frames a second and the presence layer at the browser's rate |
| Captures | `world-0330`, `world-0535`, `world-0730`, `world-1200`, `world-1740`, `world-1830`, `world-2221` |



---

# Maturity: from 8-bit to air, 18 September 2026

The feedback: the page read as an 8-bit game rather than as a mature chat product, and the elegance was missing.

## The diagnosis, in plain terms

Four things were doing it, and all four were the *hand* rather than the idea:

1. **Three-pixel cells.** Every edge in the picture was a staircase: 480 cells across a 1440-wide page.
2. **Poster colour.** A saturated cyan noon and a magenta dusk, banded in eight hard levels.
3. **An outline on everything.** Every ridge carried a crest line, the published colour was a line, the light was
   dashes. Outlines are the sticker language.
4. **Pictograms.** Chunky cloud bars, bird glyphs, heat dashes: a sprite vocabulary rather than an atmospheric one.

## What changed

| Was | Is |
|---|---|
| Canvas at 3 px per cell, `image-rendering: pixelated` | Canvas at the display's own resolution, smooth gradients throughout |
| Eight hard levels, amplitude 0.45 | No banding in the field at all; the print texture moved to one CSS halftone screen over the top |
| Saturated palette | Chroma taken out, value range widened: grey-blue noon, violet-grey dusk, deep navy night |
| A crest line on every ridge | Outlines gone; the only line is a faint rim where low sun catches the far ridge, fading along its length |
| Chunky cloud bars, bird glyphs, heat dashes | Cloud as a drifting veil a few percent strong; haze as a band of light from the visibility read; rain as thin faint lines. Birds and heat dashes were **removed from the scene rules as well as the drawing** — dead data is a debt |
| Text sitting on whatever the sky happened to be | A **scrim** in the ground's own colour over the region the reader reads, and ink weights raised from 0.66/0.44 to 0.76/0.56 |

## Two failures the measurements caught

1. **The halftone screen was lightening the whole field.** Soft-light with paper-white dots *adds* light; the
   screen is now mid-tone dots between ink and ground, which is neutral.
2. **At golden hour the ink was light on a light sky.** The mode was a flag on a palette anchor, and the blend at
   +3° altitude sat between a dark anchor and a light one. The ink is now decided by **the luminance of the sky it
   will sit on**: above 0.45 the ink is dark, above 0.12 it is light-ish, below that it is night. Contrast is by
   construction, and it cannot make the mistake again.

## Measured

| Check | Result |
|---|---|
| `npx vitest run` | **66 files, 374 checks, all passing** |
| `tsc --noEmit` | clean |
| axe, front door | passes |
| Delivered frames | **57 fps at 1440, 61 fps at 390** |
| Captures | `field-0535` (first light), `field-1200` (noon), `field-1740` (golden hour), `field-1830` (dusk, with the real crescent moon), `field-2221` (night), `field-2221@390` |

## What is still coarse, and next

The **conversation's own chrome** is the last of the old language inside this face: transcript cards, the register
switch, the stored-conversation drawer, and the starter chips, which are still pills. The composer has been
softened but not rebuilt. That is the next pass, and it is where the remaining "product" maturity lives — the
field is now the background it should be.



---

# The welcome and the conversation: two states, 18 September 2026

The feedback: the background was hijacking the page, the elegance had gone, and the earlier version had something
the smooth field lost — **the fade across the middle of the page**.

## What was actually wrong

I had removed the *structure* while maturing the *hand*. The structure was doing the work: a sky that owns the
upper page and **dissolves** into a calm ground, with the conversation on the ground. Without it the field became
a flat wash with text floating in it, and then a scrim on top made it worse rather than better.

## The two states

| | Welcome | Once the chat starts |
|---|---|---|
| Sky | owns 40% of the stage, luminous at the horizon, dark at the zenith | **expands to 92%** |
| Field | full contrast, the view | **recedes to half opacity**, becomes a backdrop |
| Ground | the reading, the line for the hour, the openings, the composer | comes up to meet the transcript |
| Scrim | a light radial on the reading for contrast | a broad, stronger wash so the transcript is calm |

The switch is a boolean from the conversation (`AskSurface.onChatState`) onto `data-chat` on the stage; CSS does
the rest, with a 600ms transition on the seam, the field's opacity and the screens.

## What carries the taste now

1. **A decisive seam.** The fade runs from 10% above the sky line to 3% below it and reaches full ground, so no
   bright sky sits under a sentence. The earlier 17%-either-side version was soft to the point of leaving the type
   on the wrong side of it.
2. **One silhouette, not three ridges.** Place without scenery.
3. **A luminous horizon** — a band of the horizon colour, strongest at first light and golden hour — which is what
   makes a sky read as air rather than as a fill.
4. **Two print screens**: a fine one over the sky, a coarser paper one over the ground, so the lower half of the
   page is not a flat field.
5. **Type with confidence**: the reading at up to 2.75rem with tighter leading, the caveat moved from a paragraph
   into the small face, three short openings in one row with the full question as their accessible name, and a
   composer with a real shadow and a circular send.
6. **The haze and the published colour are still readings** — visibility and the district's printed colour — and
   the ambient cloud is still named as decoration in the legend.

## Measured this pass

- The welcome fits one screen at 1440×900 with the composer fully in view, at noon, first light and night.
- axe, front door: passes. `tsc`: clean. Suite: **66 files, 373 checks**.
- Captures: `welcome-1200`, `welcome-0535`, `welcome-1740`, `welcome-2221`, `chatting-1200`.



---

# The asset-library question, and the paper-cut turn, 18 September 2026

The user proposed curating a library of illustrated backgrounds — thousands of structures, one per phase — and asked
for an honest opinion. This is that opinion, recorded because the reasoning matters more than the answer.

## Against the library

1. **Rights.** "Load thousands" of illustrated scenes means paying an illustrator per scene, or using work we have
   no licence for. Neither is a design decision.
2. **It would make the background lie again.** A curated "evening" card is a fixed picture: it cannot know that
   Patna is under a yellow caution, that visibility is 1.2 km, or that rain is falling at 6 mm/h. It would be
   decoration keyed to a clock — the thing this project deleted. For 700+ districts we would also have to *choose*
   each place's landmark, which invents facts about places nobody verified.
3. **It removes the one thing no competitor has.** The field is painted from the same reads that answer questions.
   A picture library cannot be.

## For its grammar

What makes the reference charming is not the illustration but the *grammar*: flat cut-paper shapes, crisp edges, one
drawn sun, a warm restrained palette, generous geometry, wide letterspaced capitals. All of that is honest and
available — so the field took it:

| Now | Was |
|---|---|
| The sky laid down as eight flat bands with a short blend at each seam | one continuous gradient |
| The sun a drawn disc with one lighter arc inside it | a radial glow with a small circle in the middle |
| Two layers of cut paper for the land, each with a short shadow hanging under its own edge | one silhouette with a gradient fill |
| Cloud a flat blob, one path so the overlaps do not double | a soft radial veil |
| The ground in the dark or light anchor's own tone, not a blend between them | blended with the sky |

## Two faults found by measuring, not by reasoning

1. **The ground crossed over before the ink did.** At golden hour the ground had already blended to a mid grey from
   the daylight anchor while the ink was still light: measured `#746A66` behind the reading, about 3.4:1. Ground
   and ink now agree about which half of the day they are in — the ground's crossover sits at a brighter sky than
   the ink's.
2. **A leftover veil from the old stage was still painting over the ground.** `.l-veil` was removed from the page
   and from the stylesheet; the field draws its own seam now and does not need help.

Clouds were also cut to a third of their size: at four hundred pixels they were cartoon, not weather.

## Measured

| Check | Result |
|---|---|
| `npx vitest run` | **66 files, 373 checks, all passing** |
| `tsc --noEmit` | clean |
| axe, front door | passes |
| Delivered frames | 52–61 fps across the two widths |
| Captures | `paper-1200`, `paper-0535`, `paper-1740`, `paper-2221` |



---

# Adopting the card language, 18 September 2026

The user asked to adopt the referenced card completely — minimal, one artifact, wide capitals, a value strip — and
to make it scale to the whole project. This is that adoption, with one substitution that had to be made and one
that did not.

## Adopted one-for-one

| In the reference | Here |
|---|---|
| One centred card with a large radius and a soft shadow | the same, at 292px, radius 24px |
| A big flat illustration standing on a ground band | a flat mark standing on a ground band, with a paper shadow under it |
| A flat sun and one flat cloud | the real sun or moon at its own position, and one drifting cloud |
| Place name in wide letterspaced capitals | `KORBA`, `INDIA` — 0.3em tracking, in the phase's accent |
| A date line under it in the same treatment | `FRIDAY · 18 SEPT · 12:00` |
| A row of values with the current one large | the forecast's own hours, the hour covering now set at 33px and the rest at 14px |
| A warm flat field around the card | the computed field: the card takes the phase's own light |

## The substitution: what the artifact is

The reference puts a landmark in the middle — the Temple of Heaven for Beijing. We cannot do that honestly: for
seven hundred districts it would mean *choosing* a landmark for places nobody has verified, and inventing
something about each of them.

So the mark is the one thing every place already has and this machine already serves: **its own boundary.**
The district layer is real geometry with names and states; the land layer gives the country. The reader's place
gives a district, no place gives India, and the mark is drawn flat, projected with a latitude correction, and
outlined in **the colour the district bulletin printed for today** when one is in force. A district wearing
today's caution is the card's best moment, and it is not decoration.

That is also why it scales: no curation, no rights problem, no invented facts — every district in the country
already has a shape, so every reader already has an artifact.

## Noted, not fixed

The district layer is **1.5 MB for the whole country** and it is fetched once per session and cached
(`staleTime: Infinity`). A route that answers one district would be better; it is a backend change and it is on the
list rather than in the batch.

## Measured

| Check | Result |
|---|---|
| `npx vitest run` | **66 files, 373 checks, all passing** |
| `tsc --noEmit` | clean |
| axe, front door | passes |
| Captures | `card-1200` (India in the published yellow at noon), `card-1740` (golden hour), `card-0535`, `card-now@390` |



---

# The layered scene, 18 September 2026

Three references were given: **Overdrop** (flat vector, time-of-day gradients, OLED night), **Firewatch**
(independently moving SVG layers for depth) and **Vercel v0** (a chat floating in frosted glass). They agree on one
architecture, and this batch builds it.

## Five layers, each moving at its own rate

| Layer | Depth | What it is |
|---|---|---|
| sky | — | a CSS gradient, animated on its own: the whole time-of-day change happens here and nothing re-renders |
| far | 1 | a distant range, almost the colour of the sky |
| mid | 2 | a skyline, a treeline or hills: one tone, no detail |
| landmark | 3 | the focal drawing, standing on the ground at the right |
| near | 4 | a foreground band of bushes and stones that crops the bottom of the frame |
| disc | 2 | the sun or the moon, which travels down the sky as the day goes on |

Depth is CSS: the page publishes the pointer as `--px` and `--py`, and every layer multiplies them by its own
number. Nothing re-renders on a pointer move; the compositor does the work. Measured: **58 fps at 1440, 61 at 390.**

## The landmark, and what it is not

The focal drawing is chosen from the place's **state** — a fort in Gujarat and Rajasthan, a gopuram in the south, a
shikhara in the plains, a dome in the north-west, a slope in the hills, a lighthouse on the coast. It is a *stylistic*
choice and the legend says what it is: **an illustration, not a photograph of your place.** Nothing in it is a claim,
which is exactly why it can be drawn without inventing anything about anybody's city.

## Transitions

- The sky cross-fades between two stacked gradients over 1.4 s, so an hour turning is a slow change of light.
- The disc is positioned by the light engine and **animated by CSS** (2.4 s on left and top), so the sun physically
  travels down and the moon rises, exactly as asked.
- Changing place cross-fades the drawn layers out and in over 620 ms with a small rise, so a new district reads as a
  cut between scenes rather than a reload.
- The welcome rises in two beats rather than appearing.

## The chat, blended rather than pasted

- One column, **centred**, 720px, floating over the scene.
- **At the welcome there is no panel at all** — the artwork owns the screen and the words sit on it.
- Once there is a conversation, the column becomes frosted glass (`backdrop-filter: blur(16px)`) so the scene bleeds
  through, with a hairline and a deep shadow.
- The scene steps back to 40% and scales up 2% while the chat is in use, so the artwork stays present without
  competing.

## Five faults found by looking

1. The disc's vertical mapping was inverted: the noon sun sat on the sentence. It is now kept inside the sky band.
2. The foreground band was almost white in daylight, so the depth did not read. Nearer is darker now.
3. The landmark borrowed the ground's colour and came out as mud. It has its own three tones: a roof that takes the
   hour's colour, a body in warm stone, and the accent for the details.
4. The far range vanished in daylight; it is a touch deeper now.
5. On a phone the words pushed the drawing below the fold. The welcome starts higher on a narrow screen.

## Measured

**66 files / 373 checks passing**, `tsc` clean, axe green, 58/61 fps. Captures: `fwatch-1200`, `fwatch-1740`,
`fwatch-0535`, `fwatch-2221`, `fwatch-1200@390`.



---

# Real palettes, real photographs, 18 September 2026

The feedback: the work was poor, stop drawing, use the internet, and give the chat a spotlight. Three things
changed.

## 1. The specified palettes are now the light engine's anchors

Daybreak, High Noon and Deep Night were given as calibrated stops with their glass pairs; dusk is drawn in the same
discipline (violet through rose to amber). They are **anchors of a ramp, not four fixed pictures**: the engine
interpolates between them by the sun's own altitude, and it chooses the dawn ladder or the dusk ladder by the sun's
azimuth, so 06:00 and 18:00 at the same altitude are different light.

## 2. Five real photographs, licensed and credited

Downloaded from Wikimedia Commons, converted to WebP, vendored into the bundle:

| frame | what it is | licence | author |
|---|---|---|---|
| dawn | Early Morning at Ajmer, Rajasthan | CC BY-SA 4.0 | Neeti0145 |
| day | Bright blue sky with cloud patterns | **CC0** | Trixia Lao |
| dusk | Monsoon clouds in Bengal | CC BY 2.0 | Rajarshi Mitra |
| night | Milky Way over India | CC BY-SA 4.0 | Nikhil More |
| rain | Rain clouds, Bramble Bay | **CC0** | John Robert McPherson |

Licences and sources are recorded in `research/design/SKY-CREDITS.json`, the files are attributed in the legend, and
the whole set is **772 KB** after conversion. The frame is chosen by the hour, and the rain frame **only when a read
returned rain** for the hour covering now.

The photograph sits over the gradient at 30% in soft-light: the palette is the engine's and the photograph is its
texture, which is also what stops a large gradient banding. On top of that, an SVG turbulence grain at **3%**, as
specified.

## 3. The chat is the centrepiece

One frosted panel, centred, on the photograph, with a big composer as the largest thing in it. The glass pair comes
from the palette: white glass with charcoal text for Daybreak and Noon, black glass with white text for Dusk and
Night, per the specification. Once the conversation starts the panel thickens and the sky recedes.

## Two real bugs, found by measuring

1. **A temporal dead zone blanked the whole page.** The palette tables call `mix` at module load and `mix` was
   declared below them. The bundle threw `Cannot access 'X' before initialization` and rendered nothing. The
   colour helpers are now declared above the tables that use them.
2. **The glass decides the ink, not the sky.** The old rule measured sky luminance to choose light or dark text.
   High Noon's zenith is a deep saturated azure, so luminance called it "dark" and asked for white ink on a white
   panel. Each named palette comes with its glass pair, so the anchor carries the answer and the mode comes from the
   palette the sky is nearest. The ground follows the same decision.

## Measured

**66 files / 373 checks passing**, `tsc` clean, axe green. **50 fps at 1440, 60 at 390** — down from 58 at 1440
because the photograph, the grain and two blend modes cost real pixels. Noted rather than hidden.

## Not done, deliberately

- No CodePen or LottieFiles code was taken. CodePen's terms do not license reuse, and Lottie asset licences vary per
  file; the photographs above are the internet contribution here.
- The conversation interior is still the old design — receipt tables, pills, transcript cards. That remains the
  largest visible gap inside this shell.


---

# The ChatGPT architecture, 19 September 2026

The feedback: brainstorm recursively, keep taking references, add the subtle background detail, and replicate the
**ChatGPT architecture** while keeping our language. All four are in this batch.

## The shape

| | Welcome | Once there are turns |
|---|---|---|
| panel | one frosted panel, **centred**, with the opening inside it | the same panel, full height |
| question box | the hero, in the middle of the screen | docked to the foot of the column |
| openings | three quiet buttons **under the box** | gone: the conversation has started |
| page | fixed at 100dvh with overflow hidden | the transcript scrolls **inside** the panel |

That last row is the whole reason the architecture works: the page never scrolls, so the bar, the panel top and
the legend stay where the reader left them while a long answer is read.

The reader question is a right-aligned bubble and the machine answer is a plain column, the way a reader has been
taught to expect, with provenance attached to the values rather than to the bubble.

## The subtle layer

SkyDetail draws three motifs in one ink at 7%, masked away from the middle so they live at the edges of the page:

1. a **graticule** — latitude and longitude lines, because the bar already prints coordinates;
2. **contours** — topographic rings in two corners;
3. a **tick ring** — the bearing marks of a compass rose.

With the specified SVG grain at 3% over the gradient, that is the subtle SVG the background was missing. All
three are declared decoration in the legend, like everything else that is not a reading.

## The incident, recorded because it happened

While removing the dead rules of the drawn layers, **a scripted edit truncated the stylesheet** from about 700
lines to 171, and a second pass made it worse by clipping comments mid-sentence. The build failed and the page
rendered nothing. The damage was recovered **from the compiled artefact of the last good build**:
web/dist/assets/main-*.css still held every rule the light layer had, in order, and the rules whose selectors
belong to this layer were written back as source with a header saying where they came from.

Two lessons, both kept:

1. **No scripted surgery on a stylesheet.** Removing rules is a deliberate edit with exact strings, not a regular
   expression over a file with comments in it.
2. **A compiled artefact is evidence.** The last good build was the only complete copy of the stylesheet left.

## Measured

| Check | Result |
|---|---|
| npx vitest run | **66 files, 373 checks, all passing** |
| tsc --noEmit | clean |
| axe, 21 surfaces at 1440 | **21 passed** in 1.3 min (slow, not broken) |
| captures | gpt4-empty-1200, gpt4-chat-1200, gpt4-chat-2221 |

