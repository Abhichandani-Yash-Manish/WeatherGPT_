# WeatherGPT: critical full-solution review

**Current status overlay:** [the integrated PS review](72-integrated-status-and-ps-review.md) records the 15 September integration. The findings and evidence below retain their historical meaning.

Review date: 13 September 2026. Reviewed code: `d6556d916e934e8d8d72151086b46552f15dada9`. This is a decision document, not an approved implementation plan or a promotion of existing readiness statuses. Hosting/sharing remains on hold.

## Verdict

WeatherGPT is an integrated, evidence-conscious local prototype with useful forecasting and historical-analysis capabilities. It is not close to acceptance of the full required solution. Several missing pieces are complete systems: applicable official alerts and delivery, general live observations, nationwide advisory coverage, specialist conversational tools, and voice/mobile access. Natural conversation and language quality also still fail within capabilities already described as implemented.

There is no defensible measured completion percentage. No agreed weighted scope baseline, representative user-task benchmark, or effort estimate exists. Calling this 70–90% complete would suggest a finishing phase that the evidence does not support. Calling it 30% or 50% would introduce another arbitrary number. The useful distinction is: a substantial foundation is built; bounded desktop journeys work; full-scope functional acceptance and dependable operation remain unachieved. The remaining work includes architecture, source access, integration, and validation, not just polish.

Here, “100%” should mean meeting an explicit acceptance contract for every required capability, with stated limits. It does not mean perfect forecasts, guaranteed outcomes, every conceivable query, or automatic aviation/field safety clearance. Those are not reasonable completion criteria. Conversely, truthful abstention is necessary but does not complete an information requirement.

## Scope and evidence

The user-supplied SIH26068 statement is authoritative. [The recorded problem statement](00-problem-statement.md) distinguishes its summary from team interpretation; it is not the verbatim original. This review maps to its eight headline features and the agreed nationwide/specialist scope. Voice and mobile are outstanding requirements, while the current execution surface remains desktop. Optional soil, population, groundwater and other research extensions should stay visible without quietly becoming prerequisites for all core weather journeys. Likewise, a particular model vendor, running WRF ourselves, or adopting Kubernetes is not established as mandatory.

I inspected current capabilities, planner/context reconciliation, dispatch, document retrieval, warning and airport tools, historical analysis, language rendering, server/UI paths, registries, and accepted/failed batch records in docs 14 and 17–20. I ran **22 fresh local HTTP turns**: 16 challenge turns, four diagnostic follow-ups, and two straightforward supported controls. All new outputs are under [the review evidence directory](../research/reviews/full-solution-audit-20260913/), with [case-by-case adjudication](../research/reviews/full-solution-audit-20260913/adjudication.md) separate from application status. These are current-clock local-model probes, not a statistically representative benchmark. Their questions now belong to development/regression material and must not later be called unseen holdouts.

The previous batch records 356 automated tests and scoped source-byte/browser checks. That suite was not rerun during this review, and its count is not used as a completion measure. New probe observations establish answer behavior; I did not independently replay every numerical value in this new sample, run a new browser/mobile acceptance suite, or measure forecast skill.

## What has actually been achieved

- **Evidence architecture:** typed numerical tools, source registries, raw hashes, publication checks, explicit validity/missingness, and claim ownership provide a reusable foundation. The reproduced P01/P02 defects have scoped repair evidence. This is meaningful engineering progress, though not a guarantee against every future attribution error.
- **Useful model forecasts:** GFS and a separately identified best-match path expose rain amount, hourly probability, temperature, feels-like temperature, wind/gusts, humidity and visibility within their contracts. Source comparisons preserve the important warning that the two paths may share GFS lineage.
- **Historical computation:** published rainfall/climate retrieval, deterministic differences, series/charts and descriptive trends work for available source regions/years. Bounded daily ERA5 history is connected separately and labelled modeled reanalysis.
- **Conversation infrastructure:** multiple typed tasks, explicit place selection, retained slots, corrections, source continuity and task-local evidence substantially improve on the earlier single-intent bottleneck. The fresh Bhubaneswar bundle preserved all four requested parts, even though only one had usable information.
- **Published bulletin retrieval:** four inspected district editions across three layout families, crop/stage ownership, hybrid retrieval, parent context, quarantines, source-linked qualification flags and verified PDF downloads are real capabilities. They make a stronger source reader, not yet a nationwide personalized adviser.
- **Scoped specialist and lifecycle work:** Indian airport METAR/TAF tools are reachable; CAP reference/update/cancel/expiry diagnostics and guarded acquisition exist. Neither achievement closes the corresponding complete specialist or alert journey.

## Requirement-by-requirement capability assessment

