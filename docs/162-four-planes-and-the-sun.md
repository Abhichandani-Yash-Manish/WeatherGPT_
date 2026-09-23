# 162 — Four planes, and the light that is actually the sun

> **The gap.** Three rounds of review said the same thing in different words: pale, monotonous, nothing
> memorable, a background that does not feel alive. They were one fault. Every surface in the product sat
> inside a tenth of a luminance step of every other, so there was nothing for the eye to rank — and nothing
> for a moving layer to be drawn against. A contour at a fifth of an alpha on near-white paper is invisible
> however fast it moves, which is why four attempts at "make the background alive" all failed.

23 September 2026, continuing docs/161. Local implementation and measured verification; no deployment or
PS acceptance claim.

---

## Four planes, ranked

| plane | luminance | what it is |
|---|---|---|
| rail | 0.008 | near-black. Chrome. Not where you read |
| bar | 0.58–0.64 | grey. Which conversation this is, and the controls that act on it |
| ground | 0.74–0.83 | the living surface. Where the atmosphere is, and dark enough to finally see it on |
| sheet | 0.97–1.00 | white. The conversation. The brightest thing on screen, because it is the product |

That last row is the point. A chat screen whose chat is a layer underneath a decoration has the wrong hero.
Putting the turns on white sheets over the living ground promotes the conversation *and* gives the
atmosphere somewhere to live — it no longer has to be dimmed to a third to stay out of the prose's way,
because it is no longer behind the prose.

## The light is the sun

The glow behind the page is positioned from the real solar altitude and hour angle at the reader's held
place, from the same solver `DayArc` is plotted from. It rises at screen left, arcs over through the
morning, sets at the right, and goes out below the horizon leaving the cool ambient alone.

So the arc on the front door and the light behind the whole page are **one fact stated twice** — one you
read, one you only feel. At four in the afternoon the page is lit from the west, because it is.

It is CSS, not canvas: two large radial gradients moved on transform and opacity are composited on the GPU
and cost the main thread nothing. The same shapes redrawn per frame on canvas were the most expensive fills
in the product.

## The day goes cool at midnight

The second revision made the whole day warm, including 02:00, and warm light at two in the morning reads as
a lamp somebody left on. The four hours now travel: cool slate at midnight, warm at first light, neutral
and bright at high sun, umber at dusk. The amber accent does **not** travel with it — an amber lamp in a
cool grey room is one of the strongest pairings there is, and a fixed accent is what makes the ground's own
temperature legible as a change rather than as a different product.

## A bare selector was overriding the whole design

The dashboard's send button was blue. Not a stale build:

```css
[data-hour='noon'] { --g-send-bg: linear-gradient(180deg, #2a68d8, #1f5ccc); ... }
```

`.g` carries `data-hour` too, and **a declaration on an element beats a value inherited from its parent**.
So every token in those four fallback blocks was overriding both the active design's palette and the live
inline spectrum, for everything inside the shell. The root got the right values and nothing below it did.

This is the third time this exact fault has been found in this project, and it survives because it fails
silently — the page still renders, just in the wrong palette. Scoped to `:root`, those blocks are the
fallback they were always meant to be. The blue send button, the yellow question bubble and a cyan rail
film all went with it.

## One pass across all nineteen surfaces

- **A card is the same white sheet the conversation uses.** `--g-fill` was solving to a translucent
  gradient, so every module card was warm glass while the answer sheets beside them were opaque white.
- **Every value is set in the numeral face.** It had reached the conversation's claims and the arc and
  nowhere else, so the dashboard's `26.4` was still in the UI sans.
- **The "ask instead" links moved below the content.** They sat between a surface's own finding and the
  tables that prove it. A keyboard user now reaches the instrument before the escape hatch, and
  `map.gaps.test.tsx` records the new tab order.
- **Place labels collapsed for display.** "Anand, Anand, State of Gujarāt" was printing three times on one
  screen. The engine, every source line and every citation still get the catalogue's full label.
- **The bar sizes to its content.** Its station chip grew a second row for the receipt and overflowed a
  fixed 68px min-height, clipping the place name against the bar's own edge.
- **The masthead states the held place**, not the station's — the station's is not known until its read
  lands, so for the first seconds of every visit it said "No place held" while the composer named the place.

## Measured

```
frontend  npx vitest run            90 suites, 594 checks, 0 failed
frontend  npx tsc --noEmit          clean
repo      audit_react_frontend.py   19 checks, 0 failed
backend   pytest tests -q           1630 passed
repo      check_status_drift.py     0 problem(s)
```

**Frame cost**, headless software rasterisation, 390 frames at 1440×900 DPR 2: mean 11.2 ms, **median
9.8 ms**, p95 25.6 ms, 27 frames over the 16.7 ms a 60 fps budget allows. The p95 is the slow layer's
rebuild, which lands whole on whichever frame it falls on. This is before any of the compositing a real GPU
does for free, and it is not a claim about a real device.

**No horizontal page scroll** at 768px or 390px (`scrollWidth === innerWidth` at both). The elements that
report as overflowing are the atmosphere, which is clipped by its own container, and the off-canvas rail.

## Limits carried forward

- **The frame measurement is software rasterisation in headless Chromium.** It is the honest number for
  what the code costs; it is not a measurement on named hardware and no device benchmark was run.
- **The surface pass was systemic, not compositional.** Material, numerals, card treatment and the order of
  the suggestion row now reach all nineteen. Individual surfaces — Watch's operator vocabulary, the map's
  legend, the document catalogue's density — have not each had their own composition reviewed.
- **Reduced motion draws one still and no firing.** A trail is motion by construction; that is a deliberate
  absence rather than a fallback.
- The build still reports the pre-existing large main-chunk warning.
