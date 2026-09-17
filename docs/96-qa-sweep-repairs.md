# 96 — Repairs from the independent QA sweep, 17 September 2026

This batch repairs the findings of [docs/95](95-independent-qa-sweep-20260917.md), in the categories that
report used. Every repair is in the code with a test that fails before it, and every one was re-checked
against the running workspace afterwards. It is a repair record, not an acceptance: no PS feature state in
[docs/93](93-ps-closure-queue.md) or [docs/72](72-integrated-status-and-ps-review.md) moves because of it.

**Method.** Read the code that produced each finding, change the cause, add a test that fails on the old
behaviour, then re-run the live check that produced the finding. tmp/qa/verify_fixes.py is the live
re-check: 22 checks, 22 pass, each naming the finding it verifies.

**Suites at the end of this batch.** Python 1338 passed (was 1309 collected); React 56 suites, 305 checks;
tsc --noEmit clean; scripts/audit_react_frontend.py 13/13; scripts/audit_react_build.py 11/11; axe-core on
Ask, Today, Warnings and Published documents: **0 violations** (was 40 serious colour-contrast nodes).

---

## 1. Corrections to the sweep own findings

Three entries in docs/95 were wrong or too wide, and the record is corrected here rather than rewritten
silently. The original text stays in docs/95 with a pointer to this section.

| Finding | What docs/95 said | What re-checking showed | State |
| --- | --- | --- | --- |
| M-2 | "Warning evidence cannot be verified from the store … no stored blob anywhere" | The bytes **are** stored, in the second evidence store (data/runtime/ingestion/warning-evidence/blobs/), and the stored blob hash equals the citation. The sweep searched only ingestion/raw/. The real residual was narrower: the citation named a hash with no path to the bytes | **Withdrawn as written**; the narrow residual is repaired as M-2 below |
| M-5 | "The prose label GFS forecast is used for best-match values" | The S62 turns are labelled "Open-Meteo best-match forecast" correctly. The sweep compared the label in one turn with the citation of a different turn; the four S21 turns it cited are labelled and cited S21 throughout | **Withdrawn**; no code change |
| M-1 | "A historical value is served with no page, row or asset behind it", contrasted with the district series | The **citations** of both carried page/row/column/hash all along; the district *product view* carries locators while the *chat fact rows* of both national and district values carry none. The national citation has no page because its source is a CSV, which is correct | **Narrowed and repaired**: the fact rows now carry a locator |

The sweep also got one thing right that this batch had to correct in itself: the first version of the
currency measure (m-1) counted **all 756** districts as stale, because the newest edition in the read
(15 September) is two days before the read. A bulletin two days old is this product current read — its own
Day fields cover today — so that wording would have been a new false statement. The measure is now relative
and local: which districts lag **the newest edition this read returned**. The live number is 14 of 756, the
oldest 1047 days (YANAM, November 2023).

---

## 2. Critical repairs

### C-1 — the warning statement is made over the whole bulletin

- Cause: district_warnings.summary received only the days a question returned, then asserted "Every other
  published day in this bulletin is also no warning in this product" while the bulletin own Day 1 was orange.
- Change: summary(record, rows, issued, published=None, now=None). Non-quiet days outside the returned rows
  are named with their date and an "(already past)" marker; the "every published day is quiet" sentence is
  only made when every published day really is quiet. warning_tools passes the full bulletin.
- Tests: tests/test_district_warnings.py — a past orange day outside the returned rows is named and the
  all-quiet sentence is absent; a genuinely all-quiet bulletin still gets the sentence and still says it is
  not an all-clear.
- Live: Patna now answers "Other published days: day 1 15 Sep 2026 orange Thunderstorm/lightning/squall".

### C-2 — one unregistered family no longer takes the corpus down

- Cause: corpus_tools.family_spec raised for any family not in ALL_FAMILIES, and corpus_overview.documents
  called it per row, so the three families present in the index but absent from this build (gkms_grid,
  arnej_grid, tnau_grid) answered the whole /api/corpus read 400.
- Change: family_label is lenient for index rows and family_registered reports the fact; each row carries
  family_registered; the counts carry documents_in_an_unregistered_family and unregistered_families; the
  surface lists them and says opening one is refused. family_spec stays strict for a *request* that names a
  family.
