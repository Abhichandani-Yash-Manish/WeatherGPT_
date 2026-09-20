#!/bin/bash
# Install, show or remove the daily refresh schedule, using the mechanism that actually works on
# this operating system.
#
#   scripts/install_daily_schedule.sh          # install or update
#   scripts/install_daily_schedule.sh --show   # what is installed, and when it last actually ran
#   scripts/install_daily_schedule.sh --remove
#
# WHY THIS REPLACES THE CRONTAB INSTALLER.
#
# The crontab entries were installed on 20 September 2026 at 01:08 and both of that day's slots -
# 07:10 and 14:40 - passed without running. Not a broken script: the laptop entered sleep at
# 07:00:41 and cycled sleep/DarkWake all morning, and macOS cron does not run a job it missed while
# the machine was asleep. It simply skips it. On a laptop that sleeps, a cron schedule is a schedule
# that mostly does not happen, and the data quietly goes stale while the crontab says otherwise.
#
# launchd's StartCalendarInterval does the opposite: a job missed during sleep runs when the machine
# wakes. That is the behaviour a daily refresh needs. So on macOS this installs a LaunchAgent, and
# on Linux (where cron is fine, and a server does not sleep) it keeps using the crontab.
#
# Twice a day, not once: a weather product refreshed once is stale for most of the day. IMD publishes
# the district bulletins in the morning and updates the warning layer through the afternoon.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.weathergpt.refresh"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
BEGIN="# >>> weathergpt refresh >>>"
END="# <<< weathergpt refresh <<<"
MORNING_H="${WEATHERGPT_MORNING_HOUR:-7}"
MORNING_M="${WEATHERGPT_MORNING_MINUTE:-10}"
AFTERNOON_H="${WEATHERGPT_AFTERNOON_HOUR:-14}"
AFTERNOON_M="${WEATHERGPT_AFTERNOON_MINUTE:-40}"

