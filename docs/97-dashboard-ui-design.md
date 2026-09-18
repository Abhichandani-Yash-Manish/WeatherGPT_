# 97 — The WeatherGPT command dashboard: UI/UX design

17 September 2026. A design specification for a WeatherGPT analytics dashboard that takes its layout and
visual language from the referenced Dribbble shot (World Risk Map — Environmental Intelligence Dashboard)
and from the supplied screenshot, while keeping every element inside this workspace own evidence rules.

The design is implemented on the Today surface (the overview view) so the surface registry, the port ledger
and the audit suite stay valid: this is a redesign of a served module, not a twentieth surface.

---

## 1. What the reference does, and why it reads as high-end

Anatomy of the shot, read from the screenshot:

1. **Chrome**: a light, near-neutral ground; a black pill primary action top-right; a rounded outer frame
   holding the app; a narrow icon rail on the left with a logo at the top and utility icons at the bottom.
2. **Command bar**: brand block, a wide rounded search field, three compact dropdown filters (region, asset,
   risk type), one period dropdown, a notification bell with a small badge, and an avatar.
3. **KPI row**: four equal cards. Each has a small glyph + label, one very large numeral with a small unit, a
   delta line, and a micro-visual (radial gauge, stacked bars, mini bar chart, progress bar).
4. **Map card**: the visual centrepiece, roughly half the content width. Title + one-line subtitle, a soft
   topographic/heat-textured map, three floating controls (zoom in, zoom out, recentre), a legend strip along
   the bottom with four swatches and range labels.
5. **Two chart cards** to the right: a bubble matrix (x = category, y = severity, bubble size = count) and an
   area/line trend with a tooltip and a period dropdown.
6. **Bottom row**: a severity list with coloured icons, labels, deltas and ages on the left; an insight card
   on the right with a big percentage, a confidence ring, a concentric decorative chart and an impact line.
7. **Craft details**: generous white space, one accent hue plus a warm/cool risk ramp, pill shapes, 12–16 px
   radii, low-contrast hairlines, numerals in a tabular face, and hover-lift on cards.

What makes it feel finished is not the decoration: it is the *rhythm* (one dominant element, one dense row,
two support columns), *alignment* (everything on a strict grid), and *restraint* (one accent, one ramp).

---

## 2. Three deliberate divergences (and why they are not optional)

| Reference element | WeatherGPT | Reason |
| --- | --- | --- |
| World map with global risk shading | **India map**, districts coloured by the warning colour IMD itself published | The workspace has no global dataset; the district warning product is national. Drawing a world map would invent geography the sources do not carry. The map frame is layer-driven, so a global layer could be added the day one is connected. |
| Portfolio Risk Score 72/100, +8.8% vs previous period | **Counts of published facts** (districts read, district-days with a published colour, editions behind the newest read, radar stations reporting) | The product states plainly that it produces no confidence score, no risk score and no skill score. A single index would contradict the product on its own front page. |
| Confidence 95% ring, High Potential Impact | **Composition of the read** (share of district-days by published colour, newest edition date, and how many districts published nothing) | Same rule. A share of published colours is a fact; a confidence percentage would be an invented number. |

Two more constraints from the existing token layer, quoted from web/tokens.css, hold throughout:

- Hazard colours (red, orange, yellow, green) are IMD hazard colours and appear **only** on hazard chips,
  hazard days and hazard text read from the source.
- A chart may only draw a value the engine returned; missing is drawn as a gap or a dashed hairline, never as
  a point, a bar or an interpolated segment.

---

## 3. Design principles

1. **Evidence is the aesthetic.** The striking part of the reference is order and contrast; here the order is
   made of provenance. Every numeral, chip and bar has a retrieval time, a source id and a unit within one
   glance of it.
2. **One dominant element.** The map is the only large shape on the page; everything else is a card of equal
   height on a strict grid.
3. **Missing is a state, not a zero.** No colour published means an outline; no row joined means "not in this
   read"; no printed date means "not stated".
