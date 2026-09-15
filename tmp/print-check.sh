#!/bin/sh
set -e
export HOME=/tmp/ab-home
BIN=agent-browser
SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/reviews/frontend-v2-20260915/after
$BIN --session $SESSION set viewport 1440 1200 >/dev/null
$BIN --session $SESSION eval 'window.WG.applyTheme("light"); location.hash = "#/assistant"; 1' >/dev/null
sleep 2
$BIN --session $SESSION pdf "$OUT/print-assistant.pdf" >/dev/null
ls -l "$OUT/print-assistant.pdf" | awk '{print $5, $9}'
