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
# HOW MANY QUEUED DISTRICT TARGETS THIS RUN SWEEPS - a rate, not a total.
#
# This was briefly raised to 200 on the reasoning that the corpus held 40 districts out of India's 756.
# That reasoning was wrong: 40 is how many QUEUED targets each run takes, coverage accumulates across
# runs, and the corpus already carries district agromet passages for 571 distinct regions. Measured
# 22 September 2026, and measured only after the change had been made and committed.
#
# The evidence against the change is stronger than the arithmetic. Of the sixteen agromet and advisory
# failures in that day's atlas run, the number whose answer says the bulletin is not held is ZERO. The
# weak group is not a coverage gap; it is good answers scored partial, an engine asking for details it
# could infer, and raw document metadata printed where prose belongs (docs/141).
#
# So it is back at 40, because tripling the request rate against a public publisher needs a reason, and
# the reason turned out not to exist.
"$PY" scripts/run_daily_cycle.py --district-limit "${WEATHERGPT_DISTRICT_LIMIT:-40}" > "$STATE/last-cycle.json" 2>> "$LOG"
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
