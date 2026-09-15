# A question in one language, documents in another — 15 September 2026

The published corpus is printed in English. A reader who asks in Hindi, Gujarati, Marathi, Bengali or
Tamil got a semantic guess at best, and often nothing at all: measured on this machine before the batch,
a Hindi question about the national bulletin was planned as a rainfall forecast of a settlement called
"बारे", a Bengali bulletin question was answered by asking which settlement "জাতী" was, and a Gujarati
district question reported that no edition was indexed under the name the reader used — although the
Nashik edition is held.

This batch makes the reading cross-lingual, and keeps every number, unit, date, place and source
identifier out of the generative step on the way.

## What changed

**A translated question is used to find passages, never to state anything.** When the question is written
in an Indic script and no passage shares an exact word with it, `corpus_tools.translated_query` asks the
configured language service for an English rendering, and that rendering is used as the retrieval query.
The passages served are still the source's own text, quoted with page and printed issue date. The turn is
`partial`, the basis is `translated_query_lexical_overlap` (or `translated_query_without_the_topic_word`
when even the translation finds no topic word), the translated wording is recorded on the retrieval
coverage, and the answer says in words which language was translated to English, by which service and
model, and that the reading is partial and the translation is not evidence. With no key configured, the
result is unchanged: the disclosed semantic-only basis from docs/32 still applies.

**A document question is routable in the reader's own script.** The rules planner's product vocabulary was
English-only, so `राष्ट्रीय मौसम बुलेटिन`, `રાષ્ટ્રીય બુલેટિન` or `জাতীয় আবহাওয়া বুলেটিন` matched no
document word and fell through to a forecast plan. `PRODUCT_WORDS` and `DOCUMENT_SIGNALS` now hold the
product words per language — the English, Hindi and Gujarati forms written by hand, and the Bengali,
Assamese, Odia, Tamil, Telugu, Kannada, Punjabi, Marathi and Urdu forms proposed by the language service
and checked to fall inside the script each language is written in. They are stored as `\uXXXX` escapes
after a Gurmukhi lookalike was entered where the Odia locative belongs.

**Words are compared on their folded form.** Bengali writes য় as one code point or as য + ়, and the
service's `আবহাওয়া বুলেটিন` and the reader's `আবহাওয়া বুলেটিনে` are the same two words. Only one form
matched, which is why the Bengali question became a rainfall forecast. `mentions()` compares on the same
folding the rest of the engine uses for places.

**A postposition is not a settlement.** `भारी बारिश के बारे में …` was read as a request about a
settlement called "बारे", because `बारे` is followed by the locative `में` that marks a place. A list of
product words, report words and postpositions in Hindi and Gujarati is now refused as a place name.

**A unit word carries the kind.** `નાસિક જિલ્લાની …` read no place at all, because the possessive `ની` is
not one of the locative markers; `नासिक जिले का …` and `மாவட்ட …` likewise. A name followed by its unit
word (`जिला`, `જિલ્લા`, `மாவட்டம்`, `ಜಿಲ್ಲೆ`, `ضلع`, `राज्य`, `રાજ્ય`, …) is now extracted with the kind
the corpus route needs: district or state.

**The publisher's English name is tried first.** The index stores "Nashik"; the reader wrote "નાસિક". The
corpus route now resolves the names it was given through the gazetteer (disclosing the reading like any
other place reading) and tries the resolved English names before the reader's own spelling, so a
non-Latin question reaches the edition that is held rather than reporting that none is.

**A document question does not die on a name the gazetteer does not hold.** The place-resolution step
asked "I could not find a settlement named X" and ended the turn; for a plan whose every task is a
document, the name is now recorded as part of the question and the corpus asks for the district in the
publisher's own terms instead. A forecast question is unchanged: an unknown place still stops the turn
rather than being replaced.

## Measured after

Six questions in five scripts against the real workspace, recorded in
`research/implementation/crosslingual-retrieval-20260915/journeys.json` and reproducible with
`python3 scripts/measure_crosslingual_retrieval.py`:

| Question | Before | After |
|---|---|---|
| Hindi, national bulletin, heavy rainfall | planned as a rainfall forecast of a settlement "बारे" | 9 passages from the bulletin, translated query recorded |
| Hindi, "what is written in the national weather bulletin" | same | 5 passages, topic word absent from the edition and stated |
| Gujarati, Nashik district agromet, grapes | no edition indexed under "નાસિક" | 3 passages from the Maharashtra / Nashik edition |
| Marathi, Nashik district agromet, grapes | no edition indexed | 3 passages, through a Deva-script translation |
| Bengali, national bulletin, heavy rainfall | asked which settlement "জাতী" was | 5 passages from the bulletin |
| Tamil, Nashik district agromet, grapes | no edition indexed | 3 passages |

Six of six now answer or answer partially (every one `partial` because a generative step mediated the
retrieval), with no exception raised and no place substituted. The declared acceptance benchmark was
re-run after these changes: **18 of 18 declared tasks (1.0)** on the development set, in
`research/reviews/acceptance-benchmark-20260915/development-r8`, with no critical failure, no shape
mismatch and no prohibited claim.

One operational finding came out of that run and is worth recording: while a serving process was up, the
same benchmark stalled after four cases for minutes on the live warning case. Stopping the server made it
complete in under a minute. The local stores are shared, and a benchmark run and a serving process contend
for them; a stalled run is not evidence about the source.

## What this does not establish

- **It is not a translated answer.** Only the *question* is translated, and only to find passages. What is
  quoted is the source's own English text with its page and printed issue date; the answer-language layer
  from docs/30 renders the composed answer under its own gate, and any number, unit, date, place or source
  identifier still passes through protected-value checks rather than a free translation.
- **No translation-quality review.** Nothing here measures whether the translation is good: it measures
  whether a question can reach the documents that mention the same words. No native speaker or fluent
  reader reviewed the vocabulary or the queries.
- **The source language is read from the script**, which is coarser than the language: Assamese is written
  in the Bengali script and is sent as Bengali, and Marathi is sent as Hindi. The translation still found
  the passages in the measured cases; the ambiguity is recorded on the result rather than presented as
  language identification.
- **A translation can lose a negation or a nuance**, which changes which passages are found. The passages
  are shown verbatim and the basis is disclosed, so the failure mode is a less relevant answer rather than
  an invented one — but it is a real failure mode.
- **The service is a paid third-party dependency.** With no key, or when it refuses, the previous
  disclosed semantic-only basis applies unchanged; the suite's own fixture forbids a test from calling it.
- **Latency is not good.** The measured questions took 21–52 seconds each: a translation call, a fused
  retrieval, and a second retrieval when the translation finds nothing in the fused top ten.
- One process, one machine, one instant against live sources. Nothing here is load, browser or device
  acceptance.
