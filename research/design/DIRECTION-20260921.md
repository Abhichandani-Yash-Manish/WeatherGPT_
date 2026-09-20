# The direction for the 21 September overhaul

This is the shared brief for three parallel workstreams that ran on one tree on 21 September 2026:
the light and material on the glass (`frontend/src/gpt/`), what each surface is for
(`frontend/src/modules/`), and the answer as a page (`frontend/src/chat/`). The engine batch that ran
beside them — the message the reader gets — is [docs/133](../docs/133-the-message-the-reader-gets.md).

It exists because three agents cannot share a taste. What they can share is a measurement, a boundary,
and a list of things this product has already refused.

## 1. Where the product actually is

Measured before any of the three started, rather than taken from the previous batch's notes.

**The ground is already continuous.** `frontend/src/gpt/spectrum.ts` computes every custom property in
the palette from the sun's real altitude and hour angle, once a minute, at the reader's own latitude.
`frontend/tools/hours.mjs` installs a fixed clock in the page and captures one route across the day,
which is how the drift is checked rather than asserted:

```
dark 06:00  hour=daybreak  bg=#f7f8f9  accent=#265dc7  rail=rgba(47, 95, 192, 0.045)  bar=rgba(224, 158, 96, 0.05)  bubble=rgba(150, 120, 190, 0.05)
dark 12:00  hour=noon      bg=#f2f6fb  accent=#1f5ccc  rail=rgba(31, 92, 204, 0.04)  bar=rgba(120, 170, 230, 0.05)  bubble=rgba(90, 130, 200, 0.05)
dark 18:00  hour=golden    bg=#0d0f1b  accent=#afc0f5  rail=rgba(195, 170, 232, 0.05) bar=rgba(226, 148, 96, 0.06)  bubble=rgba(170, 130, 190, 0.06)
dark 22:00  hour=night     bg=#0a0f1a  accent=#a8c7fa  rail=rgba(174, 192, 246, 0.05) bar=rgba(168, 169, 199, 0.06) bubble=rgba(178, 159, 213, 0.068)
```

Four different states, four different skies, and the OS colour-scheme preference is deliberately not
consulted: the ground is the hour. That was a decision made on 20 September and it stands.

**And that is the problem with it.** Look at the component tints. `rail`, `bar` and `bubble` differ from
each other by four to seven percent of one hue, on fills that are themselves within a few percent of each
other. The reader's complaint — *"the website theme right now is very monotonous"* — is correct and this
table is why: the per-component palette exists, is astronomy-derived, and is **below the threshold at
which anybody can see it.** A palette nobody can perceive is a palette that is not there.

**The strongest screen is the welcome.** The 06:00 frame is a dawn gradient, a dark ink, a large greeting,
the sun's own dial and a Blake line. Nothing else on the product is at that level. That is the asymmetry
the batch is about: the welcome is lit and everything around it is flat, and the flatness is not restraint,
it is unfinished.

**The weakest screens are the instrument surfaces.** `light-verification@1440` opens with two sentences of
title, three "Ask instead" chips, and then a card headed *"What this comparison is"* that spends three
paragraphs saying what the surface does not claim. The first screen of a surface about forecast verification
contains no verification. Same shape on Ensemble: *"What a member and a spread are"* before any spread.
Interpretation is the product's job; a disclaimer stack is not interpretation.

## 2. Four rules, and what each one forbids

These are the product's own rules, restated for this batch because a design pass is where they get broken.

**R1 — Every number a reader sees carries visible provenance, and the audit that holds it never weakens.**
`frontend/src/flagship/provenance.ts` has the three shapes that satisfy it; `provenance.surfaces.test.tsx`
and `claims.audit.test.tsx` are the net. A new surface, a new figure, a new chip: extend the audit. If a
design change would breach the rule, change the design.

**R2 — A published hazard colour is a source's word.** Red, orange, yellow and green reach a reader only
through a value a source printed, with that source's own words beside it. `--g-lit` / `data-lit` in
`Claim.tsx` is how a claim carries one. Nothing decorative may reach those four values, and interface state
may never borrow them: a refused step is monochrome and struck through.

**R3 — Absence prints its absence.** *not stated in this read*, never a zero, never a dash that reads as
zero, never dropped. An empty shell is a defect; a queue with nothing in it says so in words.

**R4 — The model's output is never an observation and a forecast is never a warning.** "Modelled value for
a grid cell", "forecast", "station report", "published warning", "provider's own index" — these are
different kinds of thing and the interface keeps them visibly apart.

## 3. The light is measured, not chosen

The palette work in this batch is held to two numbers rather than to a mood. Both are checked in vitest
against computed colours, which is why they can be checked at all — jsdom has no layout engine for axe's
own contrast rule.

