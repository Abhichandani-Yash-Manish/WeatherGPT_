# Integrated project status and critical SIH26068 review

15 September 2026. Current assessment after integrating GitHub `63fed4f` and the local workspace,
corpus-recall and evaluation repairs, followed by concurrent alert-delivery branch `70a55d1` and stakeholder-repair branch `9c8f539` (see [docs/73](73-dissemination-integration-review.md)). This document is the current status overlay; earlier review
findings and failed runs remain historical evidence. The P01–P15, R01–R12, F01–F11 and A01–A08 findings
remain binding. No broad finding is closed by this batch.
Later the same day, pull request #4 was reviewed and merged, the OpenRouter free-model ranking was re-measured and the routing order put first with the local model as the fallback, and the five capability paths that had no frontend control were surfaced; see [docs/76](76-openrouter-routing-and-frontend-delivery.md). The verdict above still holds: no broad finding is closed by that batch either, and no browser rendering was verified in it.

## Verdict

**WeatherGPT is a substantial, usable desktop prototype. Full problem-statement acceptance is not achieved.**
The earlier concern that architecture had not become practical deliverables was justified by poor discovery
and disconnected workflows. It is now possible to find a capability, prepare a place-aware question,
inspect source-backed results, continue a conversation, and keep a brief from a single workspace.

The remaining shortfall is deeper than interface polish: reliability across unfamiliar requests, useful
advisory interpretation, language and voice quality, current warning lifecycle and delivery, and mobile
and sustained-operation acceptance. Adding air quality is useful, but does not close those gaps.

No overall completion percentage is defensible. The named requirements have unequal breadth and there
is no agreed weighted denominator, representative user sample or independent domain acceptance.

## Scope of this review

The requirement baseline is [docs/00](00-problem-statement.md), the repository's summary of the
user-supplied SIH26068 statement, not a verbatim official copy. Its eight features, expected mobile
platform, ingestion/backend expectations and named use cases are assessed below. Suggested technologies
are not mandatory architecture choices. GFS/WRF are examples: consuming governed GFS output satisfies an
integration subset without running WRF ourselves. Radar and satellite are coverage ambitions; their absence
must not be invented into a separate verbatim PS requirement.

Evidence was checked against the current code, registries, batch records and new local runs. Live
verification here is a small, current-clock sample on this macOS workspace. Source inventory, development
scores, script adherence, synthetic lifecycle tests and screenshots establish different things.

## Integration and repairs

- Fast-forwarded the 11 upstream commits ending at `63fed4f`, including the CAMS air-quality adapter,
  Foundation path, API, conversation task, rules, tests and source registry. No remote history was rewritten.
- Preserved both registry batches and the README changes when resolving two stash-application conflicts.
  Renamed the local workspace report to [docs/71](71-unified-user-workspace.md), keeping the upstream
  [docs/70 air-quality report](70-air-quality.md).
- Completed the unified home and its context, independent-source loading, retry and drawer-ownership
  repairs. Added air quality as the fifteenth guided tool. Its hourly values now use the existing
  evidence-linked charts; the provider current hour stays separate. A current reading cannot make an
  absent requested forecast window count as answered. Interactive charts use a labelled group so their
  keyboard-accessible points are not nested inside an image role.
- Integrated the concurrent whole-edition recall work: up to twelve indexed sections are excerpted, and
  larger editions list every indexed heading/page. Corrected wording that falsely called excerpts full
  sections. Repaired the measurement CLI's missing `argparse` import and undefined output variable, and
  tested custom output and continued recording after a failed question.
- Tightened the benchmark: requested parameters must survive into execution, each declared measure is
  allocated once, combined tasks may satisfy disjoint measures, and exceptions retain every declared task
  in the denominator. Scorer-v2 results are not directly comparable with historical v1 headline scores.
- The stricter run exposed the rules dropping rainfall from a combined national rainfall/temperature
  history request. Both measures are now retained in the historical task and its source evidence.
- A clean detached checkout initially failed 32 source-fixture cases: the tests read ignored runtime blobs
  even though matching immutable fixtures already existed under tracked research evidence. Their lookup
  now reads those files and verifies SHA-256. No additional source document was published.
- Corrected current-status pointers and statements that still described the corpus, voice, stage progress
  or local plan monitoring as absent. The pre-update product registry is retained in the audit evidence.

## Requirements: expectation versus demonstrated state

