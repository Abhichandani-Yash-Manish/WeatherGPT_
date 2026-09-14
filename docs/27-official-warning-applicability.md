# WeatherGPT: official warning applicability (batch W1)

Recorded 14 September 2026. Assessment and source survey: [docs/26](26-ps-gap-analysis-and-official-source-assessment.md). Frozen evidence: [research/reviews/official-warning-20260914/journey.json](../research/reviews/official-warning-20260914/journey.json).

This batch attacks the single most PS-critical gap. The problem statement's theme is **Disaster Management**, its headline feature 4 is **extreme-weather alerts and early-warning dissemination**, and the project's own trajectory step 2 says to resolve official warning and observation feasibility before broadening anything else. Until this batch, `docs/21` A05 recorded that journey as missing, with `execute_warning` returning an unavailable applicability result unconditionally.

## What was blocking it, and what each blocker turned out to be

| Recorded blocker | What it actually was | Resolution |
|---|---|---|
| "Source diagnostics alone do not pass" (docs/21) | Real. The CAP relay was the only warning source wired in, and its eligibility never authorises anything | The district warning product is now wired in beside it, with its own applicability |
| "WFS day semantics" (R02 next action) | **Unverified assumption.** `adapters.py` reads `Day_1..Day_5` correctly as hazard codes, but the day boundaries were never derived, so every answer had to say `unresolved_day_boundaries` | Derived and verified: day n is the nth IST calendar day from the bulletin date, matching IMD's own day selector |
| "geographic applicability ... not established" | Real. The layer carries district polygons, but nothing resolved a user's place against them | Point-in-polygon resolution against IMD's own geometry, plus a gazetteer ladder and a district-label fallback |
| "origin authentication unverified" | **Still true, and still said.** Transport provenance is not sender authenticity | Left unverified on purpose; every answer and the trace say so |
| "feed completeness unverified" | Partly resolvable. The parser already refuses truncation (`len(features) != totalFeatures`) | Recorded as complete-for-this-layer, with no national cross-check claimed |

## The level semantics, now evidence-backed rather than assumed

The district warning layer carries `Day_1..Day_5` and `Day1_Color..Day5_Color`. Both invite a wrong reading, and the wrong reading would fabricate a warning severity.

IMD's own district warning page settles it. Its script splits the day field on commas and maps each token through a category table, so `Day_1` is a **hazard code list**, not a severity stage. `Day1_Color` is only passed to the map as a WMS `env` style parameter, and the page's four public legend terms (No Warning, Watch, Alert, Warning) are rendered server-side by WMS, not carried in the WFS attributes.

The colour mapping the project already asserted was then validated against the data itself, across all 764 features and all five days:

| colour | observations | hazard codes present |
|---|---|---|
| 1 red | 3 | 100% code 17, Extremely heavy rain |
| 2 orange | 21 | 100% code 16, Very heavy rain |
| 3 yellow | 1701 | code 4 Thunderstorms 892, code 8 Strong surface winds 777, code 2 Heavy rain 24, code 1 eight times |
| 4 green | 2050 | 100% code 1, No warning in this product |
| 0 unset | 45 | no hazard code at all |

The mapping is monotone with the hazard tier, so a colour may be stated. The four public legend **terms** are deliberately not claimed, because this feed does not carry them. Colour code 0 is quarantined rather than read as green.

## What was built

- **`weathergpt_data/district_warnings.py`** (new). Derives IST day windows from the bulletin date, selects the district covering a point from IMD's own geometry, renders the official hazard wording, and builds facts that keep the entity, window, colour, hazard codes, source and citation attached. It refuses to turn a green day, an absent feature or a quarantine into an all-clear.
- **`weathergpt_data/adapters.py`**. `valid_start_utc` and `valid_end_utc` are now derived IST windows instead of `None`; `temporal_applicability` is `day_anchored_on_bulletin_date` with the basis recorded on the record; the envelope limitation now describes what is true rather than what used to be.
- **`weathergpt_data/warning_tools.py`** (rewritten). Resolves each requested place against the gazetteer through a loosening ladder, falls back to an exact official district label, asks when a name is ambiguous rather than guessing, excludes days that have already passed, and reports the CAP relay beside the district product instead of merging them. It attaches real facts, and keeps `dissemination_eligible: false` and `origin_authentication: unverified` in the trace.
- **`weathergpt_data/capabilities.py`** and **`task_dispatch.py`**. The warning task now receives the resolved place and pin, and the capability description states what the tool actually does.
- **The workspace surface**. A dedicated official warning panel: district, bulletin time, and one row per published day with a colour chip, IMD's own hazard wording, and the derived IST window, followed by the derived-window disclosure, the no-all-clear statement and the CAP source assessment. A warning day is never rendered as a headline number, never drawn as a sampled-series ruler, and never repeated as a metric card.
- **`tests/test_district_warnings.py`** (new, 23 checks): day anchoring, one-day IST windows, today/past flags, point-in-polygon including a bounding-box trap, map fidelity against IMD's official names, no-all-clear wording, verbatim source text, severity selection, an unset colour never becoming a level, fact provenance, the stale path, and the resolution ladder.

## Verified behaviour

Live, against the official sources, on this machine:

| Question | Result |
|---|---|
| "Is there any official flood warning for Patna right now?" | **answered**, 5 day facts. Bulletin 14 Sep 2026 11:30 IST: Day 1 green, no warning in this product; Day 2 yellow, Thunderstorm/lightning/squall; Day 3 green; Day 4 yellow; Day 5 green. CAP relay reported separately: 9 messages, 0 passing the checks, newest 9 Sep 12:54 IST. |
| "Is there an official weather warning for Ahmedabad today?" | **needs_selection**, both candidates offered. The name is shared between Gujarat and Rampur, Uttar Pradesh, and the tool refuses to attach an official warning to a guessed district. |
| A point outside every district polygon | reports that no district polygon applies, rather than borrowing a neighbouring district's warning. |
| A bulletin whose published days have all passed | reported as stale with no current facts. |

Also established: the aggregator's **NDMA feed is corrupt** and is quarantined. It presents itself as the National Disaster Management Authority but serves six 2013 and 2015 Rwanda flood warnings authored by Meteo Rwanda. A naive ingest would have published foreign, decade-old flood warnings as Indian official alerts.

## What this batch does not establish

- **Origin authentication** of either source. Transport provenance is not sender authenticity, and no answer claims otherwise.
- **CAP geographic applicability to a place.** CAP is reported as a source assessment; the district product carries the applicability. The two are never merged into one verdict.
- **That a quiet day is an all-clear.** It is a statement about one official product covering land districts.
- **Live update, cancel or supersede behaviour** for the district layer, which has not been observed in a real edition.
- **Terms.** S06 still carries `usage_terms: "Not established for production redistribution"` and every source remains `user_review: pending`. This work is local, with attribution, and the terms question is a blocker for any sharing.
- **Delivery and dissemination.** A CAP lifecycle result still never authorises dissemination, and no subscription, outbox or push behaviour exists yet. The PS feature is *early-warning dissemination*, and that half remains open.
- **Observations.** Feature 1 is untouched by this batch.
- A planner variance worth recording: the same Arabian-Sea warning question returned a validation error once and a general explanation on another run, so sea and no-land-district questions are not yet handled deterministically.
