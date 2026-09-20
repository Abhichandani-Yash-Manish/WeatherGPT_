# 134 — The light and the material

*21 September 2026. The light-and-material workstream of the 21 September batch. It owned
`frontend/src/gpt/`.*

The brief had four parts: a continuous colour spectrum across the day, a frosted-glass integration for the
support elements, an end to the monotony of the per-component palette, and a mature product in both
regimes. The first was already built, and measuring it is what produced the batch's own finding: **the
function was continuous and the page was not.** What follows is measured, in the order it was measured.

## The spectrum reached the root and nothing under it

`spectrum.ts` computes thirty-two custom properties from the sun's own altitude and hour angle at the
reader's own place, once a minute, and `Field.tsx` writes them as an inline style on
`document.documentElement`. The four static hour palettes in `tokens.css` were written as bare
`[data-hour='...']` blocks. `data-hour` is set on **two** elements — the document element, where `orb.ts`
reads it, and `.g`, from `Workspace.tsx`'s own JSX — so the `.g` element matched those blocks too, and a
declaration on an element beats its parent's inline style. Every property the spectrum wrote was shadowed
one level below the element it was written on.

Measured on the running app at 17:00 IST, 21 September, through the page's own `getComputedStyle`:

| property | document element (what the spectrum wrote) | `.g`, `.g-field-sky`, `.g-rail` (what the reader saw) |
| --- | --- | --- |
| `--g-sky-1` | `#332a43` | `#c4d9f5` |
| `--g-rail-tint` | `rgba(185, 165, 230, 0.049)` | `rgba(31, 92, 204, 0.04)` |

The second column is the static `[data-hour='noon']` block, verbatim. So the sky at five in the afternoon
was the noon sky, and the three component tints commit 0584031 added had never been on screen. That commit's
message says the rail, the top bar and a reader's own bubble "stopped being one grey repeated three times";
that was true of the function and false of the page. The reader's complaint — *"the website theme right now
is very monotonous"* — was still correct after the commit that answered it, and this is why.

It was also why `tools/hours.mjs` had been reporting a drift nobody could see: it read the document element,
which is the writer, rather than the elements that paint. The tool now reads the element each property is
actually drawn on, prints both values where they differ, and says so in its own output when they do. Its
final line is the point of it:

    root and painted element agree at every frame.

**The repair is at the cause.** The four hour blocks in `tokens.css` are declared on the document element,
which is the one element the spectrum writes on, and the `.g` element — which still carries `data-hour` for
the scripts and the structural selectors that key off it — now **defers every property the spectrum owns
back to the document element**, naming all thirty-two one by one, so its own match on those blocks cannot
win. A declaration on `.g` cannot shadow a value again, and a token
added to `spectrum.ts` without being added to that deferral is a visible omission: `materials.test.ts` holds
the two lists to each other. (The four `[data-hour]` blocks keep the form the frontend audit reads them in,
and FE14/FE15/FE16 still pass on them.)

Worth recording plainly: the "reader with JavaScript off sees the four rooms" claim both files made was
never true either, because `data-hour` is only ever set by React. With JavaScript off there is no hour
attribute anywhere and the page falls back to the `:root` defaults. The static blocks are a declaration of
the palette's intent; they are not a fallback that has ever run.

## The ink was measured against its own shadow

With the wiring repaired, the second fault became visible immediately. `spectrum.ts` drove the **ink** on
solar altitude (`criticalAt`, a clean flip at −6° climbing and +8° falling) and the **atmosphere** on the
hour angle. Over a day the two clocks disagreed for up to an hour and a half, and at those instants the page
put near-black ink on a sky that had already gone to dusk.

A minute-resolution sweep over three places and both solstices, measuring `--g-paper` and `--g-mist` against
the gradient band the text actually stands on (`.g-field-sky`'s radial over its linear gradient, composited
at the points where text is drawn):

    before:  22,619 readings under 4.5:1;  the worst 1.001:1
             Kanyakumari 21 June 12:30Z, altitude 8.1° — NOON_C's #121a27 on GOLDEN_D's #3b334d

`spectrum.test.ts` had not caught it because it compared the ink against `--g-bg`, and `--g-bg` is computed
from the ink's own clock. The ink was being measured against its own shadow. That check now measures the band
as well, and adds a minute-resolution sweep through each of the two flips, because a flip is where a 1.001:1
sample lives.

