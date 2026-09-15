# The Instrument Desk — a desktop frontend overhaul, 15 September 2026

The desktop page was already the product surface, but it still read as a competent
prototype: one continuous light theme, panels stacked in a column, evidence available but
not inspectable in place, no way to move between the twelve surfaces except the rail, and
a docked composer whose position depended on how much content happened to be above it.
[docs/24](24-frontend-overhaul-plan.md) and [docs/25](25-frontend-overhaul-batch.md)
recorded the first overhaul and its six findings; `scripts/audit_workspace_frontend.py`
keeps measuring them (FE01–FE06). This batch rebuilds the visual system around one idea,
adds the capabilities the audit did not yet cover, and records the repairs as FE07.

This is a styling, interaction and evidence-presentation batch. It changes no engine, no
retrieval contract, no number, unit, source or warning rule. It is not browser, device,
screen-reader, load or language acceptance, and it makes no claim about forecast skill.

## The direction: an instrument desk

The subject is field evidence, so the page is built like a piece of field equipment:

- **housing** — graphite chassis for the rail, masthead, drawer and receipt; the working
  area is bone paper on it, at instrument contrast;
- **one measured colour** — data-teal marks measured paths (links, coverage, the live
  reading); slate carries structure; sand carries rules and hairlines;
- **hazard colours stay hazard-only** — red, orange, yellow and green appear only on
  hazard chips, hazard days and hazard text read from a source. There is no green "live"
  dot, no red error and no amber caution. Interface state is carried by wording, weight,
  position and monochrome glyphs, which is the product ethic made visible;
- **two signatures** — the *validity ruler* (what window the evidence actually covers,
  with uncovered hours hatched) and the dark carbon *evidence receipt* (measure, value,
  unit, method, place, entity, window, source, retrieved instant, evidence id, task, record
  paths);
- **night desk / day desk / system** — the same tokens inverted, stored locally under
  `weathergpt.theme`, with `color-scheme` set so form controls follow.

The stylesheet is still one dependency-free file with no inline style and no external
origin, so the strict `default-src 'self'` policy is unchanged.

## What the batch added

| Capability | What it does | Where |
|---|---|---|
| Command palette | ⌘K / Ctrl-K or the rail control; every surface, the actions (new conversation, appearance, check watches, save, print), places through `/api/places/search`, and stored conversations; arrow keys, Enter, Escape | `web/shell.js`, `#palette` |
| Appearance control | Cycles system → day → night, names the state in words, persists the choice | `#theme-toggle` |
| Twelfth surface: What changed | Vintage variance between stored forecast retrievals — retrieval count, overlapping valid hours, mean and largest absolute change per parameter, retrieval list, source disclosure | `web/panels.js`, `/api/forecast/changes` |
| Raw-packet inspector | "Inspect the raw packet" on any answer opens the exact rendered packet, bounded at 60 000 characters, with the full packet still available from the download action | `web/views.js`, drawer |
| Receipt chain | The receipt now shows source → retrieved → contract → claim as a chain, so a value and its provenance read as one object | `web/views.js` |
| Map as a working instrument | Fits the viewport at any width, sea fill, district find box that highlights a match, Enter/Space selection with an accessible name, hazard fills, unmapped never green | `web/map.js` |
| Rail collection health | Job counts, newest commit and in-flight leases per product, in the rail | `web/shell.js` |
| Frame layout | The shell fills the first viewport, so the ask desk settles on the bottom edge instead of floating where the content ends | `web/style.css` block 21 |

The vintage-variance surface is explicit about what it is: it compares *stored retrievals*
for the same valid hour, names both retrieval instants, says that a change is not an error,
that neither retrieval is validated here, that upstream run identity is not exposed, and
that this is **not** forecast skill.

## What the recorded evidence shows

Evidence directory: [research/reviews/frontend-v2-20260915](../research/reviews/frontend-v2-20260915/).
The live record is [after/live-checks.json](../research/reviews/frontend-v2-20260915/after/live-checks.json);
the pre-overhaul baseline is [baseline/baseline.json](../research/reviews/frontend-v2-20260915/baseline/baseline.json).

**Composer geometry**, one reading per viewport in Chrome 152 at the top of the document:

| Viewport | Position | Top | Bottom | In first viewport | On the bottom edge |
|---|---|---:|---:|---|---|
| 1440×1200 | sticky | 1062 | 1200 | yes | yes |
| 768×1024 | sticky | 887 | 1024 | yes | yes |
| 390×844 | sticky | 674 | 844 | yes | yes |

