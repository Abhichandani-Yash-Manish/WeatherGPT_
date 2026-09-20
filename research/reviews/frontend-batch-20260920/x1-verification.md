# X1 verified independently, not taken on the lane's word

Lane A's X1 work was checked against `x1-audit-intent-before.md` - the snapshot of what the audit MEANT
before it was touched - because the audit file is untracked and git cannot show what moved. This is what
the check found.

## What was checked, and the answer

| Question | Answer |
| --- | --- |
| Did the audit's coverage shrink? | **No, it grew**: 6 recorded packets became 8 (`clarification` and `language-hindi` added). 8 + 3 self-tests = the 11 tests that pass |
| Are the three self-tests still there? | **Yes**, by name: it can fail; a lookalike does not pass; every exclusion says what it is |
| Are the three provenance shapes still *checked* rather than matched by name? | **Unchanged**: a Claim must contain `.g-claim-source`; a calculation must match `/from\s+S\d/` and `/input value/`; a figure must say "evidence id" and contain a `td` |
| Did the exclusion list grow as a way of passing? | It grew from 13 to 16, and each addition names a **structural** region by what it is, with a reason. None is a blanket skip |
| Were the components actually fixed? | **Yes**, in five places, none of them a test edit |

## The five component fixes, and the judgement on each

1. **The notes region did not carry its own class.** The exclusion named `.g-notes`; the markup rendered a
   plain `ul.g-list`, so the turn's notes were audited as if they were values. The markup was made to match
   what the exclusion describes - the correct direction, and the opposite of widening the exclusion.
2. **A fold's count is now named as one.** The count in a disclosure header ("Requested tasks (2)") is how
   many rows the fold holds. It gained `.g-fold-count` and an exclusion that says exactly that.
3. **Timestamps are rendered as `<time dateTime>`.** `Tag` gained an `at` prop. A timestamp drawn as a
   timestamp is both better HTML and what the pre-existing `time` exclusion describes.
4. **A calculation's source is now derived from its inputs.** The recorded historical trend states thirty
   input ids and no source id, so the card printed its number with no source at all. It now reads the source
   from the facts those inputs name, and says **"source not stated"** when it cannot - which keeps failing
   X1, correctly, rather than printing a bare number. This is the one fix that changed what a reader sees.
5. **The series receipt is named as provenance.** Its rows are the plotted count, the cell, the source, the
   retrieval time, the record locator and the evidence id - provenance, not measurement, and it now says so.

## The one widening I had to judge

The `time` exclusion's reason moved from "a timestamp of the turn itself" to "when the turn ran, when a
station reported, when a bulletin was issued". That is a widening, so it needed a reason rather than a
shrug. It holds because each of those instants is rendered inside a block that names the station or the
bulletin, and the values in that block still have to be in a Claim with its source line to pass - the audit
proves that by passing on the airport and warning packets with the timestamps excused. Accepted, and
recorded here as a judgement rather than as a formality.

## The limit this approach has, stated rather than hidden

Three exclusions now excuse regions that contain source-owned numbers: a series receipt, a station's raw
transmission, and the count inside a fold. The audit cannot tell a provenance row from a measurement
dropped into one. What holds the line instead is that each region's own comment states the boundary ("a
measured value belongs in the chart's own evidence-id table or in a claim, never in this block"), and that
a `figure` and a `.g-claim` are still *checked* for the provenance they claim. This is a real limit, not a
solved problem.

## Evidence

| Command | Result |
| --- | --- |
| `cd frontend && npx vitest run src/flagship/claims.audit.test.tsx` | 1 file, **11 tests, 11 passed** |
| `cd frontend && npx vitest run src/chat src/flagship` | 14 files, **90 tests, 90 passed** - parity, print, turn-identity and page suites included |

What is NOT verified: the lane's own account and its doc (docs/120) were still in flight when this was
taken, and nothing here has been seen in a browser.
