# Plan Watch Implementation Plan

> **For agentic workers:** executed inline in the session that wrote it (the user asked for implementation
> followed by one report). Steps use checkbox (`- [ ]`) syntax for tracking. Commits are intentionally split
> chronologically so the implementation history remains reviewable.

**Goal:** Let a person describe a plan in chat, save it after asking only for genuinely missing slots, keep
checking it against the IMD district warning product while the workspace runs, and notify the person in the
app and through browser notifications only when the official state for that plan changes.

**Architecture:** A deterministic intake (`plan_intake.py`) runs before the model planner in
`ConversationEngine._ask` and owns plan statements, slot questions and plan management phrases. Plans and
notifications live in a local SQLite store (`plans.py`). A watcher (`plan_watcher.py`) reads the national
district warning attributes once per cycle, builds a per-plan snapshot keyed by edition identity, compares it
with the last snapshot, and writes change / check-in / degraded notifications. The workspace exposes
`/api/plans*` routes and starts the watcher thread in `main()`. The page renders quick-reply chips and a saved
plan card in the chat, lists plans and notifications in the Watch panel, polls the inbox and raises browser
notifications.

**Tech Stack:** Python 3 standard library (sqlite3, threading, zoneinfo), shapely (existing), vanilla JS with
the existing DOM helpers, `unittest`/pytest, Node component checks over `tests/dom_shim.js`.

## Global Constraints

- Design source: `docs/66-plan-watch.md`. Prohibitions in its section 13 are requirements.
- No advice, no go/no-go, no "safe to" wording; no all-clear; a quiet day is "no warning in this product".
- Colour is stated only for colour codes 1–3 (red, orange, yellow); code 4 is green/no warning; 0 or missing is
  "colour not supplied" and never a level.
- Flood, cyclone and fishing/sea-area plans are recorded as not connected and never mapped onto another product.
- Notifications are text only. Delivery is claimed only while the workspace runs, on this machine.
- Parts of day use `rule_planner.WINDOWS` (morning 09:30–12:30 IST, afternoon 12:30–18:30, evening
  18:30–22:30, night 21:30–23:30); a whole day is 00:30 to next-day 00:30 IST.
- One question per turn, order place → day → time; nothing is saved while a needed question is open.
- The watcher cycle is 30 minutes; degraded after 3 hours without a good read; check-in at 19:00 IST the day
  before a `once` plan; quiet hours 22:00–06:00 IST hold everything except orange and red.
- No test may reach the network, the model or the hosted language service.
- Existing watch behaviour, routes and tests (`watches.py`, `/api/watches`, `/api/watches/check`) stay intact.
- Do not commit or push.

## Deviations from docs/63 decided while reading the code

| docs/66 said | Implementation | Why |
|---|---|---|
| Upgrade `watches.py` in place, same store | New `plans.py` + `plans.sqlite`; legacy watches stay listed beside plans | Legacy watch states and tests are pinned; a separate table/module keeps both honest |
| Server-Sent Events stream | The page polls `GET /api/plans` every 30 s | `ThreadingHTTPServer` plus a token header that `EventSource` cannot send; polling is simpler and adequate locally |
| Morning 06:30–12:30 | 09:30–12:30 from `rule_planner.WINDOWS` | One definition per part of day already exists |
| Flip-flop within one cycle sent as one message | Not implemented separately | Snapshots are 30 minutes apart, so a flip inside one cycle is never observed; stated in the doc |
| Workspace working place as place fallback | Message, then the conversation's last resolved place, then ask | The working place lives only in the browser |
| Notification language from the plan | English templates in the first version; the question's language is stored | Localised plan templates are later work |

## File Structure

| File | Responsibility |
|---|---|
| Create `weathergpt_data/plans.py` | Activity templates, hazard groups, notify intent, day/time/activity parsing, window arithmetic, `PlanStore` (plans, notifications, meta) |
| Create `weathergpt_data/plan_watcher.py` | Edition sources (live, recorded), snapshot, compare, notification text, check-in, degraded, quiet hours, `run_cycle`, `baseline`, `PlanWatcher` thread |
| Create `weathergpt_data/plan_intake.py` | Turn handling: create/ask/answer slot, list, cancel, pause, resume, change, undo, "watch this plan"; summary text; packet shape |
| Modify `weathergpt_data/conversation.py` | Call intake first; plan hooks (`plan_store`, `resolve_plan_place`, `plan_baseline`); remember plan candidates |
| Modify `weathergpt_data/workspace.py` | `plan_store`, `plans`, `check_plans`, `update_plan`, `replay_plans`; routes; start watcher in `main()` |
| Modify `weathergpt_data/state_backup.py` | Include `plans.sqlite` |
| Create `scripts/capture_warning_edition.py` | Save the current national warning attributes edition as curated replay evidence |
| Modify `web/views.js`, `web/app.js` | Quick-reply chips, saved-plan card with Undo, hand-off of plan events |
| Modify `web/shell.js`, `web/style.css` | Watch panel plans + inbox, plan check, replay, polling, browser notifications |
| Create `tests/test_plans.py`, `tests/test_plan_watcher.py`, `tests/test_plan_intake.py` | Python checks |
| Modify `tests/test_suite_ui.js`, `tests/test_views.js` | Component checks |
| Modify `docs/66-plan-watch.md` | Record the deviations above |

