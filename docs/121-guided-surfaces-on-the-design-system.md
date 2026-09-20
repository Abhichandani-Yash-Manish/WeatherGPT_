# 121 — The eighteen guided surfaces, on the design system

21 September 2026. This is the styling half of B1.3 in docs/108, and it answers the item docs/111 §8 left
open: *the eighteen guided surfaces are repointed, not rebuilt: they carry the palette and the type, but
their layout is still the one written for the instrument design.* `docs/112` §5 named the same gap again.
The surfaces were repointed because docs/111's own list of selectors was wrong; they are dressed now because
this batch moves the dress itself onto the system, and what they state is not touched.

## 1. What was carried over, and why

Two things were carried over, and both for the same reason — they are the product, not the dress.

**What a surface states.** Every value keeps its unit on its line, its window, and the source line under it.
A missing, unknown or unavailable state keeps being a sentence: `not recorded`, `no row returned`,
`No source row came back with this read.`, `colour not stated`. Not one of those strings lives in this
stylesheet, and no rule here hides, zeroes or empties one. What was styled is what the read returned.

**The four published hazard colours.** They are reached only through the payload's own attribute —
`.chip-colour[data-colour]` for a colour chip, `.dash-strip-*` and `.district-*` for a bar or a shape,
`.dash-day-flag[data-colour]` for a marker on a day — and never chosen by this file. An absence is a grey,
a hatch or a dashed edge; a district with no published day is never drawn green.

Neither of those was carried over by copying a rule. They survived the port because the port only ever
changed *how* a thing is drawn: the token it reads, the size it is set in, the elevation under it.

## 2. What the dress was, and what it is now

`frontend/src/modules/modules.css` was written for the instrument design of docs/97 and docs/98. It read
the light paper token layer (`--ink`, `--paper`, `--line`, `--glass-1`, `--lift-1`, `--space-4`, `--step-4`),
and docs/111 made those names resolve to the night-flight palette. The palette arrived; the dress did not.
The table is what changed, in the module layer's own words.

| | was | is |
| --- | --- | --- |
| the frame | a second inset of `clamp(14px, 2.2vw, 28px)` inside the host's own `px-6 py-5` | the host is the frame; the module layer keeps a bottom rhythm |
| a heading | a display serif masthead at `--step-4`, and section headings in tracked-out capitals behind a 14px rule | 1.7rem in Anek for the h1, sentence-case 13.5px section labels, no rule in front of them |
| a card | `--glass-1` on a blur, `--lift-1` (repointed to `none`) for a shadow | `--g-fill`, `--g-line-soft` edge, `--g-e1` — the top-edge light and the shadow in one declaration |
| a field | a pill on a blurred translucent fill | the raised fill, `--g-r-sm`, the system's own input treatment |
| a table | restated font size, padding, collapse and header case | the workspace table atoms dress it; only a value cell's machine voice and a table's no-hyphen rule stay here |
| a value | the display serif | IBM Plex Mono, tabular, with the counted value's own clamp — mono is a value a tool owns |
| a hazard chip | a wash on a light ground, at a hue mixed for white paper | the system's own sixteen percent wash of the same colour, with that colour as ink and edge |
| motion | a section lifted and its shadow grew under the pointer | only what answers an action; the pointer lift is gone from a static block |
| size | `clamp()` behind a variable, under the 11px floor check rather than above it | a literal pixel value, ≥ 11px, all 28 of them visible to FE17 |

Every declaration in the file now names a `--g-*` token, with one exception that is the system's own: the
four published-colour washes (`--red-wash`, `--orange-wash`, `--yellow-wash`, `--green-wash`), which
`frontend/src/gpt/css/surfaces.css` declares as a sixteen percent mix of the four tokens. Measured: 40
distinct custom properties, none declared nowhere. `dashboard.css` and `indiamap.css` were already written
on `--g-*` by docs/111 §7 and are unchanged but for the one rule §4 records.

## 3. The eighteen surfaces

The change is one stylesheet, so for most of the eighteen the honest answer to "what changed on this one"
is *the shared dress*, and nothing of its own. Nine of them have something of their own as well, and those
are the rows below with a name in the text.