| Required capability | Current usable subset | What prevents acceptance |
|---|---|---|
| Real-time weather retrieval | Bounded refreshable model forecasts; airport observations for supported ICAO queries | General live station observations/nowcasts are not connected to chat. Refreshing a forecast is not observing current conditions. Official access and station/area mapping remain unresolved. |
| Natural-language forecasting | Useful point forecasts, hourly detail, selected languages and multi-turn paths | Explicit parameter changes can be overwritten by old context; explanations can contradict sibling task evidence; common requested clock windows are only partially supported. |
| Numerical weather prediction integration | External GFS and best-match products via existing adapters | Broad model/variable/horizon coverage, run lineage and local representativeness remain limited. No independent scientific forecast-skill or probability-calibration evaluation is demonstrated. Integration does not require running a new NWP model ourselves. |
| Extreme-weather alerts and early warning dissemination | CAP feed/lifecycle diagnostics | Chat currently cannot establish an applicable current official warning. Verified origin, affected-area resolution, completeness and lifecycle-to-location mapping are open. Subscriptions, background delivery, update/cancel notices and delivery-state UX are absent. |
| Location-based forecasts/advisories | Settlement-point forecasts; a few reviewed district bulletin editions | District/area aggregation and authoritative crosswalks are missing; extraction breaks on other editions; recall and conditional applicability are not established. Personal field decisions remain unresolved. |
| Indian-language support | Some Hindi/Hinglish/Gujarati understanding, controlled wording and clarification | A fresh Gujarati probability request and explicit language correction both returned English. English source excerpts are not an accessible translated advisory. No broad fluent-language acceptance exists. |
| Climate trends/history | Published aggregates and historical district rainfall, charts and descriptive slopes; short ERA5 windows | Source date/region gaps, renamed-district mapping and boundary comparability; limited parameters/analysis. Descriptive slopes are not validated attribution or future climate projections. |
| Voice and rural accessibility | Text interface | Speech input/output, transcript correction, spoken place/date/unit preservation, noisy-input testing and rural accessibility journeys are incomplete. |
| Expected mobile platform and scalable ingestion | Local desktop web, bounded request-driven acquisition, storage/retry foundations | Mobile acceptance, resilient low-bandwidth behavior, service operation and sustained refresh/load tests are missing. Hosting is intentionally paused; this is not authorization to resume it. |
| Agreed specialist coverage | Airport evidence; reusable marine/river adapters | Marine/river identity and tools are absent from chat. A discharge adapter does not supply an observed gauge water level or danger threshold. Specialist briefings need appropriate domain evidence and review. |

## Newly reproduced findings that should change the trajectory

### A01 — Context retention can defeat explicit user changes (high; P03/P08, F01/F02)

After a Kochi request for probability, gusts and feels-like temperature, a follow-up changed the afternoon period successfully. The next request, “Compare the rain amount for that same afternoon period with GFS too,” retained all three old parameters. It did not answer the new rain-amount request. An unusually explicit correction finally switched to precipitation, but exact-window coverage still remained partial.

Evidence: `live-probe/forecast_continuity-1.json` through `-3.json`, and `rain_correction.json`. In `dialogue.reconcile`, parameter inheritance depends on the model correctly declaring `changed_fields`. There are bounded lexical corrections for crops/topics, but no general proof that task deltas are faithful. This is a systemic risk, not a reason to add only this one phrase to a prompt.

### A02 — “Answered” can mean the requested language was ignored (high; P12/P13, F10)

The Rajkot query explicitly requested Gujarati. The plan recorded `language=gu`, yet the answer was English and marked answered. The same conversation's explicit request to switch to Gujarati produced English again. Understanding the query language does not establish output-language support.

Evidence: `gujarati-1.json`, `language_correction.json`. Language adherence must be part of answer acceptance, including numbers, caveats, source explanations and missing-data messages.

### A03 — Task isolation lacks reliable evidence-dependent explanation (high; P03/P12, F01/F02)

The VOBL response retrieved METAR facts in task 1, held unavailable TAF evidence in task 2, and then claimed no current weather data had been supplied in task 3's explanation. The requested explanation did not consume the evidence already retrieved for the same user request. Its completion counter still counted the explanation as completed.

The national temperature-trend request produced a descriptive slope, 40 values and useful methodological notes. Its explicit explanation task returned only “General explanation, not retrieved local weather,” yet overall status was answered. The quantitative capability worked; the explanation task did not.

Evidence: `aviation-1.json`, `climate-1.json`. Preserve task ownership, but introduce explicit dependencies between a retrieval task and an explanation of that task. Sibling evidence should be passed by declared references, not indiscriminately shared or withheld.

### A04 — Geographic ambiguity and historical aliases still obstruct ordinary use (medium; P08, R01/R10, F03/F04)

