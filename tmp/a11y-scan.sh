#!/bin/sh
# Automated accessibility scan across surfaces in both appearances, after a fresh load.
set -e
export HOME=/tmp/ab-home
BIN=agent-browser
SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/reviews/frontend-v2-20260915/after
$BIN --session $SESSION set viewport 1440 1200 >/dev/null
$BIN --session $SESSION open "http://127.0.0.1:8790/" >/dev/null
sleep 2
$BIN --session $SESSION eval 'window.WG.applyTheme("light"); 1' >/dev/null
sleep 1
$BIN --session $SESSION eval 'JSON.stringify({mute: getComputedStyle(document.documentElement).getPropertyValue("--mute").trim(), theme: document.documentElement.getAttribute("data-theme")})'
for view in assistant warnings map changes settings; do
  $BIN --session $SESSION eval "location.hash = '#/$view'; 1" >/dev/null
  sleep 1
  $BIN --session $SESSION a11y --json > "$OUT/a11y-light-$view.json" 2>/dev/null || true
done
$BIN --session $SESSION eval 'window.WG.applyTheme("dark"); 1' >/dev/null
sleep 1
$BIN --session $SESSION eval 'JSON.stringify({mute: getComputedStyle(document.documentElement).getPropertyValue("--mute").trim(), theme: document.documentElement.getAttribute("data-theme")})'
for view in assistant warnings map changes settings; do
  $BIN --session $SESSION eval "location.hash = '#/$view'; 1" >/dev/null
  sleep 1
  $BIN --session $SESSION a11y --json > "$OUT/a11y-dark-$view.json" 2>/dev/null || true
done
$BIN --session $SESSION eval 'window.WG.applyTheme("light"); 1' >/dev/null
ls "$OUT"/a11y-light-*.json "$OUT"/a11y-dark-*.json | wc -l
