# 99 — The four reported defects: causes, repairs and evidence

17 September 2026. Four defects reported with screenshots against the redesigned surfaces. Each one is
repaired at its cause, and each repair carries a check that fails without it. Nothing here is a restyle
presented as a fix: two of the four were data defects wearing a visual costume.

## 1. The editions card said "not recorded" while the page held the number

**Reported as:** the font size of the value did not fit the card (the words spilled over the card edge).

**Cause, and it was not the font.** The card read districts_behind_the_newest_edition and
newest_bulletin_date_in_this_read from the *district-rows* read only, which is 1.65 MB and answers last. The
overview read states the same national fields in milliseconds, and the card was already printing
"Bulletin date most rows carry: 2026-09-15" from it. So while the row read was in flight the card announced
an absence the page could already disprove. Two further errors in the same three lines: the fallbacks used a
truthiness test, which turns a legitimate count of 0 into a fallback, and the value slot had one size for
every value.

**Repair:**
- The three facts now take whichever read stated them first, with nullish tests so 0 stays 0
  (TodaySurface.tsx).
- A read that is genuinely in flight states "reading…", and the caption says the rows are still being read
  while the counts come from the overview read. "Still reading" is narrowed to a read actually fetching, so a
  query the shell disabled (because the overview read failed) is not described as in flight.
- The value slot measures its own content: digits and separators keep the display size, and words step down
  to the word size, wrap on a balanced measure and cannot leave the card (DashboardCharts.Kpi with
  data-value-kind, plus the .dash-kpi-number-word rule).
- The empty space the words left behind is now the edition profile: one bar per printed bulletin date the
  read returned, labelled with its own count and its year, the newest edition marked, and any edition more
  than a year behind marked as stale (the live read has one district 1047 days back, which is the reason this
  card exists).

**Checks:** frontend/src/modules/today.dashboard.test.tsx — "takes the editions count from whichever read
stated it first, and says when the rows are still being read" (the row read never resolves, the overview
carries 14, and the card must say 14 and draw the profile) and "sets a word value at the word size and a
numeral at the numeral size".

**Live evidence:** the card reads **14 districts**, the profile draws 5 bars (2023-11-05 marked stale,
2026-09-11, -12, -14, -15), and the strip colours measure at 0.92–0.95 alpha rather than the pale 0.68 that
made a 1819-row yellow read as an empty bar.

## 2. The Today map showed almost nothing on hover, and a district could not be inspected

**Reported as:** all colours should be visible, hovering should name the district and its alert, and
selecting a district should give that district's details.

**Cause:** the fills were drawn at fill-opacity .16–.34, which over a glass card is nearly invisible; there
was no pointer tip at all; and a click on a district only moved the keyboard cursor, so no district-level
detail existed on the surface.

**Repair:**
- Fills rise to .62–.88 with a stroke of the same published colour (.16–.34 before). The rule is unchanged:
  a fill exists only where the district's own row published a colour.
- A hover tip (modules/MapTip.tsx, shared by both maps) follows the pointer and states the district, its
  state, the colour as a chip, the hazard wording as printed, the published day and the edition. It is
  positioned from the pointer event that entered the feature, so hovering 756 districts costs one update per
  district entered and none per pixel moved.