The Hindi Bhopal request reasonably asked for a source-backed choice between two names. A natural-language reply identifying Bhopal city in Bhopal district repeated the same choice. The button-selection path was not tested in this review, so this is a demonstrated text-clarification failure, not proof that selection is impossible.

Mysuru district historical lookup found no series. Asking for the source name “Mysore” retrieved 2010 and correctly disclosed that the stored series ends in 2010, leaving 2020 unavailable. These are separate alias and time-coverage gaps. The Bhubaneswar bundle attempted a city-named historical district lookup instead of resolving the relevant district or requesting it. No automatic city-to-historical-district substitution should be added without a dated crosswalk.

Evidence: `hindi-1.json`, `hindi_selection.json`, `history-1.json`, `historical_alias.json`, `multi_task-1.json`.

### A05 — The central alert journey remains missing (critical dependency; P06/P10/P11, R02/R08)

The Chennai warning probe returned nine relay messages, none passing the current time/status/reference checks, with the latest message dated 9 September. It correctly refused to infer no warnings. More fundamentally, `execute_warning` always produces an unavailable applicability result even if lifecycle checks pass: origin, geography and feed completeness are not established.

“Notify me if an official flood warning is issued for Patna tonight” became a one-time warning lookup. It did not create delivery behavior or explicitly resolve the request to be notified. No fabricated subscription confirmation occurred, but the action requested was not handled.

Evidence: `official_warning-1.json`, `dissemination-1.json`, `warning_tools.py`. Source access/applicability and delivery should have their own workstream and acceptance gate; further agricultural parser improvements will not unblock them. Never treat old bulletin warning text, model rain, or CAP reference resolution alone as current official alert eligibility.

### A06 — Agriculture remains a narrow source reader (high; P07, R09, F07)

Indore's soybean/irrigation request failed bulletin extraction because its printed issue date was not resolved. Its district forecast separately asked for a town, correctly avoiding an unsupported district average. The existing Nagpur, Surat and Madurai holds also remain. Four accepted editions are not acceptance of all subsequent issues for those districts, let alone nationwide coverage.

Parent context was a necessary improvement. It did not establish full-document recall, resolve all condition/time conflicts, or validate field applicability. Keyword permission/restriction flags cannot substitute for a conditional evidence model. We also need concise, translated explanations and targeted follow-up questions; reproducing pages of English quotations is not enough to complete a farmer's journey.

Evidence: `agriculture-1.json`, docs 19–20, `bulletin_context.py`, `document_tools.py`. A source-qualified explanation can still be useful without pretending to grant a personal go/no-go clearance. Acceptance should test that useful middle ground rather than treating either a large quotation dump or a refusal as the finished product.

### A07 — Current progress accounting cannot measure completion (high; P12/P15, R11/R12)

The application counts an explanation status as a completed task even when it is empty or contradictory, and language adherence does not prevent answered status. The existing approximately 150-case benchmark and 90% task-completion/95% recall goals are proposals, not measured achievements. Previously failed and repeated model journeys remain relevant even after targeted reruns pass.

The trackers honestly retain partial/open states, but some older nested current-evidence text still cites 213 or 280 tests while the latest batch records 356. Historical records should remain frozen; one current summary should point clearly to the latest evidence rather than inviting a cherry-picked count. P01/P02 are scoped verifications, not universal closures of every related quality dimension.

### A08 — Operational and release gaps remain substantial (P10/P11/P13/P14, R06/R07)

The local HTTP server has a single global nonblocking conversation lock. Another concurrent question can be rejected; there is no demonstrated bounded model queue, cancel/stage-streaming journey, sustained ingestion service, or complete conversation retention/deletion workflow. Small mostly warm latency samples cannot establish reliable service latency. The new initial 16-turn sample ranged up to 22.17 seconds; it was not a load test.

Git tracked 618 runtime paths at review start, including a conversation database, cache databases and a model log. This is a packaging/retention problem, not evidence of public exposure. The audit itself legitimately changed runtime/cache files through local queries. Preserve frozen evidence; separate live personal state from deliberately curated fixtures before any sharing. No files were removed and no Git history was rewritten.

Static UI inspection also found that “New conversation” clears the input and immediately submits an empty question, which the backend rejects. This browser interaction was not exercised in the current review. The latest recorded browser acceptance covers only two desktop journeys and the PDF download fallback; embedded PDF viewing and broader UI/accessibility coverage remain open.

## Recommended trajectory, with exit gates

### 1. Establish independent acceptance and repair engine behavior first

Keep current adapters, provenance and typed evidence. Build the previously proposed development/holdout scenario set around required user outcomes, fresh geographies, paraphrases, corrections, mixed tasks and language. A case declares the expected tasks before execution. Review requested versus planned versus executed versus actually answered tasks separately. Count appropriate abstention/clarification separately from completed information tasks.

