# DESIGN.md — the design system

> **Active direction, 23 September 2026: the calm Meridian workspace.** Keep the light ground,
> dark rail and composer. The latest user direction replaces looping background effects with a static,
> fully visible skyline under the welcome's daylight arc. The quote sits above the composer. Answers
> read directly on a light page. `frontend/src/gpt/css/conversation.css` follows `meridian.css` and owns
> these proportions and interactions. See [docs/163](docs/163-chat-reading-and-selected-controls.md).
> Earlier motion, dark-answer and glass decisions below remain historical. The React app is the product
> surface; the HTML frontend remains decommissioned. Source ownership, honest absence, language fidelity
> and published hazard semantics remain binding.

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

Three voices, and the split is semantic rather than decorative:

- **IBM Plex Mono** — everything a tool owns: values, units, place names the resolver returned, ids,
  timestamps, editions, states. It replaced Martian Mono, which was mannered enough to make a serious
  product read as a toy. Mono is semantic only: it never dresses a label.
- **Anek** — everything a model wrote: sentences, invitations, explanations. It is a pan-Indic family, so a
  Hindi or Tamil answer is set in a face drawn for it; the script faces load on demand.
- **Nunito** — display only, and Latin only: the greeting, the hour, the reading's own numeral. A rounded
  geometric, because roundness is where the warmth in a weather interface actually lives. It never sets a
  sentence, and it never sets a script it does not cover.

A numeral in the human face is a defect. All three faces are self-hosted and bundled; the workspace serves
under `default-src 'self'`, so no CDN face can load here at all.

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

The eighteen guided surfaces still read the original token layer; `gpt.css` repoints those tokens rather than
restyling twenty-six files. The `--color-*` names must be redeclared inside `.g`, not at the root: a custom
property declared at `:root` computes there, so descendants inherit the computed value.

The dashboard and the India warning map are the exception: they were taken into this tree without their
stylesheets and had no rules at all, so `modules/dashboard.css` and `modules/indiamap.css` are written
here, on the same `--g-*` tokens. docs/111 §7 records what that cost while it was missing.

Two checks keep the claims in this file honest, because two of them were false when they were written.
`FE12` requires every `text-transform: uppercase` in the tree to be neutralised and refuses Tailwind's
`uppercase` utility. `FE13` holds every `className` string against the built stylesheet and fails when an
element's whole class list resolves to nothing — the state the dashboard shipped in.


## Instrument glass

Glassmorphism as a preset is the templated default — blur everything, twenty percent white, call it glass.
It is on every weather shot in every gallery, and it reads as a texture because the light in it comes from
nowhere.

This product has a real light: the ground is a sun-driven gradient computed from the reader's own
latitude. So every raised surface is a pane sitting in that light, and **the light has a direction**.

- `--g-light-angle` puts the catch-light on the edge the sun is actually on — the left at dawn, the top at
  noon, the right at dusk.
- `--g-light-shadow-x` throws the shadow away from it; `--g-light-height` flattens that shadow as the sun
  climbs.
- All four are set from the real solar position (`lightFrom`, from the hour angle). Each hour block holds
  the position for that hour, so a pane is lit correctly before any script runs and stays lit if none does.

On the light hours the catch-light **inverts**: a white highlight on a white card is invisible, so day
takes a bright fill and a soft dark edge instead. Night takes a weaker, cooler highlight, because after
dark the light is the moon and the city rather than the sun.

A pane is two backgrounds on one element — the fill clipped to `padding-box`, the lit border clipped to
`border-box` — so any surface becomes a pane by taking one class, with no pseudo-element and no extra node.

**Neumorphism, selectively.** `.g-raised` goes on controls meant to feel physical and nowhere else. The
accessibility failure of neumorphism is that a soft extrusion at low contrast hides the affordance, so
every extruded control keeps a real border: the extrusion makes it feel pressable, the border makes it
findable.

## The interface's own language

The engine answers in 22 languages; the chrome is translated into four (English, Hindi, Gujarati, Tamil)
and follows the answer language the reader chose, so picking Gujarati moves the whole product rather than
half of it. `chromeFor` falls back to English for the other eighteen rather than claiming them.

Three rules, from the same place every other rule here comes from:

1. **Chrome only.** The words this interface wrote about itself. Everything a *source* wrote stays as the
   source wrote it — hazard wording, place names as the resolver returned them, units, source ids, status
   lines, the engine's own sentences. A translated warning is a warning this product did not read.
2. **Values never.** A number, a unit and a timestamp are formatted, not translated.
3. **Absence stays absence.** A missing key falls back to English, never to an empty string: a blank label
   is a worse lie than an English one, because it cannot even be reported.

Four checks hold the catalogues to it, and the one that matters makes rule 1 mechanical — no catalogue may
contain a unit, a source id or hazard wording. The translations are machine-authored and unreviewed by a
native speaker (docs/112 §6).

## Where the stylesheet lives

`gpt.css` is an index; the rules are nine files under `gpt/css/` — tokens, ground, rail, chrome, thread,
surfaces, welcome, panel, glass — imported in the order the single 1780-line file had. Source order is the
cascade, so that order is not an aesthetic choice: both specificity faults found in this work were a rule
at the bottom of that file silently beating one at the top. The split was verified by building before and
after and comparing the output byte for byte.
