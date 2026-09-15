#!/bin/sh
# Keyboard-only journey: what a person meets when they never touch the mouse.
set -e
export HOME=/tmp/ab-home
BIN=agent-browser
SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/reviews/refinement-20260915
mkdir -p "$OUT"
$BIN --session $SESSION connect 9222 >/dev/null 2>&1 || true
$BIN --session $SESSION set viewport 1440 1200 >/dev/null
$BIN --session $SESSION open http://127.0.0.1:8790/ >/dev/null
sleep 3
$BIN --session $SESSION eval 'document.body.focus(); 1' >/dev/null
: > "$OUT/keyboard-tab-path.txt"
STEP=0
while [ $STEP -lt 26 ]; do
  $BIN --session $SESSION press Tab >/dev/null
  STEP=$((STEP+1))
  $BIN --session $SESSION eval 'JSON.stringify((function(){var n=document.activeElement||{}; return {tag:n.tagName||null,id:n.id||null,cls:(n.className&&String(n.className).slice(0,40))||null,text:(n.textContent||"").trim().slice(0,42),label:n.getAttribute?(n.getAttribute("aria-label")||null):null};})())' >> "$OUT/keyboard-tab-path.txt"
done
printf 'tab_steps -> '
grep -c . "$OUT/keyboard-tab-path.txt"
printf 'palette by keyboard -> '
$BIN --session $SESSION press Meta+k >/dev/null 2>&1 || $BIN --session $SESSION press Control+k >/dev/null
sleep 1
$BIN --session $SESSION eval 'JSON.stringify({palette_open:!document.getElementById("palette").hidden, focus:document.activeElement.id||document.activeElement.tagName, items:document.querySelectorAll("#palette-body .palette-item").length})'
$BIN --session $SESSION press ArrowDown >/dev/null
$BIN --session $SESSION press ArrowDown >/dev/null
printf 'palette arrows -> '
$BIN --session $SESSION eval 'JSON.stringify({active:(document.querySelector("#palette-body .palette-item.is-active")||{textContent:null}).textContent})'
$BIN --session $SESSION press Escape >/dev/null
printf 'escape closes -> '
$BIN --session $SESSION eval 'JSON.stringify({palette_hidden:document.getElementById("palette").hidden})'
printf 'map keyboard stops -> '
$BIN --session $SESSION eval 'location.hash="#/map"; 1' >/dev/null
sleep 3
$BIN --session $SESSION eval 'JSON.stringify({district_paths:document.querySelectorAll("path.district").length, tabbable_paths:document.querySelectorAll("path.district[tabindex=\"0\"]").length, svg_tabindex:document.querySelector(".map-frame svg").getAttribute("tabindex")})'
