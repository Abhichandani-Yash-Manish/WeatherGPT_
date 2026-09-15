# Comparing two forecast sources, from the rules path — 15 September 2026

PS feature 3 lists three things: NWP integration (GFS is connected), **model-vs-model comparison exposed in the
answer**, and WRF (no accessible source). The comparison existed as an operation - `forecast/crosscheck`, with
its own caveat about shared lineage - but only the *model* planner recognised the asking shape: a turn that
needed no model, which is the rules-first floor this project works to, could not produce it. That is what this
round repairs.

## What landed

| Landed | Where | Evidence |
|---|---|---|
| The rules recognise a request to compare forecast sources or check another model | weathergpt_data/rule_planner.py (`CROSSCHECK`) | tests/test_providers.py; the live journey planned by `deterministic_rules` |
| A crosscheck with **no measure named** is still left to a model, because "another model" of what is not a question the rules may guess | weathergpt_data/rule_planner.py | the same test suite |
| The comparison and its difference stay visible: the answer carries them, the page renders the calculations, and a Markdown export lists them | weathergpt_data/crosscheck.py, web/views.js | the live packets and the rendered calculations |

## What the comparison is, and is not

For the same point and window the workspace reads two connected products - the GFS point forecast and the
Open-Meteo best-match product - and reports both values and their difference, with the method recorded on the
calculation. What it says about them is narrow on purpose:

- The best-match product **may include GFS upstream**, so agreement does not establish accuracy and two equal
  numbers are not two independent confirmations. The caveat travels in the answer and in the notes.
- No average of the two is produced, no source is declared the winner, and no confidence, probability of
  correctness or skill score is invented.
- A comparison is only computed when the two windows match exactly and the hourly rows are complete; otherwise
  the comparison is reported as not comparable rather than approximated.

## Measured live

`tmp/evidence-model-comparison.py` against a live local server; packets in
`research/implementation/model-comparison-20260915/`.

- *Compare the models for rainfall in Ahmedabad tomorrow morning.* → `answered`, planned by
  `deterministic_rules/rule-planner-v1`, four facts and two calculations, with the comparison text present on the
  task and the caveat in the notes.
- *Will it rain in Ahmedabad tomorrow morning?* → `answered`, one fact, no calculations: a plain rain question
  is not a crosscheck.

## What this does not establish

- No forecast skill, calibration or accuracy, and no statement that either source is better.
- No ensemble spread: the connected products are deterministic runs, and spread is not computed here.
- WRF remains without an accessible source, so it is still absent from the comparison.
- One place and one window were measured on one morning. Nothing here is a general claim about model agreement.
