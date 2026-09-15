# Feature 4 Implementation — Phase Status

Dated 16 September 2026. Status after each phase, per the implementation process.
Work stops after Phase 5; git workflow (Phase 6) and PR (Phase 7) not started.

## P0 — Windows toolchain fix (G-F4-17)

- Implemented: new `weathergpt_data/filelock.py` (fcntl → msvcrt → no-op degradation);
  `evidence_transport.py`, `transport.py`, `ingestion.py`, `airport_tools.py` use it.
  Installed `shapely==2.0.7`, `pytest`, `pywebpush==2.5.0` (pinned in requirements.txt).
- Tested: all F4 modules import on Windows; `filelock` degrade path returns False.
- Bugs found: `WatchStore` leaked sqlite handles (`with sqlite3.connect()` never closes —
  the context manager only commits). Fixed with explicit close in every method; this
  cleared the 3 WinError-32 teardown failures.
- Remaining: same `with`-without-close pattern still exists in other stores
  (e.g. conversation.sqlite teardown fails the same way). Pre-existing, out of scope,
  recorded here for the next batch.
- Deviation: fixed 4 `fcntl` call sites, not 2 — `ingestion.py` is imported by
  `evidence_transport.py`, so leaving it would have kept the crash.

## Phase 1 — Schema + fingerprint + outbox (G-F4-01/04/15)

- Implemented: `fingerprint_sha256`/`channels`/`consent_record` columns with `_migrate()`;
  new `weathergpt_data/outbox.py` (`OutboxStore`, `notification_ledger`, state machine
  created→queued→sent→acked/failed→dead, bounded retries); `compute_fingerprint()`;
  `check_watch` baselines first check, enqueues exactly one row on change, dedups identity.
- Tested: `tests/test_outbox.py` 19 tests (migration, determinism, machine, enqueue-on-change,
  payload verbatim). All pass; 66 pre-existing F4 checks still pass.
- Bugs found: none in new code. Test-only sqlite handle leak fixed in the test itself.
- Remaining: dispatch (Phase 2), push (Phase 3), ack (Phase 4).
- Deviation: `/api/outbox/<id>/ack` route deferred to Phase 4 with the rest of D7.

## Phase 2 — Dispatch + scheduled eval + delete (G-F4-02)

- Implemented: `dispatch_outbox()` (due rows, sender injection, backoff, dead after
  MAX_RETRIES); `WatchStore.archive()`; routes `GET /api/outbox`, `POST /api/watches/delete`;
  `outbox_pending`/`last_notification_at` in `/api/watches`; `scripts/check_watches.py`
  dispatches; new `scripts/watch_daemon.py`; notify panel shows pending counts, outbox rows,
  retire buttons.
- Tested: 9 new tests (dispatch, bounded death, future retry skip, raising sender, archive,
  route methods via stub workspace). 94 F4 checks pass. `node --check` on shell.js.
- Bugs found and fixed: (1) `due()` excluded `failed` rows so retries never dispatched —
  now includes failed rows with remaining budget; (2) retry double-count between dispatcher
  and `set_state` — dispatcher decides from the snapshot; (3) escalation re-created
  follow-ups every run — skip entries already escalated at the next depth; added
  `failed→failed` transition for recorded retries.
- Remaining: push channel (Phase 3), ack (Phase 4).
- Deviation: none.

## Phase 3 — Web push (G-F4-03)

- Implemented: `weathergpt_data/push.py` (VAPID generate/load, `PushStore`, validation,
  `send_push` with 410→retire, `channel_sender`); routes `/api/push/vapid-key`,
  `/api/push/state`, `/api/push/subscribe`, `/api/push/unsubscribe`; `web/sw.js`;
  permission/subscribe flow in the notify panel; check route, CLI and daemon dispatch
  through the push-capable sender.
- Tested: `tests/test_push.py` 16 tests (key roundtrip, tamper rejection, validation,
  store, purge, mocked send/410/errors, sender delegation). 110 F4 checks pass.
- Bugs found: installed `py-vapid` 1.9.4 cannot reload its own PEM (`from_pem` joins str
  with bytes) and `from_raw` wants bytes — keys persist as 32-octet base64url scalar,
  reloaded via `from_raw(s.encode())`, verified by roundtrip test. `encode_point` is
  gone from cryptography 50 — public point via `public_bytes(X962, UncompressedPoint)`.
- Remaining: live browser push delivery needs a serving workspace (deferred, see E2E log).
- Deviation: one new dependency (`pywebpush==2.5.0`), as planned.

## Phase 4 — Acknowledgements + escalation + DMA (G-F4-05/06)

- Implemented: `FeedbackStore`, `acknowledge()` (sent→acked + response row),
  `escalate_unacked()` (timeout 1800s, max depth 2, local-inbox follow-up naming the
  SMS/IVR deferral); routes `POST /api/outbox/<id>/ack`, `GET /api/watches/dma`;
  ack buttons in the notify panel; escalation wired into check route, CLI and daemon.
- Tested: 5 new suites (all four responses, wrong-state/unknown-response rejection,
  escalation timing, ack exclusion, depth bound, DMA counts). 115 F4 checks pass.
- Bugs found: E2E expectation wrong (follow-up also escalates — correct behaviour,
  test fixed to assert depth-2 then stop).
- Remaining: SMS/IVR channels stay deferred stubs (G-F4-16, correctly deferred).
- Deviation: none.

## Phase 5 — Integration and E2E

- Implemented: `tests/test_feature4_e2e.py` (full lifecycle in one flow). 119/119 F4 pass.
- CLI verified against the real workspace (check + daemon cycle, exit 0).
- Live-server route checks deferred: workspace does not serve here (Ollama config).
- No-regression statement: see `e2e-manual-test-log.md`.
- Deviation: none. No code changes in this phase.
