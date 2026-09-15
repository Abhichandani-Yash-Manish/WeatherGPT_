# Dissemination integration review

15 September 2026. Follow-up to [the integrated PS assessment](72-integrated-status-and-ps-review.md).
Integrates concurrent branch `feature/feature4-alert-dissemination` at `70a55d1` into the unified
workspace release. This source integration is explicitly authorized by the user's request to integrate
concurrent work and push GitHub. Hosting remains held.

## Delivered change

Legacy official-warning watches now have a fingerprint outbox, per-channel state and retry history,
opt-in Web Push subscriptions, retirement, local acknowledgement and bounded local follow-up. The
Plans & inbox panel exposes these controls and the warning facts behind a notification. “Need help”
records a local response; it contacts no emergency service. Push opt-in explains the browser vendor's
external delivery service. No actual external notification was sent during this integration review.

**The two watch systems are still separate.** Activity plans use `plans.sqlite` and the normal workspace's
plan watcher. This batch adds delivery to the older `watches.sqlite` workflow. Its checks and dispatch run
on demand or through `scripts/watch_daemon.py`; starting the workspace does not install or supervise that
loop. A shared panel does not make their schedules, notification semantics or subscriptions unified.

## Integration defects repaired

- The branch replaced a blocking per-request cache lock with an immediate-failure lock. Two simultaneous
  identical weather requests then failed instead of sharing one download. A bounded 30-second wait now
  preserves coalescing; provider reservation locks remain non-blocking. Unsupported locking fails closed.
- Successful retries attempted the invalid `failed → sent` transition after sending. Dispatch now records
  the due row as queued before sending. Failed rows that outlive their watch window become `gone` before
  calling a sender. Terminal rows stay terminal. Push TTL never extends a past watch window.
- Browser subscription expiry arrives as epoch milliseconds; it is normalized and purged before delivery.
  Unsubscribing one browser preserves the channel when another active subscription remains.
- VAPID key creation is locked and atomic; existing key files are restricted to owner access on POSIX.
  Web Push requests have a 15-second transport timeout. Actual cross-platform behavior is unvalidated.