| Requirement | Current practical delivery | Critical gap and acceptance verdict |
|---|---|---|
| **1. Real-time weather retrieval** | Refreshable forecasts; nearby AWS/METAR observations; district published warning days; a composed right-now reading. Air quality adds source-labelled CAMS model output. | **Partial.** Station coverage and freshness vary; cold reads can be tens of seconds or longer. A model's current hour is not a ground observation. No continuous nationwide freshness, station-quality or arbitrary-place acceptance. |
| **2. Natural-language forecasts** | Rules-first core paths with provider fallback, guided drafts, follow-ups, explicit windows, multiple measures and source receipts. New comparison and combined-history omissions repaired. | **Usable in a bounded scope; partial overall.** The two new omissions show that `answered` can hide a missed request. Development success is not generalisation. Independent parameter/place/time/evidence checks and unfamiliar mixed requests remain necessary. |
| **3. NWP integration such as GFS/WRF** | Governed GFS and best-match products, a comparison showing both outputs, ensemble member statistics, hourly/daily contracts and answering-cell provenance. | **Integration delivered in scope; broader acceptance open.** Best-match may share GFS lineage; ensemble spread is not probability or skill. Run identity and matched-observation verification remain missing. WRF has no connected product; it is an example, not evidence that GFS integration is absent. |
| **4. Extreme-weather alerts and dissemination** | District-day applicability and warning briefs; activity plans/local watcher; separate legacy watches now have a fingerprint outbox, consented Web Push machinery and local acknowledgements. | **Critical partial.** Synthetic real-HTTP inbox lifecycle passes; no demonstrated live changed-edition → real device notification → acknowledgement/update/cancel journey. The two watch stores and scheduling paths remain separate. Origin authentication, CAP applicability, flood/cyclone delivery and offline delivery remain open. A browser inbox and synthetic tests do not establish an early-warning service. |
| **5. Location-based forecasts and advisories** | Place resolution, point/grid distinction, station distance, source-specific district identity, crop/stage intake, indexed bulletin retrieval and saved briefs. | **Partial.** National registry reach is not nationwide advisory acceptance. Conditional contradictions, field applicability, held layouts, source currency and dated boundary crosswalks remain gaps. Reading advice is not a validated personal spray/irrigation decision. |
| **6. Indian-language support** | Registry records 19/23 passing the write gate; 10/23 passing each speech/hearing gate. Day/window/measure vocabulary, guarded rendering, clarification paths and cross-language document retrieval exist. | **Partial, quality unvalidated.** These gates measure reach and invariants, not fluency or semantic correctness. Five languages lack the recorded reading vocabulary; four fail write. Source quotations remain in their printed language. English plan notifications and quoted English advice obstruct an end-to-end rural-language journey. No native-speaker acceptance. |
| **7. Climate trends and historical analysis** | Published national/district history, source-constrained descriptive trends/charts, short daily ERA5-family reanalysis, expanded variables; the combined national rainfall/temperature request is repaired. | **Useful subset; partial overall.** Source periods, parameter and district-boundary gaps constrain analysis. Seven-day reanalysis is not a general climate research workspace. No validated climate attribution, projections or scientific forecast verification. |
| **8. Voice for rural accessibility** | Confirmable transcription, speech controls, guarded spoken output and recorded Hindi/Gujarati audio round trips. | **Implemented path; accessibility acceptance missing.** No representative noisy microphone, code-mixed speech, native-speaker or field-user validation. Speech recognition confidence is not answer confidence. Third-party speech needs connectivity and sends audio off-device. |
| **Expected mobile-based platform** | Responsive web layouts; 390/768/1440-pixel checks and local Chromium use. | **Not accepted.** Desktop is the current surface by user direction. Mobile-device, touch/audio, permission, low-bandwidth and interruption journeys remain incomplete requirements. A narrow viewport screenshot is insufficient. |
| **Meteorological databases, sites, APIs and query engine** | 69 source registry entries; 28 marked both connected and wired to chat. Governed numerical tools, document index, provenance, source policy and query engine are implemented. | **Substantial integration delivered; operational breadth partial.** Fifteen ledger entries remain access-blocked and 41 are not connected. Counts reflect the ledger's dated probes, not 69 usable APIs or a fresh validation of every source. |
| **Scalable real-time ingestion** | Local stores, retries/budgets/leases, retention, queue/cancellation/progress, manual cycles, scheduled briefing loop and local plan watcher. | **Not demonstrated at service scale.** Shared-store contention and long source waits occur. Some products use Foundation directly rather than ingestion-job scheduling. No sustained multi-user/load, uptime, low-bandwidth or fresh-machine acceptance; no CI service yet. Hosting remains paused. |