---

### Task 1: Plan vocabulary, parsing and store (`plans.py`)

**Interfaces — Produces:**
- `ACTIVITIES: dict[str, dict]` keys `spraying, harvest, irrigation, outdoor_event, travel, fishing, home`;
  each `{'label', 'codes': list[int], 'pattern'}`; fishing has `'not_connected': str`.
- `HAZARD_GROUPS: list[tuple[str, set[int] | None, str]]` (name, codes or None for not connected, regex).
- `notify_intent(text) -> bool`
- `activity_of(text) -> str | None`, `label_of(text) -> str | None`
- `explicit_hazards(text) -> tuple[list[int], str | None]` → (codes, not-connected hazard name)
- `parse_day(text, now) -> dict | None` → `{'kind': 'once', 'date': 'YYYY-MM-DD', 'basis': str}` or
  `{'kind': 'always'}` or `{'kind': 'past', 'date': ...}`
- `parse_time(text) -> dict | None` → `{'start': 'HH:MM', 'end': 'HH:MM', 'next_day_end': bool, 'label': str}`
- `window_of(date_str, time_slot) -> (start_iso, end_iso)` IST ISO strings
- `class PlanStore(path)`: `create(fields) -> dict`, `get(id) -> dict`, `list(include_ended=True) -> list`,
  `update(id, **fields) -> dict`, `delete(id) -> bool`, `add_notification(plan_id, kind, dedupe_key, text,
  title, receipt, created_at, visible_at) -> int | None`, `notifications(limit=50) -> list`,
  `meta_get(key)`, `meta_set(key, value)`.

