# 66 — Plan Watch: alerts tied to what a person is planning, 15 September 2026

Status: **designed in a brainstorming session, first version implemented on 15 September 2026** (section 16).
It changes no finding status in any registry. It proposes how to close the delivery half of G11 (docs/44) using the dissemination
channel the user has now chosen: an in-app inbox plus browser notifications, text only.

## 1. The hook

> Tell WeatherGPT what you are planning. It keeps checking that plan against IMD's own products and tells
> you only when something about *your* plan changes — and shows which bulletin said so.

Sachet and the IMD apps tell everyone in an area the same thing. Plan Watch tells one person that the
official state for *their* place, *their* day and *their* activity changed, with the edition that changed
it. It covers PS feature 4 (alerts and dissemination), feature 5 (location-based advisories) and the farmer
use case in one journey, without inventing advice.

## 2. What it builds on

| Existing piece | Used for |
|---|---|
| `weathergpt_data/watches.py` (docs/38) | Store, hazard-code evaluation, no-all-clear wording, not-connected hazards |
| `weathergpt_data/warning_tools.py`, `district_warnings.py` (docs/27) | Place → district, IST day windows, colour levels validated against hazard tiers |
| `weathergpt_data/briefing_run.py` (docs/51) | "Changed / same / not comparable" reading against the previous record |
| `weathergpt_data/rule_planner.py` | Deterministic recognition of the plan statement and its slots |
| `weathergpt_data/dialogue.py` (`reconcile`, pending slots) | Carrying known slots across turns and applying later corrections to a saved plan |
| `renderChoices` in `web/views.js` | Quick-reply chips for the one missing slot, when a question is really needed |
| `weathergpt_data/briefcase.py`, `personas.py` | Save a notification as a brief; persona-specific templates |

As built, Plan Watch lives in its own modules (`plans.py`, `plan_watcher.py`, `plan_intake.py`) and its own
store (`plans.sqlite`). The earlier watch requests (`watches.py`, docs/38) keep their states, routes and tests and
are listed beside plans in the Watch panel as "Earlier watch requests".

## 3. The plan model

A plan is one record:

| Field | Example | Rule |
|---|---|---|
| `place` | Rajkot, Gujarat + resolved IMD district | Resolved by the warning tool's ladder; ambiguity becomes one quick-reply question, never a guess |
| `label` | "my cotton" | Frames notification wording only; never changes evaluation |
| `activity` | `spraying` | Inferred from the person's words; selects the hazards (section 4) |
| `hazards` | heavy rain, thunderstorm, strong wind | IMD category codes set by the template; the person can add or drop one in words |
| `when` | `once` Thu 17 Sep 09:30–12:30 IST, or `always` | `recurring` is reserved in the schema but not in the first version |
| `check_in` | on | Evening-before check-in; `once` plans only |
| `state` | `watching` | See section 7 |
| `inferred` | `{activity: "from 'fertiliser'", place: "from message"}` | Which slots were set automatically and from what, shown on request |
| `created_at`, `saved_at`, `last_checked_at`, `last_snapshot` | | `last_snapshot` holds the edition identity and per-day hazard state used for comparison |

A standing watch is an `always` plan. Dated and standing plans share one store, one watcher and one
notification path.

## 4. Activity templates

Templates choose **which official hazards are relevant to watch**. They never produce advice such as "do not
spray" and never a go/no-go.

| Activity | IMD hazard categories watched automatically |
|---|---|
| Spraying / fertiliser | Heavy rain (2, 16, 17), Thunderstorm & lightning (4), Strong surface winds (8) |
| Harvest / drying | Heavy rain (2, 16, 17), Thunderstorm (4), Hailstorm (5) |
| Irrigation | Heavy / very heavy / extremely heavy rain (2, 16, 17) |
| Outdoor event | Heavy rain (2, 16, 17), Thunderstorm (4), Heat wave (9), Dust storm (6) |
| Travel / commute | Fog (15), Heavy rain (2, 16, 17), Thunderstorm (4) |
| My home / village | All official categories 2–17 |
| Fishing trip | Offered but marked **not connected**: no official sea-area product is connected (G12) |

