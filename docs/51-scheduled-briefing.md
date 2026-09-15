# A briefing you write on a schedule: named places, the products as read, and what changed — 15 September 2026

This is the second half of WS7 in [docs/49](49-engine-architecture-and-gap-analysis.md), and it closes
that workstream's exit check. The first half ([docs/50](50-personas-and-the-briefcase.md)) gave the page
a reading position and the briefcase that keeps a composed brief. What was still missing was the
artefact a reader can have waiting: a dated briefing over named places, written by a runner, with the
change since the previous run measured rather than remembered.

## What landed

| Landed | Where | Evidence |
|---|---|---|
| A briefing over named places: the official district warning day per place, the CAP relay reported separately, the forecast window as retrieved, and what could not be read recorded rather than filled | weathergpt_data/briefing_run.py | tests/test_briefing_run.py — twelve checks over synthetic product views |
| A runner that writes the Markdown, the full record and a series index, and prints one summary line with the measured latency | scripts/briefing.py | research/implementation/briefing-20260915/series/ |
| A foreground interval: `--every SECONDS --runs N` sleeps between runs inside the process and says so, because there is no daemon, no push and no scheduler outside the command | scripts/briefing.py | the recorded two-run series and its stdout |
| Change since the previous run, measured against that run's own record: same, changed, or not comparable when one of the two runs did not read the part | weathergpt_data/briefing_run.py | the second run of the series read `same` against the first |
| The page reads the newest briefing in this workspace's series directory and renders it, or says nothing has been written and how to write one | weathergpt_data/workspace.py, web/panels.js, /api/briefing/latest | tests/test_briefcase_ui.js; browser-briefing-block.json, browser-briefing.png |

## The rules the tests pin

- **A quiet day is a quiet day in one product.** It is written as the product states it, never as an
  all-clear, and every mention of an all-clear is a statement that this is not one.
- **The CAP relay stays a separate product.** It is reported with its own source id and lifecycle
  count, and it is never merged into the district day.
- **A forecast is quoted, not summarised.** First and last value of the retrieved series with its
  sample count, labelled as model output for a grid cell and not an observation.
- **A part that could not be read is recorded with the reason**, and the run continues rather than
  substituting another product.
- **A place list is required.** A briefing reads named places; it does not sweep the country.
- **The change reading never guesses.** No previous run is `no_previous_run`; a part read in only one
  of the two runs is `not_comparable`, not a change.
- **An interval needs two runs to be measured as an interval.** The runner refuses `--every` with one run.

## Measured on 15 September 2026

`python3 scripts/briefing.py --place 'Ahmedabad, Gujarat' --place 'Kochi, Kerala' --day 1 --every 20 --runs 2
--out research/implementation/briefing-20260915/series`

- Run 1 at 05:01:19 UTC: 2 places, the official day read for both, latency 3.393 s, reading
  `no_previous_run` (there was nothing to compare against).
- The runner printed the next run instant and the note that this is a foreground interval, then slept
  20 s inside the process.
- Run 2 at 05:01:42 UTC: the same two places, latency 29.886 s (a cold read of the relay and district
  layer; the first run was warm), and the change reading came back `same` — compared against run 1's
  record, not against a memory of it.
- The series directory holds two Markdown briefings, two full records and an `index.json` naming both
  runs, their latencies, their intervals, their content hashes and their change readings.
- The workspace series (`data/runtime/briefings`, one run) is what the page reads: the Briefcase
  surface showed the run instant, the identity hash, the places read, the day, the interval, the
  latency, where it was written, the briefing text and the limits list.

## What this does and does not establish

- It establishes a briefing artefact, a runner, a measured interval and a change reading that is
  computed from the previous record.
- It does **not** establish a service. The interval is a foreground loop: close the terminal and
  nothing runs. There is no daemon, no push, no delivery, no email and no mobile notification. A user
  who wants it on a schedule runs their own scheduler and owns that trade.
- The two-run series is two runs of one afternoon on one machine; it is not a reliability measurement
  over days, and the cold latency above is one observation, not a percentile.
- No forecast skill, accuracy, impact or operational clearance is claimed. A briefing reports what
  the connected products published, and the CAP relay's geographic applicability to a place is still
  not computed.
- The page check is one desktop viewport in one browser session: no screen-reader, mobile or
  cross-browser acceptance.

## WS7 status

WS7's exit check — three personas reachable from the page, a brief saved, reopened and exported, and a
scheduled run recorded — is now met, with the limits above recorded rather than smoothed over. WS8
(language and voice) and WS9 (operations) remain open, as do the PS-feature gaps the coverage matrix
still lists as missing.