- [ ] **Step 1: Write failing tests** in `tests/test_plans.py` covering: notify intent positives
  ("let me know if anything changes", "remind me", "notify me if a heavy rain warning is issued", "keep an eye
  on my farm") and negatives ("tell me if it will rain in Surat tomorrow?", "Will it rain in Rajkot on Monday?");
  activity/label inference ("spray fertiliser on my cotton" → `spraying`, `cotton`); explicit hazards
  (flood → not connected; heat → 9,10,11); `parse_day` for Monday from Tuesday 15 Sep 2026 → 2026-09-21,
  "today", "tomorrow", "21 Sep", "always", past date; `parse_time` for morning, "all day", "4 pm", missing;
  `window_of`; store round trip, update, delete, notification dedupe returning `None` on a repeated key.
- [ ] **Step 2: Run** `python -m pytest tests/test_plans.py -q` → fails (module missing).
- [ ] **Step 3: Implement** `weathergpt_data/plans.py`.
- [ ] **Step 4: Run** the same command → all pass.

### Task 2: Watcher (`plan_watcher.py`)

**Interfaces — Consumes:** Task 1 store and window helpers; `product_api.warning_attributes`,
`product_api.decode_days`, `product_api.norm`, `adapters.HAZARDS`.
**Produces:**
- `rows_from_payload(data, meta) -> dict` → `{'edition': {...}, 'rows': {district_key: {'district', 'issued_at_utc', 'updated_at', 'days'}}}`
- `class LiveEditions(foundation)`, `class RecordedEditions(paths)`: `.read() -> edition dict` (raises `SourceError`)
- `snapshot(plan, edition, now) -> dict`
- `compare(previous, current) -> list[dict]` with `kind in {'issued','removed','changed'}`
- `run_cycle(store, source, now) -> dict` (`checked`, `notified`, `state`, `error`)
- `baseline(store, plan, source, now) -> dict | None`
- `class PlanWatcher(workspace, interval=1800)`: `.start()`, `.stop()`, `.status() -> dict`

- [ ] **Step 1: Write failing tests** in `tests/test_plan_watcher.py`: a plan 8 days out is
  `waiting_for_coverage`; a covered day with code 4 against a spraying plan yields matched codes and colour
  yellow; an unrelated code (15 fog) is not matched for spraying; baseline produces no notification; a new
  edition changing no warning → thunderstorm writes exactly one `change`; the identical edition again writes
  none; removal writes a `change` with "not an all-clear"; colour code 0 reads "colour not supplied"; check-in
  at 19:00 IST the day before is written once; three hours of failed reads writes one `degraded`, a good read
  restores state; quiet hours hold a yellow change until 06:00 IST and release an orange one immediately;
  a not-connected plan is skipped; a once plan past its window is `ended`; paused plans are skipped.
- [ ] **Step 2: Run** `python -m pytest tests/test_plan_watcher.py -q` → fails.
- [ ] **Step 3: Implement** `weathergpt_data/plan_watcher.py`.
- [ ] **Step 4: Run** → all pass.

### Task 3: Chat intake and engine wiring

**Interfaces — Consumes:** Tasks 1–2. Engine hooks on `ConversationEngine`: `plan_store()`,
`resolve_plan_place(place_dict) -> {'status': 'resolved'|'ambiguous'|'not_found'|'outside', ...}`,
`plan_baseline(plan) -> snapshot | None`.
**Produces:** `plan_intake.take_turn(engine, state, body, question, result) -> dict | None` returning a
conversation packet with `status`, `answer`, `quick_replies: [{'label','reply'}]`, `choices`,
`plan_watch: {'action', 'plan'?, 'plans'?}`; it mutates `state['plan_draft']`, `state['plan_focus']`.

- [ ] **Step 1: Write failing tests** in `tests/test_plan_intake.py` with a fake engine (fixed clock Tuesday
  15 Sep 2026 10:00 IST, in-memory resolver, stub baseline): the fertiliser/Monday statement asks exactly one
  time question with four quick replies and saves nothing; "Morning" saves a plan (spraying, codes
  [2,4,8,16,17], label cotton, check-in on, 2026-09-21 09:30–12:30) whose answer prints "Monday 21 Sep" and
  offers Undo; a fully specified statement saves with no question; an ambiguous place returns choices and a
  selection completes; "make it Tuesday" moves the focused plan; "cancel the spraying reminder" deletes it;
  "what plans do I have" lists; a flood request saves a not-connected plan and says so; an ordinary forecast
  question returns `None`; a new unrelated question while a draft is open drops the draft and returns `None`.
- [ ] **Step 2: Run** `python -m pytest tests/test_plan_intake.py -q` → fails.
- [ ] **Step 3: Implement** `plan_intake.py` and wire `conversation.py`.
- [ ] **Step 4: Run** the intake tests plus `tests/test_watches.py tests/test_conversation.py` → intake and
  watch tests pass; conversation results match the recorded baseline set.

### Task 4: Workspace routes, backup, watcher thread, capture script

- [ ] **Step 1: Write failing tests** (in `tests/test_plan_watcher.py`, `WorkspaceRouteTests`): `plans()`
  returns plans, notifications, legacy watch count and watcher status; `update_plan` pauses, resumes, ends and
  deletes and refuses unknown actions; `check_plans` runs one cycle through an injected source;
  `replay_plans` refuses fewer than two recorded editions and writes only to the replay store;
  `state_backup` lists `plans.sqlite`.
- [ ] **Step 2: Run** → fails.
- [ ] **Step 3: Implement** workspace methods and routes, `main()` watcher start, backup entry,
  `scripts/capture_warning_edition.py`.
- [ ] **Step 4: Run** → pass.

### Task 5: Page

- [ ] **Step 1: Extend component checks**: `tests/test_views.js` — a packet with `quick_replies` renders one
  button per reply and clicking sends the reply text; a `plan_watch.saved` packet renders the plan card with
  Undo calling `onPlanUndo`. `tests/test_suite_ui.js` — the Watch panel lists a plan and a notification from
  `/api/plans`, still reads legacy watches, and "Check plans now" calls `/api/plans/check`.
- [ ] **Step 2: Run** `node tests/test_views.js` and `node tests/test_suite_ui.js` → fail.
- [ ] **Step 3: Implement** `views.js`, `app.js`, `shell.js`, `style.css`.
- [ ] **Step 4: Run** both plus every other `tests/*.js` → pass.

### Task 6: Verification and documentation

- [ ] Run the full Python suite on this machine and compare failing IDs with the recorded baseline
  (`scratchpad/baseline-failing.txt`); every failure must be pre-existing.
- [ ] Run every JS suite.
- [x] Update `docs/66-plan-watch.md` with the deviations table and implementation status.
- [ ] Report to the user; do not commit.
