# Engine context, language disclosure and task dependency — 14 September 2026

This is the first repair batch taken from [the critical full-solution review](21-full-solution-critical-review.md). It follows that review's own trajectory: repair engine behaviour before expanding coverage. It closes none of the review's missing systems. Official warnings and observations, nationwide advisory coverage, marine and river chat, voice and mobile remain untouched here. Desktop work continues; hosting and sharing remain on hold.

## What changed

**A continuation can no longer lose a measure the user just named.** Parameter inheritance previously depended entirely on the planner declaring `changed_fields`. A follow-up naming a new measure while the planner omitted that tag inherited the old parameters and left the new request unanswered. `dialogue.reconcile` now also reads the measures named in the current clause — probability, rain amount, temperature, feels-like temperature, wind, gusts, humidity and visibility — and adds any that the planned task is missing, marking parameters as changed so inheritance cannot overwrite them. Longer phrases are consumed first, so “wind gusts” and “feels like temperature” resolve to one measure each. The check only ever adds a named measure; it never removes one the planner declared, and it does not run for an independent new request. This mirrors the existing literal crop/topic correction already trusted over the planner's tag.

**A requested output language that is not rendered can no longer be reported as answered.** Understanding a question's language was already separate from writing the answer in it, but nothing checked the difference. A response promised in Devanagari or Gujarati script is now measured against what was actually written. When the promise is not met, the response becomes partial, carries an explicit note, and records `language_adherence: failed` with the requested language in its trace. The generated-text path treats the same failure like its existing number and unit violations and falls back deterministically. The forecast values themselves are unchanged and remain correct; this batch discloses the gap honestly rather than translating anything. Romanized Hinglish is written in Latin script and is not measured this way.

**An explanation task now reads the evidence of the task it explains.** An explanation task previously discarded all evidence and answered from general knowledge, so it could contradict a sibling task in the same request — including claiming no weather data had been supplied while another task held it. It now takes an explicit reference to the most recent preceding task in the same request that retrieved something, and explains that task's own evidence through the existing deterministic evidence explainer. The reference is recorded as `explains` on the task result. The explanation holds no facts of its own, so ownership stays with the task that retrieved them, and no sibling evidence is shared indiscriminately. With no preceding evidence in the request, the previous general-knowledge behaviour is unchanged. An explanation that produces no text is now reported unavailable instead of counting as a completed task.

**Two packaging and interface defects.** The repository had no `.gitignore`, so 668 runtime paths were tracked: the conversation database, cache databases, request blobs and the model log. They are now ignored and untracked; every file remains on disk and no history was rewritten. Curated evidence, including the saved bulletin page images under `tmp/pdfs`, stays tracked. Separately, the desktop “New conversation” control cleared the question box and then submitted it, so starting a conversation sent an empty question the backend rejected. It now resets the thread and keeps focus without sending anything.

Implementation: `weathergpt_data/dialogue.py`, `conversation.py`, `task_dispatch.py`, `web/app.js` and `.gitignore`.

## Acceptance evidence

Evidence directory: [engine-context-repairs-20260914](../research/implementation/engine-context-repairs-20260914/).

- Baseline **356** automated tests passed before the changes. Final: **362 passed**, including six new regressions covering the named-measure repair, the measure-phrase boundaries, unchanged inheritance when no measure is named, the language gate, sibling-evidence explanation and general explanation without a reference. JavaScript component checks went from six to **eight**; the two new ones cover the conversation control.
- **Seven recorded local-model HTTP turns:** five answered, one partial, one needs selection. These are seven checked outcomes, not seven completed information requests. Durations ranged from 0.86 to 25.89 seconds on one warm machine, which measures nothing about service latency or capacity.
- **A03 is repaired in its reproduced scenario.** “Give me the latest METAR for VOBL and explain what it means” returns the observation in task 1 and an explanation in task 2 carrying `explains: t1`, describing that METAR. Task 2 holds no facts.
- **A02 is disclosed, not supported.** The reproduced Rajkot Gujarati probability request now returns partial with the adherence failure recorded, after previously being marked answered in English.
- **A01 is repaired in mechanism and pinned by test, but the live runs do not isolate it.** Both live continuations answered the newly named measure, and in both the planner declared the parameter change itself; the first pair also planned two prior tasks, so the single-task inheritance path that produced the original failure was not exercised live. The deterministic test covers that path directly. Paraphrases and repeat runs are still required.

## What remains open

- A clarification or place-selection message for a Gujarati request is still written in English. The gate does not downgrade it, because such a response does not claim to have answered. Language adherence for clarifications, caveats and missing-data messages remains unresolved.
- Hindi and Gujarati output stays unsupported for the point-tool, briefing and historical renderers. Only the controlled forecast template produces either language today.
- A04 historical and geographic aliases are untouched; they need a dated crosswalk source, not an inference added to the engine.
- A05 official warning applicability and delivery, and general live observations, are untouched. `execute_warning` still returns an unverified applicability result by design.
- A06 agricultural depth, the held Nagpur, Surat, Madurai and Indore editions, and nationwide corpus acceptance are untouched.
- A07 is only partly addressed: empty and contradictory explanation counting is repaired, but there is still no independent holdout benchmark, and no task-completion rate is claimed.
- A08 is only partly addressed: the single global conversation lock, queueing, cancellation, retention and restore remain as the review recorded them.
- No browser, mobile, voice, language-fluency, operational or agronomic acceptance is claimed by this batch.