Language and source counts above are registry snapshots, not new provider-quality measurements. The language
ledger was measured at `2026-09-15T05:17:16Z`; source rows retain their individual probe dates. Connected
and reachable remain separate from approved redistribution and production use.

## Named use cases

- **Farmers:** published advice is findable and citable. Crop, stage, validity and unresolved applicability
  still prevent treating it as a complete decision adviser. This is a major product gap, not a wording issue.
- **Aviation:** METAR/TAF selection and evidence are usable where served. The VABB TAF absence in the second
  holdout remains evidence of product coverage limits; no operational aviation briefing is claimed.
- **Flood/cyclone dissemination:** the weakest central PS journey. A modelled discharge value, coastal
  quotation or CAP reference chain must not substitute for a verified, applicable official warning.
- **Smart-city monitoring:** point views, map, observations and local plans provide a prototype base.
  Continuous coverage, reliable refresh, delivery and operator acceptance are unmeasured.
- **Climate researchers:** published values, provenance and descriptive plots are useful; periods,
  geography, parameter coverage and reproducibility constrain what can be concluded.
- **Agreed marine/hydrological scope:** wave/discharge tools and source bulletin text exist. Named sea-area
  identity, printed validity, observed levels/gauges, thresholds, flood extent and domain review remain open.

## Concurrent stakeholder repairs

Integrated `issue-solved` at `9c8f539`, including the six scoped SA01–SA06 repairs in
[docs/64](64-stakeholder-repairs.md): warning summary, historical measure order, unsupported river quantities,
model readiness, reproducible test dependencies and notification verbs in place extraction. The unified
workspace's current-day warning rendering is retained. The API now also preserves unknown hazard state
when neither hazard codes nor a meaningful summary exist; the previously vacuous absent-summary test
now exercises that real backend case.

The original stakeholder report describes another runtime and an earlier revision. Its missing model,
empty corpus, absent speech key and delivery absence are not current universal project facts. This host's
new preflight finds the configured local model installed; that catalogue check is not inference acceptance.
Its authored probes and independent numerical checks remain curated historical evidence, unchanged.

A new Tezpur browser request for observed water level returns **unavailable**, zero facts and the explicit
no-substitution explanation. That fixes an unsafe mismatch between request and answer; it does not add
the missing observed-water-level capability. Representative hydrological acceptance is still absent.

## Acceptance evidence and its limits

Directory: `research/reviews/integration-ps-audit-20260915/`.

**Latest combined working-tree verification:** 1,123 Python tests pass (one dependency warning), nine JavaScript suites pass, and all 26 steps pass. The extra static step checks the declared development requirements. Detached clean checkout `dd7fde7` also passes all 1,123 tests, nine JavaScript suites and 26 steps (36.11 seconds for Python). Its log is `stakeholder/clean-checkout-verification.txt`. It shares this host and installed dependencies; fresh-machine installation, real-device delivery and sustained load are not accepted. Evidence: `stakeholder/verification-release.txt`, `stakeholder/provider-preflight.json`, `stakeholder/tezpur-browser.json`.

**Dissemination checkpoint:** 1,105 Python tests and nine JavaScript suites pass; all 25 verification steps pass. New real-HTTP lifecycle checks use synthetic warning input. The browser panel passes its inspected accessibility subtree with one inconclusive contrast rule. See [docs/73](73-dissemination-integration-review.md) for failures, repairs, separate watch-system limits and clean-checkout follow-up. These counts establish regression coverage, not PS completion.

**Pre-dissemination checkpoint:** 1,017 Python tests passed (three dependency warnings); eight JavaScript suites
passed; all 24 verification steps passed. The release development run covers 17 cases, 19 turns and
18 declared tasks: 18 completed under scorer v2, zero recorded critical failures. This is a repaired
development set, not an estimate of performance on unfamiliar user requests. The Indore browser answer
renders 48 hourly points in two charts and keeps the two provider-current values separate. Its final
inspected accessibility subtree has zero violations and one inconclusive contrast rule.

- `verification-release.txt` is the integrated automated result. The earlier verification files remain
  checkpoints, not replacements for it. The eight JS suites are DOM/component checks.
