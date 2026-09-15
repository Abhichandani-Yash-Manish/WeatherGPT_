#!/bin/sh
# Live journeys for the two corpus features, reading the latest turn only.
set -e
export HOME=/tmp/ab-home
BIN=agent-browser
SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/reviews-tmp
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/reviews/refinement-20260915
ask_and_wait() {
  $BIN --session $SESSION eval 'location.hash="#/assistant"; 1' >/dev/null
  $BIN --session $SESSION fill "#question" "$1"
  $BIN --session $SESSION click "#ask" >/dev/null
  for step in $(seq 1 24); do
    sleep 6
    IDLE=$($BIN --session $SESSION eval '(async function(){const token=document.querySelector("meta[name=\"workspace-token\"]").content; const r=await fetch("/api/chat/progress",{headers:{"X-WeatherGPT-Token":token}}); const p=await r.json(); return p.state;})()')
    case "$IDLE" in *idle*) break;; esac
  done
  sleep 2
}
latest_turn() {
  $BIN --session $SESSION eval '(function(){var cards=document.querySelectorAll(".turn-body"); var last=cards[cards.length-1]; return JSON.stringify({turns:document.querySelectorAll(".turn").length, text:last?last.textContent.slice(0,900):null});})()'
}
latest_packet() {
  $BIN --session $SESSION eval '(function(){var buttons=Array.prototype.filter.call(document.querySelectorAll("button"), function(n){return n.textContent==="Inspect the raw packet";}); var b=buttons[buttons.length-1]; if(!b) return "no inspector"; b.click(); return "opened";})()' >/dev/null
  sleep 1
  $BIN --session $SESSION eval '(function(){var pre=document.querySelector("#evidence-drawer pre"); if(!pre) return "no packet"; var packet=JSON.parse(pre.textContent); document.getElementById("drawer-close").click(); return JSON.stringify({question:packet.question, status:packet.status, answer:(packet.answer||"").slice(0,600), plan_intents:((packet.plan||{}).tasks||[]).map(function(t){return t.kind+"/"+t.operation;}), corpus_request:((packet.plan||{}).tasks||[]).map(function(t){return t.corpus_request||null;})[0]||null, whole_document:packet.whole_document||null, edition_comparison:packet.edition_comparison||null, edition_differences:(packet.edition_differences||[]).slice(0,2), coverage:packet.retrieval_coverage||null, passages:(packet.passages||[]).length});})()'
}
$BIN --session $SESSION reload >/dev/null
sleep 4
echo '--- journey B: whole edition ---'
ask_and_wait "What does the whole Gujarat state agromet advisory bulletin say overall?"
printf 'B rendered -> '; latest_turn | head -c 500; echo
printf 'B packet   -> '; latest_packet | tee "$OUT/whole-edition-packet.json" | head -c 1200; echo
$BIN --session $SESSION screenshot "$OUT/whole-edition.png" >/dev/null
echo '--- journey C: change question ---'
ask_and_wait "What changed in the Gujarat agromet bulletin?"
printf 'C rendered -> '; latest_turn | head -c 500; echo
printf 'C packet   -> '; latest_packet | tee "$OUT/change-question-packet.json" | head -c 1200; echo
$BIN --session $SESSION screenshot "$OUT/change-single-edition.png" >/dev/null
