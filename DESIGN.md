# DESIGN.md — the design system

**The governing idea: the conversation is the product, and it sits on the reader's own sky.**

The rules are recorded in [docs/109](docs/109-bulletin-design-language.md); the look that carries them is
[docs/110](docs/110-flagship-ui.md), implemented in `frontend/src/flagship/`. Everything before those two —
the field instrument in cool paper and indigo, the aurora-glass reframe, the `.v3` layer of docs/106, and the
light language of 18 September with its sky photographs and its board — has been deleted. What those
contained is recorded in [the decommission record](research/design/DECOMMISSION-OLD-UI.md) and in docs/109.
This file describes only what exists.

## The idea

One place, one hour, one answer, and every value carrying where it came from. Two things are true of this
product and of nothing else in the category: **every reading knows its place and its hour**, and **every value
has a chain of custody**. The design is built from those two facts rather than from a mood.

**The background is the hour, not the weather.** The field behind the conversation is computed from the sun's
position at the reader's place and instant (`src/flagship/solar.ts`, the NOAA/Meeus approximation) and
resolved to four phases — night, dawn, day, dusk. It is astronomy: true everywhere, verifiable, and unable to
fabricate a condition. It is pure CSS, so it costs no image bytes.

The one thing the field may say about the weather: when **today's own column** carries a red or orange
published day, the horizon takes that published colour at its lowest edge. It comes from the read, never from
inference, and never from the five-day tally whose severity is usually already past.

## Colour

`--f-*` in `src/flagship/flagship.css`, plus HeroUI's own OKLCH tokens (`--accent`, `--radius`, `--font-*`),
which every control reads so the chrome belongs to the atmosphere rather than to a library's brand.

- The **ground and the ink** are a function of the phase. A surface never hard-codes a colour, and a light
  phase is not a dark one inverted — each phase is a complete palette.
- The **accent** is a blue chosen to sit away from all four IMD hazard hues in every phase.
- **Hazard colour belongs to hazards.** Red, orange, yellow and green are reached only through a value a
  source printed, they always carry that source's own words beside them, and interface state never borrows
  them: a refused step is monochrome and struck through, because a red glyph beside a red hazard chip is a lie
  about severity.
- **Missing has a texture, not a colour.** Covered spans are drawn solid; a gap stays hatched; an absent value
  prints *not stated in this read*.
- Contrast is measured, not assumed: every text/background pair passes WCAG AA at all four phases
  (docs/110 §4).

## Type

Two voices, and the split is semantic rather than decorative:

- **Martian Mono** — everything a tool owns: values, units, place names the resolver returned, ids,
  timestamps, editions, states.
- **Anek** — everything a model wrote: sentences, invitations, explanations. It is a pan-Indic family, so a
  Hindi or Tamil answer is set in a face drawn for it; the script faces load on demand.

A numeral in the human face is a defect. Both faces are self-hosted and bundled; the workspace serves under
`default-src 'self'`, so no CDN face can load here at all.

## The claim

One value, one window, one unit, one source, one state — the same atom in an answer, in the opening reading
and in a comparison. It carries an optional window ruler (covered spans solid, everything else hatched), a
provenance line, a light along its left edge (the source's published colour where the value *is* a published
hazard), and its depth folded underneath: the receipt, the series, the district grid.

Claims float as glass over the field. There are two elevations and no more: the sentence sits on the sky, the
claims sit above it.

## Structure

- **The conversation is the page.** Nothing precedes the answer; the country's picture opens the conversation
  as the machine's first line, and the openings beneath the question box are the registry's own questions.
- **Depth is unfolded, not laid out.** There is no rail of peer surfaces. A module opens as a sheet in the
  same frame, and a deep link opens the conversation with that sheet already open.
- **An unknown address is named in words**, never rendered as though it were the conversation.
- **The work is openable.** Real steps with real durations; a refused step stays in the list with its reason.

## Motion

One orchestrated arrival per answer, and nothing that loops for decoration (`src/flagship/motion.tsx`):

- A **value counts** from zero to exactly the number the tool returned, then settles on that string. The DOM
  holds the tool's value, never an interpolation.
- A **block rises** into place once, with a short stagger.
- The **opening sentence reveals** word by word, with every word present in the DOM from the first frame so
  selection, search and assistive technology see the whole sentence immediately.
- The only ambient movement is the sun's glow, drifting over ninety seconds.

`prefers-reduced-motion: reduce` stops all of it and leaves one still frame; so does jsdom, which is why the
suite sees static values.

## The component library

HeroUI v3 (`@heroui/react`, `@heroui/styles`) supplies the chrome — buttons, keys, and the rest of its
React-Aria-backed set — themed entirely through its own tokens. It needs no provider, ships no CSS-in-JS
runtime, and brings Tailwind v4 with it, which is why it replaced the bare Tailwind import in
`styles/app.css`. The Claim, the Work and the sentence are this product's own and are not delegated to it.
