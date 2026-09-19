# 117 — Delivering the answer

20 September 2026. The engine reaches all sixteen of its capabilities from a natural sentence, refuses
what it cannot support, and carries provenance on every value. What it does not reliably do is *answer*.
This is what a reader currently receives, measured, and what to do about it.

## 1. What a reader receives today

Every row is one real question sent to the running engine. "numbers" counts numerals in the answer prose.

| question | facts | words | numbers | the answer opens with |
| --- | ---: | ---: | ---: | --- |
| Will it rain in Ahmedabad tomorrow? | 1 | 23 | 9 | "In Ahmedabad, for 21 Sep … the forecast rainfall is 0.0 mm." |
| What is it like right now in Surat? | 3 | 103 | 86 | "Freshest station report here: SURAT, 13.37 km away, reported 2026-09-19T19:00:00+00:00…" |
| Air quality in Delhi today? | 200 | 199 | 41 | "Delhi, , National Capital Territory of Delhi · provider current hour…" |
| Ensemble spread for Kochi tomorrow? | 288 | 288 | 162 | "Kochi, Ernākulam, State of Kerala · 2026-09-21 00:30 to 23:30 IST" |
| Sea near Kochi tomorrow? | 72 | 101 | 45 | "Kochi … · model cell 9.958336, 76.20836 · …" |
| Agromet advisory for cotton? | 0 | 322 | 30 | "The live district bulletin could not be verified…" |
| Current weather at VOBL? | 2 | 32 | 5 | "VOBL · Bangaluru Intl, airport report at 20 Sep 01:00 IST…" |

Three things fall straight out of that table.

**The ratio is the tell.** The forecast answer carries nine numerals across twenty-three words and reads
as a sentence. The ensemble answer carries a hundred and sixty-two across two hundred and eighty-eight,
which is not prose — it is a spreadsheet read aloud. Nothing decides how much of a retrieval belongs in
the sentence, so everything does.

**Provenance is being used as an opening.** Four of the seven answers begin with a place label, a model
cell, a coordinate or a retrieval timestamp. That material is exactly right *under* a claim and wrong in
front of one: a reader who asked about the sea gets `model cell 9.958336, 76.20836` before they get any
sea. The claim atom already carries source, window and retrieval time — the sentence is repeating the
receipt instead of stating the finding.

**Failure is as long as success.** The agromet answer spends three hundred and twenty-two words not
answering. A refusal should be shorter than an answer, not fourteen times the length of one.

## 2. The rule

> **An answer opens with the answer.**

The first sentence states the thing that was asked, in words, in the reader's own language, with only the
numbers that carry the finding. Everything else — the station distance, the model cell, the retrieval
instant, the other 287 samples — is depth, and this product already has three places to put depth: the
claim's source line, the fold under it, and the evidence receipt.

This is not a request for less rigour. Every number stays reachable and every value keeps its chain of
custody. It is a decision about *order*: finding first, receipt second.

## 3. What to build

**3.1 A lead sentence contract.** One function composes the opening sentence for every task kind, and it
is given the claim rather than the fact list: measure, value, unit, place, window. A kind that cannot
produce one says why in a sentence of the same shape. Nothing else writes the opening.

**3.2 A numeral budget.** A guard that counts numerals against words in the composed answer and, past a
threshold, moves the tail into the fold rather than the sentence. The forecast answer sits at 0.39
numerals per word and reads well; the ensemble at 0.56 does not. The budget is a serving decision, like
the eleven-pixel type floor, and it belongs in the gate for the same reason.

**3.3 Summarise a retrieval, never recite it.** Two hundred air-quality facts are a series, and a series
has a shape: a range, a peak, a direction, a window. The chart engine already draws exactly this. The
sentence should state the shape and the card should carry the series; today the sentence tries to be the
series.

**3.4 Refusals get a length ceiling.** One sentence for what could not be answered, one for why, one for
what would fix it. The rest goes in the fold.

**3.5 The register already exists and is unused by the composer.** `brief | conversational | full` is
carried on every turn and changes how much evidence is unfolded on the card. It should also change the
sentence: brief is the lead alone, full is today's behaviour.

## 4. Order

| Batch | Work |
| --- | --- |
| A | The lead sentence contract, forecast and observation first — the two most-asked kinds |
| B | The numeral budget, with the gate check |
| C | Series summarisation for air quality, ensemble and marine |
| D | The refusal ceiling |
| E | Wire the register into the composer |

A is the one that changes what the product feels like. B stops it regressing.

## 5. Fixed while measuring

`Delhi, , National Capital Territory of Delhi` — the place label joined name, district and state
unconditionally, so a state seat with no district got an empty middle. It is visible in the answer's own
opening line, and the label is used for display, for matching and for provenance, so the gap showed in
all three.

## 6. What this does not claim

Section 1 is seven questions on one machine against a warm store; it is a measurement, not a survey. None
of §3 is built. The numeral thresholds in 3.2 come from those seven answers and want more evidence before
they go in a gate.
