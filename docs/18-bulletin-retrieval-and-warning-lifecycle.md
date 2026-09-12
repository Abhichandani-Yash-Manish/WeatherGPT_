# Bulletin retrieval and warning lifecycle — 13 September 2026

WeatherGPT now retrieves published district agricultural passages through the existing IMD source directory, rather than substituting a generic weather forecast for a bulletin question. The existing [critical review](14-product-review-and-progress-plan.md), [conversation checkpoint](17-conversation-engine-refinement.md) and nationwide SIH26068 scope remain in force. P06 and P07 move from open to **partial**, not complete. Hosting remains on hold.

## What now works

- A source question such as “What does the latest IMD bulletin say about cotton pests in Ahmedabad district, Gujarat?” retrieves the relevant published crop/stage passages, issue date and page citations.
- “Aur groundnut ke liye?” changes the crop while retaining the district and pest topic. An explicit irrigation correction changes the topic. No matching passage means an evidence gap; pesticide delivery through irrigation is not treated as irrigation scheduling advice.
- Source lookups also worked for Kamrup rice at tillering and Coimbatore banana. These are three inspected source families, not proof that every national district bulletin can be parsed.
- A combined crop-activity and rain-probability question retains two task outcomes: published advisory evidence and numerical forecast evidence. Individual activity suitability remains explicitly unresolved; source excerpts do not authorize spraying or establish field conditions.
- The response exposes complete source passages. Its page link opens the **saved, hash-verified original PDF**, so a changing publisher URL does not silently replace the cited edition. The publisher link remains available separately.
- Warning questions inspect the CAP feed and resolve its retrieved reference chains. The current sample cannot confirm applicable official warnings, and the answer says why.

## How source evidence reaches the answer

1. **Select from the existing S57 directory.** State and district names must uniquely match the publisher selector. The returned PDF must also contain the requested district, state, identifiable issuer and a resolvable issue date.
2. **Respect the source layout.** Crop/stage/table rows and page bounding boxes precede chunking. The Ahmedabad colored grid requires different rules from the Coimbatore and Kamrup tables. A wrapped date in Kamrup's table is reconstructed from its actual cell, not from arbitrary PDF text order.
3. **Preserve qualifications.** Crop stage, original text, page, row, document hash, issue date and five-day forecast context stay attached to each passage. Forecast dates are not asserted to be expiry dates for every crop recommendation. Unknown families or unverifiable dates fail closed.
4. **Publish a version.** Immutable original bytes, document/chunk hashes, an external publication manifest and a SQLite region head identify the serving edition. Reads re-extract the original PDF and check the document, chunk set and embedding hashes. A failed refresh holds the old head; unchanged PDFs are not embedded again. Superseded versions remain inspectable.
5. **Filter before ranking.** Exact source district/state, crop aliases, growth stage and requested topic restrict candidates before BM25 and multilingual E5 ranking. Reciprocal-rank fusion selects passages. Retrieval scores are explicitly not confidence scores. This is a small, scoped retriever; its multilingual relevance and recall have not been benchmarked over the national corpus.
6. **Keep task ownership.** Document passages, numerical facts and warning-source assessments have separate task/source references. The model extracts conversational intent; source text and numerical tools supply factual content. Retrieved PDF content never becomes an instruction to the model.

The local embedding model is `intfloat/multilingual-e5-small`, pinned to revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, using 384-dimensional normalized vectors, query/passage prefixes, CPU execution and safetensors. Remote code is disabled. English bulletin passages remain in their source language; the broader claim of high-quality Indian-language advisory translation is **not** established.

For another machine, install `requirements-bulletins.txt`, then run `python3 scripts/setup_bulletin_retrieval.py`. Normal retrieval uses the locally installed model. No new paid API or credentials were needed here. Other numeric tools do not load these optional document dependencies.

## Defects found and repaired during live testing

| Reproduction | Repair and retained evidence |
| --- | --- |
| The model understood groundnut but emitted `changed_fields: [parameters]`, causing cotton to survive reconciliation. | Literal crop/topic corrections now override omitted model change tags. Final HTTP follow-ups verify crop and topic, not merely response status. |
| A mixed spraying/forecast request failed interpretation because the agricultural task omitted “tomorrow.” | The relative-date compiler now preserves explicit agricultural dates as well as forecast/history dates. Requested dates outside the bulletin context are held. |
| A later forecast task copied an earlier task's passages and produced mismatched citation prefixes. | Each task starts without prior document/airport/warning payloads. Unit and final HTTP checks verify no passage leakage. |
| A black-gram row contained text naming green gram. | That source passage is quarantined. It is not silently corrected or presented as black-gram guidance. |
| CAP source failures made one exploratory request take about 169 seconds. | Shared retrieval launch budgets and bounded request timeouts stop serial source fan-out. The final cached assessment took 3.22 seconds including planning. This is not a measured cold-source latency guarantee. |

The three dated PDFs yield **48 indexed passages and one quarantined passage**: Ahmedabad 33, Coimbatore 9 and Kamrup 6. Original PDF page samples were rendered and inspected; automated extraction checks do not establish agronomic correctness of every source statement. One source spelling error remains verbatim rather than being silently rewritten.

