# State agromet coverage: 1 state to 5, and a marker bug that accepted everything — 15 September 2026

The sealed holdout's first miss was a coverage absence: *\"What does the Maharashtra state agromet advisory say
about pests?\"* answered `unavailable` because the corpus held **one** state agromet edition (Gujarat). This
round builds a target list, sweeps it honestly, and finds a defect in the family marker while doing so.

## What landed

| Landed | Where | Evidence |
|---|---|---|
| A state agromet target registry: 22 candidate centres built from the publisher's own `<centre>/mcdata/agromet.pdf` pattern, each with its state and address | data/registry/state-agromet-targets.json | the sweep records every target's outcome |
| A per-state ingest path with the district outcome vocabulary: `fetched_new`, `unchanged`, `not_issued`, `layout_unrecognised`, `no_text_layer`, `failed` | weathergpt_data/document_ingest.py (`state_spec`, `ingest_state`) | 13 offline checks in `tests/test_state_agromet_sweep.py` |
| A sweep driver that records every target's outcome and keeps them per target, so a later run cannot erase an earlier finding | scripts/ingest_state_agromet.py | 22 recorded outcomes |
| The state name each document prints, checked against the state the registry claims, in either script | weathergpt_data/document_ingest.py (`STATE_NAMES_IN_DOCUMENT`) | `state_named_in_document: true` for all five ingested editions |

## What the sweep measured

| Outcome | Targets |
|---|---|
| Ingested (with their printed issue dates) | **5**: Gujarat (2026-09-12), Rajasthan (2026-08-07), Uttar Pradesh (2026-09-11), Chhattisgarh (2026-08-07), Karnataka (printed date not stated) |
| HTTP 404 at the centre address | 16 centres (Mumbai, Pune, Nagpur, Bhopal, Chennai, Hyderabad, Kolkata, Bhubaneswar, Patna, Ranchi, Chandigarh, Dehradun, Shimla, Guwahati, Vijayawada, Thiruvananthapuram, Kochi… ) |
| Provider cooldown | 1 run (Goa) |

The corpus went from **1** state agromet edition and 257 passages to **5** editions and 890 passages. Two of
the new editions are Devanagari bulletins whose printed issue dates differ from the retrieval date, and
Karnataka's states no printed date at all - recorded as `printed_issue_not_stated` rather than borrowed from
the retrieval instant.

## The defect this round found

`_squash()` collapsed text to `[a-z0-9]` before comparing a title against the family markers. A Devanagari
title therefore squashed to the **empty string**, and the empty string is a substring of every document:
adding an Indian-language marker would have made the family accept *any* PDF as a state agromet bulletin.
It was found while testing the two Hindi editions that had just been ingested, and it is fixed to keep letters
and digits in any script. Three checks pin it, including one that refuses an unrelated bulletin.

Two consequences were corrected with their evidence recorded:

- The language of an edition follows the **script of the title that matched** (`मौसम सलाहकार` is a Devanagari
  title) rather than a front-page character count, which had called the Rajasthan edition English because the
  same page lists its AMFU partners in Latin. `language_corrections` in the registry records the two relabels
  with the matching marker as their evidence.
- The family markers moved from `markers` (all required) to `markers_any` (the sampled titles of the same
  product), matching how the district family already handles the several titles one bulletin is published
  under. The marker list is two sampled Hindi front pages and one sampled English one, each naming its state;
  it is not a pattern fitted to a failure.

## Two follow-on repairs, and the limit they leave

Adding the editions made two more defects visible, and one limit clearer:

1. **A state named without the word \"state\" now resolves.** *\"Rajasthan ki agromet advisory me sinchai ke
   baare me kya likha hai?\"* asked *which state should I check?* because the corpus path looked for a place
   whose kind was `state`. It now also accepts a place name that the indexed editions carry as a region, which
   is the corpus's own evidence rather than a hard-coded list. The answer changed from a question back to the
   reader to a named edition search.
2. **Topic words are now held in the editions' own scripts** (सिंचाई, बुवाई, कीट, खाद, कटाई and their siblings),
   so a topic filter can match a Devanagari bulletin at all.
3. **The limit that remains:** retrieval is lexical. An English question cannot match passages written in
   Devanagari, so *\"What does the Rajasthan state agromet advisory say about irrigation?\"* finds the edition
   and then reports that no indexed passage matches - which is true, and is the honest description of a
   monolingual index. Cross-lingual retrieval (a translation or an embedding bridge, with the invariant gate in
   front of it) is an open item, recorded here rather than papered over by a wider search.

## What this does and does not establish

- It establishes that six centres (Gujarat and the five new targets, one of which is the pre-existing edition)
  serve a state agromet bulletin at the publisher's centre path, that five are now indexed with their printed
  issue dates and their state named in the document, and that sixteen others answer 404 there.
- It does **not** establish nationwide state coverage: the centres that publish under a different path or
  layout are still unknown, and a 404 at a guessed address is not evidence that a state has no bulletin.
- A listed target is not a promise of an issue, and a reachable address is not a validated product: the
  outcome vocabulary keeps those apart.
- No agronomist or native speaker has reviewed the Devanagari editions; the marker acceptance is a
  structural check over sampled front pages, not a language review.