**The repair is physical rather than a tuning.** With the paper this product uses (near-black, relative
luminance 0.012, and near-white, 0.85) there is no ground luminance at which *both* clear 4.5:1 — the
crossover sits at 3.84:1. A ground that drifts across that band is unreadable whichever ink is in force, so
the ground cannot be continuous through it. The sky now shares the ink's own two altitudes and flips with it,
and inside each regime it still drifts: the day from a dull wide sky toward a saturated noon, the night from
the deep sky toward first light. The auras, the halo, the mood strength and the watermark keep the 24-hour
clock, because none of them is ever read as text.

Nothing about the ground's structure changed: the same five layers, the same gradient, the same auras, grain,
vignette and one mark. What changed is when the gradient lightens.

One consequence worth stating, because it is a design decision and not a leftover: the sky's two day anchors
are **both blue**, and the warmth of a low sun lives in the auras, the vignette and the twilight palettes.
That is not a simplification. The atmosphere and the materials now drift in OKLab's polar form — lightness,
chroma and hue angle, hue taking the short way round — because an sRGB line from the dawn's cream to the
day's blue spends the middle of every sunrise at chroma 0.005, and a neutral sky is a sky that erases the
difference between the surfaces standing on it. The dawn frame is a rose sky rather than a grey one, and that
is the arithmetic showing: a real sunrise goes cream, rose, lavender, blue.

## The materials: four surfaces, one sun

The monotony was not only the wiring. The rail, the top bar and a reader's own bubble carried fills within
0.04 and 0.068 alpha of one another — a partition that exists in the file and not in the eye. The brief's
own test decides it: a glass pane over a flat opaque panel is decoration; a glass pane over a graded sky is
an effect.

So each support surface is now a **translucent film over the ground**, and what each film says is how much
of the hour's light that material catches, at what temperature:

| material | what it is | how it reads |
| --- | --- | --- |
| the rail | the shade | the deepest and densest film; on a light page it is deeper than the sky, and after dark, where the ground is nearly the void, it is the one that takes the hour's remaining light. Its hue is the sky's own turned 30° cool. |
| the top bar | the light | the thinnest film and the least the ground's own colour: a warm pale over a cool sky, a cool pale over a night one. |
| the reader's bubble | the warmth | the only warm surface in the product, and the most chromatic. |
| the machine's pane | the instrument | the one surface carrying the product's own accent hue; the answer itself stays unboxed, and this is what its evidence sits on. |

Each material is defined **against the ground it sits on** rather than by an absolute colour of its own: a
lightness offset, a chroma offset and a hue. That is what makes the separation structural rather than
incidental. Two earlier attempts were measured and rejected: hand-picked films at the four hours drifted past
each other between the anchors (the rail and the bar came within 0.0005 of each other in OKLab chroma at
Kanyakumari on 21 June), and a rail that followed a fixed hue while the ground's hue swept 190° through a day
ended at 0.9 alpha — a film so dense it had stopped being glass — while still landing short of the colour
asked for. The hue offsets are placed in the arc the ground's own hue never enters (70°–250°): the rail at
235°, the bar at 205°, and the reader's bubble at 95°, which is the only warm hue inside that arc. A gold
bubble rather than an amber one is the one place this palette gives something up to the measurement, because
an amber is a hue the sky passes through on the way to dawn, and two colours with the same hue are not two
materials.

## What was measured

`tools/hours.mjs` installs a fixed clock in the page and captures one route across the day, reading each
value from the element that paints it. This is the 06:00–22:00 run on 21 September after the repair:

