#!/bin/bash
# Move this workspace out of ~/Desktop, so the daily refresh can actually run.
#
#   scripts/move_off_desktop.sh              # move to ~/WeatherGPT
#   scripts/move_off_desktop.sh ~/code/wgpt  # somewhere else
#   scripts/move_off_desktop.sh --check      # say what would happen, change nothing
#
# WHY THIS EXISTS.
#
# The daily refresh is scheduled and does not run. It is not a broken script and not a broken
# schedule: macOS TCC (Transparency, Consent and Control) protects ~/Desktop, ~/Documents and
# ~/Downloads, and a job launchd starts is not a job the user is sitting in front of. The refresh
# exits 126, "Operation not permitted", before it reads a single file.
#
# Measured on this machine on 21 September 2026: the launch agent fires on time and dies there.
#
# Two ways out. Grant Full Disk Access to /bin/bash, which hands a shell permission to read every
# protected folder on the machine and has to be redone on every new machine. Or keep the repository
# somewhere TCC does not guard, which is what this does. A repository is not a desktop file.
#
# WHAT IT TOUCHES. The directory, and the launch agent that names it. Nothing inside the repository:
# no path in the code is absolute, which is checked below before anything moves.
set -euo pipefail

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DEFAULT="$HOME/WeatherGPT"
CHECK=0
TARGET="$TARGET_DEFAULT"

for argument in "$@"; do
  case "$argument" in
    --check) CHECK=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) TARGET="${argument/#\~/$HOME}" ;;
  esac
done

say() { printf '%s\n' "$*"; }

say "from : $SOURCE"
say "to   : $TARGET"
say ""

if [ "$SOURCE" = "$TARGET" ]; then
  say "Already there. Nothing to do."
  exit 0
fi

case "$TARGET" in
  "$HOME"/Desktop/*|"$HOME"/Documents/*|"$HOME"/Downloads/*)
    say "REFUSED: $TARGET is inside a folder macOS protects, which is the problem being fixed."
    exit 1 ;;
esac

if [ -e "$TARGET" ]; then
  say "REFUSED: $TARGET already exists. Name somewhere else, or move it aside first."
  exit 1
fi

# Nothing may be committed that hard-codes where the repository lives. Checked BEFORE the move,
# because finding out afterwards means finding out from a stack trace.
# research/, data/processed/ and docs/ are excluded on purpose and for one reason: they are RECORDS.
# A dated report that says where it ran is telling the truth about that run, and rewriting it to say
# somewhere else would make it a lie. Only things that EXECUTE have to be portable.
STRAY="$(git -C "$SOURCE" grep -lI -e "$SOURCE" -- \
  ':!research/*' ':!data/processed/*' ':!docs/*' ':!web/dist/*' 2>/dev/null || true)"
if [ -n "$STRAY" ]; then
  say "These tracked files hard-code the current location and would break after the move:"
  say "$STRAY"
  say ""
  say "Fix those first - each should find the repository from its own location instead."
  exit 1
fi

RUNNING="$(pgrep -f 'weathergpt_data.workspace' || true)"
if [ -n "$RUNNING" ]; then
  say "The workspace is running (pid $RUNNING). Stop it first, then run this again:"
  say "    kill $RUNNING"
  exit 1
fi

if [ "$CHECK" = "1" ]; then
  say "--check: nothing was moved. The move is clear to run."
  exit 0
fi

say "Moving…"
mv "$SOURCE" "$TARGET"

# The launch agent names the old path in two places, so it is reinstalled rather than edited.
if [ -f "$HOME/Library/LaunchAgents/com.weathergpt.refresh.plist" ]; then
  say "Reinstalling the daily schedule at the new path…"
  "$TARGET/scripts/install_daily_schedule.sh" --remove >/dev/null 2>&1 || true
  "$TARGET/scripts/install_daily_schedule.sh"
fi

say ""
say "Done. The workspace now lives at $TARGET"
say ""
say "Next:"
say "    cd $TARGET"
say "    scripts/install_daily_schedule.sh --verify"
say "    python3 -m weathergpt_data.workspace --port 8765"
say ""
say "Any terminal still sitting in the old path will need a cd; nothing else changes."
