# 98 — The aurora-glass frontend: a whole-surface overhaul

17 September 2026. This batch rebuilds the look and feel of every served surface, from the reference the
user supplied (the Dribbble "World Risk Map — Environmental Intelligence Dashboard") and from the four UI
libraries named with it. It is a frontend batch: no engine, adapter, route or evidence contract changed, and
no PS feature state moves. What follows is what was built, what was decided and why, and the evidence.

## 1. What the overhaul is

Three layers, applied in order, so that every surface inherits the same language:

1. **The design layer** (web/tokens-v2.css, imported by frontend/src/styles/app.css after the existing
   tokens): glass surfaces, an aurora field, an accent gradient, three new radii and a motion scale. Every
   value is a color-mix() over the existing tokens, so light and dark keep working and no new brand colour
   enters the system. Hazard colours are untouched and are still reached only through a published colour.
2. **The component kit** (frontend/src/ui): Panel, SectionHead, Button, IconButton, Badge, HazardChip, Stat,
   Meter, Field, Switch, Segmented, Empty, SkeletonLines, Modal and a toast host — the shadcn/ui idiom
   (class-variance-authority for variants, tailwind-merge for class conflicts) with Lucide icons and Motion
   for transitions.
3. **The surfaces**: the shell (rail, topbar, command palette, toasts, aurora), the chat (welcome, composer,
   transcript, answer card), the evidence frame every module renders through (SurfaceShell, Facts, DataTable,
   Limits, Sources, Failure, Reading, ColourTag, the pinned-places bar), the dashboard (Today) and the map
   deck (Map), plus the module stylesheet those surfaces share.

## 2. What was adopted from each reference, and what was not

| Reference | Adopted | Not adopted, and why |
| --- | --- | --- |
| shadcn/ui | The component architecture: vendored components in frontend/src/ui, variants through cva, class merging through tailwind-merge, Radix stays available for popovers | Nothing: this is the base of the kit |
| Lucide | Every icon in the shell, the chat, the dashboard, the surfaces and the map: one icon map (ui/icons.ts) so the rail, the palette and a surface header cannot disagree | Nothing |
| Motion | Page-level reduced-motion config (already present), segmented-control indicator, toast entry, welcome stagger | Pointer-listener variants (whileHover/drag) are avoided: they attach DOM listeners that jsdom's stubbed AbortController rejects, and CSS hover does the same job |
| Tremor | The data language: stat tiles with label/value/unit/foot, meters, progress and colour-coded composition, all drawn from returned values | Its runtime. Tremor charts run on Recharts, which would add roughly 100 KB gzip to a chart chunk and would sit beside the project's own evidence-driven SVG charts, which already obey the rule that a chart may draw only a value the engine returned |
| HeroUI | The surface language: soft glass panels, pill chips, rounded inputs, hairline borders, quiet labels | Its runtime. @heroui/react brings a provider, a Tailwind plugin and a React-Aria tree; the initial-graph budget is 312 KB gzip and the kit above already covers the components these surfaces use |

The decision is recorded rather than hidden: the two heavy runtimes were evaluated and declined for a stated
reason, and the parts of their design that this product needs were built in-repo, in TypeScript, against the
token layer. The bundle measurement is in section 5.

## 3. The map deck (the user's explicit ask)

The Map surface now reads as an instrument rather than a table with a figure:

- **A deck**: the figure on the left (up to 46rem, in its own glass frame) and the feature table beside it,
  with the readout line under the figure.
- **Controls**: zoom in, zoom out and the current level in words; a **find-a-feature** field that moves the
  keyboard cursor to the first feature whose own description matches. Controls sit after the figure in the
  DOM and before it visually (CSS order), so the tab order stays layer selector, then the figure's single
  stop, then the controls.
- **A legend built from the pass that drew**: one chip per hazard colour that actually appears on the chosen
  layer, with its count, plus the outline count. A colour with no feature is not shown.