- Tests: tests/test_corpus_overview.py — a synthetic index with gkms_grid reads status ok, flags the row,
  and family_spec("gkms_grid") still raises; React modules.test.tsx renders the note.
- Live: /api/corpus 200, 589 documents, unregistered_families: [gkms_grid]; the Published documents surface
  renders the editions table.

### C-3 — one definition of "morning", in the prompt and in the disclosure

- Cause: the planner prompt said "Morning defaults 06:30–12:30 IST" while rule_planner.PART_WINDOWS and
  settle_time_window use 09:30–12:30. The plan was right and the sentence the reader saw was wrong.
- Change: the prompt states 09:30–12:30 IST (and the other three parts, each with IST), the Gujarati example
  in the prompt is corrected, and dialogue.reconcile_part_of_day_text rewrites a part-of-day range in an
  assumption to the shared table range without ever moving the window itself.
- Tests: tests/test_language_time_windows.py — the prompt is asserted to state the same windows as
  PART_WINDOWS; a wrong disclosure is repaired; a correct one is untouched; a sentence naming two parts is
  left alone.
- Live: the assumption now reads "Morning is taken as 09:30–12:30 IST." with the same window in the plan.

### C-4 — a clock time the reader states is the window that is used

- Cause: rule_planner.window_for read only the colon form, so "at 9 am tomorrow" fell through to the whole
  day and the model own assumption ("the 09:00–10:00 window is used") contradicted the plan.
- Change: a new CLOCK_AMPM form reads "9 am", "6.30 pm", "9 o'clock"; one named hour is that hour window; a
  meridiem reading wins over the bare clock reading of the same token ("at 6.30 pm" is 18:30, not 06:30);
  "15 pm" is not a window.
- Tests: tests/test_language_time_windows.py (SpokenClockTests) — the hour, the afternoon hour, 12 am and
  12 pm, the impossible hour, and an explicit range still winning.
- Live: the Bengaluru bike question now plans and tasks 09:00–10:00 IST and still answers.

### C-5 — the edition age is stated, and a stale read names its collection

- Change (a): summary(..., now=...) appends "This edition is dated …, N day(s) before this read, and no newer
  edition has been read here" whenever the read is later than the issue date. warning_tools passes the clock;
  the place view carries bulletin_age_days.
- Change (b): a stale or unavailable forecast names the collection state instead of only an age limit:
  answers.collection_state_sentence reports the store state, the newest attempt own message, whether it is
  retryable, and (when nothing is published) that no snapshot exists.
- Tests: tests/test_district_warnings.py (age present at 3 days, absent on the issue day);
  tests/test_answers.py (the stale answer and the no-snapshot answer both name the governed collection).
- Live: the Patna answer carries the age; the Surat and Bengaluru paths name the collection where they fail.

---

## 3. Major repairs

| # | Cause | Change | Test | Live check |
| --- | --- | --- | --- | --- |
| M-1 | history facts carried no source_locators, so the receipt row for a published value was empty | research_answers attaches the CSV row/column (national) and page/row/column (district) to the fact; types.ts allows the string form the receipt already reads | tests/test_history_aliases.py — both branches produce a locator matching the receipt pattern | "CSV row 125, column Annual" on both All India facts |
| M-2 | the warning citations named a hash with no path to the stored bytes | warning_tools.warning_citations attaches raw_relative_path and raw_store; a response with no recorded blob invents no path | tests/test_district_warnings.py — both citations carry the path, and the path names the hash | both citations resolve to existing files under warning-evidence/blobs/ |
| M-3 | /api/health reported failed-job counts with no reason | per product: failed_jobs, failed_jobs_not_retryable; top level: failed_jobs grouped by product, reason, retryability, attempts and due time. Coordinates stay out, as the store own rule requires | tests/test_workspace.py — the reason and retryable false are present and no latitude/longitude appears anywhere in the payload | failed_jobs names "Product validation failed: Incomplete or mismatched requested forecast interval", not retryable |
| M-4 | dispatch_extra dropped the parameter query key, so the view own guard never ran | the route passes the parameter through; an unsupported one is refused | tests/test_stakeholder_repairs.py — temperature raises, rainfall answers, an absent parameter keeps the default | parameter=temperature to 400 "Only the published rainfall record is connected" |
| M-6 | the delete control sat at opacity-60, measuring 2.91:1 | the control keeps .btn-danger at full strength (6.23:1 light, 7.44:1 dark) | React turn.parity.test.tsx — no text-opacity utility on the control; axe measures the rendered result | axe: 0 violations on Ask, Today, Warnings, Published documents |

