# 124 — The chat's missing affordances

20 September 2026. docs/116 §3 and §4 named four things the chat could not do: a turn's progress was the
workspace's newest turn rather than the reader's own, a dropped connection lost the answer, a question could
not be edited or retried, and a place or a window could not be changed without rewriting the sentence. All four
are built here, each with a spec that was watched failing first.

Everything measured below was measured on this machine against the running engine on port 8771
(`python3 -m weathergpt_data.workspace --port 8771 --no-warm --no-plan-watcher`), started and stopped for the
check. The saved-PDF store, the model store and the SQLite conversation store are this machine's.

## A — Progress belongs to the turn

**What was wrong for the reader.** `/api/chat/progress` answered `self.conversation.progress()`: the stage of
whatever turn the workspace had started last. The route took no request id and the client sent none, so a page
waiting on its own question could be shown another question's stage — or, when its own turn was still queued
behind one, shown the running turn's work as if it were its own. The parameter existed on `/api/chat` all along
(`weathergpt_data/conversation.py`, the supplied-or-`uuid4` request id with `cancel()` and the active map); it
was simply not on the read.

**What was built.** `ConversationEngine.progress(request_id)` reads one turn's entry and nothing else, and
`chat_progress(params)` passes the query parameter through. The client now sends the identifier it minted with
every poll (`frontend/src/chat/useConversation.ts`, `frontend/src/chat/api.ts`).

Three states are named rather than implied:

| state | meaning |
| --- | --- |
| `running` | this turn is working; `stage` is the checkpoint it is in now |
| `queued` | this turn has been accepted and is waiting for the answering slot; no stage has been reached |
| `not_running` | this process is not running this identifier — it may have finished, may be waiting, or may never have run here |

`queued` is new in substance rather than in name: the turn is registered against its identifier *before* it
takes the answering slot, so a queued turn is visible as queued and a stop arriving while it waits is honoured
at its first checkpoint. The read keeps its honesty exactly as docs/116 §3.2 described it: `stages_seen` is the
engine's own checkpoints, `stage_note` says in words which of the three states this is, and
`stages_are_facts_not_progress` is still `true`. No percentage, no ETA and no confidence appears anywhere in the
payload — asserted, not intended: `test_no_percentage_eta_or_confidence_anywhere_in_the_read` and the route
spec both fail if the word or the sign appears.

**The spec, and the failure it was watched having.** `tests/test_chat_progress_result.py::PerTurnProgressTests`
(4 specs) and `::RouteTests::test_the_progress_route_echoes_the_turn_it_read_and_does_not_borrow_another`;
`frontend/src/chat/progress.test.tsx` (3 specs). With `request_id` ignored in `ConversationEngine.progress`
(the pre-fix behaviour, measured when the file held 21 specs) the run was `5 failed, 16 passed`, including
`test_progress_names_only_the_turn_it_was_asked_about`; with the client's read reverted to `chat.progress()`,
2 of the 3 React specs fail with `expected null to be 'e54760c8-…'` — the identifier is not on the wire.

## C — A turn survives the page

**What was wrong for the reader.** A reload mid-turn lost the answer. The server had produced the packet and
the tab held the request id, and there was no route that traded one for the other: the reader re-asked, and a
long turn's work was thrown away by a stray refresh.

**What was built.** `GET /api/chat/result?request_id=` answers with the turn's own state, and the client keeps
the identifier it minted in this tab (`weathergpt.sessionStorage['weathergpt.inflight']`, written before the
request and cleared when the turn resolves) and asks on mount.

| state | what it carries |
| --- | --- |
| `pending` | the turn is still accepted here; no packet, and nothing pre-announced |
| `ready` | the engine's own packet for that turn |
| `cancelled` | the stopped turn's own packet, with the engine's sentence about what was discarded |
| `expired` | this process held a result for it and let it go after `kept_seconds` (900 by default) |
| `unknown` | this process never had it, or was restarted since |

