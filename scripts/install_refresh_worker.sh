#!/bin/bash
# Install, show or remove the RESIDENT refresh worker — the one that runs for as long as the
# machine is on, rather than twice a day.
#
#   scripts/install_refresh_worker.sh            # install or update, and start it now
#   scripts/install_refresh_worker.sh --show     # is it running, and what has it done today
#   scripts/install_refresh_worker.sh --verify   # prove it actually starts under launchd
#   scripts/install_refresh_worker.sh --remove
#
# WHY THIS REPLACES THE TWICE-DAILY SCHEDULE.
#
# scripts/install_daily_schedule.sh runs the refresh at two fixed times. Two problems with that,
# and the second is worse than the first. A district read at 07:10 whose bulletin is reissued at
# 11:00 is not seen until tomorrow, so "fresh" means "fresh as of one of two moments". And a slot
# that fails - no network, a slow publisher, a laptop that woke into a captive portal - waits half
# a day for its next attempt, with nothing in between.
#
# A worker that is simply always resident has neither problem. It picks up today's edition when
# today's edition appears, it retries on the next pass rather than in twelve hours, and nobody has
# to have guessed the right hour. `KeepAlive` restarts it if it dies; `RunAtLoad` starts it at
# login. Between the two, it is running whenever the machine is.
#
# It is not a busy loop. IMD issues each district bulletin once each morning, so the worker paces
# itself between targets and goes idle once every district has been attempted for the day. See the
# header of scripts/refresh_daemon.py for what it does and does not do to the publisher.
#
# The TCC lesson from install_daily_schedule.sh applies here unchanged: a launchd-spawned process
# does NOT inherit the Full Disk Access your terminal has, so a project living in ~/Desktop,
# ~/Documents or ~/Downloads cannot be read by this job at all. --verify checks rather than assumes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.weathergpt.refresh.worker"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DAILY_LABEL="com.weathergpt.refresh"
STATE="$ROOT/data/runtime/refresh"
PY="${WEATHERGPT_PYTHON:-$ROOT/.venv/bin/python}"
[ -x "$PY" ] || PY="$(command -v python3)"
PACE="${WEATHERGPT_REFRESH_PACE:-20}"

worker_status() {
  "$PY" "$ROOT/scripts/refresh_daemon.py" --status 2>/dev/null || true
}

install_worker() {
  mkdir -p "$HOME/Library/LaunchAgents" "$STATE"
  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$ROOT/scripts/refresh_daemon.py</string>
    <string>--pace</string><string>$PACE</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <!-- Resident: start at login, and bring it back if it dies. This is the whole difference
       between this agent and the twice-daily one. -->
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <!-- Do not let a crash-loop hammer the publisher: launchd waits this long before a respawn. -->
  <key>ThrottleInterval</key><integer>60</integer>
  <key>StandardOutPath</key><string>$STATE/worker.out.log</string>
  <key>StandardErrorPath</key><string>$STATE/worker.err.log</string>
  <!-- Background: lowest CPU and I/O priority, so the worker never competes with the workspace
       answering somebody's question. The query lease handles the publisher; this handles the
       machine. -->
  <key>ProcessType</key><string>Background</string>
  <key>LowPriorityIO</key><true/>
  <key>Nice</key><integer>5</integer>
</dict>
</plist>
PLISTEOF
  launchctl bootout "gui/$UID/$LABEL" 2> /dev/null || true
  launchctl bootstrap "gui/$UID" "$PLIST"
  echo "installed resident LaunchAgent $LABEL"
  echo "  $PLIST"
  echo "  python: $PY"
  echo "  pace:   ${PACE}s between districts; idle once every district has been attempted today"
  echo "  it starts at login and is restarted if it dies"
}

remove_worker() {
  launchctl bootout "gui/$UID/$LABEL" 2> /dev/null || true
  rm -f "$PLIST"
  echo "removed resident LaunchAgent $LABEL"
}

show_worker() {
  if launchctl print "gui/$UID/$LABEL" > /dev/null 2>&1; then
    echo "LaunchAgent $LABEL is loaded."
    launchctl print "gui/$UID/$LABEL" | grep -E "state =|last exit code|runs =|pid =" | sed 's/^/  /' || true
  else
    echo "LaunchAgent $LABEL is NOT loaded."
  fi
  echo
  worker_status
  if launchctl print "gui/$UID/$DAILY_LABEL" > /dev/null 2>&1; then
    echo
    echo "NOTE: the twice-daily agent $DAILY_LABEL is ALSO loaded. It is now redundant - the"
    echo "      resident worker covers everything it did and more - and leaving both means two"
    echo "      processes fetching the same districts. Remove it with:"
    echo "        scripts/install_daily_schedule.sh --remove"
  fi
}

verify_worker() {
  # Loaded is not running, and running is not working. Same lesson as the daily installer: this
  # checks that the process actually came up under launchd and wrote a heartbeat, rather than
  # trusting that it would.
  echo "verifying the worker starts under launchd and reports..."
  rm -f "$STATE/daemon.json"
  launchctl kickstart -k "gui/$UID/$LABEL" > /dev/null 2>&1 || true
  local waited=0
  while [ ! -f "$STATE/daemon.json" ] && [ "$waited" -lt 90 ]; do sleep 3; waited=$((waited + 3)); done
  if [ -f "$STATE/daemon.json" ]; then
    echo "VERIFIED: the worker started under launchd and wrote a heartbeat after ${waited}s"
    worker_status
    return 0
  fi
  echo "NOT VERIFIED: no heartbeat at data/runtime/refresh/daemon.json after ${waited}s."
  if [ -s "$STATE/worker.err.log" ]; then
    echo "              launchd said:"
    tail -5 "$STATE/worker.err.log" | sed 's/^/                /'
  fi
  case "$ROOT" in
    "$HOME"/Desktop/*|"$HOME"/Documents/*|"$HOME"/Downloads/*)
      cat <<'TCC'

  This project lives in a folder macOS protects (Desktop, Documents or Downloads). A launchd job
  does not inherit the Full Disk Access your terminal has, so it cannot read the project at all.
  Move the project somewhere unprotected, for example ~/WeatherGPT, and re-run this installer.
TCC
      ;;
  esac
  return 1
}

if [ "$(uname -s)" != "Darwin" ]; then
  cat <<'LINUX'
This installer is macOS-only. On Linux, run the worker under systemd --user with Restart=always:

  [Unit]
  Description=WeatherGPT resident refresh worker
  [Service]
  ExecStart=%h/WeatherGPT/.venv/bin/python %h/WeatherGPT/scripts/refresh_daemon.py
  WorkingDirectory=%h/WeatherGPT
  Restart=always
  RestartSec=60
  Nice=5
  [Install]
  WantedBy=default.target

Save as ~/.config/systemd/user/weathergpt-refresh.service, then:
  systemctl --user daemon-reload && systemctl --user enable --now weathergpt-refresh
LINUX
  exit 0
fi

case "${1:---install}" in
  --show) show_worker ;;
  --remove) remove_worker ;;
  --verify) verify_worker ;;
  *) install_worker
     echo
     echo "Installed is not the same as working. Prove it with:"
     echo "  scripts/install_refresh_worker.sh --verify" ;;
esac
