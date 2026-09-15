# Paraphrase robustness: 25 of 34 became 38 of 38 — 15 September 2026

PS feature 2 lists paraphrase robustness as missing (finding A01). This round measures it, then repairs
what the measurement found, on the development set rather than on a sealed one: this is exactly the work
a development set exists for.

## The measurement

`scripts/measure_paraphrases.py` holds eleven declared shapes with a canonical question, its declared plan,
and deterministic variants: word order, politeness, an article, a hyphen, the Hinglish marker, 'kya', a
misspelling, an abbreviated unit, a script, a station code, a coast, a compound question and a correction.
A variant holds when the planner produces the same `(kind, operation)` pairs as the shape's declaration.

| | Variants | Held | Rate |
|---|---|---|---|
| Before this round | 34 | 25 | 0.735 |
| After the repairs | 38 | 38 | 1.000 |

## What the measurement found, and the eight repairs

| Gap | Repaired |
|---|---|
| *\"What does the Gujarat state agromet advisory say about irrigation?\"* was left to a model: the document vocabulary had no agromet words | `DOCUMENT` recognises agromet and agricultural bulletins |
| *\"VOBL ka current weather kya hai?\"* was left to a model: a station code was not a station request | A four-letter station code is an aviation task, with an acronym guard so IMD, GFS, WRF and their siblings are not mistaken for stations |
| *\"Chennai district, Tamil Nadu me 1995 me kitni barish hui thi?\"* planned a forecast for a past year | Hinglish past markers join the history vocabulary, still guarded by an explicit year |
| *\"Kochi me kal tide kya hai?\"* was left to a model although no tide product is connected | Tide is out of scope and answers with the gap, like the other unconnected domains |
| *\"Ahmedabad me kal barish ke liye models compare kijiye.\"* planned a plain lookup | The crosscheck shape is order- and language-independent |
| A Devanagari question was refused by the rules floor entirely | The planner reads the script and returns the question's language (Devanagari → `hi`, Gujarati → `gu`); understanding a language still does not authorise claiming an answer in it |
| A Devanagari state name emptied the candidate list, because the catalogue's admin1 field is Latin | The state is disclosed as unused when it is written in another script; a *wrong Latin* state is still refused |
| The plan validator did not accept the `sea_area` place kind, so every coastal question fell to a model | `sea_area` is a valid kind in the schema and the validator |

Nine checks in `tests/test_paraphrase_repairs.py` and three in the planner suite pin these.

## Measured live

Six of the repaired wordings were run against a live local server; all six were planned by
`deterministic_rules/rule-planner-v1`, with the packets and the answers in
`research/implementation/paraphrase-robustness-20260915/`.

- Devanagari rain question → answered, rendered in Hindi through the invariant gate with the values intact.
- Gujarati rain question → answered, 24 facts.
- `VOBL ka current weather kya hai?` → answered as an airport report, 2 observed facts.
- The Hinglish agromet bulletin question → answered from the published bulletin.
- The tide question → **unavailable**, with the not-connected gap answer rather than an invented number.
- The Hinglish crosscheck → answered with both sources' series, 26 facts.

## What this does and does not establish

- It establishes that the eleven shapes hold across 38 deterministic variants *of this development set*.
  It is **not** a generalisation measurement: the set was written and tuned by the same hand, which is why
  the sealed holdouts in docs/54 and docs/56 exist and why their numbers are 0.615 and 0.545.
- A plan is not an answer: this measures what the planner recognises, not whether the answer is right.
- Indic-script questions now plan and render through the gate, but **no native speaker has reviewed any** of
  it, and document coverage in Indian languages is still the letterhead count in docs/52.
- Variants are generated deterministically, not sampled from users, and the Hinglish variants test one
  marker pattern rather than Hinglish in general.
