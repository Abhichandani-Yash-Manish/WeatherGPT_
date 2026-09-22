# 143 — The refresh that never stops

> **The direction.** *"The fetching sweep should run 24/7 as long as my system is on. This way 100%
> freshness is maintained, and during that background fetching process, if the app query is raised
> then it should be given priority."*
>
> **Built.** A resident worker under launchd with `RunAtLoad` and `KeepAlive`, and a lease that puts a
> waiting reader ahead of it. It found two bugs on its first run that a twice-daily job had been
> hiding for as long as the job has existed.

Written 22 September 2026, the same day as docs/142, which this finishes.

---

## Why always-on beats twice a day

docs/142 fixed *which* districts the schedule fetched. It left *when* alone, and the when was already
the weaker half.

The twice-daily agent exists because cron was worse: a laptop asleep at 07:10 does not run a 07:10
cron slot at all, it skips it, and the data goes stale while the crontab says otherwise (docs/118).
launchd runs a missed slot on wake, which fixed that. But two slots a day still means:

- **Fresh is fresh as of one of two moments.** A district read at 07:10 whose bulletin is reissued at
  11:00 is not seen until tomorrow.
- **A failed slot waits half a day.** No network, a slow publisher, a wake into a captive portal —
  whatever the reason, the next attempt is twelve hours away and nothing happens in between.
- **Somebody had to guess the hour.** 07:10 and 14:40 are guesses about when IMD publishes.

A worker that is simply always there has none of those problems, and needs no guesses. It picks up
today's edition when today's edition exists, and retries on the next pass rather than in twelve hours.

## What it does *not* do is hammer the publisher

IMD issues each district bulletin once each morning. A worker fetching flat out for twenty-four hours
would download the same bytes over and over, against a public service, to learn nothing — and that is
not a hypothetical, it is the measured behaviour docs/142 found in the old sweep: *"32 unchanged, 0
passages indexed"*, twice a day, for a week.

So "24/7" means *resident*, not *busy*:

- one target at a time, from docs/142's queue — districts a reader asked for first, then never-held,
  then longest-unread;
- **20 seconds between targets**, about three requests a minute, covering all 698 districts in roughly
  four and a half hours;
- **idle once every district has been attempted today**, waking every five minutes to see whether the
  day has turned or somebody has asked about a district it has not read.

`ProcessType Background`, `LowPriorityIO` and `Nice 5` keep it off the machine's back; the lease below
keeps it off the publisher's.

## A reader always wins

`weathergpt_data/refresh_lease.py`. A query raises a lease for exactly as long as its own fetch and
extraction take; the worker checks before each target and stands down while any is held.

It is deliberately the smallest thing that works, and each choice is load-bearing:

| | |
|---|---|
| **A file per holder, not a counter** | two questions at once cannot lose each other's lease, and neither needs a lock to raise one |
| **An expiry (90s)** | a query killed mid-fetch cannot silence the worker until reboot. An expired lease is swept, not merely ignored |
| **Bounded patience (120s)** | a workspace busy enough to never refresh is a workspace whose corpus rots while looking healthy. After that the worker proceeds and the two share the publisher like any two clients |
| **Never raises** | the lease is bookkeeping that makes a background job polite. A reader's answer must never depend on it, so every failure in it is swallowed |
| **Released when the publisher is done with, not when the turn ends** | the rest of a turn is writing prose, and the worker has no reason to wait for that |

It is **not** a mutual-exclusion lock and must not be used as one. Both processes may touch the index
at once; SQLite's locking handles that and the store's per-URL file lock handles a genuine collision
on one document. This only answers *"is a reader waiting"*.

Observed end to end, with the worker resident and a question asked against the live workspace — the
worker's own heartbeat, once a second:

```
fetching  Kadapa  readers_waiting=0
fetching  Kadapa  readers_waiting=1     <- the question's fetch raised its lease
fetching  Kadapa  readers_waiting=1
fetching  Kadapa  readers_waiting=0     <- released; the worker carried on
```

In practice most questions never contend at all: at a 20-second pace with ~3-second fetches the worker
is idle about 85% of the time.

---

## Two bugs that only an always-on worker could find

Both had been there for as long as the sweep had. Both are invisible to a job that runs forty targets
and stops, and fatal to one that does not stop.

### 1. A district that failed today stayed in the queue

