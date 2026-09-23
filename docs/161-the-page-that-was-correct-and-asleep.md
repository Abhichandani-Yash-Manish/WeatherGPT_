# 161 — The page was correct, and asleep

> **The gap.** The first implementation of Meridian kept its promise of a calm light interface by freezing
> it: one set of hex values, a static PNG of contour lines drifting eight pixels on a loop, and an audit
> check that forbade the ground from being computed at all. Every detail was right and nothing on the page
> was alive. A reader could not tell 06:00 from 23:00, and the largest thing on an answer was a note about
> who had written the sentence.
>
> **The correction.** Frozen is not the same as calm. This batch gives the page back its light, its
> weather and its hierarchy, and replaces the check that banned the code path with one that measures the
> property it was protecting.

23 September 2026. Local implementation and scoped verification; no deployment or PS acceptance claim.

---

## What was wrong, measured rather than felt

| | before | now |
|---|---|---|
| ground | one frozen palette, identical at every hour | Meridian's own four hours, drifting on the real sun |
| atmosphere | a 32 KB PNG at `opacity: .55`, invisible in practice | a contoured pressure field and a geostrophic flow, drawn |
| the retrieved value | 28px, no surface, fourth in the visual order | display size on its own plate, first |
| the value's honesty | animated from `0` through ~40 numbers nobody published | exact from its first painted frame |
| the front door | a 96px moon in a blurred halo | a 252px dial of today, solved from the sun |
| the brand mark | a raster scaled to 150% of its box | drawn, and the sun on it is where the sun is |
| working turn | 12px stage, printed twice in the first seconds | the stage is the largest thing on the turn |
| frontend checks | 559 across 85 suites | **587 across 89 suites** |

## The light moves and never leaves

`spectrum.ts` already held a complete forced-light family and a solver for the sun's position at the
reader's own held place. The previous batch could not use it, because the only light family it had was a
*blue* one, and Meridian is mineral white. So Meridian got its own four anchors — `MERIDIAN_NIGHT_C`,
`MERIDIAN_DAYBREAK_C`, `MERIDIAN_NOON_C`, `MERIDIAN_DUSK_C` — and `composeSpectrum` was split out of
`spectrumAt` so both families reach the same sixty lines of wash ladder, fill and elevation.

`MERIDIAN_NOON_C` is the selected reference to the hex. The day departs from it gently in both directions
and returns. It never crosses into the dark family at any hour or latitude.

**The selector was the whole bug.** The token block used to be declared on `:root[data-design='meridian']`
*and* `.g[data-design='meridian']`. `.g` carries the same attribute, and a declaration on an element beats
its parent's inline style — so every value the ground computed reached the document element and nothing
below it. The palette was live and the page was frozen, which is the hardest kind of dead code to see,
because everything works.

## The atmosphere is the thing the PNG was a picture of

Two canvases, `skyfield.ts`:

- **The field.** Six drifting pressure centres over a broad tilt, contoured at eleven levels by marching
  squares, with every third isobar drawn heavier the way a synoptic chart bolds one. Under it, a tonal
  wash — a warm pool at each high, a cool one at each low, both within a few per cent of the ground and
  both in the *same* family, because two saturated tints on a weather product get read as a legend.
- **The wind.** 190 trails advected along the field's gradient rotated ninety degrees, which is
  geostrophic balance and is why they curl around a centre instead of falling into it. The two layers
  cannot disagree, because they are the same field.

It answers to three real states: `pace` (resting, working, being typed into), `tension` (the contours
tighten while a request is in flight — busy, never how far along), and `bearing` (the sun's own hour
angle). It steps down to about a third while an answer is on screen and back up while the engine works.

It is decoration and says so: `aria-hidden`, no role, no label, no legend, never derived from a retrieved
value, and held far below the contrast at which a reader would try to read it.

## The value stopped lying for a flourish

`AnimatedNumber` counted from zero to the retrieved value over 900ms. For most of a second the page
displayed measurements at display size, in the machine face, beside a real source and a real window, that
the source never published — and any screenshot, print or photograph taken inside that window captured
one. The engine spends a whole retrieval layer refusing to state what it has not read.

The value is now exact from its first painted frame; what moves is the presentation of it. Five tests pin
it, including that a `0.0` reading stays distinguishable from an absent one.

## FE15 stopped banning the code path

The audit check read *"the selected light interface is stable across solar hours"* and enforced it with
`"applySpectrum(" not in Field.tsx`. That banned the mechanism instead of measuring the property, at two
costs: a palette that went dark by some other route would have passed, and "light" came to mean "one
frozen set of values".

It now checks the wiring it can see — the light colour-scheme, that Field drives Meridian's own family and
not the solar one that flips — and the property is measured in `meridianSpectrum.test.ts`: every fifteen
minutes of a full day at four latitudes from Kanyakumari to Leh, the ground stays pale, the ink stays
dark, every ink clears AA on every ground, the four hazard colours are never written, and the day is
*required to differ between its hours*.

## Verified

```
frontend  npx vitest run            89 suites, 587 checks, 0 failed
frontend  npx tsc --noEmit          clean
repo      audit_react_frontend.py   19 checks, 0 failed
backend   pytest tests -q           1630 passed
repo      check_status_drift.py     0 problem(s)
```

The dial's astronomy is checked against published almanac times for Pune, Delhi and Kochi at the equinox
and for Delhi at both solstices, to within ten minutes — the band the low-precision solar position this
product has always used is honestly good to. It is not good to one minute and the test does not pretend
otherwise.

## Limits carried forward

- **Only the chat surfaces were composed by hand.** The shared tokens, materials and micro-interactions
  reach all nineteen registered surfaces, but Watch, the warning overview, the map and the document
  catalogue have not had a fresh visual pass in this batch.
- **No performance benchmark was run.** The atmosphere is budgeted — a CSS-pixel grid, one reused
  `Float32Array`, one `Path2D` per contour level, a capped frame rate, and it stops in a hidden tab — but
  budgeted is not measured, and no frame timing was recorded on named hardware.
- **`frontend/src/assets/meridian/` is now unreferenced.** Both rasters were replaced by drawn elements.
  They are left on disk rather than deleted, because they are another session's untracked files.
- **Reduced motion draws one still of the field and no wind at all.** A trail is motion by construction;
  there is no still version of one. That is a deliberate absence, not a fallback.
- The build still reports the pre-existing large main-chunk warning.