4. **The ramp is quoted, never chosen.** A district is filled only with the colour its own returned row
   states. There is no interpolation, no gradient and no invented severity.
5. **Motion explains.** Only the existing rise/fade utilities; all collapse under prefers-reduced-motion.

---

## 4. Tokens and visual system

Everything is built from web/tokens.css. No new hex value, no new typeface, no third stylesheet.

| Role | Token | Use |
| --- | --- | --- |
| Ground | --ground | the page behind the cards |
| Card | --paper on --line hairline, --r-card 8px, --lift-1 | every card; --raiser + --lift-2 for the map only (it is the lifted element, as the reference lifts its map) |
| Ink | --ink / --ink-soft / --mute | numerals and headings / body / captions |
| Accent | --data, --data-wash | interactive and measured-path elements: focus rings, active toggles, links, the reporting ring |
| Rule | --sand, --sand-wash | section rules and the "newest edition" marker |
| Hazard | --red/orange/yellow/green + washes | only through .chip-colour[data-colour], set only from a returned colour |

Typography: --step-5 for KPI numerals (hero), --step-3 for the surface h1, --step-2 for card figures,
--step-1 for card titles, --step-0 for body, --step--1 for captions and axis labels, --mono with
tabular-nums for every measured value, identifier, coordinate and date.

Geometry: --space-* for all gaps; --r-card for cards and controls; --r-pill for filter chips and toggles;
--pad for surface padding. Minimum touch target 44x44 px on interactive rows, chips and map controls.

---

## 5. Layout system

Surface frame: max-width 84rem, padding --pad, vertical rhythm --space-5 between bands.

| Breakpoint | Grid | Composition |
| --- | --- | --- |
| >= 1400px | 12 columns | Filter bar in two rows; 4 KPI cards in one row; map spans 7 columns and 2 rows; the two charts stack in the 5-column side column; bottom row splits 7 / 5 |
| 1024-1399px | 12 columns | KPI row stays 4; map spans 12 (full width); the two charts sit side by side beneath it; bottom row 6 / 6 |
| 768-1023px | 6 columns | KPI 2x2; map full width, 4:3; charts stacked full width; bottom row stacked |
| < 768px | 1 column | KPI 2x2; map full width, 4:5 with a horizontally scrollable legend; filters wrap to two rows; the district list becomes a card list; every chart keeps its table alternative below it |

Band order (top to bottom), which is also the DOM order and therefore the tab order:

1. Header: title, lead, read line (view, status, read at).
2. Filter bar: search, state, colour, day, toggles, reset.
3. KPI row: four cards.
4. Map band: map card (dominant) + two chart cards.
5. Bottom band: warned-district list + composition card.
6. Right-now card: the existing place strip, unchanged in behaviour.
7. Evidence footer: limits, not-established, sources (from SurfaceShell).

---

## 6. Filter bar

Fields, left to right: **Search district** (text, client-side substring), **State** (select, from the rows
this read returned), **Published colour** (select: any / red / orange / yellow / green / no colour stated),
**Published day** (select: any / day 1-5, labels carry their derived date), and two toggles:
**Colour only where published** (default on) and **Dim districts with no published hazard** (default off).
A **Reset** button appears once any filter differs from its default.

Behaviour: every filter runs in the browser over the rows and geometry this read already holds; the product
is not asked again, and the bar says so in one caption. Filtering never changes a value, only what is shown.
The active-filter count is stated next to the KPI row so a filtered read cannot be mistaken for the read.

---

## 7. KPI cards (four)

Anatomy of each card: glyph + label (step--1, caps-free, mute), hero numeral (step-5, tabular), unit or
qualifier beside it (step-0, ink-soft), one caption line carrying the source and the read instant, and a
micro-visual that encodes the same fact it states.

