# Three design worlds — brainstorm 18 September 2026

Status: **proposal, not a decision.** The existing visual language (cool paper, indigo accent, Tiro/Plex
two-voice typography, 19-surface rail) is treated as wiped at the user's instruction of 18 September 2026.
Nothing here is implemented in the app yet; the app is untouched.

## What is held constant through any wipe

These four are product truth, not design language, so they survive the wipe unless the user overrides them:

1. Every value keeps its entity, window, unit, source and retrieval time. A number with no source is a defect.
2. The four IMD hazard colours are reached only through a published source, and interface colour never
   imitates them — so an accent can never read as a warning level. In the probes, hazard yellow appears only
   on the chip that quotes the bulletin.
3. No invented values, no confidence scores, no fabricated conditions. Dark, rain, cloud art is atmosphere
   only where it is *computed from something real* (the clock and the sun), never where it would imply a
   condition no source published.
4. Missing, unknown, stale and quarantined stay visible rather than being smoothed into a value.

## The shared skeleton every probe uses

Identical content in all three, so the only variable is the vibe:

```
  place · instant                                             controls
  ─────────────────────────────────────────────────────────────────────
  the answer (prose, the model's voice)
  source · cell · retrieved-at (the tool's voice)
  [ ask about a district, a river, an airport, a crop…  ]
  ─────────────────────────────────────────────────────────────────────
  YOUR BOARD
  [ hazard ][ rain ][ river ][ spread ]        ← cards, one claim each
```

The probe values are invented placeholder values and are labelled DESIGN PROBE on the page. They are not a
reading and must never be quoted as one.

## World A — "Station Board"  `probes/a-station-board.html`

Ground `#05070c`, panels barely above it, one electric cyan accent, values in **Martian Mono** (wide,
pixel-derived, machine-printed), interface in **Anek Latin**. Each card carries its own atmosphere as a
radial wash keyed to the hour it covers. Signature: the *printed register* — a 31-tick member strip, a
`printed 18:42:07 IST` line, and numerals that look like a display board rather than a headline.

Read: the closest to the user's own reference (dark, modular, huge numerals, one accent). Strongest as a
product. Weakest on charm — atmosphere is currently only a wash.

## World B — "Almanac"  `probes/b-almanac.html`

Cool newsprint `#eceae1`, two inks only — ink and **mimeograph violet** `#4a2a86` (the dye of a duplicated
district bulletin, and far from all four hazard hues). Display in **Rozha One**, prose in **Tiro Devanagari
Hindi**, provenance in **Martian Mono**. Cards are clippings: hairline rules, perforated dividers, and an
edition stamp rotated onto the corner. Signature: the *stamp* that separates a published edition from a
fetched value.

Read: the most specific to India's printed forecasting culture, and the most charming. Weakest at conveying
liveness — a printed page implies an edition, not a refresh, which is honest for bulletins and wrong for a
five-minute-old model run.

## World C — "Horizon"  `probes/c-horizon.html`

The two areas are one screen: **the conversation lives in the sky, the board sits on the ground**, divided by
a horizon that is computed, not decorated. The gradient is derived from the real solar altitude and azimuth
for the reader's place and hour (the probe computes −0.1° altitude, azimuth 271° W, civil twilight ends
19:06 IST for Surat on 18 September and prints that readout). Each board card carries a *light strip* drawn
from the same computed sky. Display in **Instrument Serif**, prose in **Instrument Sans**, provenance in
**Geist Mono**.

Read: the most flagship and the only one whose structure *is* the two-area brief. The sky is astronomy, which
is true everywhere and reports nothing about weather — so it cannot fabricate a condition. Risk: a full-bleed
sky is a big surface to carry, and the ground half must not become the old dashboard on a dark background.

## Open questions for the user

1. Which world, or which hybrid? (A's numeral discipline + C's horizon is the obvious hybrid candidate.)
2. Ground: dark-first, light-first, or one language that changes with the reader's own hour?
3. What does *customisable* mean here — choose cards from a library, resize them, arrange them, or boards per
   place and per persona?
4. Does the chat own the first screen (board below the fold), or do the two share the first screen as C does?
