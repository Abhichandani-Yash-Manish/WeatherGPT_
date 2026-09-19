#!/bin/bash
# Install, show or remove the refresh schedule in this user's crontab.
#
#   scripts/install_daily_cron.sh            # install (or update) the entries
#   scripts/install_daily_cron.sh --show
#   scripts/install_daily_cron.sh --remove
#
# It only ever touches lines between its own markers, so anything else in the crontab is carried through
# untouched. cron runs in the machine's local timezone.
#
# Twice a day, not once: a weather product refreshed once is stale for most of the day. IMD publishes the
# district bulletins in the morning and updates the warning layer through the afternoon.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BEGIN="# >>> weathergpt refresh >>>"
END="# <<< weathergpt refresh <<<"
MORNING="${WEATHERGPT_CRON_MORNING:-10 7}"
AFTERNOON="${WEATHERGPT_CRON_AFTERNOON:-40 14}"

current() { crontab -l 2>/dev/null || true; }
without_ours() { current | awk -v b="$BEGIN" -v e="$END" 'index($0,b){s=1} !s{print} index($0,e){s=0}'; }

case "${1:---install}" in
  --show)
    echo "crontab entries for this project:"
    current | awk -v b="$BEGIN" -v e="$END" 'index($0,b){s=1} s{print} index($0,e){s=0}' || true
    [ -f "$ROOT/data/runtime/refresh/last-run.json" ] && { echo; echo "last run:"; cat "$ROOT/data/runtime/refresh/last-run.json"; }
    ;;
  --remove)
    without_ours | crontab -
    echo "removed. remaining entries: $(current | grep -c . || true)"
    ;;
  *)
    {
      without_ours
      echo "$BEGIN"
      echo "# WeatherGPT daily refresh - installed by scripts/install_daily_cron.sh"
      echo "$MORNING * * * $ROOT/scripts/daily_refresh.sh"
      echo "$AFTERNOON * * * $ROOT/scripts/daily_refresh.sh"
      echo "$END"
    } | crontab -
    echo "installed:"
    crontab -l | awk -v b="$BEGIN" -v e="$END" 'index($0,b){s=1} s{print} index($0,e){s=0}'
    ;;
esac
