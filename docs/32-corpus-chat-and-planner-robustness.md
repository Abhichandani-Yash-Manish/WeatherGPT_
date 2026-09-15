# The indexed document corpus becomes conversational — 15 September 2026

This is the first repair batch from [the gap register](31-full-solution-gap-register.md). It closes the reachability half of **A06**: the national corpus that [docs/29](29-source-activation-and-document-intake.md) recorded and could not be asked about is now retrievable from an ordinary conversation. It also repairs a live planner failure reproduced while investigating that same question. It closes none of the other gaps; warning dissemination, aliases, sustained collection, voice/mobile acceptance and forecast skill are untouched.

## The live failure that started this

On this machine, before the batch:

- `"What does the latest IMD national weather bulletin say about heavy rainfall?"` **failed with no answer**: the planner wrote ~1,400 characters of tool-choice reasoning into `assumptions`, the length check rejected the whole interpretation twice, and the turn ended as `Question interpretation did not preserve the requested tasks: Invalid clarification fields`.
- `"What does the Gujarat state agromet advisory bulletin say about irrigation?"` planned as a district crop lookup and answered `"Which district and state should I look up in the IMD agricultural bulletin?"` — a state composite bulletin was already indexed and could have answered it.

## What changed

**Disclosure fields can no longer kill a valid plan.** `language.bound_disclosures` clips `assumptions` and `unsupported_parameters` before validation, and the planner prompt now asks for at most three short assumption sentences and forbids tool-choice reasoning in them. Nothing here changes a task, place or time; a malformed task still fails. The live question above now plans instead of crashing.

**A published product named in the question reaches the corpus.** A new task kind, `document`, performs a bounded `lookup` over the whole-document passage index through `weathergpt_data/corpus_tools.py`. `dialogue.ground_document_request` routes exactly one task to it when the user names a publisher product (`national weather bulletin`, `extended range`, `press release`, `flash flood guidance`, `sea area bulletin`, `coastal weather bulletin`, `special advisory`, `state/composite agromet`, `district forecast and warnings`), while a district crop/stage question keeps its existing crop path. `dialogue.ground_named_place` binds a single state the question names outright, including its native-script GeoNames alternate names, when the planner left `places` empty — and refuses when two states are named or a clarification is pending.

**Every answer carries the record, not a currency claim.** A retrieved document reports its family, scope, region, physical page, printed issue date, age against the printed issue, retrieval instant, extraction status and a corpus document reference. A document whose printed issue date is not stated is `partial` with currency unknown; a printed `valid_till` that has passed is stated as a record, not current guidance. The answer quotes a bounded excerpt (520 characters) and keeps the full passage on the evidence record.

**Warning text is separated and never becomes a current warning.** Passages whose section or body carries warning wording are classified `warning_reference`, listed in their own section, and always followed by: this is what a document published, it is not a current applicable official warning, not an all-clear, and current applicability is answered only by the official warning check. Any warning-classified hit makes the turn `partial`. Crop-family text carries the individual-field limitation. Opposing permission/restriction wording is flagged unresolved, reusing the parent-context flag model.

**Earlier editions are retired from current retrieval.** The newer printed edition is found from the passage index, not from the hit set, so an edition that does not contain the asked words still supersedes one that does. If only a superseded edition matches, the turn says so and does not serve it as current; asking for the historical edition explicitly returns it.

**A hit must share a word with the question, or disclose that it does not.** Rank alone cannot say "the document does not mention this", so a passage is served only when it contains at least one exact content word from the question. When the question is written in an Indic script and no lexical support exists at all, the top three semantic matches are served with `match_basis: semantic_only_indic_script_disclosed`, a partial status and an explicit sentence that wording support is unverified.

## Defects found while building this

