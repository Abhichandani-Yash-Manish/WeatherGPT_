# Feature 4 Implementation Plan — Dissemination Build

Prepared 16 September 2026. Mapped 1:1 to gap register G-F4-01…G-F4-17 in `feature4-gap-report-current-vs-ideal.md`.

---

## Scope

Implement D4 (change detection + outbox + delivery state), D5 (web push), and D7 (acknowledgements) into the existing codebase. Every phase is independently testable. Official-source integrity is preserved throughout: LLM never alters warning facts, CAP lifecycle never authorises dissemination, quiet days are never all-clears, and no fake government integrations are introduced.

---

## Prerequisite — P0: Windows toolchain fix

**Gap item:** G-F4-17

**What:** Guard bare `import fcntl` in three modules (POSIX-only; crashes on Windows). Install missing `shapely` and `pytest`.

**Files to modify:**
- `weathergpt_data/evidence_transport.py:2` — `import fcntl,urllib.request,urllib.error,time` → guard with `try/except ImportError`, fallback to `msvcrt.locking` (Windows) or no-op (single-process)
- `weathergpt_data/transport.py:62` — same pattern; already partially guarded but bare import still present
- No other F4 files need it (ingestion.py and airport_tools.py have the same issue but are not F4-critical paths)

**Approach:** Create a shared `weathergpt_data/filelock.py` utility that provides `flock(path, exclusive)` as a context manager, using `fcntl.flock` on POSIX and `msvcrt.locking` on Windows. All three files import from this single module.

**Dependency installs:**
- `pip install shapely==2.0.7 pytest` (both already in requirements files but not installed on this machine)

**Tests (after):**
- All 66 F4 tests run with 0 failures and 0 errors (currently 3×PermissionError + 3×ModuleNotFoundError)
- `python -m unittest discover -s tests -p "test_*.py"` passes with no F4-related failures
- Verify `filelock.py` works on Windows: concurrent writes to temp file from two threads

---

## Implementation Phase 1 — Watch schema + fingerprint + outbox (D4 core)

**Gap items:** G-F4-01, G-F4-04, G-F4-15

### 1A: Watch schema migration

**What:** Extend `watches` table with columns needed for change detection, delivery channels, and consent. Backward-compatible migration (ALTER TABLE ADD COLUMN IF NOT EXISTS pattern, already used in other SQLite stores in this codebase).

**New columns on `watches` table:**
| Column | Type | Purpose |
|---|---|---|
| `fingerprint_sha256` | TEXT | SHA-256 of the current official state that matters to this watch |
| `channels` | TEXT (JSON array) | Delivery channels: `["local_inbox"]` initially, extensible to `["local_inbox","web_push"]` |
| `consent` | TEXT (JSON) | Per-channel consent record: `{"local_inbox": {"granted_at": "...", "source": "explicit_chat_request"}}` |

**Migration code:** `WatchStore._migrate(db)` called in `__init__`, uses `PRAGMA table_info(watches)` to check existing columns before ALTERing.

### 1B: Outbox table + delivery state machine

**What:** New SQLite table `outbox` in the same watches.sqlite database, plus a `notification_ledger` table for delivery history.

**`outbox` table:**
| Column | Type | Purpose |
|---|---|---|
| `id` | TEXT PK | UUID |
| `watch_id` | TEXT FK | References watches.id |
| `correlation_id` | TEXT | Ties a check cycle to its notification (for E2E tracing) |
| `fingerprint_sha256` | TEXT | The fingerprint that triggered this notification |
| `state` | TEXT | `created` → `queued` → `sent` → `acked` or `failed` → `dead` |
| `payload` | TEXT (JSON) | Notification content: hazard, place, official facts, timestamp, limitations |
| `channel` | TEXT | `local_inbox` (initially) |
| `created_at` | TEXT | ISO-8601 |
| `updated_at` | TEXT | ISO-8601 |
| `retry_count` | INTEGER | 0 initially; incremented on failure |
| `max_retries` | INTEGER | 3 (bounded; no uncontrolled loops) |
| `next_retry_at` | TEXT | ISO-8601; set on failure with backoff |
| `last_error` | TEXT | Last failure reason |