`sweep_queue` counted only `status == 'ok'` as done. Under a twice-daily job that is harmless — the run
ends. Under the resident worker, the 71 districts whose last read was a failure — most of them held
outcomes like `layout_unrecognised` that will fail again on the next byte-identical body — would be
retried immediately, forever, and nothing else in the country would ever be reached.

An attempt is an attempt. A failure today is retried tomorrow, or now under `--retry-failed`, which is
the switch that exists to say *try those again*.

### 2. Several outcomes recorded nothing at all

Worse, and found by running the worker and watching it:

```
targets_this_run 14   outcomes {'failed': 14}
document head for Kadapa: None
```

**Fourteen consecutive attempts on one district**, all failed, no head written, nothing else reached.
`ingest_district` wrote a head on some terminal paths and not others — a selection step that could not
resolve the district, a body that was not a PDF, a publisher that served nothing, a publish that
raised, all returned a record and left no trace. The district stayed "never held", which is the *top*
of the refresh queue, so the worker fetched it again, and again.

Every terminal outcome now records the attempt, and **records it under its own name**. That second part
matters and fixed a standing inaccuracy: the recorder that did exist flattened everything to `failed`,
which contradicts the vocabulary this project has kept since docs/29 — *`not_issued` is an answer,
`layout_unrecognised` is held, and only transport or extraction errors are failures*. A publisher's
unreviewed layout was indistinguishable from a broken fetch. `freshness` now counts `last_read_failed`
and `last_read_withheld` apart, because the gap between them is the publisher's layouts and not this
workspace's diligence.

After the fix, eight consecutive targets are eight *different* districts, and `never_held` falls 80 → 72.

---

## Seeing it

A resident process that cannot be asked *"are you alive and are you getting anywhere"* is a process
people turn off. It writes a heartbeat after every target:

```
$ python3 scripts/refresh_daemon.py --status
resident worker: pid 36992, RUNNING
  state        fetching  (19 seconds ago)
  district     Shahdara  (no edition is held and nobody has asked yet)
  this run     40 targets, 0 passages, {...}
  corpus       41 of 698 districts attempted today, 15 read, 68 never held, median last read 8 days
```

`scripts/install_refresh_worker.sh --verify` proves it starts *under launchd* and writes a heartbeat,
rather than trusting that it will — the same lesson as docs/118's installer, where a job was installed,
loaded, and could not read the project at all because a launchd process does not inherit the Full Disk
Access a terminal has. That check is carried over unchanged.

The worker stops between targets, never mid-document: launchd sends SIGTERM on logout and on reload,
and dying inside an extraction would leave the day's manifest describing work that did not finish.

Its fetches are appended to the same day-manifest the sweep writes, tagged `fetched_by:
resident_worker`. A reader of the day's file should not have to know which mechanism fetched a district.

---

## What is now redundant

The twice-daily agent `com.weathergpt.refresh` still works and is now unnecessary — the worker covers
everything it did. It is **not** harmful to leave loaded: both take their queue from the same corpus
index, so a sweep starting after the worker has attempted everything finds an empty queue and does
nothing. `install_refresh_worker.sh --show` says so, and names the one command that removes it. It was
left in place rather than removed unilaterally.

## Measured

- Full suite **1595 → 1616**, no regressions. Three standing assertions changed deliberately and each
  says why in its own docstring: the same-day failure retry, the held-layout status vocabulary, and
  every-outcome-records-an-attempt.
- The worker is installed, verified under launchd, and running: `state = running`, 40 targets on its
  first pass.
- The lease was observed handing over end to end against the live workspace, and is pinned by tests
  for the ordering (stand down *before* fetching), the expiry, concurrent holders, and bounded
  patience.

## Open

- **The never-held districts are mostly unservable.** 68 of 698 are listed in the publisher's directory
  but their address does not deliver a PDF — *"a listing is not a promise of an issue"*, as
  `district_targets` has said all along. They are recorded as `failed` where several are probably
  really `not_issued`; telling those apart needs the served body inspected, which is its own change.
- **The first pass spends its early hours on those 68**, because never-held outranks stale-held in the
  queue. It self-corrects — after one attempt they carry heads and never enter that bucket again — but
  a district that has failed its last several attempts arguably should not keep its place near the
  front.
- **The 20-second pace is a judgement, not a measurement.** It is gentle and it covers the country
  inside a morning; nobody has measured what rate this publisher actually tolerates, and the first full
  day of resident operation is the thing to watch.
- **Sleep and wake are untested.** launchd restarts the worker if it dies, but a machine that suspends
  mid-fetch and resumes hours later has not been observed.
