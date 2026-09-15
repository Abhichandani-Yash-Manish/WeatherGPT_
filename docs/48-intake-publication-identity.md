# The intake holds what it cannot verify, and a re-fetch is not a new edition — 15 September 2026

This cycle started as an attempt to give the cross-edition comparison real publisher text:
[docs/47](47-answer-transparency-and-edition-coverage.md) recorded that no live comparison
was possible because every product and region held exactly one indexed edition. Re-running
the document intake to fetch today's editions was the obvious next move. It failed, and
the failure was worth more than the fetch.

## What the review found

```
python3 scripts/ingest_documents.py run --family national_bulletin --family flash_flood_national \
    --family sea_area_bulletin --family coastal_bulletin
→ exit 1
  SourceError: Immutable document publication already differs
```

One unverifiable publication aborted the whole sweep. Investigating it, in order:

1. **The refusal was right, the abort was not.** The publication on disk is evidence and must
   not be rewritten; but a four-family sweep should record one held target and continue, not
   stop.
2. **The identity check compared annotations, not evidence.** The stored payload for the
   sea-area PDF (sha `732cdfa9…`) records `age_days: 0`, `currency:
   printed_issue_matches_retrieval_date` and no `marker_basis`, because it was ingested on
   the printed issue date. The same bytes fetched today derive `age_days: 1`,
   `printed_issue_differs_from_retrieval_date` and `marker_basis: no_marker_required`.
   None of that is a change in the document, and all of it was in the compared payload.
3. **A character annotation was part of the passage id.** Six stored passages and six freshly
   extracted passages of the same bytes had **disjoint ids**. Diffing them field by field, the
   only difference on the first passage was `text_quality`: `text_layer_clean` stored,
   `control_characters_replaced` fresh. `text_quality` was inside the id input, so the same
   document could extract to a different identity on a different run.

## What was repaired

| Repair | Behaviour now |
|---|---|
| The intake holds an unverifiable target | `ingest` catches the publication refusal, records it as `{stage: publish, held: true, error: …}` and continues the run; the publication is still never rewritten |
| Publication identity is content and address | Identity is `sha256, family, region, scope, source_id, issue_date, pages, bytes, language, extraction_version, printed_times, issue_date_basis, issuer_basis` plus every passage's printed position and text. Clock-derived fields (`age_days`, `currency`, `printed_issue_is_retrieval_date`) and later-added annotations (`marker_basis`, provenance paths) are not identity, so a re-fetch of unchanged bytes is **idempotent** and a changed passage or identity field is still refused with the reason named |
| `text_quality` leaves the passage id | The same bytes extract to the same passage id. Stored ids are unchanged - ids are recorded, not recomputed - and publications made after this batch derive ids from content and position only |

The refusal message now names the document, the region and the reason
(`passage text differs…`, `identity fields differ: issue_date…`, `the stored document payload
is not in this index`), because an integrity error that does not say what differs cannot be
acted on.

## The re-run

```
python3 scripts/ingest_documents.py run --family national_bulletin --family flash_flood_national \
    --family sea_area_bulletin --family coastal_bulletin
→ exit 0
  national_bulletin     accepted 1, rejected 0
  flash_flood_national  accepted 1, rejected 0
  sea_area_bulletin     accepted 1 (idempotent re-record), rejected 1
  coastal_bulletin      accepted 7, rejected 2 (held at extraction: layout needs review)
```

The corpus grew from 582 documents / 6,700 passages to **584 documents / 6,739 passages**, and
the two held coastal targets are recorded as rejected with their reason rather than as a crash.

## The honest result, and the honest limit

**No product and region holds two editions after this run.** The publisher still serves the
14 September editions for these four families, so the live cross-edition comparison remains
unexercised on real text - exactly as [docs/47](47-answer-transparency-and-edition-coverage.md)
recorded. What this cycle bought is not the comparison: it is that the intake can be re-run at
all, that a re-fetch is not mistaken for a new edition, and that the same bytes can no longer
extract to a different identity.

## Evidence

- [research/reviews/intake-repair-20260915/evidence.json](../research/reviews/intake-repair-20260915/evidence.json) -
  the run's per-family outcomes, the corpus size after it, the three defects with their
  measured details, and the limits.
- data/processed/bulletins/2026-09-15/manifest.json - the run's own manifest, written by the
  intake.
- tests/test_document_ingest.py::PublicationIdentityTests - five component checks pinning
  idempotence, the two refusals, the id rule and the held-target path.

## What this cycle did not do

- It did not create a second edition, and nothing here makes one exist. Until the publisher
  issues another edition of the same product and region, the comparison is exercised by
  component checks only.
- It did not change any source's terms, any issue date, any currency and any retrieval
  instant. The stored payload keeps the annotations measured when it was first ingested; only
  new publications derive them anew.
- It did not run the other document families, and it did not re-run the benchmark or the
  frontend evidence: neither was touched by these repairs.
