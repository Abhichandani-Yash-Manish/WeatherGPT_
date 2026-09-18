# DESIGN.md — the design system

**The governing idea, since 18 September 2026: the conversation is the product, and the sky is the answer.**
The visual system this file replaces — a field instrument in cool paper and indigo, then an aurora-glass
reframe — has been deleted; what it contained is recorded in
[the decommission record](research/design/DECOMMISSION-OLD-UI.md). This file describes only what exists.

## The idea

One place, one hour, one answer, and every value carrying where it came from. Two things are true of this
product and of nothing else in the category: **every reading knows its place and its hour**, and **every value
has a chain of custody**. The design is built from those two facts rather than from a mood.

**The background is the answer.** The field behind the conversation is composited from the same reads that
answer questions — the sun's computed position, the forecast's rain and visibility for the hour covering now,
and the colour a district bulletin printed for today. It is not decoration pretending to be weather: when there
is nothing to paint with, the sky is astronomy alone. The legend under every surface names each input.

## Colour

`--l-*`, computed per place and hour in `src/light/solar.ts`:

- The **ground** is a function of the sun's altitude: seven complete grounds — night, twilight, low light,
  golden, day, high day — interpolated continuously. A surface never hard-codes a colour; a light-mode surface
  is not a dark one inverted.
- The **accent** is the current ground's own, chosen to sit away from all four IMD hazard hues in every mode.
- **Hazard colour belongs to hazards.** Red, orange, yellow and green are reached only through a value a source
  printed, they always carry that source's own words beside them, and interface state never borrows them: a
  failed step is monochrome and struck through, because a red glyph beside a red hazard chip is a lie about
  severity.
- **Missing has a texture, not a colour.** Covered spans are drawn; a gap stays hatched; a stale value dims; a
  quarantined page keeps its quarantine mark.

## Type

Two voices, and the split is semantic rather than decorative:

- **Martian Mono** — everything a tool owns: values, units, place names the resolver returned, ids, timestamps,
  editions, states.
- **Anek Latin** — everything a model wrote: sentences, invitations, explanations.

A numeral in the human face is a defect. Both faces are self-hosted and bundled; the workspace serves under
`default-src 'self'`, so no CDN face can load here at all.

## The claim

One value, one window, one source, one state — the same atom in an answer, on a board tile, and in a comparison
sheet. It carries an optional window ruler (covered spans solid, everything else hatched), a provenance line
under a hairline, and one light strip along its top: the source's published colour where the value *is* a
published hazard, and the layer's accent everywhere else.

## Structure

- **The stage** — one rounded field of computed sky, the conversation centred on it, the legend at its foot.
- **The conversation is the page.** Nothing precedes the answer; the country's picture opens the conversation as
  the machine's first line, and the openings beneath it are the registry's own questions.
- **Depth is unfolded, not laid out.** The board is its own surface (`#/board`), not a rail of peers.
- **The work is openable.** Real steps with real durations; a failed step stays in the list with its reason.

## Motion

- The field is **printed at twelve frames a second**, because print does not need sixty. Motion is slow by
  construction: the drift follows the wind, the rain falls at its measured rate, the light moves a degree every
  four minutes.
- **The reading moves the field; the reader moves the light.** When a read returns different values the field
  repaints from them, so the sky changes when the answer changes. (A cross-fade between the previous field and
  the new one is the next motion item and is **not** implemented: today the repaint is immediate.) The pointer
  springs the light's centre and a click sends a ring travelling along the wind — the reader's presence, and the
  one thing in the field that is decoration, which is why the legend says "the pointer's light is decoration".
- `prefers-reduced-motion: reduce` stops everything, including the pointer response, and leaves one still frame.
- Motion may explain and may accompany. It never loops for decoration, never animates a number to a *different*
  number, and never delays reading a value.

## Accessibility

The gate is `tests/ui/a11y.spec.ts` (axe, wcag2a/aa + 21a/aa + best-practice) over every registered route *and*
the front door, which is not in the route registry. Contrast is guaranteed by construction rather than checked
by eye: ink and ground come from the same computed light. Nothing is carried by colour alone.