## Warning progress and remaining gap

The CAP resolver uses the standard's sender/identifier/sent reference triples. It handles updates, cancellations, duplicate identities, expired/test/private messages, missing parents, conflicting payloads, broken ancestry and competing update branches. Cross-sender cancellation requires authorization that this prototype does not possess. Its conservative holds are implementation policy, not a claim of full CAP conformance.

The fresh feed probe contained nine messages, all expired at inspection. The newest message was sent on 9 September. The WFS probe returned 764 features, with 742 accepted and 22 quarantined; its day timing and current applicability remain unresolved. Only the CAP source assessment is connected to chat in this batch. Neither feed reachability nor an empty eligible set establishes an all-clear.

Origin authentication, geographic applicability, complete national coverage, historical update/cancel examples and sustained cadence remain required before current official warning dissemination. CAP lifecycle eligibility deliberately never sets `dissemination_eligible` to true.

## Verification and evidence

- **319 Python tests passed**, including source-layout, crop mismatch, source/index tampering, invalid stage/date, task ownership, PDF delivery and CAP lifecycle cases. The earlier 280-test checkpoint remains preserved.
- **15 real Ollama HTTP turns** on the standard local workspace: seven answered, two partial, two clarification/selection and four explicit evidence gaps. An explanation of the previous sourced response is included among the answered turns. Gaps are not counted as completed questions.
- Source replay checked **11 displayed passage instances, 50 forecast values with units and time locators, two historical source cells and nine CAP source records**. The three original PDFs account for 48 indexed passages; displayed instance counts include re-explanation.
- Recorded HTTP median 5.51 seconds, maximum 11.69 seconds. Most source data/model state was cached. These are a small local sample, not a service-level target or nationwide performance result.
- Two subsequent standard-URL checks verify the final wording, mixed-task ownership and the newly added saved-PDF endpoint against the original SHA-256.
- JavaScript component tests check citation ownership, page links, literal source text and unsafe-link rejection. Syntax and existing chart component checks pass. **Browser visual/interaction acceptance remains unverified**; the earlier browser-tool policy block was not bypassed.
- All **230 registered asset hashes** and the prior frozen code checkpoint remain unchanged. New retrieval artifacts supplement the registry's existing source identities; no additional meteorological source count is claimed.

Evidence: [acceptance summary](../research/implementation/evidence-retrieval-20260913/acceptance.json), [final Python tests](../research/implementation/evidence-retrieval-20260913/all-tests-final.txt), [HTTP/source verifier](../research/implementation/evidence-retrieval-20260913/verify_acceptance.py), [standard workspace checks](../research/implementation/evidence-retrieval-20260913/standard-url-check.json), [preservation check](../research/implementation/evidence-retrieval-20260913/preservation-check.json). Earlier failed exploratory outputs remain in the evidence directory and are not final acceptance results. The new [code/registry checkpoint](../data/processed/checkpoints/evidence-retrieval-20260913/checkpoint-manifest.json) preserves this batch separately from all previous checkpoints.

## Next gates against the original problem statement

| Review concern | Current state | Next acceptance requirement |
| --- | --- | --- |
| P03/P08: natural intent and entity context | Crop/topic corrections, source explanations and mixed requests verified in this sample | Held-out multi-turn questions, multi-crop requests, ambiguous dates/places, missing stage and transliteration coverage |
| P07/R09: document use | Three bulletin families connected with provenance and local hybrid retrieval | Broader district editions, publication transitions, translation quality, topic recall, OCR/font failures, missing table sections and usage terms |
| P06/R02: official warnings | Retrieved lifecycle chains and source-health explanation implemented | Verified origin, affected-area mapping, WFS day semantics, completeness and current operational feeds |
| P01/P02: evidence ownership/integrity | Existing numerical gates preserved; source-bound passage/index checks added | Independent held-out source audits and sustained tamper/failure evaluation |
| P10/P11/R06: operation and latency | Request caching, shared provider reservations, refresh holds and launch budgets | Background refresh scheduling, cancellation, concurrent-load trials, retention and cold-source latency |
| Wider SIH scope | Prior weather/history/airport tools retained | Marine/river identities, operational warnings, validated agriculture decisions, multilingual voice and mobile accessibility remain incomplete |

This advances the PS's conversational, location-based and meteorological-source integration requirements. It does not establish scientific forecast accuracy, agronomic validation, disaster clearance, national document coverage or full SIH compliance.

## Primary architecture references

The [IMD district advisory directory](https://mausam.imd.gov.in/responsive/agromet_adv_ser_district_current_en.php) supplies the source selection path. The [Sentence Transformers semantic-search documentation](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html) informs query/document encoding; the [E5 model card](https://huggingface.co/intfloat/multilingual-e5-small) supplies the model-specific prefixes. [OASIS CAP 1.2](https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html) defines update/cancel reference semantics. The stricter geography, expiry, integrity and task-completion gates above are WeatherGPT implementation decisions.