**Contrast.** Every text/background pair ≥ 4.5:1 for body and ≥ 3:1 for large text, sampled across the
continuous spectrum at every 15 solar-minutes of a day (and across latitudes and both solstices, as
`spectrum.test.ts` already does), not only at the four old phase anchors.

**Separation.** The rail, the top bar, the reader's own bubble and the ground must be *distinguishable* at
every instant. The measurable form of that: convert each pair to a perceptually uniform space and require a
minimum difference in chroma **and** in hue — a distance the eye can resolve at the size the element is
drawn, not a distance that exists in the file. The thresholds and the arithmetic go in the test, so the
claim "the components visibly differ" is a measurement and not an adjective.

The previous faintness is exactly what happens without the second number, so the second number is the point
of the batch.

## 4. What this product has already refused

`docs/111` recorded seven background directions and six rejections, every one because the background tried
to be the subject. That record stands and this batch does not reopen it. The current shape — an hour-keyed
gradient, auras, grain, a vignette, and one mark at welcome strength — is the answer.

Impeccable's craft floor (`tmp/design-refs/impeccable/craft-floor.md`, from `pbakaus/impeccable`, read for
guidance and not copied) refuses a set of category defaults, and four of them are live risks here:

- *No kicker or eyebrow above a heading.* The heading carries its own weight.
- *No glass and blur as decoration rather than as a specific effect.* The brief asks for a frosted
  integration, so the test is: does the pane float over something the reader can see through it? A glass
  pane over a flat opaque panel is decoration. A glass rail over a graded sky is an effect.
- *No status-chip soup, no cards in cards, not everything at equal weight.* A surface where every block has
  the same fill, the same border and the same size has no hierarchy and is not a design.
- *No monospace as a costume.* Mono here is semantic — values, units, ids, timestamps — and never a label.

`docs/109` and `DESIGN.md` at the root remain the contract; where this document and those disagree, they
are right and this one is wrong.

## 5. Motion

`transitions.dev` (Jakub Antalik — the author of the thinking-orbs already integrated in docs/130) was
fetched whole into `tmp/design-refs/transitions-dev/` — 32 patterns, each with the CSS and a
`prefers-reduced-motion` guard. **Reference, not source**: the repository carries no licence file, so
nothing is copied verbatim. What is taken is the part that is a decision rather than an expression — the
durations, the easing families, the idea that an entrance is asymmetric with its exit (slower in, quicker
out), and that a state change is expressed on the element that changed rather than on its container.

Which patterns are genuinely wanted, and which are refused:

| Wanted | Where | Why |
| --- | --- | --- |
| Text states swap | the greeting and the bar's title across the hour | the page already changes under the reader's feet; this is the change's own expression |
| Panel reveal | the rail's collapse, the reading panel | both are regions the reader opens |
| Menu dropdown | the palette, the place picker | origin-aware opening is the difference between a menu and a mystery |
| Icon swap | the rail's marks when a home is chosen | two glyphs cross-fading in one slot |
| Skeleton reveal, streaming text, reasoning stream, thinking states | the working turn | the wait is already honest about its stages; docs/131 and docs/130 own this |
| Accordion | the claim's fold | depth unfolds; the unfold is the motion |

| Refused | Why |
| --- | --- |
| Card hover tilt, cursor glare, gravity letters, fluid orb | decoration on a surface whose subject is a measurement |
| Shimmer text, matrix loader, spinning counter | a loop that carries no state is a loop that lies about progress |
| Success check, confetti, like button | this product does not congratulate anybody |
| Banner stacking | the top bar is a title, not a notification centre |

## 6. The three workstreams, and the boundary between them

Each owned its own directory and wrote its own record. No stream edited another's files, and none of them
committed: the tree was committed once, by the engine stream, after the three had reported and their output
had been looked at.

| Stream | Owns | Record |
| --- | --- | --- |
| Light and material | `frontend/src/gpt/` | [docs/134](../docs/134-light-and-material.md) |
| What each surface is for | `frontend/src/modules/` | [docs/135](../docs/135-what-each-surface-is-for.md) |
| The answer as a page | `frontend/src/chat/` | [docs/136](../docs/136-the-answer-as-a-page.md) |
| The message the reader gets | `weathergpt_data/` | [docs/133](../docs/133-the-message-the-reader-gets.md) |

Two shared rules that are not a matter of taste:

- **A stream that cannot make a change work does not leave it half-made.** If a surface earns nothing, cut
  it and say so in the record. A commit that says what was deleted and why is a better outcome than one
  that polishes something nobody should open.
- **A stream reports what it could not do.** Named, with the reason. "Everything was done" is not a claim
  any of these records is allowed to make.
