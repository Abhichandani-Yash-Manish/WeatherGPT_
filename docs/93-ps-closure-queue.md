# 93 — Final PS solution progress review, and the closure queue

17 September 2026. This is the current overlay after R6, and it sits on four standing documents:

- [docs/72](72-integrated-status-and-ps-review.md) — the integrated requirement-by-requirement verdict;
- [docs/84](84-ps-progress-and-pictures.md) — the PS progress reading and the picture set;
- [docs/89](89-final-integration-audit-and-closure-plan.md) — the integration audit and the **definition of done**
  for each feature, which this document does not restate in full;
- [docs/90](90-frontend-r2-flagship-transcript.md), [docs/91](91-frontend-r3-r5-all-surfaces.md),
  [docs/92](92-r6-decommission-readiness.md) — the frontend batches and the decommission record.

It is a review and a queue, not an acceptance: every state below names the evidence that exists, the criterion
that would close the row, and the artefact the closure has to produce.

## 1. The measured state on 17 September 2026

| What | Measured now | Where it is readable |
| --- | --- | --- |
| The served surface | the built React page only; the legacy asset map was replaced by a 404 at the same depth, so a stale bookmark fails in words instead of fetching a deleted script | docs/92 §4c; `scripts/audit_react_frontend.py` (13 checks), `scripts/audit_react_build.py` (11 checks) |
| The gate | `verify_all.py` 20 steps, 0 failed, including the drift guard and the port-ledger audit | `scripts/verify_all.py` |
| Python suite | 1351 tests collected and passing, which is the count the README records (1309 before the QA repair batch of 17 September, docs/96) | `python3 -m pytest tests/ -q` |
| React suite | 62 suites, 349 component checks, `tsc --noEmit` clean (55 and 296 before docs/96; docs/97 added the dashboard suite; the aurora-glass overhaul of docs/98 added the kit suite; the reported-defect repairs of docs/99 added the matrix geometry checks) | `frontend/`, run under Vitest |
| Component-check ledger | 110 of 110 vanilla checks named against a React spec; 203 test names verified in 33 spec files on every gate run | `research/reviews/frontend-react-r2-20260917/check-port.json`; `scripts/audit_port_ledger.py` |
| Source ledger | 70 registered addresses: 20 active through a governed connector, 3 active via another registered source, 15 blocked by a credential or licence gate, 10 reachable but not connected, 5 awaiting a product address, 10 catalogues or documentation rather than data products, 4 without an address, 3 not sources; one probe failure (S11) kept | `data/registry/source-review.json` (compiled 16 September 2026); [docs/29](29-source-activation-and-document-intake.md) for what each flag means |
| Corpus, as the product read it | the Published documents page read 589 documents, 7,372 passages and 570 regions in a 17 September read (588 in the earlier capture of the same day); one document sits in a family this build does not register and is listed and labelled rather than dropped (docs/96 §2, C-2) | `docs/images/06-documents.png`; docs/96 |
| Pictures | eight React captures at 1440×900, taken on loopback against a throwaway store | [README](../README.md#what-it-looks-like); the pre-R6 set stays in docs/84 |
| Warning and plan machinery | canonical warning state, a named change detector, a claim/lease outbox with a retry taxonomy, consented Web Push, acknowledgements and a supervision heartbeat | docs/85; `GET /api/watch-health` |

**Evidence directories.** R3 and R4 were recorded with R5 in `research/reviews/frontend-react-r5-20260917/`
(the surfaces batch spans R3–R5; [docs/91](91-frontend-r3-r5-all-surfaces.md)), so no separate `frontend-react-r3-*`
or `frontend-react-r4-*` directory exists. R0, R1, R2 and R6 each have their own, and the run behind this
review is recorded in `research/reviews/ps-closure-review-20260917/`.

**None of the numbers above is acceptance.** A suite count measures regression coverage; a reachable address is
not a selected or validated product; a capture is one render of one page on one machine on one day. The rows below
are the only place where a feature state is decided, and every one of them is still short of the criterion its
row states.

## 2. The eight features, one by one

Definitions of done are in [docs/89 §5](89-final-integration-audit-and-closure-plan.md#5-the-ps-features-with-a-definition-of-done).
The state column here is the post-R6 reading; the delta column names the single next thing that moves it.

| # | Feature | State | The delta that still stands | The next verifiable step |
| --- | --- | --- | --- | --- |
| 1 | Real-time weather information | **partial** | a per-product coverage statement, and a measured cold-read bound rather than the incidental 12–31 s recorded in docs/53 | write the coverage statement per product and measure a cold read end to end |
| 2 | Natural-language querying | **delivered in scope for tested shapes; partial overall** | an unfamiliar request that mixes two products is not independently adjudicated; task coverage is recorded but not asserted for every answered turn | record an adjudicated mixed request, then assert coverage per turn |
| 3 | NWP integration (GFS/WRF named) | **delivered in scope** | WRF is unconnected and recorded as an example, not a gap in GFS | no closure step owed |
| 4 | Alerts and early-warning dissemination | **partial — the weakest journey** | no live changed edition has produced a notification on a real device with the acknowledgement returning to the ledger; origin authentication stays unverified, and the product keeps refusing dissemination | one recorded device journey: change → notification → acknowledgement → update/cancel |
| 5 | Location-based forecasts and advisories | **partial** | a conditional statement in a general or warning section is not yet reconciled with the crop passage or disclosed together | reconcile one real document pair, or disclose both, with the wording and a test |
| 6 | Indian-language support | **partial, measured** | no native speaker has accepted a sample in any script, and the interface itself is not localised (labels, dates, numerals) | reviewer notes per script; localised shell labels in the React build |
| 7 | Climate trends and historical analysis | **partial** | the district boundaries used are not dated by a crosswalk, and the uncertainty of the geography is unstated | land the dated crosswalk, then re-run one trend with it attached |
| 8 | Voice for rural accessibility | **path implemented, not accepted** | every criterion needs real audio and real users: noisy or code-mixed input, measured spoken output, a keyboard-free journey | record a real-audio round trip, keeping the Sarvam key in local configuration |

Front-facing work that the earlier queue listed and that has since closed: the landing page and the owner gate
(docs/90), every one of the eighteen module surfaces beside Ask (docs/91), the strict-CSP browser acceptance run
(docs/91), the vanilla decommission with the component-check ledger closed (docs/92), and the picture set
regenerated from the React build.

## 3. Cross-cutting rows

- **Security and delivery contract**: the loopback-only server, the per-process `X-WeatherGPT-Token` and the
  strict CSP (`default-src 'self'`, `script-src 'self'`, `style-src 'self'`, `frame-ancestors 'none'`) are
  re-checked against the built page, not the sources. Preserved, not new evidence.
- **Integration breadth**: *delivered in scope, partial overall*. Registration is not selection: 20 addresses are
  active through a governed connector, and the closure criterion stays "each connected source has answered a real
  request in a recorded journey".
- **Retrieval breadth (A06)**: the corpus is indexed and browsable, but the chat path is still the narrow chunk
  reader; whole-document recall and cross-edition contradiction handling remain the priority engine gaps
  ([docs/31](31-full-solution-gap-register.md), [docs/89 §4](89-final-integration-audit-and-closure-plan.md#4-gaps-this-audit-found-and-what-closes-each)).
- **Engine gaps carried with the frontend batches**: `series_from_packet` drops per-record member counts;
  `product_api.ensemble` does not propagate a stale or partial adapter status; the marine sea-cell selection
  has no distance guard. Each is a repair with a test, not a research question.
- **Mobile**: *not accepted*. Desktop web is the declared surface by user direction, and mobile remains an
  incomplete PS requirement rather than a cancelled one.
- **Scalable ingestion and operations**: *not demonstrated*. Hosting is held, the watcher is a foreground loop,
  and there is no sustained run recording queue depth, stalls and recovery on a fresh machine.

## 4. The closure queue

Ordered by the value the problem statement rewards and by dependency. Every row ends in a commit with its evidence
under `research/reviews/`, and no row closes on a count, a screenshot or this plan.

| # | Closure step | The artefact that closes it | Blocker or dependency |
| --- | --- | --- | --- |
| Q1 | The corpus chat path (A06): whole-document recall and contradiction handling | a recorded question answered from a whole document, and a passage pair reconciled or disclosed, with the tests | none; highest value, and feature 5 depends on it |
| Q2 | Feature 4 live journey | the notification payload, the device acknowledgement, the ledger rows, and an update and a cancellation | a real browser subscription on a real device |
| Q3 | Feature 5 in a real document | the general/warning passage, the crop passage, the disclosure wording and its test | Q1 |
| Q4 | Feature 1 coverage and the cold-read bound | a per-product coverage statement and a recorded cold read with its bound | none |
| Q5 | Feature 2 adjudication | one recorded mixed unfamiliar request, answered with both products or refused, plus per-turn coverage assertions | none |
| Q6 | Feature 6 review and localisation | reviewer notes per script; localised labels, dates and numerals in the shell | native speakers (external) |
| Q7 | Feature 8 real audio | the recording, transcript, spoken output and the journey | real users and a noisy environment |
| Q8 | Feature 7 dated geography | the dated crosswalk artefact and a trend re-run with it attached | the crosswalk source (R01, docs/31) |
| Q9 | Engine-gap batch | the three repairs above, each with a test that fails before it | none |
| Q10 | Mobile, service scale and operations | a touch journey on a device with the network interrupted and restored; a sustained run with queue depth and recovery | user direction on mobile; hosting is held by user direction |

## 5. What this review does not claim

It does not claim operational acceptance, validated forecast skill, nationwide corpus acceptance, live warning
dissemination, native-speaker language quality, real-audio or field voice acceptance, mobile acceptance or
service-scale operation. It does not claim that a green gate proves correctness of an answer, only that the checks
it runs pass. It does not claim that the eighteen module surfaces are complete products; each keeps its stated
limits. And it does not retire any requirement: the mobile, language, voice, ingestion and dissemination rows
stay open until their criterion is met with recorded evidence.
