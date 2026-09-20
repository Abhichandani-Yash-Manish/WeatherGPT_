# X1's audit as it stood before lane A touched it

Read from `frontend/src/flagship/claims.audit.test.tsx` at 23:26 on 20 September 2026, before the lane that
was assigned it had written anything. Recorded verbatim so that "the audit is green now" can be checked
against what the audit MEANT, rather than against whatever it says afterwards. The file was untracked when
this was taken, so git cannot diff it; this is the only record of its intent.

## The three provenance shapes the audit accepts

| selector | shape | the check it must pass |
| --- | --- | --- |
| `.g-claim` | a Claim with its source line | it contains `.g-claim-source` |
| `.calc` | a calculation stating its inputs, source and method | its text matches `/from\s+S\d/` AND `/input value/` |
| `figure` | a figure whose rows carry the evidence id of every point | its text matches `/evidence id/i` AND it contains a `td` |

## The exclusions, verbatim, with the reason each states

| selector | because |
| --- | --- |
| `.g-prose` | the sentence the model wrote around the values; every value it states is a Claim below it |
| `.g-claim-note` | prose qualifying a claim; the claim it belongs to is audited on its own |
| `.g-chips` | metadata about this turn - when it was answered - not something the turn retrieved |
| `.g-work` | how the turn ran: steps, latency, which model planned it. A measurement of this product, not of the weather |
| `.g-tally` | what was asked and how much came back; a count of tasks, not a retrieved value |
| `.tasks` | the per-task list, which names tasks by id and repeats their own notes |
| `.g-notes` | the turn's notes and assumptions - "morning defaults to 06:30-12:30 IST" states how a word was read |
| `.g-composer` | what the reader is typing, not what the product is asserting |
| `button` | a control; its label names an action rather than stating a value |
| `[aria-hidden="true"]` | not announced to a reader and not read by one |
| `.sr-only` | a screen-reader label for a control |
| `svg` | a drawing; the chart specs audit its scale and its labels |
| `time` | a timestamp of the turn itself, not a retrieved value |

The file itself sets the standard for changing this list: *"A region is excluded by what it IS, never by
'this one is noisy': if a retrieved value ever moves into one of these, the audit should start failing, and
that failure would be correct."* So an exclusion added by this batch is legitimate only if it names a region
by what it is and would still fail on a retrieved value inside it.

## The three self-tests that must survive, whatever else changes

1. `the audit can fail — a bare number carries no provenance`
2. `a shape that only looks right does not pass — the check is on the content`
3. `every exclusion says what it is, not that it was inconvenient`

Test 3 is the one that makes a widened exclusion list self-policing, and tests 1 and 2 are the ones that make
the audit a check rather than a decoration. If any of the three changes name or disappears, the correct
reading of "green" is that the audit was softened, not that the product improved.

## The measured state at this snapshot

`cd frontend && npx vitest run src/flagship/claims.audit.test.tsx` → **9 tests, 6 failed, 3 passed**: the
three above. The six failures, and the twenty-three individual offenders, are listed in this batch's lane
report and in docs/120.

## What was also true, and is a gap this batch has to close

`scripts/verify_all.py` did not run this file, or any vitest spec: `NODE_SUITES = []` is iterated and never
populated. The audit could fail while the clean-machine entry point printed a pass. That was measured on the
same day and is now repaired in the gate (see docs/129).