**`notification_ledger` table:**
| Column | Type | Purpose |
|---|---|---|
| `id` | TEXT PK | UUID |
| `outbox_id` | TEXT FK | References outbox.id |
| `event` | TEXT | `queued`, `sent`, `acked`, `failed`, `dead` |
| `timestamp` | TEXT | ISO-8601 |
| `detail` | TEXT (JSON) | Event-specific payload |

**Delivery state machine:**
```
created → queued → sent → acked
                    ↘ failed → (retry_count < max_retries) → queued
                              → (retry_count >= max_retries) → dead
```
States `created` and `dead` are terminal for a given notification. No notification is sent from `dead`.

### 1C: Fingerprint function

**What:** Deterministic SHA-256 of the official state that matters to this watch. Used for change detection: if the fingerprint of the current state differs from the stored fingerprint, a new notification is warranted.

**Fingerprint inputs (concatenated, then SHA-256):**
- Watch ID
- Hazard type
- Resolved place name + state
- Sorted list of `(district_label, day_index, colour_code, sorted_hazard_codes, quiet)` tuples from current official day rows
- Bulletin date (from warning_records)
- CAP lifecycle eligible count (integer; never the records themselves)

**Why these inputs:** The fingerprint captures what actually changed in the official products that matter to this watch. A colour code change, a new hazard code, or a CAP lifecycle count change all produce a different fingerprint. A quiet→quiet same-day doesn't change.

**Code location:** `weathergpt_data/watches.py` — new function `compute_fingerprint(watch_id, hazard, place, day_rows, bulletin_date, cap_eligible_count)`

### 1D: Integration into check flow

**Modify `check_watch()`** in `watches.py`:
1. After `execute_warning()` returns, compute the fingerprint from the day_rows and CAP state
2. Load the watch's stored `fingerprint_sha256`
3. If no stored fingerprint (new watch): store the fingerprint, do NOT enqueue (first check is baseline)
4. If stored fingerprint differs: enqueue outbox notification, update stored fingerprint
5. If stored fingerprint matches: no notification (dedup)

**Modify `WatchStore.create()`:** New watch starts with `fingerprint_sha256 = None` (baseline established on first check).

### 1E: API changes

**Extend `/api/watches` response:**
- Add `outbox_pending` count per watch
- Add `last_notification_at` per watch

**New route: `/api/outbox`:**
- GET: list outbox items for all watches, with state and payload summary
- Filter by `?state=sent` or `?state=acked` etc.

**New route: `/api/outbox/<id>/ack`:**
- POST: mark a notification as acked, record the feedback (safe/need_help/evacuating)
- Body: `{"response": "safe"}` or `{"response": "need_help"}` etc.

### 1F: Frontend changes

**`web/shell.js` — wireNotify():**
- Extend the watch inbox table to show delivery state and outbox status
- Add "Mark seen" button per notification in outbox
- Update the check result display to show fingerprint change / no change

**`web/index.html`:**
- Add `#outbox-panel` section alongside existing `#notify-panel`

### Tests for Phase 1:
1. `test_watches.py` — schema migration on empty DB, migration on existing DB with old schema
2. `test_watches.py` — fingerprint determinism (same inputs → same hash), sensitivity (one changed day → different hash), None inputs handled
3. `test_watches.py` — outbox state machine: all transitions, dead state stops retry
4. `test_watches.py` — check_watch: new watch stores baseline, same state no enqueue, changed state enqueues
5. `test_watches.py` — ledger records all state transitions
6. `test_watches.py` — API routes return correct payloads

**Deviation note:** No webhook, email, or government push integration. `local_inbox` is the only connected channel. Web push is Phase 4.

---

## Implementation Phase 2 — Scheduled evaluation + dispatch (D4 completion)

**Gap items:** G-F4-02, G-F4-15 (dispatch side)

### 2A: Outbox dispatch

**What:** Process queued outbox items through their connected channels. For `local_inbox`, this means the notification is ready to display in the inbox panel. For `web_push` (Phase 4), it means sending a push message.