- Clicking a district (or a city on another layer) selects it, and a district inspector
  (modules/DistrictInspector.tsx) opens beside the figure with the edition, its age at this read, the day
  inspected, and every published day-row with the colour and the wording as printed, the day covering today
  marked. Two actions leave the surface and both carry the district: **Open in Warnings**
  (#/warnings?district=..., which now prefills that surface's filter) and **Ask about this district**
  (#/assistant?ask=..., a new deep link the shell seeds once into the conversation).
- With nothing selected the panel is a state index instead of blank space: every state the read returned,
  ordered by how many of its districts published a colour for the day being inspected, each row carrying the
  top colour and the coloured/total count, and choosing one filters the figure and lists that state's
  districts. None of this asks the product for anything new: it is the same read, regrouped.

**Checks:** "opens the district inspector from the figure with the district days and two working links", and
"lists the states in the read before a district is chosen, and filters the figure from one".

**Live evidence:** hovering a district returns "JAMNAGAR · GUJARAT · green · No warning in this product ·
17 Sep 2026 · edition 2026-09-15"; clicking it opens the inspector with edition 2026-09-15, age 2 days, the
yellow day row "Thunderstorm/lightning/squall" for 2026-09-15 and the green quiet rows after it, and both
links carrying JAMNAGAR.

## 3. The bubble matrix collapsed its rows

**Reported as:** the yellow and green circles ran into each other and into the labels.

**Cause:** the row pitch was 26 units against a maximum radius of 10, the bubbles were drawn from x=46 while
the colour labels were right-aligned at x=40, and the count sat above a bubble in the space the row above
needed — at the live shape of the read, where one day holds 433 and 387 district-days.

**Repair (DashboardCharts.BubbleMatrix):** the geometry is now stated as rules the checks assert —
a fixed 56-unit label gutter with the plot starting at 70, so no bubble can enter the labels; rows pitched at
twice the largest radius plus a line of text plus padding, so a count can never land on the row above; radius
capped at 13 and floored at 3; a wider viewBox (620 units) so the figure is drawn near 1:1 instead of being
scaled up; vertical day guides behind the rows; the published date as a second label line; and a title
element on every bubble carrying day, colour and count.

**Checks:** modules/matrix.geometry.test.tsx, three checks over the drawn attributes: no bubble inside the
gutter, no two bubbles closer than the sum of their radii, every row pitch greater than twice the largest
radius, nothing clipped at the top, and a cell the rows did not return drawn as nothing at all.

**Live evidence:** 13 bubbles, maximum radius 13, **minimum gap between any two bubbles 29.8 units** (the
checks require the gap to be positive).

## 4. The Map surface had no data and an empty side panel

**Reported as:** the map was blank and boring, with nothing in the panel.

**Cause, and it was a real one.** The live districts layer states a key, a name and a state and **no colour at
all** — the colour lives in the warning product. The Map surface filled a feature only from the feature's own
properties, so the one layer that can carry the warning colours could only ever be drawn as outlines, and the
surface opened on the first layer of the manifest. The side of the map was a table with no join, and nothing
to inspect.

**Repair:**
- The surface opens on the district layer, and the note under the selector says why.
- The district layer is joined to the warning rows by district key, from the same shared read the Today
  surface uses (one cache key, so the 1.65 MB read is not fetched twice). A day selector and the
  colour-only-where-published toggle come with it.
- The panel is an inspector: the chosen layer's join state in words (756 features drawn, 743 carrying a
  published colour, 13 outlines), the layer inspector with the selected feature's own properties, the join key
  it matched on, its hazard wording and how the figure drew it, the layer's attribution, and the full district
  inspector with the day rows and both action links when the layer is the district layer.
- Hover tips on every layer, and selection now zooms to the feature.
- The accessible table stays on the page in a collapsed details block, carrying the same rows the figure draws.

**Checks:** "opens on the district layer and fills a district from the warning row it is joined to" (including
the day selector moving the join off today and the figure following it).

**Live evidence:** layer **districts**, **743 filled / 13 outlines**, a tip on hover naming the district and
its published colour, and a click opening the district inspector with all five day rows and the edition.

## 5. What was touched, and what was not

- Frontend only: TodaySurface, DashboardCharts, DistrictRiskMap, MapSurface, WarningsSurface (deep link),
  App.tsx (the ?ask= seed), modules.css, and three new modules (MapTip, DistrictInspector, and the matrix
  geometry checks).
- **No backend route, adapter, registry entry or answer contract changed.** The warning payload already
  carried every field these repairs read; the defects were in which read the client trusted and in what it
  drew.
- One test was re-pointed rather than rewritten (the map's circle count is now scoped to the figure, because
  the shell's own icons are SVGs too); no test name changed, so the 203-name port ledger still verifies.

## 6. Measured state after the repairs

| Check | Result |
| --- | --- |
| React suite | **59 suites, 329 checks** (was 58 and 321; 8 checks added for these four defects) |
| TypeScript | clean |
| audit_react_frontend / build / registry / ledger | 13/13, 11/11, 10/10, 2/2 (203 names) |
| Initial bundle | 186 KB gzip against the 312 KB budget |
| axe-core | 0 violations on Ask, Today, Warnings and Published documents |
| Pictures | the eight-picture gallery re-captured from this build |

## 7. Open items

1. Nothing in the district inspector is a live warning feed; it is the stored edition's own rows, and the
   surface says so where it matters.
2. The map still draws no station markers and has no free pan, and the degenerate rectangle one district
   geometry carries near the bottom of the figure is the served geometry, not a drawing error — it is left as
   the read returned it.
3. The state index shows the first 40 states in colour order and says so; the full state table is the
   warnings surface's job.
4. These are frontend repairs: no feature acceptance state moves because a card, a tip or a join was fixed.
