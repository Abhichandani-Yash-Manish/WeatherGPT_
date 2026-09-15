# The district corpus becomes reachable, and the topic word decides — 15 September 2026

[docs/32](32-corpus-chat-and-planner-robustness.md) made the published corpus conversational and closed the
reachability half of **A06** for the national families. This batch is what a fresh probe found still standing
between a reader and the 571 district editions that [docs/29](29-source-activation-and-document-intake.md)
recorded, and it repairs four defects plus two answer-quality problems on that route. It closes nothing else:
the cross-lingual lexical limit, contradiction handling, translated explanations and field applicability stay
exactly as [docs/21](21-full-solution-critical-review.md) A06 left them.

## What was measured before

Fourteen corpus questions were run through the real conversation engine on this machine. Two raised an
exception rather than answering, one asked a question the reader had already answered, and three district
crop questions ended in an internal mismatch message:

- `"What does today's district agromet bulletin for Nashik say?"` →
  `Question interpretation did not preserve the requested tasks: Unknown published document family`. The
  district family was indexed under 571 districts and could not be *requested*.
- `"What does the latest flash flood guidance say for Assam?"` → the whole turn failed with
  `TypeError: tzinfo argument must be None or of a tzinfo subclass, not type 'datetime.timedelta'`, because
  `printed_validity` passed a UTC offset where a `tzinfo` belongs.
- `"What changed in the latest state agromet bulletin for Maharashtra?"` → `Which state should I check?`
  although the publisher's own dated directory lists Maharashtra; no edition for it is held here, which is a
  different fact from a missing place.
- `"What does the agromet bulletin for Nashik say about grapes?"` → `The task could not retrieve verified
  evidence: Bulletin retrieval is unavailable: District did not uniquely match the publisher directory`. The
  GeoNames record for Nashik carries `admin2 = Nashik Division`, a revenue division rather than a district,
  and the reader's own name was never tried against the publisher's directory.
- The same question on Pune and Madurai → `Printed district could not be verified with the supported layout
  rules` while those districts' editions were already indexed and current in this workspace.
- Asked about **grapes**, the Nashik edition served eight passages of which one mentioned grapes: every
  passage of a district edition carries the district name, so the district word alone satisfied the
  "share a word with the question" rule.

## What changed

**One registry for "is this a family this workspace knows?"** `FAMILIES` holds the discovery-address
families; the district family is target-driven from the publisher's directory and lived only in
`DISTRICT_SPEC`. `document_ingest.ALL_FAMILIES` is now the single view of every registered publishing
family, and task validation, the capability declaration, the source-ledger audit and the source tests all
read it. The ledger is unchanged: this makes the district family requestable, not newly ingested.

**A printed valid-till time is a timezone.** `printed_validity` builds `timezone(timedelta(...))`, so a
document that states `1730 IST` is read and its expiry compared against the clock instead of crashing the
turn. Expired printed validity is still served as the published record, never as current guidance.

**An absent edition is not a missing place.** A state the publisher's directory covers, with no edition
held, now answers: `No indexed document is published for Maharashtra in this family. The state editions held
here are Chhattisgarh, Gujarat, Karnataka, Rajasthan, Uttar Pradesh.` An absent district answers with the
count of indexed names and the close spellings (`Kendrapara` for `Kendrapada`) as a hint to confirm — a
substitution remains refused.

**Every name the record supplies is tried against the publisher's directory, and a rejection is disclosed.**
`execute_document` tries the place's district field, the GeoNames `admin2` and the reader's own name in
order. When a label such as `Nashik Division` is not a district, the note says so and names what was read
instead: `Read as Nashik, Maharashtra in the publisher directory: the directory spells both names as
asked. The label Nashik Division is not a district in that state.` When nothing matches, the turn asks
which district is meant and lists the close names in that state, instead of returning an internal mismatch.

**When the live bulletin cannot be verified, the indexed edition answers — and says so.** The live reader
fetches the publisher's current PDF and verifies the printed district before serving it; that gate refused
three of four district crop questions in the probe while the same districts' editions sat indexed here. The
turn now reads the indexed edition, with its own printed issue date, currency, physical page and saved
document, and the first sentence of the answer is the refusal and what was read instead. Crop and
growth-stage annotation belongs to the live extractor and is not claimed for that reading.

**The words that name the topic decide which passage is served.** `corpus_tools.topic_tokens` removes the
place names of the request and the words every published document shares, and a passage is served only when
it contains a topic word. The Nashik grape question now serves the one grape passage instead of eight
passages that merely say `Nashik`. When no indexed passage of that product and region contains the topic
word, the answer says so, the status is `partial`, and `match_basis` records
`lexical_overlap_without_the_topic_word` — the passages that share the other words are shown as what they
are, not as an answer.

**A warning question about a named published document stays a document question.** The interpretation
check that requires a `warning` task when the question says "warning" now exempts a plan whose only tasks
are documents that each name a family, because those answers serve warning-classified passages in their own
section labelled reference-only. `"Is there any warning in the latest sea area bulletin?"` answered; it
previously depended on the model's wording that day and could fail at interpretation.

**The account shows it.** The retrieval account gained two rows for corpus answers: the words that name the
topic with whether a returned passage contains them, and, for the two disclosed weaker bases, what the
wording support actually is. `scripts/audit_workspace_frontend.py` FE08 now fails if the corpus stops
recording the topic words or the account stops explaining them.

## Measured after

Fourteen journeys, one process, one instant, recorded in
`research/implementation/corpus-reachability-20260915/journeys.json` and reproducible with
`python3 scripts/measure_corpus_reachability.py`:

| Set | Before | After |
|---|---|---|
| Ten corpus questions (national, marine and state families) | 4 answered, 2 asked for a place the question had already given, 1 partial, 1 internal mismatch, **2 raised an exception** | 8 answered, 1 partial, 1 honest absence, 0 exceptions |
| Four district crop questions (Ahmedabad, Nashik, Pune, Madurai) | 1 answered, 3 ended in an internal mismatch | 4 answered, three of them from the indexed edition with the live refusal stated |

The fourteen-journey run recorded above: 11 answered, 1 partial, 2 unavailable, 0 errors.

The four district crop questions took 0.3–1.3 s each; the live-reader fallback is why three of them answer
at all. 876 Python tests pass (12 new in `tests/test_corpus_reachability.py`), the component checks and
`scripts/verify_all.py` pass, and the new checks fail if the district family leaves the registry, if a
printed valid-till time stops being a timezone, if an absent state or district stops naming what is held, if
the topic words stop deciding, or if the indexed-edition fallback stops disclosing itself.

## Limits this batch does not remove

- The corpus is a record of what publishers issued. Nothing here is a forecast, an observation, an official
  warning, an all-clear or personalized advice, and no answer claims currency beyond the measured printed
  issue date.
- The indexed-edition fallback reads document passages. It has no crop or growth-stage annotation, and it
  does not replace the live reader when the live reader can verify an edition.
- Five state agromet editions are held; the other directory states answer as absent and name the held ones.
- English questions still cannot lexically match Devanagari editions, so an Indic-script answer keeps its
  disclosed semantic-only basis.
- Contradiction handling across conditions and dates, whole-document recall, translated explanations and
  field applicability remain open A06 work.
- Every measurement here is one machine, one network and one instant against live sources, taken while a
  sibling session worked in the same workspace. No publisher was surveyed and no source terms changed.