None of the five is an empty success: only `ready` and `cancelled` carry a packet, and `expired` is kept
distinct from `unknown` because "the workspace let it go" and "the workspace never had it" are different
sentences to a reader. A missing or malformed identifier is a 400 in words, not an `unknown`.

The client shows the restored turn only after the workspace has confirmed it. A pointer this process cannot
confirm — a stale line in this tab's storage, or a read that failed because the workspace did not answer — puts
nothing on screen: no question, no notice and no error about a turn the client cannot name. That is deliberate
and pinned; it is also what keeps the feature from writing into a page the reader is already typing in.

**The spec, and the failure it was watched having.** `tests/test_chat_progress_result.py::ResultTests` (6
specs) and `::RouteTests::test_the_result_route_*`; `frontend/src/chat/resume.test.tsx` (6 specs). With
`GET /api/chat/result` absent from the server, the two route specs fail (404, `2 failed, 19 passed`); with the
engine's retention replaced by a fixed `unknown`, `9 failed, 12 passed`; with `resume()` disabled in the hook,
`5 failed` of the 6 React specs
(`Unable to find an element with the text: THE TURN THAT OUTLIVED THE PAGE.`).

## D — Edit the question, retry the refusal, ask the sources again

**What was wrong for the reader.** A typo could only be corrected by typing the sentence again, and the old
answer stayed on screen beside its replacement. A refusal returned the question to the box with nothing to
press. An answer could not be re-read at all — in a product whose answers rest on a live read, "ask the sources
again" is the more meaningful button, and `Collect fresh evidence` already existed on the card without the
re-ask beside it.

**What was built.** `frontend/src/gpt/Workspace.tsx` draws the three controls on the newest question and the
newest answer, and `frontend/src/chat/useConversation.ts` moves turns rather than only sending requests:

1. **Edit this question** drops that turn and everything after it and puts the text back in the box, so the
   answer that belonged to the question is replaced rather than left beside the correction. The request in
   flight is aborted at the same moment, and the reducer's key guard drops its answer if it arrives anyway
   (`case 'answer'`: `if (!state.working || state.working.key !== action.key) return state;`).
2. **Ask again** (a refusal or a notice) re-sends the same question and replaces the refusal where it stood.
3. **Ask the sources again** (an answered turn) asks `/api/refresh` for the point the answer read, then sends
   the same question, and the answer that comes back states what happened. That sentence is measured from the
   two packets' own retrieval instants (`latestRead`, `freshnessNote` in `frontend/src/chat/model.ts`): a later
   instant is stated as later, the same instant is stated as the same read served again, and a packet that
   records no retrieval instant is stated as saying nothing — never as fresh.

Each control carries what it will do in its `title`, and a control that sends a sentence carries that sentence,
which is the rule docs/115 already set for the notify chip. The specs assert the title text.

**The spec, and the failure it was watched having.** `frontend/src/chat/affordances.test.tsx` (7 specs). With
the control rows removed (the pre-fix state, in which no such control existed) the run was
`6 failed, 1 passed`:
`Unable to find an accessible element with the role "button" and name "Edit this question"`, `"Ask again"` and
`"Ask the sources again"`.

## E — Inline disambiguation, and changing one thing

**What was wrong for the reader.** A `needs_selection` answer cost a whole turn: the chips sent a new request
and the transcript grew a second question. And a reader who wanted the same question for another place, or for
another window, had to rewrite the sentence and hope the planner agreed — with the panel knowing the place and
the claim knowing the window, neither of which was an affordance.

**What was built, from the engine's own slot rules.** For the place choice, the client now resends the question
the choice belongs to, with the `selection_id` the engine issued, and the answer replaces the held turn in
place. The engine binds a selection to its question (`conversation.py`: `if q!=state['last_question']: raise
SourceError('This place choice belongs to another question…')`) and does **not** append the question to the
history when a selection id is present, so the conversation keeps one user turn — the choice is a choice, not a
second question.

