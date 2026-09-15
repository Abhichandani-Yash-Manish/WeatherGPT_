# Bounded queue and stage-boundary cancellation — 15 September 2026

[The gap register](31-full-solution-gap-register.md) recorded **G07** from docs/21 A08 and P11: one non-blocking global conversation lock, a second question rejected instantly, and a stop control that aborted only the page request while the server kept working. This batch replaces that behaviour with a bounded queue, a cancellation endpoint that reports exactly what happened, and checkpoints that discard a stopped turn's partial evidence. It does not add stage streaming, does not turn the local model into a concurrent service, and does not make cancellation interrupt an inference already in flight.

## What changed

**A bounded queue replaces instant rejection.** `conversation.BoundedGate` keeps one active turn and at most three waiting turns, each waiting up to 45 seconds. A fourth waiting request, or a wait past the timeout, is refused with a message naming the limit rather than joining an unbounded queue. `Workspace.chat` creates its conversation engine once under a lock, so two first requests cannot create two engines and two effective locks.

**A turn can be stopped at a stage boundary and says what that means.** Every request carries a client-generated `request_id` (a UUID the client supplies, so the stop control knows what to name). The engine records the current stage and checks for cancellation:
- after the conversation state is loaded,
- after planning,
- between dispatched tasks,
- before the answer is finalised.

A cancelled turn returns `status: cancelled` with a message naming the stage it stopped at; its facts, citations, passages and calculations are discarded and never saved as evidence, and the conversation history records that the turn was stopped. A stop that arrives after the turn finished returns `state: not_running` with a truthful detail instead of claiming a cancel.

**The interface stops the server, not just the page.** The stop control marks the turn, posts `POST /api/chat/cancel` with the request id, aborts the page fetch, and reports the server's own response: `cancel_requested` with the stage, `not_running` if the turn had already finished, or an explicit failure if the stop could not reach the workspace. The old notice claiming that stopping the page does not cancel server work is gone; the remaining variant is only for a direct abort where no stop was requested.

## Recorded acceptance evidence

[research/implementation/queue-cancel-20260915](../research/implementation/queue-cancel-20260915/), local HTTP on this machine with the local Ollama planner:

| Check | Observed |
|---|---|
| Stop while a turn is planning | `POST /api/chat/cancel` → `cancel_requested` at stage `started`; the turn returned `status: cancelled` at the `planned` checkpoint with no facts, after 24.8 s — the time the planner took to finish the stage that was already in flight |
| Stop after completion | second cancel → `not_running`, with the detail that nothing of the turn was kept back |
| Two concurrent questions | first answered in 6.6 s, second waited and answered in 13.5 s; neither was rejected instantly |

**598 Python tests pass** (from 591), including seven new checks: queue capacity rejection, the wait timeout, a running turn cancelled at its next boundary with partial work discarded, a stop after completion reported as not running, invalid request ids refused, and the workspace cancel route's validation. All five JavaScript component suites pass, including the updated stop check that now asserts the stop names the request id, reports the server response, and states that partial work is discarded.

## What this does not establish

- **Cancellation is not pre-emptive.** It is checked at stage boundaries; an Ollama inference already in flight runs to completion before the stop takes effect. The 24.8-second journey is exactly that limit, and it is recorded rather than hidden.
- **No queue-position or stage streaming.** A waiting question is not told where it is, and a running question does not stream progress. P11 keeps the streaming half open.
- **No capacity measurement.** Two concurrent journeys are not a load test, a p95, or a service-level claim. Local one-machine behaviour is all that was observed.
- **No multi-user or hosted behaviour.** The surface remains loopback-only and desktop-only, and hosting stays on hold.
