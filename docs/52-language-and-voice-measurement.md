# Language and voice, re-measured: a stricter gate, six journeys, and real audio — 15 September 2026

This is WS8 in [docs/49](49-engine-architecture-and-gap-analysis.md). The provider layer, the rules
planner, the corpus, the comparison and the alert and advisory journeys had all landed; what had not
been re-measured since was the language and voice path, and the fresh measurement found two real
defects in it. Both are repaired here, and the ledger and the journeys are recorded again against the
repaired gate.

## What the re-measurement found

| Found | Why it mattered | Repaired |
|---|---|---|
| A Tamil rendering that contained **Telugu characters** passed the script check and was shipped | A rendering that mixes Indian scripts is not a rendering in the requested language, and no value check could see it, because the script check only counted the target script | weathergpt_data/languages.py: `foreign_script_letters`; weathergpt_data/rendering.py fails the sentence and reports the offending characters |
| A rendering whose prose was **not in the target script at all** still reported `ok`, because the script result was computed and never used | The gate's own script verdict was decorative | `ok` now requires the script verdict not to be False |
| A refused script rendering was reported to the reader as an **unreachable translation service** | The reader was told the wrong reason, and a provider problem hid a quality refusal | weathergpt_data/answer_language.py names `rendered_in_another_script` distinctly, with its own reader-facing note |
| An explicit **agromet advisory with a crop** was planned as a district warning lookup | "advisory" is both a warning word and a farm word; the warning branch was checked first, so the wrong product was read | weathergpt_data/rule_planner.py: strong warning words still win, but a crop with advisory wording and no warning word is the agriculture shape |
| "Ahmedabad, Gujarat mein …" was planned as the place **Gujarat**, and the gazetteer offered twenty villages called Gujar in Saharanpur | A comma pair is one place with its state, and the state is the disambiguator | weathergpt_data/rule_planner.py keeps the qualifier as the state |
| A midnight-to-midnight day was explained as "read as 00:30 to 00:30 IST", which names no date | It reads as a zero-length window | weathergpt_data/transport.py names both resolved bounds with their dates |

## The ledger, re-measured under the stricter gate

`python3 scripts/measure_language_support.py --all --record` → `data/registry/language-support.json`.

- **write: 19 of 23** registered languages verified. Four fail, each with its own recorded reason:
  Tamil (a protected value was duplicated by the rendering), Sindhi and Manipuri (the rendering was not
  written in the script), Santali (a protected value did not survive).
- **speak: 10 of 23** (English, Hindi, Bengali, Gujarati, Kannada, Malayalam, Marathi, Odia, Punjabi,
  Telugu). The other languages are refused by the provider with its own beta-access message, recorded
  per language rather than smoothed into "not supported".
- **hear: the same 10**, each verified by transcribing the audio that was just synthesised and checking
  that the transcript came back in the language's own script.
- A language the provider refuses keeps its refusal; a language that passed before can fail now, and
  Tamil did exactly that when the gate got stricter. That is the ledger working, not a regression to hide.

## Six journeys through the gate

Driver: `tmp/evidence-language-voice.py` against a live local server. Each row is one turn.

- **Hindi, Hinglish question** (Ahmedabad rain tomorrow morning) → `partial`: the gate refused a
  rendering in which values did not survive. The source answer is kept and the note says so.
- **Gujarati** → `answered`, `written_by_template`: a reviewed Gujarati template produced the answer,
  so no model touched it.
- **Hindi, Aurangabad** → `answered`, `rendered_with_protected_values`, 24 facts: a verified rendering
  in which every protected value is the original characters.
- **Tamil** → `partial`, `rendered_in_another_script`: the gate caught Telugu characters in the
  rendering and refused it, and the reader is told that rather than told the service was down.
- **Hindi clarification** ("Sultanpur mein kal barish hogi?", 20 candidates) → `needs_selection` with the
  clarification itself rendered through the gate in Hindi, candidates kept as published.
- **Hindi document question** (Ahmedabad district agromet advisory for cotton) → the agriculture route
  read five published passages and the rendering was refused (`values_did_not_survive`) rather than
  shipping a partly rewritten answer.

## Real audio

`python3 scripts/measure_speech_roundtrip.py --languages hi,gu` — synthesise a sentence carrying a
place, a number with a unit and a negation, then transcribe it.

- **Hindi**: 188,204 bytes of audio, detected `hi-IN`, place present, unit present, negation present,
  and the number came back as a **word** (पैंतीस) rather than as digits. Recognition probability was not
  returned by the service this time and is recorded as unknown rather than invented.
- **Gujarati**: 225,836 bytes, detected `gu-IN`, place present, digits present, negation present, and
  the unit marker did **not** come back (the transcript wrote મિલીમીટર where the probe carried મિલિમીટર).
- Both are reach and phenomenon measurements. Neither is an accuracy, intelligibility or fluency test,
  and no transcript is compared with the source text as though equality were the standard.

## Document language coverage, measured rather than assumed

Of **6,739** indexed passages in the bulletin corpus, **107** contain Devanagari characters and **5**
contain another Indic script. Inspection shows these are the bilingual letterheads of coastal bulletins
("India Meteorological Department / भारत मौसम विज्ञान विभाग"), and the extraction is visibly degraded
on some of them ("िव ान", "सी . ड"). No indexed passage carries substantive non-English prose.

So document coverage in the language sense is **not** established: a quoted passage is evidence and is
never rewritten, which means an answer in Hindi can carry Hindi prose around English quotations, and
nothing here claims more. The measurement exists so that gap is a number rather than an impression.

## What this does and does not establish

- It establishes that the gate now catches mixed scripts and out-of-script renderings, names the failure
  it actually had, and that the ledger and six journeys were re-measured under that gate.
- It does **not** establish fluency, accuracy or native acceptability. No native speaker has reviewed any
  rendering, transcript or audio, and the ledger records reach, not quality.
- Recognition probability is the recogniser's own number and is recorded as such; it is never answer or
  forecast confidence, and it was absent for one of the two probes.
- It does not establish mobile, noisy-input, barge-in, screen-reader or cross-browser voice acceptance.
- One probe per language and six turns are not a usability study. The corpus measurement is one instant
  of one corpus, and its limits are recorded with it.
