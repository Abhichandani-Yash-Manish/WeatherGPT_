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
# HOW MANY DISTRICT TARGETS THIS RUN SWEEPS - a rate, not a total.
#
# The number has been argued about twice and both arguments were wrong, so the history is kept here.
#
# It was first raised to 200 on the reasoning that the corpus held 40 districts out of India's 756.
# That was wrong: 40 is a RATE, and the corpus already carries district agromet passages for 571
# distinct regions. It went back to 40 on the reasoning that coverage accumulates across runs, so the
# rate only decides how fast the country is covered.
#
# That second reasoning was also wrong, and this is the one that cost something. Coverage did NOT
# accumulate: the sweep read its "already done" set out of the DAY's manifest, so every run began
# again at the top of the publisher's directory. Measured 22 September 2026 across three days:
#
#     2026-09-20  40 swept, deferred_by_limit 658   31 fetched_new, 290 passages
#     2026-09-21  40 swept, deferred_by_limit 658   32 unchanged,     0 passages
#     2026-09-22  40 swept, deferred_by_limit 658   32 unchanged,     0 passages
#
# Twice a day, the same forty districts, indexing nothing, while 541 of 667 heads had not been read
# since the 14th and 399 of 662 held editions still carried the printed issue date 2026-09-11.
#
# The rate was never the problem and it stays at 40. What changed is the ORDER (docs/142): the queue
# now comes from the corpus index rather than the day manifest, and takes the districts readers
# actually asked for first, then the ones never held, then the ones longest unread. The query layer
# fetches what a reader asks for on the turn itself, so this job is the tail nobody asked for. At 40
# a run, twice a day, that tail is covered in about nine days and stays covered; before this it was
# covered never. Raise WEATHERGPT_DISTRICT_LIMIT to go faster, watching the publisher's tolerance on
# the first widened run rather than assuming it in either direction.
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
