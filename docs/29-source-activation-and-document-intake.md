# Source activation and national document intake — 15 September 2026

Two things that had been asserted are now measured: what every registered source actually does when you call it, and what the national district bulletin corpus actually contains when you fetch all of it.

This batch closes the source-review half of the overhaul plan and lands the document intake half. It does **not** make the new corpus answerable in conversation — that work is open and is named at the end. Desktop web continues; hosting and sharing remain on hold.

## Source activation ledger

The registry held 67 sources, 62 of them carrying `user_review: pending` and most saying "proposed; no production source selected". Every one now carries a status and the bounded probe that produced it, in `data/registry/source-review.json`, rebuilt by `scripts/audit_sources.py`.

| Status | Count |
|---|---|
| active | 17 |
| blocked_access | 15 |
| reachable_not_connected | 10 |
| not_a_data_product | 10 |
| product_address_pending | 5 |
| address_missing | 4 |
| active_via | 3 |
| not_a_source | 3 |

One probe failure is recorded (S11, intermittent TLS handshake timeouts on that host, which succeeded on a later attempt). No source is left unmeasured, and a test fails if one ever is.

**The ledger had drifted from the code, and that is the finding worth keeping.** Eight sources were being ingested by a registered document family while the ledger still reported no connector, because the flag was hand-curated. It is now derived from the family registry in code, so adding a family updates the ledger on the next rebuild instead of leaving a stale denial behind.

Rebuilding it also exposed that one word was carrying two different claims. These are now separate fields:

- `connected` — a registered connector pulls this source into the local corpus (**26**)
- `wired_to_chat` — an ordinary conversation can reach it (**18**)

The eight in between — S07, S08, S58, S59, S64, S65, S66, S67 — are ingested but not conversational, and each now says so explicitly rather than borrowing the stronger claim. Reporting intake as reachability would have overstated what a user can actually ask for.

The recorded decision is `approved_local_prototype`, with redistribution not approved and production approval not granted. Registration is not selection, and a reachable address is not a validated product. The credential-gated `api.imd.gov.in` sources stay visible as `blocked_access` with their exact endpoint and next action rather than being quietly dropped; they need an IMD API key, which belongs in local backend configuration if one is obtained.

## Document intake

Eleven national, state and marine families are registered by address or discovery — national bulletin, national and South Asia flash flood guidance, extended range, ERF, press release, RSMC special advisory, state agromet and state district bulletins, sea area and coastal bulletins — with an exclusion list so the publisher's SOPs, adverts, recruitment notices, health PDFs and external papers never enter the corpus. A recorded run on 14 September indexed 18 documents across those families.

Beside the existing crop/stage chunk index there is now a whole-document passage index. Passages carry family, scope, region, physical page, source locator and printed issue evidence, and are retrievable across the whole corpus rather than only within one district's crop rows.

### Change detection was measured, not assumed

Before designing a 698-target sweep, the district address was probed directly. Evidence: `research/discovery/evidence/district-change-detection-20260914T191404Z`.

| Probe | Result |
|---|---|
| `HEAD` | 403, refused |
| `GET` | 200, but no `Last-Modified`, `ETag`, `Content-Length` or `Accept-Ranges`, under `Cache-Control: no-store` |
| `If-Modified-Since` | ignored, full body returned |
| `Range: bytes=0-2047` | ignored, full body returned |
| Two full `GET`s | byte-identical |

There is no validator to make a request conditional on, so the cheap sweep does not exist and every target must be downloaded. Bodies are byte-stable across repeats, so their sha256 is a sound change signal. An unchanged body therefore skips extraction, and nothing else. This is the measurement the plan required rather than the assumption it warned against.

### Retrieval success is not an issue date

The Ahmedabad body hashed to the same value already recorded against S57 from the 11 September inspection — the same PDF was still being served three days later. Nagpur's printed issue was 1 September when fetched on the 14th, thirteen days old.

So currency is measured from the printed issue date against the retrieval date, and stays `printed_issue_not_stated` when the layout does not state one. A fetch that succeeds says nothing about whether a bulletin was issued today.

### The family is recognised by what publishers actually print

The same product appears under several titles. The marker set is taken from 24 sampled district front pages and each entry names the district it came from:

- `gramin krishi mausam sewa` — Kaushambi, Mirzapur, Beed, Kullu, Tapi, Sheohar, Sikar
- `gkms` — Raigad, where the service is named only in the joint-issue line
- `agromet advisory` — Madurai, whose bulletin is titled AAB, and Gondia and Chandrapur, which hyphenate it
- `pdf_dist_advisory` — Pathankot, printed from the agromet.imd.gov.in download route

Matching runs over whitespace-stripped text across the opening pages, for two measured reasons: Wayanad's extraction renders its own title as `GraminKrishiMausamSewa(GKMS)` with the spaces gone, and Sonitpur's first page carries no text layer at all. Every document records which title matched.

Surat and Madurai, both held since [docs/19](19-context-and-retrieval-coverage.md), now extract. Sonitpur is still held, correctly — its front matter genuinely has no extractable text and OCR is not part of the reviewed path.

### Outcomes stay distinct

`not_issued` is a publisher statement and an answer, not a failure. `layout_unrecognised` holds an edition rather than indexing it. `no_text_layer` quarantines. Only transport or extraction errors are `failed`, and failure records are preserved rather than cleaned up. The sweep is resumable, idempotent, locked against a concurrent run, disk-guarded and byte-budgeted, and records the position it stopped at. `--retry-failed` re-tests only errored targets, so a handful of failures does not re-download the corpus.