- After the fixture repair, a detached clean checkout at `d4eb3c3` passed all **1,017 Python tests**, all
  eight JS suites and all fifteen static/environment checks. The failed initial checkout and final logs
  are retained as `clean-checkout-*`. This used the same host and installed dependencies; it does not
  establish a fresh-machine installation, Windows compatibility or CI service.
- `development-v2/` preserves the first stricter run that exposed the historical omission.
  `development-final/` preserves an intermediate scorer limitation: a combined task could not yet satisfy
  two disjoint declarations. `development-release/` is the corrected scorer and repaired engine run.
  None is a sealed holdout, a user study, a semantic safety review or a forecast-accuracy score.
- `corpus-recall.json` records the real national-bulletin CLI run: eleven indexed sections served, with a
  bounded-reading disclaimer. The source text stays in the local review archive.
- `browser-acceptance.json` records the guided Indore air-quality journey, source/window checks and charts.
  The first post-restart attempt hit the stale page token and required reload; a 25-second wait did not
  count as success. A refreshed page subsequently completed. This remains a practical restart limitation.
- Browser accessibility findings are retained before and after the chart-role repair. An incomplete
  contrast rule remains inconclusive, rather than being counted as passed.
- Historical sealed probes remain relevant warnings: the first set completed 8/13 declared tasks and the
  second 6/11 (docs/54 and docs/56). They used earlier code and scorer versions, were small and were read
  during development. They are neither current performance estimates nor comparable controlled trials.

The scorer is still not an independent truth oracle. It checks execution parameters and statuses, not
whether every value, citation, geographical match, caveat and requested language is correct. A model
comparison still needs both products inspected; a returned passage still needs relevance and applicability
review. Regex absence of prohibited wording is weaker than semantic safety validation.

## Priority order and concrete exit gates

1. **Prove the warning journey.** Capture different official editions; verify relevant change, repeat
   suppression, expiry/cancellation, degraded reads, restart and acknowledgement. Exercise the real browser
   notification permission/delivery path. Separately close authoritative origin/applicability and
   flood/cyclone product gaps before claiming those warning workflows.
2. **Make task completion independently measurable.** Expand held-out cases across unfamiliar places,
   multiple measures, corrections and adversarial boundaries. Audit the final evidence against the
   declared request, not only the task status. Hold back cases from implementation; publish failures too.
3. **Bound latency and contention.** Measure cold/warm and concurrent users; bound upstream reads and lock
   waits; reuse validated geometry without pretending stale attributes are current. Test cancellation,
   queue overload and slow/failed sources. A 45-second page timeout alone does not repair the service.
4. **Validate accessible language and voice with users.** Native-speaker review of answers, negation,
   places/dates/units, clarifications and caveats; real noisy audio and rural connectivity; explain the
   original quotation alongside a separately verified translation where supported.
5. **Complete mobile and domain acceptance.** Real phone journeys, durable/local notification behavior,
   source-reviewed agriculture/aviation/marine/hydrology cases and reproducible installation/load checks.

These priorities are acceptance work, not a proposal for another foundational rewrite. Broader data
inventories, more persona labels or additional model providers should not displace them.

## Publication and state

This release publishes source, tests and curated audit evidence to GitHub as explicitly requested. It does
not deploy or host the product. Local credentials, runtime databases, conversations, logs, voice and
supplemental source-text exports remain excluded. Historical committed evidence is preserved. The local
preview at port 8766 runs without a second background watcher beside the existing workspace process;
normal startup enables activity-plan monitoring, which only operates while that local process runs. Legacy-watch Web Push requires its separate on-demand or foreground check/dispatch loop; no supervised scheduler is installed.

## Final integration checkpoint

The release includes concurrent `feature/feature4-alert-dissemination` at `70a55d1` and
`issue-solved` at `9c8f539`, plus the original air-quality/reanalysis/ensemble work through `63fed4f`.
The remaining ensemble branch's substantive code patches were already present; only old documentation
renumbering/count patches remained unmatched and were not used to overwrite the current assessment.
Final application code was verified at `dd7fde7`; the following record commit changes documentation and
curated verification evidence only. No force push, hosting, deployment or actual notification send is part
of this release. Authored stakeholder audit packets already committed on the concurrent branch remain
curated historical evidence; local user conversations, credentials, databases and supplemental captures
remain excluded.
