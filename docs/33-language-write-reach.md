# Language write reach: the service's own wider model — 15 September 2026

[The gap register](31-full-solution-gap-register.md) recorded **G04**: thirteen of twenty-three registered languages failed the measured `write` check, and the reason was one request shape rather than an inability. `speech.translate` called `/translate` with no model, so the provider default (`mayura:v1`) answered; for as, brx, doi, kok, ks, mai, mni, ne, sa, sat, sd, ta and ur it returned HTTP 400 with a message that itself names `sarvam-translate:v1`. Speech is refused for those languages because speech requires a verified write, so one missing parameter removed two directions.

This batch changes that parameter path and re-measures. It does not change the gate, the per-direction registry, the key handling or the honesty rules.

## What changed

`speech.translate` now retries exactly once when — and only when — the refusal message names `mayura`. A refusal that does not name it (an authentication failure, for example) is raised unchanged. The model that actually produced the rendering is recorded on the result (`provider_default` or `sarvam-translate:v1` plus the selection reason), and the response remains a rendering, never evidence. Two tests pin the retry, the no-retry path and the recorded model.

## Measured outcome

Re-run of `scripts/measure_language_support.py --only <the 13> --record` on this machine, with the key read from local configuration. Before and after are kept in [research/discovery/evidence/language-remasure-20260915](../research/discovery/evidence/language-remasure-20260915/); the registry is `data/registry/language-support.json`.

| Direction | Before | After |
|---|---:|---:|
| `write` verified | 10 | **20** |
| `speak` verified | 10 | 10 |
| `hear` verified | 10 | 10 |

Ten languages moved from `write: failed` to `write: verified`: Assamese, Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Nepali, Sanskrit and Urdu. They join the ten already verified (English, Bengali, Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Punjabi, Telugu). The interface already offers only measured languages, so these become selectable for written answers immediately.

Three languages still fail the write gate, and each failure is recorded with the gate's own finding:

- **Tamil** — the rendering duplicated a protected date (`2026-09-16`) and was refused. The gate worked; the model is flaky on this probe.
- **Santali** — the rendering lost the `S21` source identifier and was refused.
- **Sindhi** — protected values were lost and the result was not written in the Arabic script this project checks; the gate refused it.

**Speech is beta-gated for the ten new written languages.** Every text-to-speech attempt returned HTTP 400: `Please request beta access to <language>-IN by contacting our support team.` That is an access state, not a quality verdict, and it is recorded per language per direction. The interface offers "Listen" only where `speak` is verified, so those ten are readable but not speakable today.

## What this does and does not establish

- It establishes that twenty languages can pass a deterministic gate on one probe sentence with every number, date, place and identifier preserved, and that three cannot.
- It does **not** establish translation quality, register, grammar or fluency. No native speaker has reviewed any output, and the probe is one sentence at one instant against model versions that can change.
- It does **not** turn any declared capability into a supported one. `languages.supports()` still reports only measured states, and a failed language is refused rather than offered with a warning.
- It does **not** change the privacy trade. Each measurement and each runtime rendering is a hosted call: the text leaves the machine. The key stays in local configuration and is never written to a trace, manifest or log.
- It does **not** add Sarvam to the source registry or the evidence store. A translation is a rendering of an answer this project already justified; it earns no source identifier and is never cited as the basis for a fact.

## Evidence

- `research/discovery/evidence/language-remasure-20260915/language-support-before.json` — the registry before the run.
- `research/discovery/evidence/language-remasure-20260915/summary.json` — the measured before/after, the changed rows, the still-failed reasons and the beta-access refusals.
- `data/registry/language-support.json` — the current per-language, per-direction registry.
- **591 automated tests pass**, including the three new translation-model checks. No test reaches the hosted service; the retry is exercised against a stub.