- **Zoom** is an SVG transform attribute on a group, attribute-driven and therefore CSP-safe.
- The accessible equivalent (the full table), the layer manifest table, the keyboard traversal, the working
  place from a place feature and the /api/now read for it all remain, unchanged in behaviour.

The Today dashboard's own map keeps its stricter joined rule (a fill only where the district's own warning
row published a colour for the day being inspected), and both maps share one projection (mapFigure.ts).

## 4. What the shell and the chat gained

- **Aurora field** and a glass rail with the surface icon per entry, an active pill that animates between
  entries, the shortcut printed on hover, and one real key hint.
- **A glass topbar**: the store-state badge, the per-product health panel as a glass popover, "Reading as"
  and "Answer in" as pills, and icon actions for plans, commands, theme, new and lock.
- **Toasts** for what a reader just did (chrome, never evidence).
- **Chat**: a hero welcome with the ideas as glass cards, a glass composer dock with send/mic/stop icons, and
  a transcript restyled to glass (user turns carry the accent gradient, fact rows are tiles, the receipt is a
  glass panel, the machine record is an inset pane).
- **Every module surface** inherits the glass section panes, the icon-tiled header with status chips, framed
  tables, tile counts and icon-headed footer sections, because they all render through the same components.

## 5. Measured evidence

| Check | Result |
| --- | --- |
| TypeScript | tsc --noEmit clean |
| React suite | 58 suites, 321 checks passing (was 57 and 316; one new suite for the component kit) |
| Python suite | 1338 passing, unchanged by this batch |
| Initial bundle budget | main 604 KB raw / 182 KB gzip + react 4 KB gzip = **186 KB gzip against the 312 KB budget** (127 KB before the batch) |
| Stylesheets | 1 (the audit checks no external CSS import) |
| audit_react_frontend.py | 13 of 13 |
| audit_react_build.py | 11 of 11 |
| audit_surface_registry.py | 10 of 10 |
| audit_port_ledger.py | 2 of 2: all 203 named tests still exist in their 33 spec files (no test was renamed) |
| verify_all.py | 20 steps, 0 failed |
| axe-core | 0 violations on Ask, Today, Warnings and Published documents (a scroll-region violation the table frames introduced was repaired: the wrapper is focusable only when it actually overflows) |
| Pictures | the eight-picture gallery in docs/images/ was re-captured from this build at 1440x900 |
| Responsive | the shell and the dashboard keep clientWidth = scrollWidth at 375, 768, 1024, 1400 and 1440 px |

## 6. What this batch does not claim

- **No feature state moves.** Warning delivery, nationwide corpus acceptance, language quality, voice, mobile
  and service scale stay exactly where docs/93 leaves them. A glass panel is not an accepted feature.
- **No engine or evidence change.** No route, adapter, registry or answer contract was touched; the audits
  and the Python suite cover that, not this document.
- **No mobile-device or native-speaker review.** The responsive rules are measured in a headless browser, and
  the language surfaces were not reviewed by a speaker of any of them.
- **The heavy references are not wired in.** HeroUI and Tremor runtimes were declined for budget and
  duplication reasons (section 2); the parts adopted from them are in-repo components.
- **No performance claim beyond the budget.** The dashboard still reads about 3.2 MB on first open (docs/97
  section 15); this batch did not reduce that, and the geometry is now also drawn on two surfaces.

## 7. Open items

1. The answer card's action row (copy, save, print, collect evidence, briefcase) still uses the old button
   classes in places; the receipt is glass but that row is the next pass.
2. The map draws districts, states, land, basins, coast zones and places; station markers from the
   observations network are not drawn yet, and the deck has no free pan/zoom.
3. The dashboard's chart cards use the project's SVG charts, not Tremor; if Tremor's runtime is ever wanted,
   it should land behind a lazy boundary with its own budget line.
4. Dark theme is derived but has not been reviewed picture by picture, and no one has looked at these
   surfaces on a phone.