**Code location:** New function `dispatch_outbox(store)` in `watches.py`. For each `queued` item whose `next_retry_at <= now`:
1. Mark as `sent` (for local_inbox, display is immediate)
2. Record in ledger
3. If channel is `web_push`, call push notification sender (stub in Phase 2, real in Phase 4)

### 2B: Background check scheduler

**What:** A bounded, foreground, configurable interval check that can be invoked by the daily cycle runner or by a simple `while True; sleep` loop in development.

**Implementation:** Extend `scripts/check_watches.py` to also run `dispatch_outbox()` after the check cycle. This keeps the "manual trigger now, scheduler later" decision documented while giving a functional dispatch path.

**Modify `run_daily_cycle.py`:** The existing `watch check` step now also dispatches outbox.

**New optional script: `scripts/watch_daemon.py`:**
- Foreground loop: check watches every N minutes (configurable via `--interval`), dispatch outbox
- Logs each cycle summary to stdout (JSON)
- No background thread, no signal handling — a simple bounded loop for development
- Documented as "development convenience, not a production daemon"

### 2C: Delete watch route

**New route: DELETE `/api/watches/<id>`:**
- Archive the watch (set state to `expired`), cancel all queued outbox items for it
- Ledger records the deletion

### Tests for Phase 2:
1. `test_watches.py` — dispatch_outbox: queued items become sent, dead items are skipped
2. `test_watches.py` — check cycle + dispatch end-to-end: register watch → check → change detected → outbox queued → dispatch → sent
3. `test_watches.py` — delete watch cancels pending outbox
4. `test_watches.py` — dedup: same check twice → only one outbox entry

---

## Implementation Phase 3 — Web push (D5)

**Gap items:** G-F4-03

### 3A: VAPID key store + subscription store

**New file: `weathergpt_data/push.py`:**
- VAPID key pair generation (using `py_vapid` or manual ECDSA)
- Key storage: `data/runtime/ingestion/push-vapid.json` (gitignored; under `data/runtime/`)
- Subscription store: new table `push_subscriptions` in `watches.sqlite`

**`push_subscriptions` table:**
| Column | Type | Purpose |
|---|---|---|
| `id` | TEXT PK | UUID |
| `endpoint` | TEXT | Push service URL |
| `p256dh` | TEXT | Client public key |
| `auth` | TEXT | Client auth secret |
| `created_at` | TEXT | ISO-8601 |
| `expires_at` | TEXT | ISO-8601; from subscription expiration |
| `watch_id` | TEXT | Optional: bound to a specific watch |
| `state` | TEXT | `active`, `expired`, `revoked` |

### 3B: Push sending

**New dependency:** `pywebpush` (add to `requirements.txt`) — handles VAPID signing + encrypted push delivery.

**In `dispatch_outbox()`:** When channel is `web_push`, use `pywebpush.webpush()` to send to each active subscription. Handle:
- `201 Created` → mark sent
- `410 Gone` → mark subscription expired, remove from active pool
- Other errors → mark failed, retry with backoff

### 3C: API routes

**New routes in `workspace.py` make_server:**
- `GET /api/push/vapid-key` — returns public VAPID key (safe for client)
- `POST /api/push/subscribe` — stores push subscription, returns success
- `POST /api/push/unsubscribe` — revokes subscription
- `GET /api/push/state` — subscription count, active/expired counts

### 3D: Service worker + frontend

**New file: `web/sw.js`:**
- Service worker: listens for `push` event, shows `self.registration.showNotification()`
- Click on notification opens/focuses the workspace tab

**Modify `web/index.html`:**
- Add `<script>` block that on page load:
  1. Checks `Notification.permission`
  2. If not `granted`, requests permission on user action (button click in notify panel)
  3. Registers service worker (`/sw.js`)
  4. Subscribes to push via `/api/push/subscribe`
  5. Stores subscription endpoint locally for status display

**Modify `web/shell.js` — wireNotify():**
- Add "Enable notifications" button when permission not granted
- Show subscription status (active/expired/none)
- Show push delivery status in outbox items

