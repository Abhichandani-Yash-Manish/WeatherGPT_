# 100 — The agriculture repairs: quotes that answer, and the holdings the surface never showed

17 September 2026. Two defects reported from use: farming questions were not answered properly, and the
Farm advisories surface showed no data. Both were real, and the second one is the plainest evidence for
the first: this machine holds **571 district advisory editions and 6,187 indexed passages**, and its own
farm surface was showing a directory listing and an empty brief form.

## 1. What was measured before anything changed

| Probe | Result |
| --- | --- |
| /api/advisories/states, /api/advisories/districts | 36 states, 33 districts for Gujarat — a publisher directory, no advisory text |
| The Farm advisories surface | the directory, a district list and "No district has been named yet, so no brief was composed and no advice is shown" |
| The corpus index | 571 district_agromet regions, 6,187 passages, 5-6 state agromet editions, 890 passages |
| "What does the district agromet advisory for Ahmedabad say for cotton?" | answered, but as a document blob: a 520-character excerpt beginning "3 | P a g e", cut mid-word, no source rows, no crop or stage |
| The same question in Hindi | **unavailable**: "The retrieved Ahmedabad bulletin is dated 2026-09-11 ... It cannot answer a request for current advisory context" |
| "What does the Gujarat state agromet advisory bulletin say about irrigation?" | answered with a milking-animal sentence first, and dose-table fragments ("18.5 SC 3 ml in 10 litres") as section headings |

## 2. The defects and their causes

**A. A source-lookup question was refused as a current-context request.** The live district reader fetches
the publisher's PDF and gates it on the bulletin's forecast window. On 17 September that window
(2026-09-12–2026-09-16) had ended, so the gate refused — while the edition itself was indexed and perfectly
able to answer "what does the advisory say for cotton". Whether a reader got an answer or a refusal depended
on whether the live fetch happened to fail first (the indexed fallback) or succeed (the gate), so the same
question answered differently minute to minute, and a Hindi question was refused while its English twin was
answered.

**B. The quote was taken from the head of a long extraction block.** A district or state edition is indexed
as blocks of 700+ characters that run several districts, crops and sections together. The answer quoted the
first 520 characters, which is why an irrigation question led with "Udder of milking animals" and why a
cotton answer began with page furniture. The cut fell mid-word, and page furniture ("3 | P a g e",
private-use bullet glyphs) was kept.

**C. Dose tables were quoted as advice.** Two retrieved passages were pesticide label fragments, and their
text became the *section heading* of a quoted item, so a dose line arrived looking like the heading of an
advisory.

**D. Document answers carried no source rows.** The corpus path set citations only; the task merge copied
facts, citations and passages into the response but not sources, so every surface that lists sources showed
an empty list for a document answer.

**E. The surface had no holdings.** The advisories surface read the publisher's directory (a catalogue of
states and districts) and the brief route, and never asked what this machine actually holds. A reader
therefore saw no advisory content anywhere on the farm surface.

## 3. The repairs

**Answering a stale edition (A).** In source-lookup mode a bulletin whose forecast window has passed now
serves the indexed edition with its printed issue date and an explicit statement that the forecast half is
not current; the refusal is kept for decision-support and for date windows outside the bulletin. Measured
after the change: the same question in English, Hindi and Gujarati all answer from the indexed edition with
the staleness stated, and the Gujarati answer is written in Gujarati.

**Quoting what the question is about (B).** `corpus_tools.on_topic_excerpt` quotes the sentence the asked
word is in, with the following sentence for context (the preceding sentence only when the match is short),
cuts on sentence boundaries and never mid-word, and says when the quote is an excerpt. `clean_quoted`
removes page furniture and private-use glyphs before quoting; the passage kept in evidence is unchanged.

**Label text is labelled, not advised (C).** `label_text_only` recognises dose/label passages: their text
is quoted under "Printed product-label or dose text in these documents (a label, not advice)", a printed
heading that is label text is replaced by a line saying so, and a mixed answer states that label wording is
quoted as printed and is not the workspace's recommendation. No dose is chosen, adjusted or endorsed.

**Sources travel with a document answer (D).** `execute_corpus` sets one source row per served document
(source, product, family, region, state, printed issue date, retrieval instant, sha256 prefix, locator), and
`task_dispatch.execute_plan` merges those rows into the response, deduplicated.

**The surface shows what this machine holds (E).** A new product view, `/api/advisories/holdings`, reports
the ingested advisory editions per published region — documents, passages, oldest and newest printed date,
the age measured against that edition's own retrieval instant, languages, source ids and body state — with
per-state buckets and counts. The Farm advisories surface now opens on it: counts, a region filter, a state
filter, and a "Read its advice" control on each row that composes the brief for exactly the region the
publisher's edition carries, in source-lookup mode. The publisher directory and the brief form stay below it.

## 4. Measured after the repairs

| Check | Result |
| --- | --- |
| /api/advisories/holdings | **571 regions, 571 documents, 6,187 passages, 29 states named, 37 regions whose edition states no printed date**; 33 regions in Gujarat; the state family adds 5 editions and 890 passages |
| Farm advisories surface | counts, 60 region rows with printed dates and ages, and a working "Read its advice" that renders that district's published passages |
| "…district agromet advisory for Ahmedabad say for cotton?" | quoted from the cotton sentence, no page furniture, printed issue date and staleness stated, **source rows present** |
| The same question in Hindi (hi-Latn) and Gujarati | both answered from the indexed edition; the Gujarati answer is written in Gujarati |
| "…Gujarat state agromet advisory … irrigation?" | leads with the irrigation advice; dose-derived headings replaced by a label statement; a label-wording disclosure is attached |
| Python suite | **1,345 passing** (7 new checks in tests/test_agriculture_repairs.py) |
| React suite | 59 suites, **330 checks** (one new holdings check in the advisories spec) |
| Audits | surface registry 10/10 with the new route declared, frontend 13/13, build 11/11, ledger 2/2 |
| Pictures | research/implementation/agriculture-repairs-20260917/ holds the holdings and brief captures at 1440x900 |

## 5. What this does not claim

- The holdings are an inventory of what this machine ingested. They are **not** nationwide coverage, not
  proof that a bulletin was issued today, and not an acceptance of the advisory product.
- A holding's printed date is the edition's own; where the edition states none, the date and the age stay
  unknown rather than being borrowed from the retrieval instant (37 regions are in that state).
- Answers quote the publisher's text with its issue date and say when the live bulletin could not be
  verified. The forecast half of a stale edition is stated as not current; no irrigation, sowing, spray or
  dose decision is made, and no field-level claim is made from a district bulletin.
- Topic selection is lexical over the indexed text with the source's own crop/stage annotation where the
  index states one. A passage that does not contain the asked word is served from its head and the answer
  says the reading is on the other words of the request, rather than substituting another product or region.
- Retrieval is still lexical for a question written in a script these English editions do not share: the
  semantic-only path is disclosed, and the passages served are the source's own English words.

## 6. Open items

1. Passage boundaries come from the extraction, so a quoted sentence can still carry the tail of an adjacent
   section; a section-aware split of the district blocks is the next quality step.
2. The holdings inventory is read from the corpus index on each surface open; a cached per-family aggregate
   would make it cheaper, and it is not needed yet at 6,187 passages.
3. Crop and growth-stage annotation exists in the live extractor and in some indexed passages; the corpus
   path does not yet annotate a passage whose index states none, and it says so rather than guessing.
4. Nothing here changes a source's status in the registry: S57 and S07 remain registered with their recorded
   approval states and unresolved usage terms.
