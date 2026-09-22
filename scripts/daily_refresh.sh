#!/bin/bash
# One refresh run, safe to be called by cron.
#
# The cycle itself is scripts/run_daily_cycle.py. This wrapper adds the three things a scheduled job needs
# and a foreground command does not: it refuses to overlap a run already in progress, it writes what
# happened somewhere a later check can read, and it keeps a bounded log instead of mailing root.
#
# A weather product refreshed once a day is stale for most of the day, so the installer schedules two
# runs. IMD publishes the district bulletins in the morning and updates the warning layer through the
# afternoon; neither time is a guarantee, which is why the freshness audit reads the store rather than
# trusting this to have worked.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

STATE="$ROOT/data/runtime/refresh"
LOG="$STATE/refresh.log"
LOCK="$STATE/refresh.lock"
STATUS="$STATE/last-run.json"
mkdir -p "$STATE"

# A run that is already going keeps going; this one records that it stood down and leaves.
if ! mkdir "$LOCK" 2>/dev/null; then
  held=$(cat "$LOCK/pid" 2>/dev/null || echo unknown)
  if [ "$held" != unknown ] && ! kill -0 "$held" 2>/dev/null; then
    # The holder is gone - a machine that slept or a run that was killed. Take the lock.
    rm -rf "$LOCK" && mkdir "$LOCK" 2>/dev/null || exit 0
  else
    echo "$(date -u +%FT%TZ) skipped: a refresh is already running (pid $held)" >> "$LOG"
    exit 0
  fi
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT

started=$(date -u +%FT%TZ)
echo "$started starting" >> "$LOG"

PY="${WEATHERGPT_PYTHON:-python3}"
# HOW MANY DISTRICTS THIS RUN SWEEPS. It was 40, and India has 756 - so the corpus held agromet
# bulletins for about five per cent of the country and every question about the other ninety-five could
# only be answered "not held here". That is the whole of the weakest group in the scenario atlas
# (agromet and advisories, 60-76% against 89% overall): a coverage gap, not a reasoning one.
#
# Measured on the run of 22 September 2026: the sweep takes 99.5 s for 40 districts, about 2.5 s each,
# inside a refresh that finishes in 3 m 23 s. At 200 the sweep is roughly eight minutes on a job that
# runs unattended, twice a day, with nobody waiting on it - and a reader waiting for an answer cannot
# afford thirty seconds. That asymmetry is the argument in docs/141 against fetching documents at
# question time: the same work, moved onto the schedule, costs nothing anyone experiences.
#
# The sweep takes QUEUED targets, so coverage grows run by run either way; this is the difference
# between covering the country in weeks and covering it in days. Lower it with the environment
# variable if the publisher turns out not to tolerate the rate - which is worth watching on the first
# widened run rather than assuming in either direction.
"$PY" scripts/run_daily_cycle.py --district-limit "${WEATHERGPT_DISTRICT_LIMIT:-200}" > "$STATE/last-cycle.json" 2>> "$LOG"
code=$?
finished=$(date -u +%FT%TZ)

"$PY" - "$STATE" "$started" "$finished" "$code" <<'PYEOF' >> "$LOG" 2>&1
import json, sys, pathlib
state, started, finished, code = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])
cycle = {}
try:
    cycle = json.loads((state / 'last-cycle.json').read_text())
except Exception:
    pass
steps = cycle.get('steps') or []
(state / 'last-run.json').write_text(json.dumps({
    'schema_version': 'refresh-run-v1',
    'started_at_utc': started, 'finished_at_utc': finished,
    'exit_code': code, 'ok': code == 0 and bool(cycle.get('ok', code == 0)),
    'steps': [{'step': s.get('step'), 'ok': s.get('ok'), 'seconds': s.get('seconds')} for s in steps],
    'failed_steps': [s.get('step') for s in steps if not s.get('ok')],
}, indent=1) + '\n')
print(f'{finished} finished exit={code} ok={code == 0}')
PYEOF

# A log that grows without limit is its own outage. Keep the last 2000 lines.
tail -n 2000 "$LOG" > "$LOG.trim" 2>/dev/null && mv "$LOG.trim" "$LOG"
exit $code