| # | Label | Numeral | Micro-visual | Source |
| --- | --- | --- | --- | --- |
| 1 | Districts in this read | count | a 100%-wide segmented strip of the colour tally; the unset share is hatched, not coloured | warnings national, tally |
| 2 | District-days with a published colour | sum of the tally | four labelled bars, one per published colour, each with its exact count | same tally |
| 3 | Editions behind the newest in this read | count, with the oldest age beside it | a small age ruler: newest edition marked in sand, oldest marked with its day count | newest_bulletin_date_in_this_read, districts_behind_the_newest_edition, oldest_bulletin_age_days |
| 4 | Radar stations reporting a status | reported of returned | a reporting ring (SVG arc, attribute-driven) plus the two numbers in words | radar stations / reported |

States: a KPI whose payload field is absent renders "not recorded" in place of the numeral and keeps its
micro-visual empty with a dashed baseline; it never renders 0 for a value the read did not state.

---

## 8. The map card (the centrepiece)

**Join model, stated on the card.** The map is a join of three reads, each with its own retrieval time: the
served district geometry (/api/map/static/districts: 756 polygons, each with k/n/s), the national warning
rows (/api/warnings/national: one row per district with its published days), and the composed overview
(/api/overview: counts and editions). The card names the join key (the district key) and states that a
geometry with no matching warning row is drawn as an outline, because absence of a row is not absence of a
warning.

**Fill rule.** A district path is filled only when its own returned row states a colour, and only through
.chip-colour[data-colour] equivalent classes on the SVG path. Four classes exist (red, orange, yellow,
green, as published). Any other value, or none, leaves the path unfilled with a hairline stroke. No gradient,
no interpolation, no severity ramp of our own.

**Controls.** Zoom in, zoom out, reset (three 44x44 buttons, top-right of the frame, keyboard reachable);
the two toggles from the filter bar; a legend strip along the bottom with the four hazard swatches plus a
"no colour published" swatch, each with its district-day count from the tally.

**Readout.** A fixed-height line under the map states what is under the pointer or the keyboard cursor, in
the surface own words: district, state, the published day label and colour, the hazard wording as published,
the edition date, and "not in this read" when the join found no row. An empty readout states how to inspect
the map instead of showing a blank.

**Keyboard.** The drawn districts act as one tab stop; ArrowLeft/ArrowRight/ArrowUp/ArrowDown move the
cursor across districts in the current filtered order, Home/End jump to the ends, Enter selects the district
into the readout, Escape clears. Focus is a visible 2px --data ring on the path.

**Accessible equivalent.** The same information is a real table under the map: district, state, day, date,
colour chip, hazard wording, day state. The map is aria-described as a schematic figure with a summary line
(how many districts are drawn, how many carry a published colour), never as the only carrier of the data.

**Zoom.** Three fixed levels (1x, 2x, 4x) applied as an SVG transform attribute on the drawn group, centred
on the selected district or the map centre, with the current level stated in words. Attribute-driven, so it
works under the strict CSP.

---

## 9. Charts

**Chart A — published colour by published day (bubble matrix).** X axis: day 1 to day 5 with the derived
date under each label. Y axis: the five published values (red, orange, yellow, green, unset). Bubble radius
is a square-root scale of the count of district-days in that cell, so area tracks the count; the exact count
is printed beside the bubble when the cell is non-zero. A cell with no returned rows is a gap: no bubble, no
zero dot. Bubble fill follows the published colour only for the hazard ramp; unset is a hatched neutral. A
table of the same cells sits beneath the chart.

**Chart B — editions by printed bulletin date.** Bars of the number of districts per printed bulletin date,
oldest to newest, with the newest marked in sand and each bar labelled with its exact count. Dates with no
editions are gaps, never interpolated. The read that carried a November 2023 date shows as a separated bar
with its date printed, because that separation is the finding.

Both charts are SVG with presentation attributes only (no inline style), each wrapped in figure/figcaption
with the exact numbers in the caption and a table alternative.

---

## 10. Warned-district list