| Surface | What changed | What deliberately did not |
| --- | --- | --- |
| **Advisories** | sections, fields and the holdings table on the shared dress; failure panel on the system's alert edge and wash | the quoted advice is the source's own text, the condition lines are attributed to the source, and the district brief keeps its three headings |
| **Air quality** | shared dress; the point/cell/parameter tables take the workspace table atoms | which cell each reading came from, and the advisory editions' own region and source lines |
| **Aviation** | shared dress; a station whose freshness the payload did not state now draws a **dashed** edge (§4) | the `stale` and `within_prototype_age_limit` words are the payload's, and the row's own retrieval time |
| **Briefcase** | shared dress; the confirm dialog and the source-identifier table | the kept brief's title, id, retrieval time and the no-delivery sentence |
| **Changes** | shared dress | the vintage rows, the statements carried in the payload, and the printed editions |
| **Climate** | shared dress | the stored series is drawn as the read returned it, including its gaps |
| **Compare** | shared dress; the two-column inline layout's `--space-4` is now `--g-4` | both sides keep their own read and the accent edge that says which is the comparison |
| **Documents** | shared dress; the document frame's inline border, radius and fill are the system's tokens | a pruned body still states what survives; the opened document is still from this machine |
| **Ensemble** | shared dress | member, distribution and spread are three different things in the markup and stay so |
| **Forecast** | shared dress | the meteogram's drawing, which lives in the chart layer; and `no value returned for this point` is still a gap in the series rather than a plotted point |
| **Map** | the schematic figure's ink is a named class (`dash-map-ink`) instead of an inline arbitrary value; shared dress on the controls and the inspector | the district fills: still only the colour its own row published, three greys for the three absences |
| **Marine** | shared dress; the two-column inline layout's `--space-4` is now `--g-4` | the wave and discharge values, their units and the 50 km cell guard's own sentence |
| **Observations** | shared dress; the unknown-freshness chip is dashed, the stale chip is neutral | the station's distance, age and stale flag are the payload's, and 'stale' stays the word |
| **Settings** | shared dress | the source ids, the routing order, and that nothing outside this machine is read |
| **Today** | KPI cards on `--g-fill`/`--g-e1`; the editions bar renamed `dash-chart-bar`; a word-shaped KPI now steps down (see §4) | the counted values, the printed-day strip, the district list's own wording and edition, and 'not recorded' as the value of a count no read returned |
| **Verification** | shared dress | the measured comparison and its window |
| **Warnings** | shared dress; the district × day matrix and the chips that carry a published colour now print that colour (ink, wash and edge — §4) | the matrix's cells are still blank where no day was published, and the brief keeps its own sentence that it is not a warning anyone else receives |
| **Workspace** | the dashboard's own dress; the map card's second elevation now reaches the page instead of being overridden (§4) | the question box, the tool list, 'nothing was sent', and the kept-on-this-machine lists |