### Tests for Phase 3:
1. `test_push.py` — VAPID key generation produces valid ECDSA pair
2. `test_push.py` — subscription CRUD: create, list, expire, revoke
3. `test_push.py` — 410 handling marks subscription expired
4. Manual: register → grant permission → receive push → click opens workspace

**Dependencies added:** `pywebpush` (only new dependency)

---

## Implementation Phase 4 — Acknowledgements + delivery state machine (D7)

**Gap items:** G-F4-05, G-F4-06

### 4A: Acknowledge endpoint

**Modify `/api/outbox/<id>/ack`:**
- Accepts: `{"response": "safe"}` | `{"response": "need_help"}` | `{"response": "evacuating"}` | `{"response": "seen"}`
- Transitions outbox state: `sent` → `acked`
- Records feedback in `notification_ledger`

**New table `watch_feedback`:**
| Column | Type | Purpose |
|---|---|---|
| `id` | TEXT PK | UUID |
| `watch_id` | TEXT FK | References watches.id |
| `outbox_id` | TEXT FK | References outbox.id |
| `response` | TEXT | `safe`, `need_help`, `evacuating`, `seen` |
| `timestamp` | TEXT | ISO-8601 |
| `channel` | TEXT | Channel through which ack was received |

### 4B: Escalation ladder

**What:** If a notification is `sent` but not `acked` after a configurable timeout (default: 30 minutes), escalate to the next channel.

**Escalation chain (local prototype):**
```
web_push (30 min) → local_inbox visual alert (60 min) → [SMS/IVR deferred: G-F4-16]
```

**Implementation in `dispatch_outbox()`:**
- After dispatching a `web_push` item, check if `sent_at + escalation_timeout < now` and state is still `sent`
- If so, create a new outbox entry with channel `local_inbox` and a higher-priority payload
- Max escalation depth: 2 (no infinite chain)
- SMS/IVR channels: register stubs that log "channel not connected" and mark as `deferred`

### 4C: DMA aggregate