Purpose: the districts whose published days cover **today** and are not quiet, sorted by the strongest
published colour (red, orange, yellow) then alphabetically. Each row: colour chip, district name, state, the
hazard wording as published, the day label with its date, and the edition date. Rows are buttons that set the
map selection, so the list and the map are one instrument.

Empty states are distinct and stated: "no published hazard covers today in this read" (all quiet or future
days) versus "no rows returned". The card shows the first 12 with a "show all N" control; the full set stays
in the table under the map.

---

## 11. Composition card (in place of the insight card)

Left: a donut of district-days by published colour, drawn as SVG arcs from exact counts with the total in the
centre and every slice labelled in a legend with its count. Right: three lines of prose facts — the newest
edition date, how many districts carry an edition older than it, and how many district-days published no
colour — followed by the standing limits (not a risk score, not a forecast, not an all-clear, origin
unverified). The reference confidence ring is deliberately absent; the donut is a composition of published
values, and its caption says so.

---

## 12. Right-now card (kept)

The existing place strip is kept unchanged in behaviour and wording: name a place, read GET /api/now, and
keep the station observation, the published district day and the model hours in three separate rows with
their own ages. It is the page promise that the dashboard reads a product, while this card reads a point.

---

## 13. States

| State | Treatment |
| --- | --- |
| Loading | The KPI row shows four card skeletons with the label only and a dashed numeral placeholder; the map frame shows its outline grid with a "reading geometry" caption; charts show axes without bars. No number is ever shown before it is read. |
| Empty (read returned no rows) | Every card states its own absence in words and keeps its frame; the map draws an empty frame with the reason. |
| Error | One alert for the surface read (the existing Failure component). Auxiliary reads (geometry, national rows) fail inline and quietly, each naming its own read, so a page never grows five alerts. |
| Stale | The age is stated beside the affected value (edition age, retrieval age), never as a colour of our own. |
| Partial | The card that lost a read keeps its frame and says which read is missing; the rest of the page stands. |

---

## 14. Accessibility

- Contrast: all text >= 4.5:1 against its surface; the delete-control defect repaired in docs/96 is the
  precedent for measuring the rendered result with axe rather than trusting the class list.
- Focus: every interactive element has a visible ring (2px --data, 2px offset); the map path focus ring is
  drawn on the active path and mirrored by the readout and the table row.
- Targets: >= 44x44 px for map controls, toggle pills, list rows and filter selects; spacing >= 8 px.
- Chart alternatives: every chart has an adjacent table with the same numbers, and each SVG figure carries
  role="img" with an aria-label that summarises the encoding and the count.
- The map is not pointer-only: the keyboard path above, plus the table equivalent, plus the readout line.
- Motion: only the existing rise/fade utilities; nothing animates on scroll; prefers-reduced-motion collapses
  them.
- Print: cards break inside, the map prints at its frame size, and the tables carry the data.

---

## 15. Performance and delivery constraints

- Three reads on the dashboard. Measured on this machine, 17 September 2026: /api/overview 2.9 KB,
  /api/warnings/national 1.65 MB (756 rows), served district geometry 1.53 MB (756 polygons) — about 3.2 MB on
  first open, then served from the render cache. Geometry is fetched once, memoised, and projected once per
  filter change; the map's path list is memoised, so hovering a district re-renders the readout and not 756
  paths.
- The two dashboard reads wait for the overview read, so a failed overview does not ask the store for 1.65 MB
  of rows nobody will see.
- No inline style attributes anywhere: dynamic encodings use SVG presentation attributes or CSSOM writes,
  which is what the strict CSP (style-src self) permits; the surface must render identically with the policy
  enabled.
- One stylesheet: the dashboard classes are appended to modules.css, which is imported once.
- The surface keeps its registry id (overview) and its exported Surface and intents, so the surface registry
  audit, the port ledger and the existing Today checks stay valid.

---

## 16. Honesty mapping (reference element to WeatherGPT element)