| hour | hour attr. | sky | rail film (painted) | bar film (painted) | bubble film (root and painted) |
| --- | --- | --- | --- | --- | --- |
| 06:00 | daybreak | `#eedced` | `rgba(134, 218, 245, 0.52)` | `rgba(230, 247, 242, 0.75)` | `rgba(227, 212, 87, 0.46)` |
| 08:00 | noon | `#d4e1f2` | `rgba(156, 208, 232, 0.52)` | `rgba(255, 254, 232, 0.416)` | `rgba(241, 202, 82, 0.46)` |
| 12:00 | noon | `#c4d9f5` | `rgba(133, 202, 232, 0.52)` | `rgba(246, 248, 211, 0.416)` | `rgba(243, 189, 29, 0.46)` |
| 16:00 | noon | `#d6e1f1` | `rgba(158, 208, 231, 0.52)` | `rgba(252, 254, 234, 0.416)` | `rgba(240, 202, 87, 0.46)` |
| 18:00 | golden | `#12152a` | `rgba(0, 65, 98, 0.5)` | `rgba(93, 126, 47, 0.2)` | `rgba(134, 65, 4, 0.672)` |
| 22:00 | night | `#080f21` | `rgba(0, 43, 63, 0.8)` | `rgba(98, 110, 43, 0.2)` | `rgba(108, 51, 0, 0.75)` |

    frames: 9 | distinct colour states: 8
    root and painted element agree at every frame.

Eight states, not nine, and the tool says so itself: 20:00 and 22:00 are the same frame because the night
sky's own drift has reached its deep end and has nothing left to move that a screenshot can see.

Contrast, measured over the sweep (three places × both solstices × every fifteen solar minutes, and at
one-minute resolution through each of the two regime flips). Floor is WCAG AA — 4.5:1 for body text, 3:1 for
non-text — and every pair is composited as the stylesheet composites it:

| pair | worst | where |
| --- | --- | --- |
| `--g-paper` on the sky band | **12.13:1** | Kanyakumari 21 June, 74.6° |
| `--g-mist` on the sky band | **5.55:1** | Kanyakumari 21 June, 74.6° |
| `--g-paper` on the rail | **10.30:1** | Kanyakumari 21 June, 7.6° |
| `--g-mist` on the rail | **4.75:1** | Kanyakumari 21 June, 7.6° |
| `--g-paper` / `--g-mist` on the bar | **10.31 / 4.76:1** | Kanyakumari 21 June, 7.6° |
| `--g-paper` on the reader's bubble | **7.42:1** | Kanyakumari 21 June, 7.6° |
| `--g-paper` / `--g-mist` on the pane | **12.18 / 5.62:1** | Nagpur 21 June, 6.9° |
| the rail's and the bar's own icon inks | **4.76 / 4.82:1** | Kanyakumari 21 June, 7.6° |
| `--g-mist-2` on the ground and the pane | **3.74 / 3.38:1** | Kanyakumari 21 June, 7.6° |

The `--g-mist-2` figures are at the non-text floor because that is what the step is for: the product's own
FE14 rule reserves it for edges, hairlines and the machine's quietest metadata, and quiet *text* takes
`--g-mist`. Five places inside this batch's own files were crossing that line and are repaired: a
conversation row's question, a claim's provenance line, a fold's count, a row's own drop control and the
rail search's placeholder were all set in the tertiary step.

Separation, in OKLab, worst over the same sweep:

| pair | worst chroma | worst hue |
| --- | --- | --- |
| rail / bar | 0.0303 | 21.3° |
| rail / bubble | 0.0164 | 136.1° |
| rail / ground | 0.0142 | **18.1°** |
| bar / bubble | 0.0508 | 98.8° |
| bar / ground | **0.0128** | 42.2° |
| bubble / ground | 0.0364 | 26.9° |

The floors in `materials.test.ts` are set just under those measurements — 0.010 of OKLab chroma and 15° of
hue for every pair at every sampled instant — and the numbers are in the test's own comment so the claim can
be re-checked rather than believed. What they are worth is stated there too: 15° of hue at these chromas is
a visible shift on a 268px-wide column, and 0.010 of chroma is about a tenth of the distance between the noon
sky and a white page. This document does not claim the four materials are obviously different. It claims they
are measurably different, at every instant of a day, and the difference is of a size the eye can resolve on a
flat area.

## Where the evidence is

The hour sweeps, the captures and the tool's own JSON reports are preserved under
`research/reviews/light-and-material-20260921/`: `hours-before/` is the same nine frames taken before the
repair (where the tool read the root, and the reader saw the static blocks), `hours-after/` is the run above,
and `capture-report.json` records the sixteen full-page captures at four widths in both colour schemes, with
zero overflow and zero failed requests.

## Motion

