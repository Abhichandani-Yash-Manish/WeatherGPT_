# The browser sweep: 19 surfaces, four widths, and one real accessibility finding

20 September 2026. Nobody had looked at the eighteen restyled module surfaces in a browser - the gate reads the
built CSS, and the audit measures ink against the page ground - so this ran the project's own UI harness against
a real workspace on loopback. It found a serious accessibility defect that no unit test, no built-output audit
and no lane summary had reported.

## How it was run

    python3 -m weathergpt_data.workspace --port 8781 --no-warm --no-plan-watcher
    cd frontend && UI_BASE_URL=http://127.0.0.1:8781 npx playwright test tests/ui/routes.spec.ts
    cd frontend && UI_BASE_URL=http://127.0.0.1:8781 npx playwright test tests/ui/a11y.spec.ts

## What passed

- **84 route checks: all passed** - 19 surfaces plus the two place addresses, at 1440, 1024, 768 and 390. Each
  one loads with its heading, makes no failed request, logs no console error and has **no horizontal overflow**.
  That is the layout verification the stylesheet rewrite could not have had any other way.
- **84 of 88 accessibility checks passed** - axe clean on every surface at every width, including the place page
  in both its states.

## What failed, and what was repaired

`#overview` failed axe at **all four widths** with `color-contrast` (serious). Repairing one selector revealed the
next, which is the evidence that this was one property of the ladder rather than four mistakes:

| Offender axe named | What was wrong | Repair |
| --- | --- | --- |
| `.chip-colour[data-colour='green']` | a **published hazard colour** at **4.07:1** on its own 16 percent wash, because `--*-wash` mixes over `transparent` and therefore composites over whatever card it lands on | the wash now mixes over `--g-void`, so the chip's field is a value the product decides (**5.1:1**) |
| `.dash-map-caption`, `.inspector-count` | the tertiary step as text on a raised card | mist |
| `.dash-map-zoom`, the map legend | `.quiet` text, and a card's fill costs the tertiary step about half a point | **the ladder**: quiet text now takes mist everywhere. FE14's own comment states the rule - over the sky the product uses paper and mist, and the tertiary step belongs to surfaces - but a raised card is not one of the grounds FE14 measures |
| `table ... th[scope="col"]` | table headers, same reason | `.g th` takes mist |

## What is still failing, and why it is recorded rather than papered over

**One axe violation remains on `#overview`: the map table's column headers, at 12px and weight 600.** Measured in
the page at the night hour: the ink computes to `rgb(115, 127, 151)`, which is the night hour's own
`--g-mist-2` (`#737f97`) - so a rule I did not find is still setting those headers to the tertiary step, and my
change to `.g th` did not reach them. On the page ground that ink measures **4.755:1** and passes; on the card
behind the table it fails, which is the whole finding.

**Two checks disagree about this and both are right about what they measure.** FE14 measures the ink ladder
against the grounds it knows, and FE16 measures a published colour against its own wash - both pass. axe
composites what the browser actually paints, including a card's gradient fill, and fails. FE16's model of "a
published colour on its wash over a card" is an assumption; the page is a gradient. That gap is the real
finding here, wider than the one header row it caught.

**A limitation of the diagnostic I wrote for it**: `frontend/tools/a11y-contrast.mjs` reports a node's computed
ink and walks up for an opaque background colour - and a card drawn with a `background-image` gradient has a
transparent `background-color`, so the tool reports the page ground and rates the header as passing (4.755:1)
where axe rates it as failing. The tool is useful for finding a colour and misleading for judging it, and that
is written here so the next person does not trust it further than it goes.

## Repairing the ladder did not move the gate

After all of it: `python3 scripts/audit_react_frontend.py` **19 checks, 0 failed** (FE12-FE17 included), and
`npx vitest run src/modules src/styles src/gpt` **30 files, 191 tests, 0 failed**.

## What is not covered

- **Only the hour the sweep ran in.** The workspace resolves its ground from the clock, so these runs measured
  the night ladder. Daybreak, noon and golden are asserted in tokens and measured by FE14/FE16, not swept in a
  browser - and the light hours are exactly where a hazard colour's field is hardest.
- **No visual baselines.** `visual.spec.ts` iterates the registry and has none stored for the new modules, so
  nothing here checks that a surface *looks* right, only that it loads, fits, and passes axe.
- **No device.** Headless Chromium on one machine at four widths.
- **The remaining violation is not fixed**, and the reading it needs is a design decision: either text on a card
  takes a brighter step than the page does, or the card's fill stops lightening the field behind small text.