- **`capabilities.retrieval_plan` used an eager default.** `registry[sid].get('integration', {}).get('status', registry[sid]['evidence_level'])` evaluated `evidence_level` even when an integration status existed, so adding the corpus capability crashed every turn with `KeyError: 'evidence_level'`. Repaired and pinned by test.
- **`passage_document` denied documents published in both corpora.** The chunk corpus writes `publications/<sha>.json`; the passage corpus writes `publications/documents/...`. The documents table keeps whichever payload published first, so a shared body (Ahmedabad/arnej, for example) verified against the wrong namespace and raised `Document publication manifest mismatch`. Verification now accepts the manifest that actually describes the stored payload, whichever namespace it is in.
- **A district name already in the publisher's directory demanded its state.** `execute_document` required the user to repeat a state the publisher's own directory determines, because the planner had left it empty. A district-kind place now fills its state from that dated directory; a settlement name is never promoted to a district this way, and two states sharing a name still ask.
- **The first corpus answer quoted an unasked-for document.** Without a lexical support check the tool served its top-ranked passage for `"snow over Leh"` from a rainfall bulletin, because a dense score is never zero. The floor above is the repair; the test pins the refusal.

## Acceptance evidence

**588 automated tests pass** (from 569), including 19 new checks: 4 for disclosure bounding, 14 for the corpus tool and its routing, and 1 source-ledger reconciliation. Implementation: `weathergpt_data/corpus_tools.py` (new), `language.py`, `dialogue.py`, `tasks.py`, `capabilities.py`, `task_dispatch.py`, `document_ingest.py`, `document_tools.py`, `bulletin_index.py`, `conversation.py`, `scripts/audit_sources.py`.

Recorded journeys: [research/implementation/corpus-chat-20260915](../research/implementation/corpus-chat-20260915/), five local HTTP turns on one machine with the local Ollama planner. These are five checked outcomes, not five completed information tasks, and not an acceptance benchmark.

| Journey | Asked | Outcome | What it demonstrates |
|---|---|---|---|
| C1 | national weather bulletin, heavy rainfall | **partial**, 10 passages, one document | Whole-document retrieval from the national bulletin with page, printed issue and retrieval instant attached; three passages classified warning reference and separated |
| C2 | Gujarat state agromet bulletin, irrigation | **partial**, one document | State-scope retrieval with the state bound from the publisher directory; no district demanded |
| C3 | Ahmedabad district agromet bulletin, cotton | **answered**, 3 of 4 crop passages | The crop path still works and now fills Ahmedabad's state from the directory without asking |
| C4 | coastal weather bulletin, Gujarat coast | **partial**, 10 passages, several documents | Several same-day marine editions distinguished by document identity; warning text separated |
| C5 | Gujarati question about the Gujarat state agromet bulletin | **partial**, 3 semantic-only passages, rendering **refused by the gate** | The Indic-script semantic path is disclosed and the value gate caught a real duplication (`30-40 kmph` repeated 16 times) and kept the source-language answer rather than shipping a damaged rendering |

**Source reachability ledger.** `data/registry/source-review.json` was rebuilt offline. `wired_to_chat` is now derived from `capabilities.corpus_sources()` rather than curated by hand, so a newly registered family flips on rebuild. Reachability moved from 18 to **26** sources, adding exactly the eight that were ingested and not conversational: S07, S08, S58, S59, S64, S65, S66, S67. Nothing about their approval status changed: the decision remains `approved_local_prototype`, redistribution not approved.

**C5 is also a preserved failure.** Its semantic fallback selected a reading-order-garbled passage (`KHEDA Inten sity Light thunderst orm…`) and did not answer the irrigation question well. That is recorded rather than hidden: extraction reading order is unverified for these documents, the turn is `partial`, and no wording match is claimed.

## What this batch does not establish

- **No full-document recall.** Retrieval returns up to ten passages ranked and filtered; the answer says it is a selected extract, not the complete bulletin.
- **No archive.** The corpus is what publishers served on the sweep days. Bodies are pruned after seven days while passages and hashes stay; `/api/documents/<sha>` answers 410 with what survives.
- **No currency.** 530 of 566 district documents were already older than their retrieval date when fetched, and 36 stated no printed date at all. The tool now states this per document; it does not fix it.
- **No agronomic, warning, marine or hydrological validation.** Warning text remains reference; crop text remains district guidance; no personal go/no-go is granted.
- **No OCR.** Documents without a text layer stay quarantined.
- **Held layouts stay held.** 45 districts remain `layout_unrecognised` and 82 addresses delivered no PDF, exactly as docs/29 recorded.
- **No cross-edition contradiction resolution.** Same-edition opposing wording is flagged unresolved; different editions are retired, not reconciled.
- **No benchmark.** Five journeys are five checks; the declared acceptance set is still open (G08).