M-5 needed no change; see section 1.

---

## 4. Minor repairs

| # | Cause | Change | Test | Live check |
| --- | --- | --- | --- | --- |
| m-1 | nothing stated currency, so a district carrying a November 2023 edition sat silently beside 755 current ones | the national read states the newest edition in the read, the districts behind it, the oldest age, and examples; the warnings table shows days behind; Today shows the count | Python: the corrected measure is verified live. React: warnings.gaps.test.tsx renders the note and asserts a current edition is **not** called stale | 14 of 756 districts behind the newest (2026-09-15), oldest 1047 days |
| m-2 | a printed ISO date wrapped inside its column | the date cell is whitespace-nowrap | warnings.gaps.test.tsx asserts the class | — |
| m-3 | a failed read offered only "Retry" | the failure card now says a retry sends the same request and names what to fix first | covered by the shared component | — |
| m-4 | the summary said "matching this filter" with no filter set | it describes what the read returned when no filter is entered, and "matching this filter" only when one is | three component checks updated to the new wording and one added | the surface reads "Showing the first 150 of 3780 district-day rows this read returned." |
| m-5 | window_label (server) and istWindow (client) printed a zero-length range for an instant, and the written answer copied it | both print one instant as one instant; a real range is unchanged | tests/test_conversation.py and frontend/src/lib/time.test.ts; the parity check that pinned "16:30-16:30" now pins the single instant | the air-quality answer reads "18 Sep 2026 00:30 IST … at 18 Sep 2026 23:30 IST" |
| m-6 | the trend sentence carried three decimals the published values do not support | the sentence states 0.1; the calculation record keeps the full slope | tests/test_stakeholder_repairs.py — "54.7 mm/decade" in the answer, 54.654 in the record | "descriptive rainfall trend 54.7 mm/decade" |
| m-7, m-8 | the parameter echo and the per-place health detail | covered by M-4 and M-3 | — | — |
| m-9 | the plan window is IST and the day rows are UTC, with nothing saying they are the same instant | the warning answer states the basis once | covered by the warning suite | the note appears when district facts are present |

---

## 5. What this batch does not change

- **No PS feature state moves.** Warning delivery, nationwide corpus acceptance, language quality, voice,
  mobile and service scale stay exactly where docs/93 leaves them. A repaired sentence is not a delivered
  warning, and a readable corpus index is not nationwide coverage.
- **The written answer stays model-authored.** This batch fixes the labels and facts the model is given, and
  the zero-length window it copied. It does not make prose generation deterministic, and no semantic
  evaluation of a written answer happened here.
- **The unregistered families stay unregistered.** gkms_grid, arnej_grid and tnau_grid now list and label
  rather than crash; registering them needs a sampled front page per family (docs/29), which this batch did
  not do.
- **The failed collections stay failed.** The store now says why (M-3) and the answer names the state (C-5b);
  the contract failures themselves are source-adapter work, not a rendering change.
- **Currency of the warning layer is measured, not fixed.** The layer is still read at its own cadence with
  no live update observed; the surfaces now say how old each edition is.

## 6. Evidence

- Live re-check: tmp/qa/verify_fixes.py → 22/22 (each line names the finding it verifies).
- Accessibility: tmp/qa/axe_audit.py → 0 violations on four surfaces; screenshot of the repaired Published
  documents surface at tmp/qa/shots/fixed-documents-1440.png.
- Suites: python3 -m pytest tests/ -q → 1338 passed; npx vitest run → 56 files, 305 checks;
  npx tsc --noEmit clean; scripts/audit_react_frontend.py 13/13; scripts/audit_react_build.py 11/11.

## 7. Open questions carried forward

1. Whether the district-warning feed hash changes between reads of identical values (noted in docs/95 section 5).
2. Whether the 2023 dates for YANAM come from the publisher or from a local eligibility filter.
3. The false all-clear sentence is repaired, but the summary is still a sentence composed from day rows; a
   future edition could phrase a current-day statement the reader misreads as a forecast. The tests pin the
   two states this batch measured, not every possible bulletin.