At the end of the document the ask desk has ended, so the composer rests at 1085, 912 and
650 px respectively and the colophon strip follows it. That is the measured behaviour, not
a claim that the composer is welded to the viewport at every scroll offset.

**Surfaces**: all twelve opened by hash at 1440×1200 — one visible surface each, content
rendered, no "Request failed"/"Not found" wording, zero page errors, zero console messages.

**Capabilities, read live**: palette opens with 17 items in two groups and filters to
`Surat, Sūrat, State of Gujarāt` (S61) plus one stored conversation, Escape closes it;
appearance cycles light → dark → system and applies it to the document; the inspector opens
a 6 284-character exact packet and says it is not a summary; a district path is
`role="button" tabindex="0"` and opens the drawer on click *and* on Enter; the find box
highlights one match for "Patna"; switching to day 3 repaints 273 yellow polygons and one
unmapped polygon; one real question ("Will it rain in Ahmedabad tomorrow morning?")
first returned a clarification naming two Ahmedabad candidates and, after the choice, an
answered card of 0.0 mm over a covered window with one receipt and its source (S21).

**Print**: exporting the assistant surface produced a three-page PDF that keeps the answer
and omits the masthead, rail, composer and colophon — the print policy's intent, checked
with `pypdf` rather than assumed.

**Accessibility, automated only** (axe-core through the browser CLI, five surfaces × two
appearances): **0 violations in all ten scans**. Nine selects gained accessible names, the
map svg became `role="group"` so its focusable district buttons are no longer nested inside
an image, and the colour tokens below were corrected where they failed contrast:

| Token | Before | After | Binding ratio |
|---|---|---|---:|
| `--mute` (day desk) | #697c81 | #59696e | 3.54 → 4.63 on the sunk surface |
| `--mute` (night desk) | #81979d | #889da2 | 4.30 → 4.64 on the dark yellow wash |
| `--orange` | #b25e12 | #a35611 | 3.98 → 4.60 on the orange wash |
| `--yellow` | #8a6c00 | #856800 | 4.35 → 4.62 on the yellow wash |

Ten scans still report one *incomplete* group each: axe cannot determine contrast for text
over the housing gradient or for glyph-only controls. An automated scan is not
screen-reader, keyboard-only or zoom acceptance.

## Component and workspace checks

| Check | Result |
|---|---|
| Python tests | see README (unchanged by this batch) |
| JavaScript component checks | 57 checks across six suites (`test_charts`, `test_views`, `test_bulletin_ui`, `test_conversation_ui`, `test_suite_ui`, `test_voice_ui`) |
| Frontend workspace audit | `python3 scripts/audit_workspace_frontend.py --baseline` — FE01 **verified_live**, FE02–FE07 resolved, CSP, class-leak and syntax checks ok |
| Drift guard | `python3 scripts/check_status_drift.py` |

The component suites pin the DOM contract this batch extended: the twelfth surface, the
palette (groups, filtering, running an item), the appearance cycle, the rail readout, the
changes surface's skill limit, and the raw-packet inspector handing the exact packet to the
drawer.

## What this does not establish

- One browser (Chrome 152) on one machine, one reading per viewport. No cross-browser,
  device, orientation, zoom, screen-reader, load or latency acceptance has been run, and no
  mobile-platform claim is made.
- The automated accessibility scans are axe-core only; the *incomplete* gradient and
  glyph-only cases stay unverified, and forced-colors/high-contrast behaviour is styled but
  not measured in a real high-contrast session.
- No forecast skill, calibration, accuracy, warning validity or all-clear meaning is
  measured or implied anywhere in the interface. The vintage-variance view compares stored
  retrievals; the skill half stays blocked on run identity plus matched observations.
- No native-speaker review exists for any output language, and no speech acceptance was
  run here.
- Screenshots are local prototype states over loopback. Hosting, sharing and redistribution
  remain on hold, credentials stay in local backend configuration, and no runtime
  conversation is published.

## How to re-run

```sh
python3 -m weathergpt_data.workspace --port 8790           # serve the local workspace
python3 scripts/audit_workspace_frontend.py --baseline     # FE01–FE07 and the CSP checks
python3 scripts/build_frontend_live_checks.py              # rebuild the record from the scans
for f in tests/test_*.js; do node "$f"; done               # the six component suites
python3 scripts/verify_all.py                              # the full local verification
python3 scripts/check_status_drift.py                      # summary and registry drift
```