No control was added and none was removed. No sentence, number, unit, place name, source id or hazard word
was touched. The diff is: `frontend/src/modules/modules.css` (rewritten on the system's tokens), one rule
added to `indiamap.css`, and in the components — one inline style value in `CompareSurface.tsx`, one in
`MarineSurface.tsx`, three in `DocumentViewer.tsx`, three Tailwind arbitrary values in `Evidence.tsx`, seven
`text-[length:var(--step--1)]` and one ink value in `MapSurface.tsx`, and the one class rename in
`DashboardCharts.tsx`.

## 4. Five rules that were declared and never drawn

The port surfaced five rules that a reader never saw. Each was found by measuring the built stylesheet
rather than by reading the file, because each looked correct in the file.

1. **A published colour chip printed no published colour.** `.chip-colour[data-colour='red']` is two simple
   selectors; the workspace's `.g .btn, .g .btn-ghost, .g .chip` atom is also two, and it is emitted later
   in the bundle. Measured in Chromium on the built stylesheet: with the rule at two parts the chip's ink is
   `rgb(158,171,192)` — the workspace's secondary ink — its edge is `rgb(34,45,64)`, and the red the bulletin
   printed appears only as the word. At three parts (`.g .chip-colour[data-colour='red']`) the same probe
   reads ink and edge `rgb(226,89,111)` on the sixteen percent wash. FE16 measures the intended pair; the
   page had been showing neither.
2. **"not recorded" printed at the numeral size.** `.dash-kpi-number-word` is one simple selector and
   `.g .dash-kpi-number` — the workspace's counted-value rule, added to make a four-figure count fit — is
   two and later. The same probe reads the word slot at **45.76px** as it was and **22px** now. The
   component's own comment says this was the reason the class exists; the class had never applied, which is
   why the workspace also had to add `overflow-wrap: anywhere` to stop it bursting the card.
3. **The map's inspected day looked like every other day.** `IndiaWarningMap.tsx` marks the selected day
   with `className="is-current"` and nothing declared that class: it was written as `.chip.is-current`, and
   this is a list row. The rule was inert *and* the name resolved, so FE13 passed. Removing the inert rule
   is what made FE13 report the element, and the marker now exists — `.imap-days .is-current`, an accent
   edge, never a hazard hue.
4. **The map card's elevation never reached the page.** `.dash-card-map` claimed `--raiser` and a second
   lift; the workspace's card rule is two simple selectors and later, so the card rendered with that rule's
   fill and no shadow. It is now `.g .dash-card.dash-card-map`.
5. **The absence edge was inert too, and `is-stale`/`is-current` asked for a hazard hue where no source
   printed one.** `.chip-unstated` and `.chip.is-unknown` — the dashed edge that says a colour or a
   freshness was not stated — were two simple selectors against the workspace chip atom's two, and lost the
   same way, so a chip that meant "not stated" was drawn identically to one that carried a value. They are
   now `.g .chip.chip-unstated` and `.g .chip.is-unknown`. Alongside them sat `.chip.is-stale` and
   `.chip.is-current`, which painted a read's age red and green; both were inert for the same reason, so
   nothing a reader saw changes by deleting them, and what is gone is the only place this stylesheet asked
   for a hazard colour without a source. The age is not lost — the chip prints the payload's own word for
   it.

Two other rules were removed as dead, verified against every `className` in `frontend/src` before removal:
`.dash-ruler`, `.dash-ruler-mark`, `.dash-ruler-label` and `.map-tip-fixed`, plus `.dash-map-toolbar` and
`.dash-map-hint`, name nothing. Two names are new and each is a shape the system did not have:
`module-skeleton-bar` (the loading bar, whose wash is the same 38 percent of the line colour in the same
colour space it was inline) and `dash-map-ink` (the schematic figure's stroke ink). One name changed:
the editions bar was `.dash-bar`, the same name as the Today filter row, so a `<rect>` took the filter row's
flex, border, radius, padding and shadow as well as its own fill — the collision docs/111 §7 records for
`.dash-strip` and `.dash-bubble`, answered the same way, by renaming rather than by making them fight.

## 5. Where each rule is held

| Rule | Where it is held |
| --- | --- |
| the four published hazard colours are reached only through the payload's attribute | `.chip-colour[data-colour]`, `.dash-strip-*` and the two chart shapes that restate the ramp (`.dash-bubble`, `.dash-donut-slice`), `.district-*` (including `.district-quiet`, which is a day the bulletin itself called quiet), and `.dash-day-flag[data-colour]` in `dashboard.css`. The module layer names no hazard colour outside those, with one exception it states deliberately: `.module-failure`'s edge uses the system's own alert step, because a read that failed is a state of the read and not a severity of the weather |
| an absence is a grey, a hatch or a dash | `.dash-strip-unset`, `.dash-bubble.dash-strip-unset`, `.dash-donut-slice.dash-strip-unset`, `.district-stated-not-on-ramp`, `.dash-swatch-empty`, `.g .chip.chip-unstated`, `.g .chip.is-unknown` |
| a missing value is never drawn as zero, a blank or a green | the markup: `notRecordedWhen` prints the words into the value slot, `DataTable` prints `no row returned`, `Coverage`/`Sources` print their own absence sentence. No rule here hides an empty container |
| every value keeps its unit and its window | the markup, unchanged; the module layer styles the value and its source line, and sets a numeral in mono with tabular figures so a changing value does not shuffle its line |
| the ink ladder | `.module-lead`, `.module-note` and `.module-fact-label` are `--g-mist` (the secondary ink), never `--g-mist-2`, because they sit on the module's own ground as well as on a card. The tertiary step is used only inside a card: table headers, captions, provenance |
| no shouted heading | no `text-transform: uppercase` remains in any stylesheet this lane owns, so FE12's neutralising list is now a backstop rather than the mechanism |
| no type under 11px | every size in the module layer is a literal ≥ 11px (28 of them). The one smaller rule left is `indiamap.css`'s city label at 3px — three SVG user units inside a 480-unit viewBox, which FE17 exempts by design and the file records |
| motion answers an action | the pointer lift on a KPI card is the only transform; a static section does not move; `prefers-reduced-motion` removes even that |

One residual is worth stating plainly rather than leaving for a reader to discover. The bundle emits the
module layer **before** the workspace stylesheet — measured on this build: `.module-section{` at byte 21,341
and `.g .module-section{` at 78,817; `.g .chip-colour[data-colour=red]` at 24,014 and `.g .chip-colour{` at
78,868. So every workspace rule of equal specificity wins, and a rule declared here at one part fewer than
its workspace counterpart is a value the browser never uses. The rules this batch repaired are stated at the
specificity the cascade needs, which is the technique `frontend/src/gpt/css/surfaces.css` itself uses for
`.pill-accent`. One place is left as it renders rather than as it was written: a `.dash-card` is dressed by
`.g .glass, .g .glass-soft, .g .glass-strong, .g .dash-card, .g .planwatch` — a translucent raise on an
eighteen-pixel blur, with no shadow — and the module layer now states only that card's own column, radius,
edge width and inset, rather than a fill and a shadow that would lose. Reconciling the two card treatments
(the workspace's glass and the dashboard's `--g-fill`/`--g-e1`) belongs to whoever owns
`frontend/src/gpt/css/`, not here.

## 6. Evidence

| Command | Observed |
| --- | --- |
| `cd frontend && npx tsc --noEmit` | clean, 0 errors, exit 0 |
| `cd frontend && npx vitest run src/modules` | **24 files, 134 checks, 0 failed** — the same 24 and 134 the batch started from, so no surface spec changed its meaning |
| `cd frontend && npm run build` | built in 1.17s, no error |
| `python3 scripts/audit_react_frontend.py` | **19 check(s), 0 failed** — FE12, FE13, FE14, FE15, FE16 and FE17 all read the built output, so they measured this work rather than the previous bundle |
| `cd frontend && npx vitest run src/styles/styles.test.ts` | **1 failure, and it is not this lane's**: `gpt.css declares no rule for: g-notes (src/chat/AnswerTurn.tsx); g-fold-count, g-series-receipt (src/chat/parts.tsx); g-place-claim, g-place-source (src/gpt/Rail.tsx)`. Those five files are read-only here. The check reads a `g-` token inside a Tailwind arbitrary value as a class name, and my first attempt at porting the skeleton bar and the map ink tripped it — which is why both are named classes now |
| Chromium on the built stylesheet, one probe, both states | chip ink/edge `rgb(226,89,111)` on the 16 percent wash as stated, `rgb(158,171,192)` / `rgb(34,45,64)` at two parts; word slot 22px as stated, 45.76px at two parts |
| built-stylesheet byte offsets | module layer at 21k and 24k, workspace layer at 78k (§5) |
| a `var()` audit over the three module stylesheets | `modules.css` names 40 custom properties, all `--g-*` except the four published-colour washes; `indiamap.css` names 32, all `--g-*`; `dashboard.css` names 39, all `--g-*` except `--rain`, which the component sets from the payload |
| an old-versus-new selector diff over `modules.css` | 6 dead names dropped, 2 inert compound rules dropped, 3 names added (`dash-chart-bar`, `module-skeleton-bar`, `dash-map-ink`) |

## 7. What this does not claim

- **The depth registry is not this batch.** docs/108's B1.3 has two halves, and this is the styling half.
  Nothing here makes a module surface unfold from a claim in an answer, keeps one claim's evidence attached
  while another task reads it, or gives the module that owns a claim the ability to answer inside the
  conversation. That is the later batch, and until it lands a module surface is still a screen a reader
  navigates to rather than depth an answer opens.
- **Nobody has looked at these eighteen on a device.** Every measurement above is a static one: a built
  stylesheet, a headless browser at one viewport, a token audit, a selector diff. No reader has scrolled a
  surface, no layout has been checked at a phone width, and no capture of these eighteen exists. The earlier
  docs/111 note stands — a capture would be one render on one machine even if there were one.
- **A green gate is not a design acceptance.** FE13 checks that an element resolves to *some* rule, not that
  the rule is the right one; that is exactly why an element wearing only the inert `.chip.is-current` passed
  it, and why the chip that printed no colour passed FE16 for as long as it did. The five repairs in §4 were
  found by measuring, and the next batch that measures this layer may find more.
- **`src/chat/**` and `src/gpt/**` are mid-edit by other lanes.** The vocabulary check reports five `g-`
  names those files use and their stylesheet does not yet declare. It is reported rather than repaired here,
  because those files are not this lane's to touch.
- **The module layout is still the instrument design's.** The widths, the breakpoints and the grids are the
  ones docs/111 §8 records as the outstanding item. This batch changed the dress and the frame's inset, not
  the arrangement.

## 8. Open, and next

1. **The depth registry** (above) — the other half of B1.3.
2. **The card collision**: a `.dash-card` is glass from the workspace and `--g-fill`/`--g-e1` from
   `dashboard.css`. One of the two should win product-wide, and the decision belongs with the file that
   declares the glass.
3. **A browser acceptance of these eighteen**, at a desktop width and a phone width, by someone other than
   the author of the stylesheet.