### Retention

Document bodies are pruned after seven days by `scripts/prune_bulletins.py`; passages, hashes, publication manifests and per-day intake manifests are kept permanently, and a body still wanted by a newer retrieval of the same bytes is not pruned. Report-only is the default.

`/api/documents/<sha>` now distinguishes three cases instead of answering 404 to all of them: the body is served, the document is published but its body is outside the window (410, naming the retained hash, extracted pages and the policy), or the identity was never published (404). A citation the user holds no longer gets denied as though the document never existed.

## National sweep

Recorded in `data/processed/bulletins/2026-09-15/manifest.json`. All 698 listed districts were attempted, across seven passes: four bounded trial passes, one full national pass, and two `--retry-failed` passes.

| Outcome | Districts |
|---|---|
| fetched_new | 566 |
| unchanged | 5 |
| layout_unrecognised | 45 |
| failed | 82 |
| **listed** | **698** |

336 MB downloaded, 6,187 passages indexed, 64 minutes of sweep time in total. The full national pass alone was 682 targets in 49.7 minutes for 283 MB.

**Change detection and idempotency were demonstrated, not asserted.** A pass over already-recorded districts queued nothing. A `--recheck` pass re-downloaded five Gujarat districts, hashed them, matched the recorded head and indexed zero passages — the measured behaviour, since the publisher offers no conditional request and an unchanged body can only skip extraction.

**Every remaining failure has one cause.** After the retry passes, all 82 are `District address did not deliver a PDF` — the publisher returns something that is not a PDF for those districts. No transient timeout and no defect of ours remains in the failure set; the earlier timeout and publication-collision failures were recovered by retrying and by the shared-edition fix.

### Not one bulletin was issued on the day it was fetched

Of the 566 documents with a printed issue date:

| Currency | Districts |
|---|---|
| printed_issue_differs_from_retrieval_date | 530 |
| printed_issue_not_stated | 36 |
| printed_issue_matches_retrieval_date | **0** |

Age of the printed issue against the retrieval date: minimum 2 days, median 4 days, maximum **376 days**.

This is the batch's most important measurement. A national sweep that succeeds on 566 districts does not deliver 566 current advisories. The median district's bulletin was four days old and at least one was more than a year old, so a system that treated fetch success as currency would have presented year-old agricultural advice as today's. Currency is read from the printed date, it is recorded per document, and it stays `not_stated` for the 36 layouts that print no date at all.

### One edition can serve many districts

The publisher's selector returned a single Haryana bulletin for eight districts — Bhiwani, Hisar, Jhajjar, Mahendragarh, Palwal, Rewari, Rohtak and Sirsa. Publication identity is therefore content *and* region, and a published document reports `selected_for_regions` and `is_shared_edition`. A reader asking about Rohtak is reading an advisory that also covers seven other districts, which is provenance rather than trivia.

## Defects found while building this

Four were real and two of them would have been silent:

- **`text_quality` could never fire.** `_split` cleaned control characters and discarded the damage flag before `_build` could read it, so every passage reported `text_layer_clean` and a damaged extraction was presented as clean text.
- **Publication namespace collision.** Document and chunk publications both wrote `publications/<sha>.json`, so any district present in both corpora failed to publish against its own other-shaped manifest. This is the cause of the `Immutable document publication already differs` failures in the first sweep pass.
- **Sweep accounting.** `already_recorded_today` counted targets trimmed by `--limit` as though they had been recorded.
- **The 410 route itself.** A missing chunk-publication manifest was briefly reported as a pruned body, which is a different claim: it means the identity belongs to the other corpus, not that anything was deleted.

Separately, `test_an_unknown_colour_is_not_converted_into_a_level` read the real wall clock while asserting the wording of the "day one covers today" branch, so it passed only on the day its fixture bulletin is dated. The clock is now pinned; this was test brittleness, not a defect in `district_warnings`.

## Tests

**543 automated tests pass**, up from 432. 61 are new: 13 reconciling the ledger against the registry and the code, and 48 over document intake, extraction and retention.

The reconciliation tests fail on drift in either direction — a family the ledger does not know about, a connector the ledger claims that the code does not have, reachability inferred from intake, a status outside the vocabulary, a probe recorded against an address other than the registered one, counts disagreeing with the rows, or an approval note that has grown into a readiness claim.

The intake tests take no measurement of their own. Their marker fixtures are the printed titles of named real front pages, because a marker list fitted to a couple of failures would not be evidence.

## What remains open

- **571 districts are indexed and none of them is reachable.** Nothing in conversation can query the corpus. The chat path is still the narrow crop/stage chunk reader for a single district, which is exactly finding **A06**. This is the most valuable next piece of work and it is not done.
- Held layouts are held, not solved: 45 districts are outside the corpus until their families are widened or OCR is reviewed, and 82 more return something that is not a PDF at all.
- Nothing in this batch establishes that any indexed advisory is current. 530 of 566 were already out of date on arrival, and the corpus is a record of what was published, not of what applies today.
- Eight ingesting sources have no conversational path, and the new adapters in the plan — NASA POWER, ephemeris, marine bulletins, MC bulletins, crop advisory, Mausamgram — are not built.
- No contradiction handling across editions, and no general/warning/crop separation in the new passage index.
- `api.imd.gov.in` remains blocked without a key.
- Engine findings **A01** context retention, **A02** language output, **A04** district aliases and **A07** task accounting are untouched by this batch.
- Nothing here measures forecast skill, establishes operational readiness, or claims national coverage of anything beyond what the recorded manifest names for the day it names.