The templates need the full IMD category table (codes 1–17, docs/26), not only the three codes `watches.py`
maps today. As built, the names come from `adapters.HAZARDS` (IMD's own category table); per-code
"observed in the feed or not" labelling is not built. Flood and cyclone stay on the not-connected list and
are never mapped onto a similar product.

## 5. Setup in chat: infer everything, ask only what is really missing

There is no form. The agent builds the plan from what the person already said in the conversation, remembers
it, and asks a question **only when a slot the plan cannot work without is missing and cannot be inferred**.
Everything else is set automatically and shown in one short summary the person can change or undo.

### Slot rules

| Slot | Set automatically from | Asked only when |
|---|---|---|
| Notify intent | "tell me / let me know / remind me / notify / alert", Hindi and Gujarati equivalents (extends `WATCH_INTENT`) | Never. A plan described without intent gets a one-tap **Watch this plan** chip in the answer, not a question |
| Place | The message; otherwise the place already accepted in this conversation (the page's working place is not sent to the server) | None of these exists, or the name is ambiguous (the existing selection choice) |
| Day | "Monday", "kal", "18 Sep"; "always", "my farm", "my home" → `always` | A dated plan with no day at all ("I'll spray soon") |
| Time | "morning", "subah", "after 4 pm", "all day" | A dated activity plan with a day but no time — for example "spraying fertiliser on Monday". A dated hazard watch with no activity watches the whole day instead of asking |
| Activity | The person's words: spray, fertiliser/khad, harvest, irrigation, wedding/event, travel/commute | Never. Unrecognised activity → a general plan watching all official hazards |
| Hazards | The activity template (section 4) | Never. The person can add or drop one later in words ("also tell me about heat") |
| Label | The person's words: "my cotton", "the wedding" | Never |
| Evening-before check-in | On by default for dated plans | Never |

Question rules:

- **One question per turn**, in the order place → day → time. A typical plan needs zero or one question and
  never more than three.
- A question is offered as quick-reply chips plus free text, for example
  `[Morning] [Afternoon] [Evening] [All day]` or type a time. Parts of day use the single definition from
  `rule_planner.WINDOWS` (morning 09:30–12:30, afternoon 12:30–18:30, evening 18:30–22:30 IST).
- A weekday name means the next occurrence of that day, today included if its time has not passed. The summary
  always prints the resolved calendar date, so a wrong reading is caught without asking.

### Worked example

> **Person:** I'm going to spray fertiliser on my cotton in Rajkot on Monday, let me know if anything changes.
>
> **WeatherGPT:** What time on Monday? `[Morning] [Afternoon] [Evening] [All day]`
>
> **Person:** *taps Morning*
>
> **WeatherGPT:** Saved. I'm watching **Monday 21 Sep, morning (09:30–12:30 IST) in Rajkot, Gujarat** for your
> cotton spraying — IMD warnings for heavy rain, thunderstorm and strong wind. Official warnings for Monday
> become available on 17 Sep, and I'll message you the evening before. `[Change] [Undo]`

### Saving and remembering

- The plan is **saved as soon as the last needed slot is known**. The summary is the confirmation; **Undo**
  deletes it and **Change** accepts a correction in words. Nothing is saved while a needed question is still
  open.
- The plan is kept in the plan store and referenced from the conversation state, so later turns act on it:
  "make it Tuesday", "move it to the afternoon", "cancel the spraying reminder", "what plans do I have?".
  Corrections go through `dialogue.reconcile`, and the new summary is printed after every change.
- A related question surfaces the plan: asking "will it rain in Rajkot on Monday?" answers the question and
  adds "Monday morning is your cotton spraying plan."
- Browser notification permission is requested once, when the first plan is saved. If it is refused, plans
  still work through the in-app inbox and the summary says so.
- Notifications appear only while WeatherGPT is running, stated once in the first summary and in the Watch
  panel, not repeated on every plan.
- Plans can also be listed, paused and ended from the Watch panel.

## 6. The watcher

A server-side loop inside the workspace process (engine choice A from the session):

- One cycle every **30 minutes**. The IMD GeoServer path has a cache TTL but no request budget in
  `evidence_transport.py`; the 30-minute floor is this design's own politeness limit and must be recorded
  as such.
- Each cycle reads the **national** district warning attributes **once**, regardless of the number of plans,
  through the governed `Foundation`/`Store` path so every read is hashed and event-logged.
- For each active plan: resolve its district's day rows, keep only the days its `when` covers, intersect the
  day's hazard codes with the plan's hazards, and build a snapshot keyed by **bulletin edition identity**
  (bulletin time plus content hash).
- Compare with `last_snapshot` using the `briefing_run` reading: `changed`, `same`, or `not_comparable`.
  Only `changed` produces a change notification. `not_comparable` is never reported as a change.
- The loop runs only while the workspace runs. There is no daemon and none is claimed.

### Coverage before day 5

The district product covers five days from the bulletin date. A `once` plan further out is in
`waiting_for_coverage`, and the card says *"Official warnings for Thursday 24 Sep become available on 20 Sep."*
Watching starts automatically on the first edition whose five days include the plan day.

## 7. Plan states

```
collecting ─last needed slot─► saved ─► waiting_for_coverage ─► watching ⇄ changed
                                                          │
                                                   plan_day ─► ended
      any active state ─► degraded ─(next good read)─► previous state
      any state ─► paused ─► previous state        any state ─► deleted
```

`always` plans never reach `plan_day` or `ended`. **Undo** from `saved` deletes the plan outright.

## 8. Notifications (text only)

There are exactly three kinds. Silence never stands for "nothing changed".

| Kind | When | Example text |
|---|---|---|
| Change | The snapshot for a covered day changed, including a warning removed or downgraded | "Thursday for your cotton spraying in Rajkot changed: No warning → Thunderstorm & lightning (yellow). IMD district warning bulletin 16 Sep 11:30 IST. This is official product state, not an instruction." |
| Evening-before check-in | 19:00 IST the day before a `once` plan, if enabled | "Tomorrow's plan in Rajkot: no warning in this product for Thursday as of the IMD 16 Sep 11:30 bulletin. This is not an all-clear." |
| Watch degraded | No successful read for 3 hours, or the plan's district could not be resolved | "The IMD district warning layer could not be read for 3 hours. Your Rajkot plan is not being checked." |

Rules:

- **Deduplication key:** plan + day + hazard set + edition identity. A re-published identical edition does
  not notify.
- **Flip-flop:** snapshots are taken 30 minutes apart, so a hazard that appears and disappears inside one cycle
  is never observed and produces no message; no separate collapsing logic exists.
- **Quiet hours:** 22:00–06:00 IST, held to the inbox, except days at the orange or red level (colours 2 and
  1, validated in docs/27). Colour 0 is never read as a level.
- Every notification carries the evidence receipt (district, day window, hazard codes as published, colour,
  source id, bulletin and retrieval instants) and, for a change, **Ask about this change** (puts an official
  warning question for that place and date into the assistant). Plans are paused, resumed or deleted from the
  Watch panel. Save as brief and snooze are not built.
- Delivery surfaces: the in-app inbox in the Watch panel (the source of truth) and a browser
  `Notification` raised by the page, which polls `GET /api/plans` every 30 seconds. Notifications are never spoken.

## 9. Plan card

```
Cotton spraying · Rajkot, Gujarat · Thu 17 Sep 09:30–12:30 IST
 ● No warning in this product (IMD 16 Sep 11:30)     Evidence level: district warning, day 2
 Checked 9 min ago · check-in Wed 19:00 · [Ask] [Edit] [Pause] [End]
```

## 10. Replay mode for demonstrations

A live day may carry no warning anywhere near the demo place. Replay mode points the watcher at **two recorded
district-warning editions** from saved evidence instead of the live layer, so a real change can be shown end
to end: notification, receipt and "Ask about this change". Every surface shows *"Replay of recorded IMD
editions"* while it is on, replay plans are stored separately from live plans, and a replay result is never
written to the live inbox.

## 11. Persona fit

- **Farmer:** `once` activity plans (spraying, harvest, irrigation) are offered first.
- **District officer:** `always` plans over several districts. The first version sends per-plan notifications;
  a one-digest-per-edition view is later work.
- **Traveller:** `once` travel plans for one place. Two-place trips and route conditions are not supported.

## 12. First version and later work

| First version | Later |
|---|---|
| `once` and `always` plans | `recurring` plans |
| Six connected activity templates plus not-connected fishing | Nowcast and the right-now station reading on the plan day |
| Full IMD category table with observed/unobserved labels | Model-forecast limits on the day before, within the Open-Meteo budget (1,000 a month shared with chat) |
| District warning evidence, waiting-for-coverage state | Officer digest per edition |
| Change, check-in and degraded notifications; quiet hours; dedup; flip-flop | Traveller two-place plans |
| In-app inbox plus browser notification (page polling) | Delivery channels beyond this machine (needs a user decision and hosting) |
| Chat setup that infers every slot, asks only for a missing place, day or time, and saves with Undo | |
| Replay mode | |

Out of scope by decision: spoken notifications.

## 13. Prohibitions that stay in force

- No advice, no go/no-go, no "safe to" wording.
- No all-clear; a quiet day is a quiet day in one product.
- No colour level where the feed does not carry one; colour 0 is quarantined.
- Flood, cyclone and sea-area plans are recorded as not connected, never mapped onto another product.
- CAP relay state stays a separate source assessment and never triggers a plan notification on its own.
- Origin authentication remains unverified and is said so in the receipt.
- Delivery is claimed only while the workspace is running, only on this machine.

## 14. Acceptance checks for when it is built

- "Spray fertiliser on my cotton in Rajkot on Monday, let me know" asks exactly one question (time) and sets
  activity, hazards, label and check-in automatically.
- A fully specified plan statement asks no question and is saved with a summary showing the resolved date.
- Nothing is saved while a needed question is open; Undo deletes a saved plan.
- "Make it Tuesday" and "cancel the spraying reminder" change the saved plan and print the new state.
- A plan beyond day 5 shown as waiting, then watched automatically when coverage begins.
- A replayed edition pair producing exactly one change notification, and a re-published identical edition
  producing none.
- A removal or downgrade producing a change notification.
- A 3-hour read failure producing exactly one degraded notification, and recovery clearing it.
- Quiet hours holding a yellow change and releasing an orange change.
- An ambiguous place never producing a plan without a selection.
- A fishing, flood or cyclone plan recorded as not connected.
- Browser permission refused: the inbox still receives every notification.

## 15. What this design does not establish

- Section 16 records what was built and checked; it is not accepted by any user journey or browser run.
- It is not a dissemination service: nothing leaves this machine, and nothing runs while the workspace is closed.
- It does not resolve G11 origin authentication, G12 sea-area identity or source terms.
- No usability benefit is established; the activity templates are proposals that need farmer and officer review.

## 16. Implementation status — 15 September 2026

Plan: `docs/superpowers/plans/2026-09-15-plan-watch.md`. The implementation was committed in chronological slices after the repository was pulled from `origin/main`.

### What was built

| Piece | Where |
|---|---|
| Activity templates, hazard groups, notify intent, day/time parsing, readable place labels, the plan store | `weathergpt_data/plans.py` |
| Edition reading (live and recorded), snapshot, compare, change / check-in / degraded notifications, quiet hours, lifecycle, replay, the background watcher | `weathergpt_data/plan_watcher.py` |
| The chat turn: infer, ask one question, save with Undo, change, cancel, pause, resume, list, "Watch this plan", related-plan sentence | `weathergpt_data/plan_intake.py`, wired first in `ConversationEngine._ask` |
| `GET /api/plans`, `POST /api/plans/check`, `/api/plans/update`, `/api/plans/replay`; watcher started in `main()` (`--no-plan-watcher` to skip); `plans.sqlite` in state backups | `weathergpt_data/workspace.py`, `weathergpt_data/state_backup.py` |
| Recorder for replay editions | `scripts/capture_warning_edition.py` (writes `research/implementation/plan-watch-editions/`) |
| Quick-reply chips, saved-plan card with Change and Undo, Watch panel plans + notifications + receipts, check, replay, unread count, browser notifications | `web/views.js`, `web/app.js`, `web/shell.js`, `web/style.css` |

Two rules were settled while building: time is asked only for activity plans (a dated hazard watch watches the
whole day), and "make it Tuesday" moves a dated plan to the Tuesday nearest its current day, never a past one.

### Checked

- 50 new Python checks (`tests/test_plans.py`, `tests/test_plan_watcher.py`, `tests/test_plan_intake.py`) and two
  new component checks (`tests/test_views.js`, `tests/test_suite_ui.js`); every JS suite passes.
- Full Python suite on this Windows machine: the failing set is identical to the set recorded before the change
  (305 environment failures from POSIX-only locking and open SQLite handles on Windows); no new failure.
- Through the real engine, gazetteer and vendored district geometry: the fertiliser/Monday statement asked one
  time question, "Morning" saved it, "make it Thursday" moved it, a heavy-rain request for Patna became a standing
  plan, listing and cancelling worked.
- A live read of the IMD district warning attributes (755 districts, from WSL) produced covered snapshots for
  Rajkot and Patna and a baseline cycle with zero notifications. Real points resolve to IMD's own keys
  (Ahmedabad → AHMADABAD), so plans, the map and the warning table share one key space.

### Not established

- **The live read fails on this Windows Python** with a certificate-verification error for the IMD host; the
  plan reports that it could not read rather than calling the day quiet. Not investigated further.
- No real change between two IMD editions has been observed by the watcher; no editions are recorded yet, so
  replay cannot run until `scripts/capture_warning_edition.py` has captured two different editions.
- No browser run: quick replies, the card, polling and `Notification` were checked only against the DOM shim.
- English wording only; the question's language is stored for later localisation.
- No usability, farmer or officer review of the templates, and no measurement of missed or unnecessary alerts.

### Portability check — 15 September 2026

The macOS path was checked statically from this Windows checkout. `scripts/start_weather.py` uses
`pathlib`, `sys.executable` and the Python standard library; it does not invoke PowerShell, Windows paths or
Windows-only commands. The active locking code uses POSIX `fcntl`, which is provided by macOS. macOS execution
could not be performed on this host. The available checks passed `compileall`, `node tests/test_views.js` and
`node tests/test_suite_ui.js`. The focused Python plan tests could not be collected on Windows because this
interpreter has no `fcntl`; that is an environment limitation, not a macOS compatibility failure.
