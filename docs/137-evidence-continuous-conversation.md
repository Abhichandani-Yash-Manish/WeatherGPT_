# 137 · Evidence-continuous conversation

**Recorded:** 21 September 2026  
**Scope:** the first chat-refinement slice after the docs/136 answer-as-page batch  
**Status:** implemented locally; acceptance is the checks in §6, not a claim of full frontend completion

## 1. The broken journey

A live answer used the structured `AnswerTurn`: finding, claim, unit, place, window, source, reading time,
kind, limitations and claim-owned depth. Reopening that same conversation used only the bounded planner
history, whose assistant entries intentionally kept at most 2,000 characters of prose. The frontend then
drew the stored prose as “Restored from this machine”. Every evidence affordance disappeared even though
the composer still promised that every value kept its source and read time.

That was not a cosmetic inconsistency. A reopened value could no longer show what kind of value it was,
which source owned it, when that source was read, or what the original answer refused. It failed the
product’s evidence contract at the moment a reader returned to rely on an earlier answer.

## 2. The contract now

Every newly completed turn stores two different things for two different jobs:

- `history` remains the twelve-message, role/content planning context. An assistant row carries only a
  receipt identifier in addition to its bounded text. Facts and traces never enter the next planner prompt.
- `answer_packets` holds the JSON-serialisable public packet that the answer route returned. Receipts are
  pruned with the history rows that name them; this is not an unbounded second conversation log.

`GET /api/conversations/<id>` is now `conversation-transcript-v2`. A stored receipt is returned on its
assistant turn and is rendered through the ordinary `AnswerTurn`, so claims, citations, timestamps,
warning lifecycle, task accounting and depth do not acquire a second restoration renderer.

Older conversations remain readable, but the interface does not invent the missing receipt. It says
“receipt unavailable”, explains that sources, reading time and limits cannot be reconstructed, and offers
**Read it again**. The Markdown export carries the same limitation.

## 3. Watch boundary repaired with it

The answer card used to infer a heavy-rain watch sentence from any resolved place plus a warning, rain,
rain-probability or temperature fact. That changed the user’s question in the client: a temperature fact
could become “Notify me if a heavy rain warning is issued … tomorrow” without the engine proposing that
scope.

The client now renders only `quick_replies` supplied by the answer packet. It does not derive a watch
hazard, day or place from facts. A watch still is not created by rendering a chip; pressing an engine-owned
reply asks its exact sentence and the engine may register or refuse it.

## 4. What this does not finish

- Existing text-only conversations cannot be retrofitted with receipts.
- The independent reading panel and module homes still re-fetch some material instead of opening the
  packet-owned depth of a claim. Forecast, warning and document depth are the next integration target.
- Compare still compares places rather than two sources for one claim, and the ensemble and verification
  homes still choose a default variable/lead without a claim handing them context.
- This batch does not establish live-model fluency, nationwide corpus acceptance, warning-origin
  authentication, live device delivery, mobile acceptance or full SIH26068 compliance.

## 5. Design decision

The normal answer component is the restoration component. That keeps the docs/108 and docs/136 rule—one
sentence followed by claims, with depth owned by the claim—continuous across a reload. A second “history
card” visual language would have made old and current evidence look like different products and would have
created another place for source handling to drift.

## 6. Verification evidence

- Backend receipt and legacy fallback: `tests/test_conversation.py` and
  `tests/test_conversation_ledger.py`.
- Reopened packet renders its claim, source and copy action: `frontend/src/App.test.tsx`.
- Legacy prose states the missing receipt and offers a fresh read: `frontend/src/gpt/shell.test.tsx`.
- A weather fact cannot create a watch chip; an engine-provided reply can:
  `frontend/src/gpt/shell.test.tsx`.
- Repository acceptance remains `scripts/verify_all.py`, frontend typecheck and the production build.