- The branch's sole pywebpush pin excluded the project's Python 3.9 runtime. Requirements now select
  a compatible branch and pin cryptography for each Python range. This host exercised Python 3.9 only.
  A project virtual environment isolates these additions; it inherited installed system packages, so this
  is not a clean dependency-install acceptance result. Version constraints were checked against the
  [official 2.5 package metadata](https://pypi.org/project/pywebpush/2.5.0/) and
  [2.1.2 metadata](https://pypi.org/project/pywebpush/2.1.2/).
- Removed stale “no push” claims, labelled coordinate inputs, exposed notification evidence, and retained
  delivery timestamps after acknowledgement. Added the notification component suite to the common verifier.
  Failed verification now prints its diagnostic output rather than only the last summary line.

## Verification

Evidence: `research/reviews/integration-ps-audit-20260915/dissemination/`.

- `verification-release.txt`: **1,105 Python tests, nine JavaScript suites, all 25 verification steps pass**.
  The subsequent three HTTP/retry checks also pass after the delivery-timestamp refinement.
- `tests/test_dissemination_integration.py`: real loopback HTTP registration → baseline → changed state →
  local inbox → duplicate suppression → source/unit/window inspection → acknowledgement → retirement.
  Missing-token reads and writes return 403. Only the warning-tool boundary is synthetic; no live official
  edition or push-service delivery is claimed. Acknowledgement preserves the original send timestamp.
- The real local Chromium panel loads the labelled form, old watches, channel controls and external-push
  disclosure. Its accessibility subtree reports zero violations, with one inconclusive contrast rule.
  Existing watches were only read; no subscription was created and no check of user watches was triggered.
- `verification.txt` and `verification-final.txt` preserve failed integration runs. The first had two
  failures; the second retained the lock regression. The outbox assertion changed deliberately to require
  newly exposed evidence. `failure-detail-scoped.txt` records the lock failure. An unscoped diagnostic
  command accidentally collected historical checkpoint tests; its output remains in the local review
  archive and is not treated as a product test result.
- The earlier development benchmark's 18/18 score belongs to the preceding release. It was not rerun as
  independent warning acceptance and still measures task status/parameters rather than factual truth.

Detached clean checkout `ba3cdbd` passed all 1,105 Python tests, nine JavaScript suites and all 25 steps, recorded in `clean-checkout-verification.txt`. It used this host and dependency environment. The subsequent stakeholder branch and final combined checks are recorded in docs/72; this is a dated checkpoint, not the final test count. Same-host checks cannot establish fresh-machine installation or sustained operation.

## Critical remaining gaps

1. **No live edition-to-device acceptance.** No current official change has been independently followed
   through actual OS notification, offline delay, reconnection, update/cancel and acknowledgement.
2. **No source authority shortcut.** Fingerprints and CAP references do not establish origin authenticity,
   current applicability or flood/cyclone product coverage. Official wording is not operational clearance.
3. **No exactly-once service claim.** Check locking and atomic enqueue protect some boundaries, but dispatch
   has no multi-worker claim/lease and a crash after external send can duplicate delivery. A successful send
   to one subscription can mark a channel sent while another endpoint fails. Per-device receipt is absent.
4. **No supervised unified scheduler.** Activity plans and legacy watches need one explicit product contract
   and a measured sustained cadence. Manual checks and a foreground loop do not demonstrate an unattended service.
5. **No rural delivery acceptance.** English notices, opt-in/permission behavior, native languages, phones,
   poor connectivity and real field users remain unvalidated. SMS/IVR/WhatsApp are not connected channels.

The incoming reports [`74-dissemination-build.md`](74-dissemination-build.md) and
[`75-dissemination-build.md`](75-dissemination-build.md) (renumbered from 68 and 71 on
15 September 2026 to clear duplicate document numbers; content unchanged) retain branch-authored dates,
phase evidence, historical “unmerged” text and self-assigned percentages. **Their approximately 89% overall
and 94% trajectory scores are not adopted by this review.** Neither represents measured full-PS completion.
P06/P10/P13/P14 and A05 remain partial/open; this batch implements useful machinery and repairs integration
regressions, without closing the disaster-warning journey.

## PR #4 review and merge resolution (15 September 2026)

Reviewed the open PR #4 head `beaddad` against `main` at `b007548`. Its implementation is already
inside main: the authorized integration landed the branch at `70a55d1` and this review's repairs
have since been applied on top, so main's copies are equal or newer on every file the branch
touches. Measured examples of main being ahead: `filelock.py` raises `OSError` where the branch
degraded to a no-lock path, `web/sw.js` says notification content is unavailable instead of
implying a watched state changed, and `push.py`, `workspace.py`, `web/shell.js` carry the
integration repairs above. A three-way merge therefore changes nothing but the branch's leftover
bookkeeping.

Resolution recorded in the merge commit:

- `data/registry/product-progress.json`: kept main's consolidated `deliverable_state`. The branch's
  older wording (its P03/P06/P14 evidence and its "dissemination build unmerged" entry) is
  superseded by this review's evidence and the stakeholder-repair records.
- The branch renamed its build report to `docs/73-dissemination-build.md`; 73 is this review's own
  number. The two historical build reports keep their content and are renumbered to clear duplicate
  document numbers: `docs/68-dissemination-build.md` → `docs/74-dissemination-build.md` and
  `docs/71-dissemination-build.md` → `docs/75-dissemination-build.md`. The branch's duplicate
  `docs/73-dissemination-build.md` was dropped; nothing was lost.

Verification on the resolved tree: `.venv/bin/python scripts/verify_all.py` reports 26 step(s),
0 failed, including 1123 Python tests and the nine Node component suites on this macOS Python 3.9
host. One environment fact is worth recording: the system `python3` lacks `pywebpush`/`py_vapid`,
so eight push and push-through-the-outbox checks fail there, while the project `.venv` runs the
whole suite green. The push suites therefore require the project environment, not the system one.

Still open after this merge, unchanged: no live edition-to-device acceptance, no origin
authentication, no supervised unified scheduler and no rural delivery evidence.
