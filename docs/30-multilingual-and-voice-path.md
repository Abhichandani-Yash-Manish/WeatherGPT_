# Multilingual output and voice access — path plan, 15 September 2026

Problem statement features **6 (multilingual support for Indian languages)** and **8 (voice-enabled interaction for rural accessibility)** are the two named PS features with no implementation at all. This is the plan for both, using the Sarvam AI key the user holds. It is a plan, not a batch: nothing here is built yet and nothing here is measured yet.

This path runs parallel to the source and document work in [docs/29](29-source-activation-and-document-intake.md). They share no code and can proceed independently.

## Where the project actually stands on these two

**Feature 6 is understood but not delivered.** The planner already records a requested output language — `en`, `hi`, `gu`, `hi-Latn` — and retains it across turns. `dialogue.language_gap` then measures whether the answer was actually written in the promised script, and `conversation.py` downgrades the response to `partial` with an explicit note when it was not. That machinery is honest, and it is the reason this gap is visible rather than hidden: the system says it could not answer in Gujarati instead of pretending it did.

Two limits are worth naming precisely:

- `SCRIPTS` in `dialogue.py` contains exactly two entries, `hi` and `gu`. For every other Indian language the gap check cannot measure anything, so it returns `False` and the answer passes as adherent by default. Extending output coverage without extending this check would convert a visible gap into an invisible one.
- Understanding the question's language has never established output support, and that separation must survive this work.

**Feature 8 does not exist.** The surface is desktop web, text only. There is no audio input, no audio output, and no microphone permission anywhere in `web/`.

## What Sarvam provides

Read from the Sarvam documentation on 15 September 2026. Model versions and limits move; each of these is a starting point to confirm at integration time, not a fixed contract.

| Capability | Endpoint | Model | Languages |
|---|---|---|---|
| Speech to text | `POST https://api.sarvam.ai/speech-to-text` | `saaras:v3` (default), `saaras:v4` | 23 (22 Indian + English) |
| Text to speech | `POST https://api.sarvam.ai/text-to-speech` | `bulbul:v3` (default), `bulbul:v2` | 11 (10 Indian + English) |
| Text translation | to confirm | Mayura (11), Sarvam-Translate (23) | 11 / 23 |
| Chat LLM | `/v1`, OpenAI-compatible `/v2/chat/completions` | `sarvam-105b` | 11 |

Authentication is an `api-subscription-key` header on every call.

Speech to text takes multipart audio, accepts a BCP-47 `language_code` or `unknown` for auto-detection, and returns `transcript`, the detected `language_code` and a `language_probability` between 0 and 1. REST responses are bounded at 30 seconds, so long audio needs the batch path rather than this one.

Text to speech takes `text` plus a BCP-47 `language_code`, caps input at 2,500 characters on `bulbul:v3` (1,500 on v2), and returns base64 audio in a chosen codec.

**The coverage numbers differ per direction, and that difference is the design.** 23 languages can be heard, 11 can be spoken, and translation reaches either 11 or 23 depending on the model. There is no single "multilingual" state to record. Support has to be stored per language *per direction* — understood, readable, writable, speakable — in the same way this project already preserves unknown, missing, stale and reference-only rather than collapsing them.

## The central risk

A translation or speech layer sits directly between verified evidence and the user. Everything this project has built to keep a number attached to its entity, time, unit and source is bypassed if a generative model is allowed to restate the answer freely.

The specific failure that matters here is not a clumsy phrase. It is a machine translation that drops a negation, so `no warning in this product` becomes a warning; or that rewrites `34.0 °C` into a different numeral system, or localises a district name into something that no longer matches the official bulletin. In a disaster-management product delivered by voice to a rural user, that is a safety defect, not a cosmetic one.

This is the same class of failure as the two already recorded in this repo: the planner renaming a requested water level to `river_discharge`, and the planner claiming a Gujarati answer it had not written. Both were fixed by deterministic checks on the output rather than by instructing the model more firmly. Translation must be gated the same way.

## Proposed design

Three separate concerns that must not be merged.

### Output path — text

The answer is already composed from verified facts. Two options:

**(a) Templates per language over the structured facts.** No model between evidence and user. Numbers, units, places, times and source identifiers are never generated. Highest integrity, and the most work per language added.

**(b) Machine translation of the rendered answer, behind an invariant gate.** Reaches PS 6's breadth quickly, and carries the risk above.

