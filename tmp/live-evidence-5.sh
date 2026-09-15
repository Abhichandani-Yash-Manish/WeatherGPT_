#!/bin/sh
# One more live turn, for a place not asked before, to watch the retrieval stages.
set -e
export HOME=/tmp/ab-home
BIN=agent-browser
SESSION=wg-frontend
SHOT=wg-shot
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/reviews/refinement-20260915
$BIN --session $SESSION eval 'location.hash="#/assistant"; 1' >/dev/null
$BIN --session $SESSION reload >/dev/null
sleep 4
COLLECT='(async function(){const token=document.querySelector("meta[name=\"workspace-token\"]").content; const input=document.getElementById("question"); input.value="Will it rain in Imphal, Manipur tomorrow between 09:30 and 12:30?"; document.getElementById("ask").click(); const out=[]; for (let i=0;i<600;i++){ await new Promise(function(r){setTimeout(r,100);}); const response=await fetch("/api/chat/progress",{headers:{"X-WeatherGPT-Token":token}}); const p=await response.json(); const host=document.getElementById("stage"); out.push({ms:i*100, state:p.state, stage:p.stage, label:p.stage_label, seen:p.stages_seen, waiting:p.queue.waiting, line:(host?host.textContent:"").slice(0,220)}); if (p.state==="idle" && i>10) break; } return JSON.stringify(out); })()'
nohup sh -c "cd /Users/yashabhichandani/Desktop/WeatherGPT && HOME=/tmp/ab-home $BIN --session $SESSION eval '$COLLECT' > '$OUT/stage-sequence-imphal.json' 2>&1" &
COLLECTOR=$!
sleep 4
$BIN --session $SHOT screenshot "$OUT/stage-line.png" >/dev/null 2>&1 || true
wait $COLLECTOR || true