Four decisions were taken from the reference set in `tmp/design-refs/transitions-dev/` (Jakub Antalik, read
as reference and not copied — the repository carries no licence file), re-authored on this product's own
tokens and named where they are used:

- **Panel reveal** (pattern 07): opening a column and closing it are not the same motion, so the rail's
  collapse and the reading panel's arrival take `--g-enter` (400ms) and its release takes `--g-exit` (320ms),
  on an exponential-out curve. The panel also takes the pattern's short cross-blur, because a panel arriving
  from the edge of a page with a hard edge reads as a page moving rather than as a panel opening.
- **Text states swap** (pattern 04): the greeting changes when the hour changes, on the element the reader is
  looking at rather than on a container. The exit half of that pattern animates the outgoing text and React
  replaces the text node in one commit, so what is taken is the entrance — a 3px blur and an 8px rise on
  `--g-enter`.
- **Icon swap** (pattern 09) supplied the duration only: `--g-icon-swap`, 180ms, kept for the next batch that
  needs two glyphs in one slot. Nothing in this batch uses it.
- **Accordion** (pattern 21): the claim's fold already unfolds with the same rise, and its height is the
  `<details>` element's own; replacing that with the pattern's grid-rows technique would trade a native
  element for a smoother animation on a control a reader opens once. Left as it is.

Everything added is stilled by `surfaces.css`'s existing `prefers-reduced-motion` block, which zeroes every
transition and animation inside `.g`. That was checked rather than assumed: the block is global, the rail and
the panel are inside `.g`, and the only motion outside it is the one the product already had.

## What this batch deliberately did not do

- **It did not touch the ground's concept.** No layer was added or removed; the gradient, the auras, the
  grain, the vignette and the one mark are the layers docs/111 settled. What changed is the clock the
  gradient's lightness runs on, and the reason is in the contrast measurement above rather than in taste.
- **It did not box the answer.** The machine's material is carried by what its evidence sits on — the
  supporting claims, the transcript, a pane — because the lead claim is a statement on the ground and the
  column is the answer's container. The user's brief asked for "the chat bubbles" to carry identity; the
  reader's bubble does, and the machine's is its evidence rather than a wrapper around its prose.
- **It did not put the quote line on glass.** The welcome's own comment refuses a panel there, and it is
  already the quietest thing on the screen. A pane behind a line of verse that sits on the sky would be the
  decoration this batch's brief names as the failure mode.
- **It did not adopt a component library.** rareui.com, obsidianui.dev and 21st.dev were read as interaction
  references; `docs/98` declined HeroUI and Tremor for bundle budget and nothing was added.
- **It did not use designspells.com.** The site sits behind a Vercel bot check and could not be read from
  this machine.
- **It did not copy anything from the transition references.** They are a decisions reference; the durations
  and curves are in this product's own token names and every use names the pattern it came from.

## What this does not claim

The sweep proves a property of the palette, not of the page. It composites the two gradients the stylesheet
declares; it does not run a browser, so an element that paints a *third* background over the sky, a gradient
the stylesheet gains later, or an ink a component chooses for itself are all outside it. The in-browser axe
run remains the check on the rendered page, and it still disables its own contrast rule.

Contrast is proven against the materials at the two bands each is drawn on — the top of the sky for the rail
and the bar, the middle for the bubble and the pane. A surface that moves between bands moves outside that
proof.

The separation floors are the design's own worst measured values, not a perceptual standard: they say the
materials are measurably different, not that a reader will name them. No reader has looked at this, and the
four-hour sweep is one render on one machine.

The materials' opacity is set per minute by the geometry of the colour they have to reach, and it is not
uniform: over the light hours the rail's film is 0.52 and the bar's 0.42, so the sky reads through both, while
at the deepest night the rail's is 0.80 and the reader's bubble's 0.75. That is the honest cost of a hue
rotation at a fixed lightness — a thin film cannot turn the ground's colour, and there is little light at
night to filter in the first place. The frosted effect is real where the reader spends most of the day and
weakest where there is least to see through.

`--g-mist-2` is still used as text in four places outside this batch's files (`g-work-detail`, `g-work-ms`,
`g-work-glyph`, `g-receipt-key`), where it measures 3.74:1 on the ground. FE14's rule says quiet text takes
the mist step and the tertiary step belongs to surfaces; those four are un-swept, and this batch did not
change them.