The recommendation is **(b) with a hard gate, and (a) for the safety-critical clauses**. Warning colour, hazard wording, validity windows and "this is not an all-clear" statements should not pass through a translation model at all; they are short, finite, and worth templating.

The gate is a deterministic post-translation check: every number, unit, date, place name and source identifier present in the source answer must survive into the translation, and negations must be preserved. If the check fails, the translation is discarded and the response keeps the existing honest downgrade rather than shipping an unverified rendering. A failed gate is recorded, not swallowed.

`SCRIPTS` must grow alongside every language that becomes writable, so the existing adherence check keeps measuring rather than silently passing.

### Output path — voice

Speak only text that has already passed the gate. The 2,500-character limit means chunking, and a chunk boundary must never separate a number from its unit or a hazard from its negation. Audio is a rendering of the answer, never a second generation of it.

### Input path — voice

Audio goes to speech-to-text, and the transcript enters the existing planner as an ordinary question. The transcript is a *claim about what was said*, not a fact, and it must be shown back to the user and be correctable before it drives an answer — particularly for place names, which the gazetteer already treats as ambiguous, and for numbers.

`language_probability` is the ASR model's own number. It may be displayed as recognition confidence. It is never an answer confidence, never a forecast confidence, and never combined with anything else into a score. This project computes no confidence scores and that does not change here.

## What this path must not claim

- A translated official warning is a convenience rendering, not an official product. IMD's published wording stays authoritative and must be retained and reachable beside any translation.
- Recognition confidence is not answer confidence.
- Voice access is an accessibility feature, not operational clearance, and not a dissemination channel for official alerts.
- Supporting a language for input does not mean supporting it for output, and neither means the underlying evidence exists in that language.
- No redistribution of source material through any of these surfaces.

## Sarvam is not a source

This matters more than it sounds. The project has one governed path for outside data: `transport.Store`, which pins a request contract, stores an immutable hash-addressed body, rebuilds values from those bytes and publishes provenance. Everything in `data/registry/sources.json` is a *source of evidence* and earns a source identifier.

Sarvam is not that. It returns a rendering of an answer the system has already justified from its own evidence, or a transcript of what a user said. Neither is meteorological evidence.

So: Sarvam responses must not enter the evidence store, must not be assigned a source identifier, must not appear in the source registry as a data product, and must never be cited as the basis for a fact. A translated sentence carries the provenance of the answer it was translated from, and nothing more. The client for this path is a separate bounded client, and it must not weaken the credential-free discipline `Store` enforces for real sources.

## Configuration

The project already reads local configuration from `WEATHERGPT_`-prefixed environment variables — `WEATHERGPT_MODEL` and `WEATHERGPT_OLLAMA_URL` in `language.py` and `scripts/start_weather.py`. The Sarvam key follows the same convention as `WEATHERGPT_SARVAM_API_KEY`, read at use, never written to a tracked file, never echoed into a trace, a manifest, an evidence record or a log line. Absence of the key is a normal state: every language feature must degrade to the existing honest downgrade rather than erroring.

## An architectural change that needs a decision

This project is local-first. The workspace binds to loopback, the model is local Ollama `qwen3.6`, and source bodies stay on disk. Every Sarvam call is a hosted API call, which means the user's question — and, on the voice path, an audio recording of their voice — leaves the machine and reaches a third party.

That is a defensible trade for features 6 and 8, which cannot realistically be built locally to this quality. It is not a trade to make silently. It needs to be stated in the interface, and the key belongs in local backend configuration only, never committed and never logged.

## Staging

1. Configuration, a bounded client on the existing transport discipline, and a **measured** per-language capability registry — measured because the documented language list is a claim, and this project records what it observed.
2. Text output: translation behind the invariant gate, templates for safety-critical clauses, `SCRIPTS` extended per language made writable.
3. Voice output over gated text, with chunking that respects numbers and units.
4. Voice input with a confirmable transcript.
5. Evidence: recorded journeys per language, and a measured table of which languages pass the gate, including the ones that do not.

## Open questions

- Which languages first? Hindi and Gujarati are already partly modelled in the gap check and are the obvious start.
- What do the key's credits and rate limits allow? That bounds whether translation runs per answer or is cached per rendered answer.
- Should the Sarvam LLM replace or complement local Ollama? This is the larger question, because it changes the project's offline and privacy posture well beyond features 6 and 8.