An existing check already pinned the old body — `frontend/src/chat/card.parity.test.tsx` asserted that the
chip's own label was sent as the question. That assertion is updated to the question the choice belongs to, with
the engine's refusal sentence quoted in the spec, because the old body cannot resolve: the engine requires the
question the choice was offered for.

For a changed place or window, the change travels *beside* the unchanged sentence, as its own field, so nothing
has to hope the planner reads the sentence differently:

- `place: {label, latitude, longitude, state?}` — the point the reader chose, resolved without searching the
  name again, because searching it again is the ambiguity the reader just resolved. The label is recorded as
  the reader's, never as a match of ours (`name_match_basis` and the packet's note say so in those words), and a
  question naming more than one place is refused rather than read at one of them.
- `window: 'tomorrow evening'` — a phrase from the engine's own day and part-of-day tables, resolved by the
  same calendar compiler the rules floor reads (`ground_relative_slots`), on a copy of the plan. Whether it was
  applied is reported either way: `reader_changes[{field:'window', requested, applied, label, basis}]`, and when
  it could not be resolved the question's own window is what is read, said in the packet's notes.

The turn states what changed from the engine's own record of it (`changeNote`), so a re-read turn never looks
like the same question answered about somewhere else. The window controls offer only phrases the shared
compiler resolves today; `day after tomorrow` is deliberately not among them, and the Python spec pins why —
the phrase contains the shorter word `tomorrow`, the compiler finds two possible days in it and declines to
choose. It is reported as not applied rather than papered over, and the gap is recorded here rather than widened
in a file this batch does not own.

**One defect found by running it, not by reading it.** Against the live workspace the note about the changed
place reached the packet and the structured `reader_changes` record did not. The cause: the task dispatcher
resolves a point against its own task packet and merges a named set of fields back
(`task_dispatch.py`), so a record written on the turn's own dict during that resolution is dropped. The record
is now held for the turn and merged into its packet at the end, and
`test_a_place_resolved_inside_a_task_still_reaches_the_turn` pins exactly that path.

