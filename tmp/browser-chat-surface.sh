#!/bin/sh
set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
(lsof -ti tcp:8790 | xargs -r kill) 2>/dev/null || true
sleep 1
env HOME=/Users/yashabhichandani nohup python3 -m weathergpt_data.workspace --port 8790 > /tmp/wg-server.log 2>&1 &
sleep 4
export HOME=/tmp/ab-home
export AGENT_BROWSER_SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/implementation/chat-surface-20260915
mkdir -p "$OUT"
agent-browser open 'http://127.0.0.1:8790/#/assistant' >/dev/null 2>&1
agent-browser reload >/dev/null 2>&1
sleep 3
agent-browser fill '#question' 'Is any warning in force for Patna, Bihar today?' >/dev/null 2>&1
agent-browser click '#ask' >/dev/null 2>&1
i=0; while [ $i -lt 20 ]; do if agent-browser eval 'String(document.querySelectorAll(".turn").length)' 2>/dev/null | grep -q '^"1"$'; then break; fi; sleep 3; i=$((i+1)); done
echo '--- actions on the warning answer'
agent-browser eval 'JSON.stringify(Array.from(document.querySelectorAll(".turn .actions button")).map(function(b){return b.textContent;}))' 2>&1 | tail -1 | tee "$OUT/actions-warning.json"
agent-browser click '.turn .actions button[aria-label], .turn .actions button' >/dev/null 2>&1 || true
echo '--- click the alert brief action'
agent-browser eval 'var bs=Array.from(document.querySelectorAll(".actions button")); var b=bs.filter(function(x){return x.textContent.indexOf("Write the alert brief")===0;})[0]; if(b){b.click(); return "clicked";} return "not found";' 2>&1 | tail -1
sleep 12
agent-browser eval 'String((document.querySelector("#drawer-title")||{}).textContent) + " || " + String((document.querySelector("#drawer-body")||{}).textContent).slice(0,320)' 2>&1 | tail -1 | tee "$OUT/drawer-alert-brief.txt"
agent-browser screenshot "$OUT/warning-answer-and-alert-brief.png" 2>&1 | tail -1
echo '--- retrieval account rendered?'
agent-browser eval 'String(document.body.textContent.indexOf("What was retrieved, and what is missing"))' 2>&1 | tail -1
agent-browser open 'http://127.0.0.1:8790/#/settings' >/dev/null 2>&1
sleep 4
agent-browser eval 'var blocks=Array.from(document.querySelectorAll(".block")); var card=blocks.filter(function(b){return b.textContent.indexOf("Model providers")===0;})[0]; return card?card.textContent.slice(0,420):"not found";' 2>&1 | tail -1 | tee "$OUT/settings-provider-card.txt"
agent-browser screenshot "$OUT/settings-provider.png" 2>&1 | tail -1