verify_darwin() {
  # Installed is not running, and running is not permitted. macOS TCC protects ~/Desktop,
  # ~/Documents and ~/Downloads, and a launchd-spawned process does NOT inherit the Full Disk Access
  # your terminal has. Measured 20 September 2026 with this project on the Desktop: launchd fired
  # the job, bash could not even getcwd into the directory, and the run exited 126 having done
  # nothing - "Operation not permitted". cron fails the same way for the same reason. So this
  # actually runs the job and checks whether the record moved, instead of trusting that it will.
  local before after
  before="$(python3 -c "
import json,sys
try: print(json.load(open('$ROOT/data/runtime/refresh/last-run.json'))['started_at_utc'])
except Exception: print('none')
" 2>/dev/null || echo none)"
  echo "verifying by running the job through launchd (this takes a few minutes)..."
  launchctl kickstart "gui/$UID/$LABEL" > /dev/null 2>&1 || true
  while launchctl print "gui/$UID/$LABEL" 2> /dev/null | grep -q 'state = running'; do sleep 10; done
  after="$(python3 -c "
import json,sys
try: print(json.load(open('$ROOT/data/runtime/refresh/last-run.json'))['started_at_utc'])
except Exception: print('none')
" 2>/dev/null || echo none)"
  local code
  code="$(launchctl print "gui/$UID/$LABEL" 2> /dev/null | sed -n 's/.*last exit code = \([0-9]*\).*/\1/p' | head -1)"
  if [ "$before" != "$after" ]; then
    echo "VERIFIED: the job ran through launchd and the refresh record advanced to $after"
    return 0
  fi
  echo "NOT VERIFIED: launchd ran the job (last exit code ${code:-unknown}) and the refresh record did"
  echo "              not move. It is still $before."
  if [ -s "$ROOT/data/runtime/refresh/launchd.err.log" ]; then
    echo "              launchd said:"
    tail -3 "$ROOT/data/runtime/refresh/launchd.err.log" | sed 's/^/                /'
  fi
  case "$ROOT" in
    "$HOME"/Desktop/*|"$HOME"/Documents/*|"$HOME"/Downloads/*)
      cat <<'TCC'

  This project lives in a folder macOS protects (Desktop, Documents or Downloads). A scheduled job
  does not inherit the Full Disk Access your terminal has, so it cannot read the project at all -
  "Operation not permitted", exit 126, nothing done. cron fails identically; this is not a launchd
  problem. Two ways out, and the first needs no permission grant:

    1. Move the project somewhere unprotected, for example ~/WeatherGPT, and re-run this installer.
    2. System Settings > Privacy & Security > Full Disk Access, add /bin/bash, then re-run
       this installer with --verify. This is a broad grant; prefer option 1 if you can.

  Until one of those is done the schedule is installed and will not run, which is the exact failure
  this installer exists to stop being silent.
TCC
      ;;
  esac
  return 1
}

last_run() {
  if [ -f "$ROOT/data/runtime/refresh/last-run.json" ]; then
    echo
    echo "last actual run:"
    python3 - "$ROOT/data/runtime/refresh/last-run.json" <<'PY'
import json, sys
from datetime import datetime, timezone
run = json.load(open(sys.argv[1]))
started = run.get('started_at_utc') or ''
try:
    age = (datetime.now(timezone.utc) - datetime.strptime(started, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc))
    hours = age.total_seconds() / 3600
    verdict = 'OK' if hours < 24 else 'STALE - it has not run in over a day'
    print('  started %s  (%.1f hours ago)  exit=%s  %s' % (started, hours, run.get('exit_code'), verdict))
except ValueError:
    print('  started %s  exit=%s' % (started, run.get('exit_code')))
PY
  else
    echo
    echo "last actual run: never - no data/runtime/refresh/last-run.json exists"
  fi
}

install_launchd() {
  mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/data/runtime/refresh"
  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$ROOT/scripts/daily_refresh.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <!-- Two slots a day. launchd runs a slot it missed while the machine was asleep, as soon as it
       wakes; cron does not, which is why this exists. -->
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>$MORNING_H</integer><key>Minute</key><integer>$MORNING_M</integer></dict>
    <dict><key>Hour</key><integer>$AFTERNOON_H</integer><key>Minute</key><integer>$AFTERNOON_M</integer></dict>
  </array>
  <!-- Not at load: installing the schedule should not itself trigger a five-minute refresh. -->
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$ROOT/data/runtime/refresh/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/data/runtime/refresh/launchd.err.log</string>
  <key>ProcessType</key><string>Background</string>
</dict>
</plist>
PLISTEOF
  launchctl bootout "gui/$UID/$LABEL" 2> /dev/null || true
  launchctl bootstrap "gui/$UID" "$PLIST"
  echo "installed LaunchAgent $LABEL"
  echo "  $PLIST"
  echo "  slots: ${MORNING_H}:$(printf '%02d' "$MORNING_M") and ${AFTERNOON_H}:$(printf '%02d' "$AFTERNOON_M") local time"
  echo "  a slot missed while asleep runs on wake, which is the whole point of using launchd here"
}

remove_launchd() {
  launchctl bootout "gui/$UID/$LABEL" 2> /dev/null || true
  rm -f "$PLIST"
  echo "removed LaunchAgent $LABEL"
}

show_launchd() {
  if launchctl print "gui/$UID/$LABEL" > /dev/null 2>&1; then
    echo "LaunchAgent $LABEL is loaded."
    launchctl print "gui/$UID/$LABEL" | grep -E "state =|last exit code|runs =" | sed 's/^/  /' || true
  else
    echo "LaunchAgent $LABEL is NOT loaded."
  fi
  if crontab -l 2> /dev/null | grep -q "weathergpt refresh"; then
    echo
    echo "NOTE: crontab entries for this project are also present. On macOS they are the ones that"
    echo "      silently skip a slot the machine slept through. Remove them with:"
    echo "      scripts/install_daily_cron.sh --remove"
  fi
}

crontab_current() { crontab -l 2> /dev/null || true; }
crontab_without_ours() {
  crontab_current | awk -v b="$BEGIN" -v e="$END" 'index($0,b){s=1} !s{print} index($0,e){s=0}'
}

install_cron() {
  {
    crontab_without_ours
    echo "$BEGIN"
    echo "# WeatherGPT daily refresh - installed by scripts/install_daily_schedule.sh"
    echo "$MORNING_M $MORNING_H * * * $ROOT/scripts/daily_refresh.sh"
    echo "$AFTERNOON_M $AFTERNOON_H * * * $ROOT/scripts/daily_refresh.sh"
    echo "$END"
  } | crontab -
  echo "installed crontab entries:"
  crontab -l | awk -v b="$BEGIN" -v e="$END" 'index($0,b){s=1} s{print} index($0,e){s=0}'
}

ACTION="${1:---install}"
if [ "$(uname -s)" = "Darwin" ]; then
  case "$ACTION" in
    --show) show_launchd; last_run ;;
    --remove) remove_launchd ;;
    --verify) verify_darwin ;;
    *) install_launchd; last_run
       echo
       echo "Installed is not the same as working. Prove it with:"
       echo "  scripts/install_daily_schedule.sh --verify" ;;
  esac
else
  case "$ACTION" in
    --show)
      echo "crontab entries for this project:"
      crontab_current | awk -v b="$BEGIN" -v e="$END" 'index($0,b){s=1} s{print} index($0,e){s=0}' || true
      last_run ;;
    --remove) crontab_without_ours | crontab -; echo "removed crontab entries" ;;
    *) install_cron; last_run ;;
  esac
fi
