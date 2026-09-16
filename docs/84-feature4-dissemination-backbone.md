# Feature 4 dissemination backbone: watches become subscriptions, the outbox becomes reliable

16 September 2026. The instruction that set this batch: close the Feature 4
dissemination gap — turn the warning engine from a request-driven lookup into
a continuously monitored, stateful, subscription-driven delivery system — and
do it by extending what already works, not by rebuilding it. Five phases,
each committed separately on `feature/feature4-alert-dissemination`.

## What was already true

The warning engine was solid and stayed untouched: governed S15/S06
ingestion, point-in-polygon district applicability with a gazetteer ladder,
CAP lifecycle resolution that never authorises dissemination, hazard-code
fidelity, IST day windows, verbatim Web Push bodies, and an inbox UI that
says what it cannot do. The audit put this at ~62%: a real prototype loop,
no production dissemination.

## What was missing, and what each phase added

**Phase 1 — a state to compare.** There was a fingerprint but no canonical
schema and no named change event. `warning_state.py` adds canon-v1 snapshots
(structured official fields only; fetch times, request ids and rendered text
excluded by construction) and `detect()` with seven explicit kinds. The
existing hash input is reproduced byte-for-byte, so stored fingerprints stay
valid — no migration, no re-notification storm. Watch creation is now
idempotent: same place, hazard and window returns the existing watch.

**Phase 2 — an outbox that survives overlap and crashes.** The second checker
used to get a refusal and a crash between send and mark could duplicate.
There is now a `claimed` state with owner and lease (a lock, not a delivery
outcome — the ledger keeps its exact shape), silent reclaim of stale claims,
a UNIQUE delivery-identity key so one logical event enqueues once, an error
taxonomy (retryable/purged, with purge going straight to gone), jittered
backoff, a 24-hour maximum retry age, and per-state depths for health.

**Phase 3 — supervision you can check.** The daemon loop now survives one bad
cycle, skips overlapping runs instead of dying, and writes a heartbeat tick
every cycle; manual runs record ticks too. `GET /api/watch-health` reports
the mode honestly — foreground-supervised, manual-recent, or manual-only —
with tick age, queue depths, watch counts and plan-watcher state. No hosted
daemon is claimed.

**Phase 4 — hardening around delivery.** Per-route rate limits with HTTP 429
on the six watch/push/ack mutations, an advisory Urgency header on red/orange
push, DOCTYPE quarantine in the CAP parser, a dead-letter section in the
inbox, and a hostile-content suite proving feed text is carried verbatim and
never interpreted.

**Phase 5 — geography the relay was missing.** A pure CAP polygon/circle
matcher (CAP lat,lon order, geodesic circles, geocodes held with codes
listed, never raises), a small reviewed alias table that resolves ambiguity
to asking rather than guessing, a disclosed alias fallback in the warning
path, and per-point CAP applicability carried as additive evidence — facts,
lifecycle and fingerprints untouched.

## Data model

Additive only, same SQLite stores, no new database: five nullable outbox
columns (claim owner/lease, idempotency key, error class) plus a UNIQUE index
(NULL keys on old rows never collide); watch rows gain fingerprints through
the existing migrate path. No table rebuilt, no data deleted.

## API

One new token-gated route (`GET /api/watch-health`); `429` on spent budgets;
`error_class` added to outbox summaries; `claimed` accepted as a filter and
counted in delivery aggregates. No route removed, no contract broken.

## Testing

66 new tests, all passing: canonicalization order/volatile invariance,
legacy-hash identity, every detector transition, idempotent creation, worker
overlap, stale-lease recovery, dedupe, purge/age/jitter bounds, heartbeat
freshness, overlap-skip, rate budgets and route wiring, parser quarantine,
verbatim builders, urgency reaching the provider call, polygon/circle/geocode
verdicts and alias scoping. Full-suite before/after comparison by test ID:
identical failure sets (pre-existing environment breakage in corpus/chat
areas), zero regressions. Synthetic delivery, duplicates, update, cancel and
expiry are proven with test doubles; live-device push and a sustained live
IMD run are explicitly not claimed.

## Limits that stay labelled

Foreground supervision only (no hosted scheduler); origin, geographic and
completeness verifiers still forced false (the matcher is built, promotion
waits on live proof); flood/cyclone/heat/cold/sea-area still held as not
connected; no out-of-band channel; escalation stays inbox-local and says so.

## Branch

`feature/feature4-alert-dissemination`, rebased onto the latest `main`
before pushing, five commits in phase order, working tree clean except local
research notes kept out of the branch. Next: sustained live-IMD edition run,
one live-device push-to-ack journey, and the hosting decision.