**The spec, and the failure it was watched having.** `frontend/src/chat/inline.test.tsx` (5 specs);
`tests/test_chat_progress_result.py::ReaderChangeTests` (7 specs) and `::InlineChoiceTests`. With the old chip
behaviour restored (send the choice's own label with the selection id, as a new turn), 1 of the 5 React specs
fails (`expected 'Bhopāl, Ashoknagar, Madhya Pradesh' to be 'Tell me about rainfall in Bhopal.'`); with the
change controls removed, the other 3 fail (`Unable to find … "Change the place"` / `"Change the window"`). With
the control rows removed in the pre-fix state the affordances run was `6 failed, 1 passed`. With
the reader's place ignored, `2 failed, 19 passed`; with the reader's window ignored, `3 failed, 18 passed`.

## Evidence

Every count below is from this machine on the batch's final tree. The frontend specs are run together with the
specs they share a directory with, so a change cannot break a neighbour silently.

| command | observed |
| --- | --- |
| `cd frontend && npx tsc --noEmit` | clean, no output |
| `cd frontend && npx vitest run src/chat` | 17 files, 100 tests passed |
| `cd frontend && npx vitest run src/gpt src/shell src/test` | 11 files, 71 tests passed |
| `cd frontend && npx vitest run src/styles` | 2 files, 8 tests passed |
| `python3 -m pytest tests/test_chat_progress_result.py -q` | 26 passed |
| `python3 -m pytest tests/test_chat_queue.py tests/test_route_inventory.py tests/test_workspace.py tests/test_conversation.py tests/test_chat_preview.py tests/test_conversation_ledger.py tests/test_continuation_repairs.py tests/test_context_matrix.py -q` | 82 passed (108 with the new file) |
| `GET /api/chat/result?request_id=<finished turn>` | `ready`, the engine's packet, `kept_seconds` 900 |
| `GET /api/chat/progress?request_id=<finished turn>` | `not_running` |
| `GET /api/chat/progress?request_id=<never-run id>` | `not_running`, the fallback sentence |
| `GET /api/chat/result?request_id=<never-run id>` | `unknown` |
| `GET /api/chat/result` / `?request_id=nope` | 400 in words |
| any of the two routes without the token | 403 |
| `POST /api/chat {'window': 'tomorrow evening'}` on the live engine | `reader_changes[0].applied` true, `label` `22 Sep 2026 18:30-22:30 IST`, the fact window equal to it |
| `POST /api/chat {'place': {'label': 'Surat, Gujarat', 21.1702, 72.8311}}` | `reader_changes` present, the fact read at `Surat, Gujarat`, the note naming Ahmedabad as what the question said |

Fences this batch had to leave alone, because they are not this lane's files.

- The status-drift guard compares README's recorded Python test count with what pytest collects, and this batch
  adds 26 collected tests (1439 → 1465). **The gate step needed is `README.md` line 376's `# 1439 Python tests`
  → `# 1465 Python tests`** by whoever owns README; nothing else in the guard is affected.
- `frontend/src/test/msw.ts` has no handler for `GET /api/chat/result`, so the two chat specs that leave a turn
  in flight print an msw "unmatched request" notice for it. Nothing fails — the route's own specs declare their
  handlers — but a default handler returning `unknown` belongs there.
- The gate step for the browser journeys below is a real reload against the running workspace on 8771, which
  needs a browser this lane did not drive.

A live turn took 14.0 s for a forecast question and 7.8 s for the same question with the place changed — one
machine, a warm store and this machine's model; §1 of docs/116 already says a cold first model call is a
different number.

## What is not built, and what is not claimed

- **Batch B — streaming over SSE — is not built.** `/api/chat` is still one POST that resolves with the whole
  packet, the client still polls one stage at a time (now its own), and nothing is readable before everything
  is ready. Nothing in this batch is a substitute for it: per-request progress makes the poll honest, not
  unnecessary.
- **The latency figures are from this machine, once each.** They are not a benchmark, not an average, and not a
  promise; the 7.8 s and 14.0 s turns above are two questions I ran.
- **Not verified without a browser.** The refresh-mid-turn journey is exercised through jsdom with mocked
  routes: the storage pointer, the five states, the restored question and the landed answer are all pinned, but
  no real browser reload against the running server was performed here, and the panel drawn by
  `WorkingTurn`/`AnswerTurn` — whose files this lane does not own — is checked only through the specs that
  already cover it.
- **The client's own controls are not verified in a browser either**: no screenshot or manual pass of the three
  new affordances on a real screen exists in this batch, so their placement and their behaviour on a narrow
  viewport are unmeasured.
- **The edit is a screen edit, not a store edit.** The transcript on screen truncates and re-asks; the
  workspace's stored conversation keeps the original turn and appends the re-asked question, because the store
  is append-only. A restored transcript is therefore a superset of what an edited screen shows, and this is
  recorded rather than repaired.
- **`day after tomorrow` does not resolve through the shared day compiler**, for the reason given in E. The
  control is not offered and the engine reports the phrase as not applied; the compiler itself is in a file
  this batch does not own.
- **A place label supplied with a point is the reader's label.** The engine checks that the coordinates are
  valid and records the label as supplied by the reader, not as a gazetteer match; it does not reverse-lookup
  the point, so a client could label a pin with another place's name. The note on the turn and the resolved
  point both say where the label came from.
- **`/api/chat/result` is in memory only.** A workspace restart forgets every held result, which is why
  `unknown` names the process rather than the reader; nothing here survives a restart and nothing is claimed to.
- **No warning, marine, river or corpus behaviour is touched.** These four batches move turns and read stages;
  they change no value, no source, no validity window and no refusal.
