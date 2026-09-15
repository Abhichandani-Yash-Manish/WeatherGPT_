# Feature 4 E2E Test Log — Dissemination Build

Dated 16 September 2026. Phase 5 of the implementation process.

## Automated E2E (all passing)

File: `tests/test_feature4_e2e.py` — 4 tests, all passing.

| Scenario | How verified | Result |
|---|---|---|
| New warning → exactly one notification | register (quiet baseline) → changed facts → `check_watch` enqueues 1 row, `dispatch_outbox` marks sent | PASS |
| Duplicate official state → no duplicate | repeat check with identical facts → no new row, dispatch returns [] | PASS |
| Updated state → notify only on change | new hazard code → exactly one more row, different id | PASS |
| Withdrawn warning → notify, never all-clear | quiet again → new row, payload limitations contain all-clear wording, `matched=false` | PASS |
| Expired window → silent end | check past `window_end` → state expired, no new row | PASS |
| One check run, one correlation id | `check_due` over 2 watches → both rows share the run id | PASS |
| Delivery failure → bounded retry → dead | unknown channel → failed with backoff → dead after MAX_RETRIES; no further dispatch | PASS |
| Unacked sent → escalation, depth-bounded | sent + 2h → 1 local-inbox follow-up (depth 1) → follow-up escalates once (depth 2) → chain stops | PASS |

Full F4 file set: **119 passed** (`test_outbox` 33, `test_push` 16, `test_feature4_e2e` 4,
`test_watches` 10, `test_cap_lifecycle` 9, `test_district_warnings` 23,
`test_place_typos_and_coasts` 8, `test_advisory_place_resolution` 8,
`test_alert_brief` 8).

## CLI E2E against the real workspace (passing, no server)

- `python scripts/check_watches.py --json` → schema `watch-check-run-v1`, checked 0
  (no watches registered), dispatched [], escalated []. Exit 0.
- `python scripts/watch_daemon.py --cycles 1 --interval 60` → one cycle summary,
  exit 0. Dispatch + escalation wiring executes without errors.

## Live-server route checks — DEFERRED (environment)

Booting `python -m weathergpt_data.workspace` on this machine does not serve:
the local prototype requires Ollama configuration that is not present here,
so no HTTP route could be exercised live. The following must be run where the
workspace serves (loopback, token from `/` meta tag):

1. `GET /api/watches` → `watch-inbox-v1` with `outbox_pending` per watch.
2. `GET /api/outbox` → `outbox-v1` rows; `?state=sent` filter.
3. `GET /api/push/vapid-key` → `push-vapid-v1`, 87-char public key.
4. `GET /api/push/state` → `push-state-v1` counts.
5. `GET /api/watches/dma` → `watch-dma-v1` districts.
6. `POST /api/watches/check {}` → results + `dispatched` + `escalated`.
7. `POST /api/push/subscribe` with a real browser subscription → subscribed.
8. Browser: enable notifications → grant permission → receive a push on the next
   state change → tap opens the workspace.
9. `POST /api/outbox/<id>/ack {"response":"safe"}` → `outbox-ack-v1`.
10. `POST /api/watches/delete {"id":...}` → watch expired, pending cancelled.

Route handlers are covered at the method level by `WorkspaceRouteTests`,
`test_outbox.py::DMATests`, and the ack/escalation suites; only the HTTP
transport layer above awaits a serving workspace.

## No-regression statement

- Every test file touching modified modules passes: all F4 files listed above.
- Broader suite (`pytest tests/`, 626 passed): the 239 failures + 107 errors are
  pre-existing environment issues, not regressions — verified by (a) failure
  text (`'unavailable' != expected`: no live model backend; `WinError 32` on
  `conversation.sqlite` teardown in stores this batch did not touch;
  `cp1252` collection error in `test_acceptance_benchmark.py`), and (b) a stash
  check proving the pre-change tree cannot even be collected on Windows
  (32 collection errors from bare `import fcntl`), so no narrower baseline exists.
- No test outside the new F4 files references the changed response shapes
  (only `test_corpus_tools.py:403` matched, on `task_dispatch.execute_plan`,
  unrelated).
