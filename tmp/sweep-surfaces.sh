#!/bin/sh
# Walk every surface in the real browser at desktop width and report what rendered.
set -e
export HOME=/tmp/ab-home
BIN=agent-browser
SESSION=wg-frontend
SUMMARY='JSON.stringify((() => { const open = Array.prototype.filter.call(document.querySelectorAll(".surface"), s => !s.hidden); const s = open[0]; return { open: open.length, surface: s ? s.dataset.surface : null, chars: s ? s.innerText.trim().length : 0, svgs: s ? s.querySelectorAll("svg").length : 0, tables: s ? s.querySelectorAll("table").length : 0, held: s ? s.innerText.indexOf("Request failed") >= 0 || s.innerText.indexOf("Not found") >= 0 : false }; })())'
$BIN --session $SESSION set viewport 1440 1200 >/dev/null
$BIN --session $SESSION reload >/dev/null
sleep 1
for view in overview warnings map observations forecast changes climate advisories aviation marine assistant settings; do
  $BIN --session $SESSION eval "location.hash = '#/$view'; '$view'" >/dev/null
  sleep 1
  printf '%-13s ' "$view"
  $BIN --session $SESSION eval "$SUMMARY"
done
