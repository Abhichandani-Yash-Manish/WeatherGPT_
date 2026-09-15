# Dissemination build: fingerprint outbox, web push, acknowledgements — 16 September 2026

> Historical branch record. Current integration, repaired behavior, verification limits and PS verdict are in [docs/73](73-dissemination-integration-review.md) and [docs/72](72-integrated-status-and-ps-review.md). Branch dates and self-scored percentages below are preserved history, not current acceptance.

[The gap register](31-full-solution-gap-register.md) recorded **G11** from docs/21 A05, whose
delivery half stayed open after [the watch-request batch](38-watch-requests.md) closed the request
half: watches were registered and checked on demand, but nothing could notify, nothing was
remembered between checks, and no channel existed. This batch builds the delivery half honestly:
a SHA-256 fingerprint of the observed official state, a transactional outbox with a bounded-retry
delivery machine, web push to the owner's browser, and two-way acknowledgements — with no fake
government integration, no invented warnings, and no all-clears.

Status: **implemented and tested through Phase 5 on branch
`feature/feature4-alert-dissemination`, PR #4 open awaiting Yash's review — not merged.**
Plan: `research-feature4/feature4-implementation-plan.md`. Per-phase status:
`research-feature4/phase-status.md`. E2E log: `research-feature4/e2e-manual-test-log.md`.

## What changed

- **P0 prerequisite.** New `weathergpt_data/filelock.py` (fcntl → msvcrt → documented no-op)
  replaces bare `import fcntl` in `evidence_transport.py`, `transport.py`, `ingestion.py` and
  `airport_tools.py`, so the warning path imports on Windows. `WatchStore` sqlite handles now
  close explicitly (the `with sqlite3.connect()` pattern only commits; it never closed, which
  locked temp databases on Windows teardown).
- **D4 core (G-F4-01/04/15).** The `watches` table gains `fingerprint_sha256`, `channels` and
  `consent_record` via `_migrate()` without data loss. New `weathergpt_data/outbox.py` holds the
  `outbox` table, the `notification_ledger` (every state move), and the delivery machine
  (`created → queued → sent → acked`, `failed` with backoff, terminal `dead`, `MAX_RETRIES = 3`).
  `compute_fingerprint()` hashes the structured official facts only — never rendered text — so an
  identical official state reproduces the hash exactly. `check_watch` stores a baseline on the
  first check and enqueues exactly one notification on a later change, nothing on identity.
- **D4 dispatch (G-F4-02).** `dispatch_outbox()` sends due rows through a per-channel sender
  (`local_inbox` inline; anything unconnected fails closed with bounded retry). `WatchStore.archive()`
  retires a watch and cancels its pending rows. New routes `GET /api/outbox` and
  `POST /api/watches/delete`; `/api/watches` rows carry `outbox_pending` and
  `last_notification_at`. `scripts/check_watches.py` dispatches after checking; new
  `scripts/watch_daemon.py` is the foreground check loop (manual trigger on repeat, still no daemon).
  The notify panel shows pending counts, outbox rows and per-watch Retire buttons.
- **D5 web push (G-F4-03).** New `weathergpt_data/push.py`: VAPID pair generated once into
  gitignored `push-vapid.json`, `push_subscriptions` bound per watch or unbound, 410/404 purges
  dead endpoints, push bodies carry outbox facts verbatim. Routes `GET /api/push/vapid-key|state`,
  `POST /api/push/subscribe|unsubscribe`; new `web/sw.js`; permission/subscribe flow in the panel.
  One new dependency: `pywebpush==2.5.0`.
- **D7 acknowledgements (G-F4-05/06).** `POST /api/outbox/<id>/ack` moves `sent → acked` with a
  recorded response (`safe`, `need_help`, `evacuating`, `seen`). `escalate_unacked()` follows up
  unacked rows in the local inbox after 30 minutes, at most 2 deep, naming the SMS/IVR deferral
  instead of pretending another channel delivered. `GET /api/watches/dma` aggregates per-place
  watches, notifications, acks and help signals. Ack buttons sit beside each sent row.
- **Surfaces.** All routes keep the loopback Host check, session token and CSP posture; the
  service worker is served same-origin at `/sw.js`.

## Recorded live evidence

[research/implementation/dissemination-20260916](../research/implementation/dissemination-20260916/),
local engine on this machine:

| Record | Ran | Observed |
|---|---|---|
| `check.json` | `python scripts/check_watches.py --json` against the real workspace | schema `watch-check-run-v1`, 0 watches registered, 0 enqueued, 0 dispatched, exit 0 |
| daemon cycle | `python scripts/watch_daemon.py --cycles 1` | one cycle summary, dispatch + escalation wiring live, exit 0 |
| `lifecycle.json` | `tests/test_feature4_e2e.py` (warning tool mocked at the boundary; store, fingerprint, outbox, dispatch, ack and escalation all real) | L1 new→one notice; L2 duplicate→none; L3 update→one more; L4 withdrawn→notice, never all-clear; L5 ack→expired silent; L6 one correlation id per run; L7 failure→dead bounded; L8 escalation depth 1→2→stop |

No live IMD journey with a real notification is recorded: no watch was registered against the
live feed on this machine, and the workspace does not serve here (Ollama configuration), so no
browser push was delivered. The route handlers are method-tested; the HTTP layer checklist sits in
the E2E log for a serving machine.

**119 F4 checks pass** (`test_outbox` 33, `test_push` 16, `test_feature4_e2e` 4, plus 66
pre-existing across `test_watches`, `test_cap_lifecycle`, `test_district_warnings`,
`test_place_typos_and_coasts`, `test_advisory_place_resolution`, `test_alert_brief`). After the
rebase onto `origin/main`, **173 pass** (119 F4 + 54 plan/warm suites) with both node UI suites
clean. No test reaches the network or the model.

## Registry and review trail

- `data/registry/product-progress.json`: S5 deliverable state records the build, its evidence
  and its open items.
- `data/registry/hardening-progress.json`: `watch_requests_batch` carries the
  `dissemination_build_20260916_unmerged` entry.
- `docs/29-extreme-weather-alert-feature-report.md`: dissemination-build revision section.
- Branch `feature/feature4-alert-dissemination` (commit `63e91eb`) rebased onto `origin/main`
  (`197bd25`); two conflicts resolved keeping both sides; suite re-run green after the rebase;
  pushed without force-push. **PR #4 is open and unmerged, awaiting Yash's review.**

## What this does not establish

- **No live delivery proven end to end.** The push path to a real browser and the HTTP route
  layer await a serving workspace; mocked-send tests and method tests stand in for them.
- **No SMS/IVR/WhatsApp.** Escalation beyond the local inbox is a named deferral (G-F4-16),
  never a silent drop and never a fake send.
- **No flood, cyclone, heat or cold coverage.** Those watches stay `hazard_not_connected`;
  the required source products are still missing.
- **No CAP applicability, origin authentication or all-clear change.** The relay is reported
  as before; lifecycle eligibility still never authorises dissemination.
- **No background daemon or scheduler.** Checks run on demand, from the CLI loop, or from the
  daily cycle step; sustained cadence is unmeasured.
- **Role-aware NLG, district alias crosswalk, nowcast and marine wiring are untouched** and
  remain in the gap register.