| Reference | Here | Evidence carried |
| --- | --- | --- |
| Environmental Risk Overview title | Today, with the read line (view, status, read at) | envelope view/status/generated_at_utc |
| Filters (All Regions, All Assets, All Risk Type, Last 30 Days) | Search, State, Published colour, Published day | the rows this read returned; client-side only |
| Portfolio Risk Score | Districts in this read | warnings national |
| High-Risk Assets | District-days with a published colour | tally |
| Active Alerts | Editions behind the newest in this read | newest edition, oldest age |
| Monitored Assets | Radar stations reporting | radar stations/reported |
| Risk map | Published warning colour per district | geometry + national rows, joined by district key |
| Risk Exposure bubbles | Published colour by published day | tally per day |
| Portfolio Risk Trend | Editions by printed bulletin date | bulletin date counts + newest edition |
| Top Risk Regions list | Districts with a published hazard covering today | per-district days, hazard wording, edition date |
| Intelligence Insight + confidence | Composition card | share of district-days by published colour + limits |

---

## 17. Verification of this design

Measured at the end of this batch, 17 September 2026:

- **Eleven component checks** in frontend/src/modules/today.dashboard.test.tsx: KPI numbers from the payload and
  an absent field as "not recorded"; a fill only from the published colour, with a no-colour day and a district
  with no row both left as outlines; keyboard traversal to a district with no row, with the readout saying so; a
  filter that narrows in the browser and states that the product was not asked again; the day selector changing
  the fill and the toggle stopping it; a bubble per returned cell with an empty cell as a gap; the warned list
  carrying only today's non-quiet districts; a failed warning read leaving the rest of the page standing with no
  alert; no number before the read answers; one alert and one h1; and the map's table carrying the same rows the
  figure draws, including a district with no warning row.
- **The existing Today checks stay green** after being re-pointed at the KPI row: national counts, the tally
  table (an absent colour still stated as "not recorded"), the right-now card, the surface limits and sources,
  one h1, and the token contract across the surfaces' reads.
- **Suites:** React 57 suites and 316 checks with tsc --noEmit clean (was 56 and 305); Python 1338 passed.
- **Audits:** audit_react_frontend.py 13/13; audit_react_build.py 11/11; audit_surface_registry.py 10/10;
  audit_port_ledger.py 2/2 (203 names in 33 spec files); still one stylesheet.
- **Accessibility:** axe-core reports 0 violations on Ask, Today, Warnings and Published documents.
- **Responsive, measured in the same headless browser at four widths** (clientWidth equals scrollWidth at every
  one, so no horizontal overflow anywhere):

  | Viewport | KPI columns | Map aspect ratio | Map width |
  | --- | --- | --- | --- |
  | 375 x 812 | 2 | 4 / 5 | full column |
  | 768 x 900 | 2 | 4 / 3 | 652 px |
  | 1024 x 900 | 2 | 4 / 3 | 897 px |
  | 1400 x 900 | 4 | 16 / 11 | 1038 px (band in one column, charts side by side) |
  | 1440 x 900 | 4 | 16 / 11 | 608 px (band in 7/5 columns) |
- **A fresh capture replaces docs/images/04-today.png** (1440x900, headless Chrome on loopback against the live
  store): the four KPIs, the map beginning, and the published-colour by published-day matrix. The earlier
  capture of the old Today surface stays in the repository history and is described in docs/84.

## 18. Open items

1. The map draws districts only. A states or land outline layer exists in the manifest and could be added as
   optional context; it is not drawn until the design is reviewed with real data on screen.
2. Zoom is fixed-step, centred on the selection. Free pan/zoom needs a projection service or a vector tile
   story, which is outside this surface.
3. The bubble matrix will be unreadable in a month when every day carries thousands of rows; a per-state
   breakdown is the likely next axis, and the chart is written so the cell key can change without a redesign.
4. No mobile device has been used to review this design: the responsive rules above are measured in a
   headless browser at 375/768/1024/1440 px, not on hardware.
