#!/bin/sh
# Refresh the after-fix evidence set: every surface, the palette, the raw inspector,
# the night desk and one phone-width frame.
set -e
export HOME=/tmp/ab-home
BIN=agent-browser
SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/reviews/frontend-v2-20260915/after
$BIN --session $SESSION set viewport 1440 1200 >/dev/null
$BIN --session $SESSION eval 'window.WG.applyTheme("light"); window.scrollTo(0,0); 1' >/dev/null
for view in overview warnings map forecast changes observations advisories climate aviation marine settings; do
  $BIN --session $SESSION eval "location.hash = '#/$view'; window.scrollTo(0,0); 1" >/dev/null
  sleep 2
  $BIN --session $SESSION screenshot "$OUT/surface-$view.png" >/dev/null
done
$BIN --session $SESSION eval 'location.hash = "#/assistant"; 1' >/dev/null
sleep 2
$BIN --session $SESSION eval 'window.scrollTo(0, document.documentElement.scrollHeight); 1' >/dev/null
sleep 1
$BIN --session $SESSION screenshot "$OUT/surface-assistant.png" >/dev/null
$BIN --session $SESSION eval '(function(){document.getElementById("palette-open").click(); var input=document.getElementById("palette-input"); input.value="surat"; input.dispatchEvent(new Event("input",{bubbles:true})); return 1;})()' >/dev/null
sleep 1
$BIN --session $SESSION screenshot "$OUT/palette.png" >/dev/null
$BIN --session $SESSION eval '(function(){document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true})); return 1;})()' >/dev/null
$BIN --session $SESSION eval '(function(){var b=Array.prototype.filter.call(document.querySelectorAll("button"), function(n){return n.textContent==="Inspect the raw packet";})[0]; b.click(); return 1;})()' >/dev/null
sleep 1
$BIN --session $SESSION screenshot "$OUT/raw-inspector.png" >/dev/null
$BIN --session $SESSION eval '(function(){document.getElementById("drawer-close").click(); return 1;})()' >/dev/null
$BIN --session $SESSION eval 'window.WG.applyTheme("dark"); location.hash = "#/assistant"; 1' >/dev/null
sleep 2
$BIN --session $SESSION screenshot "$OUT/assistant-dark.png" >/dev/null
$BIN --session $SESSION eval 'location.hash = "#/map"; 1' >/dev/null
sleep 3
$BIN --session $SESSION screenshot "$OUT/map-dark.png" >/dev/null
$BIN --session $SESSION eval 'window.WG.applyTheme("light"); location.hash = "#/changes"; 1' >/dev/null
sleep 2
$BIN --session $SESSION screenshot "$OUT/changes.png" >/dev/null
$BIN --session $SESSION set viewport 390 844 >/dev/null
$BIN --session $SESSION eval 'location.hash = "#/assistant"; window.scrollTo(0,0); 1' >/dev/null
sleep 2
$BIN --session $SESSION screenshot "$OUT/mobile-assistant.png" >/dev/null
ls -1 "$OUT"/*.png | wc -l