Repair parameter-change reconciliation, explicit task dependencies for explanation, output-language adherence and natural place clarification as classes of failure. Test paraphrases and repeated runs; preserve failures. Evaluate the existing planner against alternatives only on the same benchmark if failures persist. A stronger model or a larger prompt alone does not validate context logic.

**Exit:** all reproduced critical failures resolved across relevant paraphrases; zero wrong-entity/time/unit or invented-warning failures in the declared release set; supported task-completion target and per-domain denominator reported. At least 90% supported-task completion is a proposed initial gate from docs 14, not a present achievement. Fluent review is required for claimed language journeys.

### 2. Resolve official warning and observation feasibility as a critical dependency

Confirm supported product access, use terms, issue/validity semantics, authoritative station/admin mappings and source lineage. Establish one complete warning journey before expanding it: source → applicable area → active/update/cancel/expiry state → intelligible message → an explicitly requested delivery mechanism with duplicate/update handling. First prove it locally with recorded scenarios and clearly labelled tests, then live supported data. Do not fabricate active warnings when none are present.

**Exit:** an independently checked location/event lifecycle can be resolved; late, missing, conflicting, cancelled and stale data produce the right states; no-notification and created-notification states are explicit. Source diagnostics alone do not pass. If approved live access remains unavailable, record the external blocker and avoid claiming this requirement complete. No external outreach or hosting is authorized by this proposed workstream.

### 3. Expand coverage by complete journeys and source families

For agriculture, validate multiple editions per family, including transitions, missing sections, font/layout failures and withheld cases. Build a reviewed question-to-passage/context set and measure missed relevant guidance, not just exactness of retrieved quotations. Represent constraints by crop/stage/activity/time/source; retain unresolved conditions. Pair usable source explanations with weather only where their scopes match.

Connect marine and river chat through verified sea-area/gauge/model-cell identities and appropriate parameters, reusing existing adapters. Complete airport evidence explanations. Add dated geographic aliases/crosswalks for historical and area-specific queries. Keep observed water level, modeled discharge and flood impact distinct.

**Exit:** complete examples from several geographic/source families plus negative controls, repeated across new source editions. Publish supported and unsupported coverage explicitly. District counts and adapter counts cannot replace these checks. Nationwide remains the final scope, even though acceptance must be built in bounded increments.

### 4. Complete accessible product behavior and dependable operation

Add concise answer-first presentation with expandable original evidence; full claimed-language output; usable clarification, retry/cancel and source inspection. Complete voice with editable transcripts and tested place/date/severity/unit preservation, then mobile/rural access journeys. Establish a bounded concurrent request path, scheduled freshness, outage behavior, retention, reproducible setup and measured capacity. This work can proceed locally under the hosting hold.

**Exit:** representative desktop/mobile/voice user journeys, fluent/domain review, clean-machine startup, cold/warm/outage/concurrency measurements and retention/restore checks. Hosting or sharing is a later user decision, not an automatic consequence of passing local tests.

## What to deprioritize and what needs a user decision

Do not make the next milestone simply “support three more PDFs,” “reach 400 tests,” add a model-provider name, or redesign the landing page. Those may be useful tasks inside a measured journey, but they are poor proxies for delivering the required solution. Do not rewrite the whole system: the numerical/provenance foundation is worth retaining.

The recommended immediate focus is engine acceptance and correction, with warning/observation access feasibility investigated alongside that work. After those gates, invest in nationwide/specialist coverage and accessible delivery. The alternative of continuing primarily with bulletin layouts would deepen one feature while leaving major PS requirements untouched.

Calendar estimates require the delivery deadline, available contributors/time, supported official data access and willingness to use hosted inference/speech later. None is needed to establish this review's technical verdict, and none is assumed here. The next decision is the milestone to pursue, not whether the prototype deserves a more optimistic completion label.

## Existing finding continuity

All historical P01–P15, R01–R12 and F01–F11 evidence remains unchanged. Current P01/P02 scoped verification stands; P03–P10, P12/P13/P15 remain partial, P11/P14 open. Current R03/R05/R12 scoped verification stands; R08 remains open and other R findings remain partial. In particular, R05's repaired river-ingestion regression does not mean river chat exists. The fresh findings above add evidence to unresolved work; they do not erase prior accepted or failed journeys.

F01/F02 task fidelity, F03/F04 geographic scope, F05 forecast parameters, F06 travel limitations, F07 agricultural usefulness, F08/F11 historical support/missingness, F09 unconnected research datasets and F10 language remain part of the review. Earlier descriptions may be historical: current hourly probability and descriptive trends should receive credit, while route-wide travel evidence and the optional research datasets should not be silently marked solved.
