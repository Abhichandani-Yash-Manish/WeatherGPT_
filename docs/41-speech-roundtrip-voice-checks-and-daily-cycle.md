# Spoken round trips, voice component checks and the opt-in daily cycle — 15 September 2026

Three remaining register items are addressed in their locally verifiable scope: **G06** (what a spoken round trip actually preserves, and component checks for the voice surface), **G13** (a bounded foreground daily cycle without installing a scheduler), and the measurement records that go with them.

## What a spoken round trip preserves

scripts/measure_speech_roundtrip.py speaks a probe sentence, transcribes it back and records presence only: place, a number as digits or words, the unit and the negation marker. It never compares the transcript with the source text as though equality were the standard, and it records recognition probability as the recogniser's own number.

Live report, 15 September 2026 (research/implementation/speech-roundtrip-20260915/report.json):

| Language | Place | Numerals | Unit | Negation | Recogniser language |
|---|---|---|---|---|---|
| Hindi | present | absent as digits, present as the word form (the known behavior) | present | present | hi-IN |
| Gujarati | present | absent as digits (word form) | **not matched by the probe markers** | present | gu-IN |

Recognition probability was not returned on this run and is recorded as null rather than inferred. The Gujarati unit not matching the markers is recorded as an observation, not as a failure conclusion: the transcript may spell the unit differently, and one probe cannot settle it.

**Voice component checks** (tests/test_voice_ui.js, now part of scripts/verify_all.py): the language selector offers only measured write languages, sorted by English name, and tracks measured speech separately; a transcript is shown with its detected language and with recognition confidence labelled as recognition only; using the transcript fills the composer and closes the panel; speech is refused with no request sent where the project has not measured it.

## The opt-in daily cycle

scripts/run_daily_cycle.py runs one bounded, foreground cycle: registered document families, an optional district sweep with an explicit limit, the watch check, the retention report (report-only unless --apply-prune) and a health read. It installs nothing: no daemon, scheduler or background process exists, and the recorded decision stays "manual trigger now, scheduler later".

Live run: `--families national_bulletin` completed four steps in about 41 seconds — documents 9.1 s, watch check 29.4 s, retention report 2.0 s, health 0.05 s — all ok. The full evidence is research/implementation/daily-cycle-20260915/cycle.json.

## What this does not establish

- **No speech accuracy or intelligibility claim.** One probe per language, no native review, no noisy-input testing, no browser audio acceptance.
- **No continuous collection.** The cycle is manual; nothing runs on a schedule and no source cadence is validated.
- **No district sweep rehearsal here.** The district sweep stays opt-in and was not run in this bounded cycle because the last full national sweep is already recorded.
