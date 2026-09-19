# 112 — Instrument glass: the overhaul plan

19 September 2026. The brief: glassmorphic, neumorphic, minimal; colour that follows the time of day and
the condition; the Codex layout as the structural reference; maximum creativity, free hand on the
documentation. This is the plan and the reasoning behind it.

## 1. What the Codex reference actually says

The attached shot is not about colour. Structurally it is four decisions, and all four are ones this
product had got wrong:

1. **The rail is one calm list of uniform rows.** New chat, Pull requests, Scheduled, Plugins, Explore,
   then Projects, then Recents — every one the same height, the same size, the same weight, with the
   keyboard shortcut inline on the right. Ours had a 2×2 navigation grid sitting on top of the list and
   competing with it. That grid is what "the rail seems like a half-hearted component" was pointing at.
2. **The right column is a context panel, not dead space.** Codex puts *Environment* there — the state of
   the work in progress. Ours had roughly 570px of nothing beside a 740px reading column.
3. **`Worked for 1m 50s ›`** — the machinery is one collapsed line. Ours printed five paragraphs.
4. **Colour is semantic only.** Almost everything is greyscale; green, red and orange appear only where
   they carry meaning. That is already this product's hazard rule, applied to the whole interface.

## 2. The design idea

Glassmorphism as a preset is the templated default. It is on every weather shot in every gallery, and it
reads as a texture rather than as glass, because the light in it comes from nowhere.

This product already has a real light. The ground is a sun-driven gradient computed from the reader's own
latitude, and the hour is decided by the sun's true altitude. So:

> **Instrument glass: every raised surface is a pane sitting in that light, and the light has a direction.**

The catch-light on a pane's border follows the sun — the left edge at dawn, the top at noon, the right at
dusk — and the shadow falls away from it and flattens as the sun climbs. Four custom properties carry it
(`--g-light-x`, `--g-light-angle`, `--g-light-shadow-x`, `--g-light-height`), set from the real solar
position, with a correct default per hour so a pane is lit properly before any script runs and stays lit
if none ever does.

Why this rather than a blur preset:

- it is derived from the product's own subject — your place, your hour — instead of borrowed;
- one token drives every surface, so it stays coherent and can be tested;
- it is not a thing other products do.

**Neumorphism, selectively.** The soft extrusion goes on controls meant to feel physical — the send, the
mic, a forecast day cell — and nowhere else. The accessibility failure of neumorphism is that a soft
extrusion at low contrast hides the affordance, so every extruded control here keeps a real border: the
extrusion makes it feel pressable, the border makes it findable.

## 3. The plan

| Batch | Work | State |
| --- | --- | --- |
| 1 | The light model and the pane system | done |
| 2 | The rail as one calm list; conversations led by their place | done |
| 3 | The context panel in the right column | done |
| 4 | Interface localisation (i18next) | done, chrome only |
| 5 | Splitting `gpt.css` and `Workspace.tsx`; documentation | planned |

## 4. The resource list, honestly

Of the fifteen resources named, five are already installed and in use: Framer Motion (as `motion`),
Lucide, HeroUI, Radix and Tailwind v4.

Four do not fit this stack, and saying so is more useful than pretending otherwise:

- **Vercel AI SDK** and **next-intl** are Next.js-specific. This is a Python server (`weathergpt_data/`)
  serving a built Vite SPA; there is no Node route handler for either to attach to. Streaming already
  works over the Python server's own endpoints.
- **LangChain** would mean replacing a working Python planner and retrieval layer that 1373 tests stand
  behind.
- **Tremor** conflicts with a guarantee this repository deliberately keeps: the chart engine `web/viz.js`
  is pinned by the vanilla parity checks in the port ledger, 110 of them. Tremor is a reasonable choice
  for *new* Board widgets; it is not a reasonable replacement for the engine those checks cover.

**i18next is the genuinely valuable unexploited item.** The engine answers in 22 languages and the
interface around it is entirely English: a Gujarati answer arrives wrapped in "New conversation",
"Warnings" and "What it's doing". That is the largest gap between what this product claims and what it is,
and it is batch 4.

## 5. What this does not claim

The four hours' default light positions are hand-set to match the solar position at those hours; they are
a fallback, and the real position always wins when the script runs. The pane system has been looked at on
one machine at three hours. The eighteen guided surfaces still carry the palette without having been
rebuilt on it, which remains B1.3 in docs/108.


## 6. What the interface may translate, and what it may not

Batch 4 added i18next with four catalogues — English, Hindi, Gujarati, Tamil — and the interface follows
the answer language the reader already chose, so picking Gujarati moves the whole product rather than half
of it. The document's `lang` attribute follows too, because that is what a screen reader and the browser's
own hyphenation read.

Three rules govern it, and they come from where every other rule in this product comes from — that nothing
is stated which a source did not state:

1. **Chrome only.** Navigation, buttons, headings, empty states: the words this interface wrote about
   itself. Everything a *source* wrote stays exactly as the source wrote it — hazard wording, place names
   as the resolver returned them, units, source ids, status lines, the engine's own sentences. A
   translated warning is a warning this product did not read.
2. **Values never.** A number, a unit and a timestamp are formatted, not translated.
3. **Absence stays absence.** A missing key falls back to English rather than to an empty string, because
   a blank label is a worse lie than an English one — it cannot even be reported.

Four checks hold the catalogues to it: every language carries exactly the English keys, no string is
blank, a catalogue file exists for every language the interface claims, and no catalogue carries a unit,
a source id or hazard wording.

The chrome is translated into four languages and the engine answers in 22. `chromeFor` falls back to
English for the other eighteen rather than claiming them, for the same reason the engine's own language
support is measured per direction: claiming a language you do not have is the failure this product is
built to avoid.

**These translations are machine-authored and have not been reviewed by a native speaker.** They cover
interface chrome only, so the risk is a clumsy label rather than a wrong warning — but they should be
reviewed before anyone relies on them, and that review is not done.
