# DESIGN.md — the design system

**The governing idea: the conversation is the product, and it sits on the reader's own sky.**

The rules are recorded in [docs/109](docs/109-bulletin-design-language.md); the system that carries them is
[docs/111](docs/111-mature-design-system.md), implemented in `frontend/src/gpt/`. docs/110 recorded the
ChatGPT architecture, which stands; its flagship look was superseded. Everything before those two —
the field instrument in cool paper and indigo, the aurora-glass reframe, the `.v3` layer of docs/106, and the
light language of 18 September with its sky photographs and its board — has been deleted. What those
contained is recorded in [the decommission record](research/design/DECOMMISSION-OLD-UI.md) and in docs/109.
This file describes only what exists.

## The idea

One place, one hour, one answer, and every value carrying where it came from. Two things are true of this
product and of nothing else in the category: **every reading knows its place and its hour**, and **every value
has a chain of custody**. The design is built from those two facts rather than from a mood.

**The ground whispers.** Seven background directions were tried here and six were rejected, each because the
background tried to be the subject. The ground is now three CSS layers at about a twelve percent contrast
range — a gradient keyed to the hour, one halo where the light is, and a single horizon hairline, which is
all the depth there is. The hour comes from the sun's real altitude at the reader's place
(`src/gpt/fieldPaint.ts`, NOAA/Meeus with the equation of time). It states the hour and nothing else: no
condition is ever drawn, so there is nothing to caption.

## Colour

`--g-*` in `src/gpt/gpt.css`. A night-flight palette rather than a tinted grey: `#070b14` void, `#0c1220`
ground, `#131b2b` raised, `#1e2838` line, `#8b98ad` mist, `#e8edf5` paper.

- The ground is one dark palette; the hour shifts only the gradient and the halo, by a few degrees. A
  surface never hard-codes a colour.
- The **accent** is `#a8c7fa`, a pale instrument blue, used on under five percent of the surface and chosen
  to sit far from all four IMD hazard hues.
- **Hazard colour belongs to hazards.** Red, orange, yellow and green are reached only through a value a
  source printed, they always carry that source's own words beside them, and interface state never borrows
  them: a refused step is monochrome and struck through, because a red glyph beside a red hazard chip is a lie
  about severity.
- **Missing has a texture, not a colour.** Covered spans are drawn solid; a gap stays hatched; an absent value
  prints *not stated in this read*.
- Contrast is measured rather than assumed, and the accent is spent on under five percent of the surface.

## Type

Two voices, and the split is semantic rather than decorative:

- **IBM Plex Mono** — everything a tool owns: values, units, place names the resolver returned, ids,
  timestamps, editions, states. It replaced Martian Mono, which was mannered enough to make a serious
  product read as a toy. Mono is semantic only: it never dresses a label.
- **Anek** — everything a model wrote: sentences, invitations, explanations. It is a pan-Indic family, so a
  Hindi or Tamil answer is set in a face drawn for it; the script faces load on demand.

A numeral in the human face is a defect. Both faces are self-hosted and bundled; the workspace serves under
`default-src 'self'`, so no CDN face can load here at all.

## The claim

One value, one window, one unit, one source, one state — the same atom in an answer, in the opening reading
and in a comparison. It carries an optional window ruler (covered spans solid, everything else hatched), a
provenance line, a light along its left edge (the source's published colour where the value *is* a published
hazard), and its depth folded underneath: the receipt, the series, the district grid.

A claim is not a card in a kit: the leading claim is a plain block with the value at display size and no
border, and supporting claims are quiet hairline slabs. Different jobs, different treatments. The published
colour is a short bar beside the value, never a wash over the block.

## Structure

- **The conversation is the page.** Nothing precedes the answer; the country's picture opens the conversation
  as the machine's first line, and the openings beneath the question box are the registry's own questions.
- **Depth is unfolded, not laid out.** There is no rail of peer surfaces. A module opens as a sheet in the
  same frame, and a deep link opens the conversation with that sheet already open.
- **An unknown address is named in words**, never rendered as though it were the conversation.
- **The work is openable.** Real steps with real durations; a refused step stays in the list with its reason.

## Motion

Motion answers an action and does nothing else:

- The composer lifts and its edge takes the accent on focus; the send scales on press.
- A turn arrives once, a 6px rise over 220ms.
- One dot pulses while the engine works, beside the engine's own word for the stage it is in.
- A fold's chevron turns as it opens.

Nothing loops for decoration. The one exception is the horizon hairline, which drifts fourteen pixels over
forty-eight seconds and is never caught moving. `prefers-reduced-motion: reduce` collapses all of it.

## The component library

HeroUI v3 (`@heroui/react`, `@heroui/styles`) is installed and brings Tailwind v4 with it, which is why it
replaced the bare Tailwind import in `styles/app.css`. The workspace's own chrome — the rail, the composer,
the tools — is written directly against these tokens rather than delegated, because the controls are few and
the fit matters more than the head start. The Claim, the Work and the sentence are this product's own.

The eighteen module surfaces still read the original token layer; `gpt.css` repoints those tokens rather than
restyling twenty-six files. The `--color-*` names must be redeclared inside `.g`, not at the root: a custom
property declared at `:root` computes there, so descendants inherit the computed value.