**New route: GET /api/watches/dma`:**
- Returns per-district aggregate: how many active watches, how many notifications sent, how many acked, how many `need_help`/`evacuating`
- Computed from watch_feedback + outbox + watches tables

### 4D: Frontend ack flow

**Modify `web/shell.js`:**
- For each `sent` outbox item, show response buttons: "Safe", "Need help", "Evacuating"
- POST to `/api/outbox/<id>/ack` on click
- Update display to show acked state

### Tests for Phase 4:
1. `test_watches.py` — ack transitions sent → acked, records feedback
2. `test_watches.py` — escalation: sent + timeout → new outbox entry
3. `test_watches.py` — escalation depth limit: no chain beyond 2
4. `test_watches.py` — DMA aggregate: correct counts per district
5. `test_watches.py` — ack via local_inbox button works end-to-end

---

## Implementation Phase 5 — Integration + E2E testing

**This is Phase 5 of the overall process. No code changes; testing only.**

### E2E scenarios to verify:

| Scenario | Expected behaviour | Verified by |
|---|---|---|
| **New warning** for a watched place+haazard | Exactly one outbox notification, correct hazard/place/facts | Manual + automated |
| **Duplicate** official state (same fingerprint) | No new notification (dedup) | Automated |
| **Updated** official state (changed colour/hazard) | Exactly one new notification on state change | Manual + automated |
| **Cancelled** CAP message | Notification with "official warning no longer published" (not all-clear) | Manual + automated |
| **Expired** watch window | State → expired, no re-notification, no outbox dispatch | Automated |
| **Delivery failure** (mock push failure) | Retry with backoff, dead after max_retries, no uncontrolled loop | Automated |
| **Ack flow** | sent → acked via button, feedback recorded, DMA updated | Automated |
| **Escalation** | sent but not acked → escalation to next channel after timeout | Automated |
| **Schema migration** | Existing watch DB upgraded without data loss | Automated |
| **Fingerprint determinism** | Same official state → same hash across runs | Automated |
| **No regressions** | All existing 627 tests still pass | Automated |

### Test approach:
- All automated tests use `unittest.TestCase` (existing pattern)
- F4-specific tests run via: `python -m unittest tests.test_watches tests.test_cap_lifecycle tests.test_district_warnings tests.test_push tests.test_outbox`
- Full suite via: `python -m unittest discover -s tests -p "test_*.py"`
- Manual tests documented in `research-feature4/e2e-manual-test-log.md`

---

## Gap item mapping

| Gap | Phase | Status |
|---|---|---|
| G-F4-01 (fingerprint/outbox/change-detection) | Phase 1 + 2 | Implementing |
| G-F4-02 (background/scheduled eval) | Phase 2 | Implementing |
| G-F4-03 (web push/VAPID/service worker) | Phase 3 | Implementing |
| G-F4-04 (delivery state machine/ledger) | Phase 1 | Implementing |
| G-F4-05 (escalation ladder) | Phase 4 | Implementing |
| G-F4-06 (two-way feedback) | Phase 4 | Implementing |
| G-F4-07 (role-aware NLG) | — | Deferred (needs model work) |
| G-F4-08 (CAP geographic applicability) | — | Deferred (needs PIP on CAP polygons) |
| G-F4-09 (district alias crosswalk) | — | Deferred (80.8% today; gazetteer covers rest) |
| G-F4-10 (nowcast wiring) | — | Deferred (unwired product) |
| G-F4-11 (marine/cyclone relays) | — | Deferred (unwired products) |
| G-F4-12 (multi-agency dedupe) | — | Deferred (L2 priority) |
| G-F4-13 (origin authentication) | — | Deferred (needs IMD API access) |
| G-F4-14 (live update/cancel/supersede) | Phase 5 | Verified via existing cap_lifecycle.resolve() |
| G-F4-15 (watch schema diverges) | Phase 1 | Implementing |
| G-F4-16 (SMS/IVR/WhatsApp) | Phase 4 | Stubs only; correctly deferred |
| G-F4-17 (Windows toolchain) | P0 | Implementing |

---

## Files to create

| File | Purpose |
|---|---|
| `weathergpt_data/filelock.py` | Cross-platform file locking (fcntl/msvcrt) |
| `weathergpt_data/outbox.py` | Outbox store, delivery state machine, dispatch |
| `weathergpt_data/push.py` | VAPID keys, push subscriptions, push sending |
| `web/sw.js` | Service worker for push notifications |
| `tests/test_outbox.py` | Outbox + fingerprint + dispatch tests |
| `tests/test_push.py` | VAPID + subscription + push tests |
| `research-feature4/e2e-manual-test-log.md` | Manual E2E test log |

## Files to modify

| File | Change |
|---|---|
| `weathergpt_data/evidence_transport.py` | Guard fcntl import |
| `weathergpt_data/transport.py` | Guard fcntl import |
| `weathergpt_data/watches.py` | Schema migration, fingerprint, outbox integration, delete route |
| `weathergpt_data/conversation.py` | Register consent on watch creation |
| `weathergpt_data/workspace.py` | New routes (/api/outbox, /api/push/*, /api/watches/dma) |
| `web/shell.js` | Outbox display, ack buttons, push enable button |
| `web/index.html` | Outbox panel, push permission UI |
| `requirements.txt` | Add pywebpush |
| `scripts/check_watches.py` | Also dispatch outbox |
| `scripts/run_daily_cycle.py` | Watch check step includes dispatch |
| `docs/29-extreme-weather-alert-feature-report.md` | Update implementation status |
| `data/registry/product-progress.json` | Update S4/S5 status |
| `data/registry/hardening-progress.json` | Update watch_requests_batch |

---

## What is NOT in scope

- **Government/external integrations**: No SMS, IVR, WhatsApp, or official push service connections. Stubs log intent only.
- **Flood/cyclone/heat/cold products**: Still `hazard_not_connected`. No fake mapping onto district warning.
- **CAP geographic applicability PIP**: Deferred. CAP lifecycle eligibility remains "unverified" and never authorises dissemination.
- **District alias crosswalk**: Deferred. Gazetteer fuzzy match covers the gap.
- **Role-aware NLG**: Deferred. Requires model fine-tuning or template expansion.
- **Production hosting/sharing**: Explicitly on hold per product decision.
