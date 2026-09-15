#!/bin/sh
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
agent-browser eval '(function(){ return JSON.stringify(Object.keys((window.WG||{}).briefDrawers||{})); })()' 2>&1 | tail -1
agent-browser fill '#question' 'Is any warning in force for Patna, Bihar today?' >/dev/null 2>&1
agent-browser click '#ask' >/dev/null 2>&1
i=0; while [ $i -lt 24 ]; do n=$(agent-browser eval '(function(){ return String(document.querySelectorAll(".turn").length); })()' 2>/dev/null | tail -1); case "$n" in '"1"') break;; esac; sleep 3; i=$((i+1)); done
echo '--- actions offered on the warning answer'
agent-browser eval '(function(){ return JSON.stringify(Array.from(document.querySelectorAll(".turn .actions button")).map(function(b){return b.textContent;})); })()' 2>&1 | tail -1 | tee "$OUT/actions-warning.json"
echo '--- open the alert brief drawer from the chat action'
agent-browser eval '(function(){ var bs=Array.from(document.querySelectorAll(".actions button")); var b=bs.filter(function(x){return x.textContent.indexOf("Write the alert brief")===0;})[0]; if(!b){return "action not found";} b.click(); return "clicked"; })()' 2>&1 | tail -1
sleep 15
agent-browser eval '(function(){ var t=(document.querySelector("#drawer-title")||{}).textContent||""; var b=((document.querySelector("#drawer-body")||{}).textContent||"").slice(0,300); return t + " || " + b; })()' 2>&1 | tail -1 | tee "$OUT/drawer-alert-brief.txt"
agent-browser screenshot "$OUT/chat-warning-with-alert-brief.png" 2>&1 | tail -1
echo '--- advisory brief action on an agriculture answer'
agent-browser fill '#question' 'What does the Ahmedabad district agromet advisory say for cotton?' >/dev/null 2>&1
agent-browser click '#ask' >/dev/null 2>&1
i=0; while [ $i -lt 24 ]; do n=$(agent-browser eval '(function(){ return String(document.querySelectorAll(".turn").length); })()' 2>/dev/null | tail -1); case "$n" in '"2"') break;; esac; sleep 3; i=$((i+1)); done
agent-browser eval '(function(){ var turns=document.querySelectorAll(".turn"); var last=turns[turns.length-1]; return JSON.stringify(Array.from(last.querySelectorAll(".actions button")).map(function(b){return b.textContent;})); })()' 2>&1 | tail -1 | tee "$OUT/actions-advisory.json"
agent-browser eval '(function(){ var bs=Array.from(document.querySelectorAll(".actions button")); var b=bs.filter(function(x){return x.textContent.indexOf("Write the advisory brief")===0;})[0]; if(!b){return "action not found";} b.click(); return "clicked"; })()' 2>&1 | tail -1
sleep 15
agent-browser eval '(function(){ var t=(document.querySelector("#drawer-title")||{}).textContent||""; var b=((document.querySelector("#drawer-body")||{}).textContent||"").slice(0,260); return t + " || " + b; })()' 2>&1 | tail -1 | tee "$OUT/drawer-advisory-brief.txt"
agent-browser screenshot "$OUT/chat-advisory-with-brief.png" 2>&1 | tail -1
echo '--- settings surface: the key flow'
agent-browser open 'http://127.0.0.1:8790/#/settings' >/dev/null 2>&1
sleep 5
agent-browser eval '(function(){ var blocks=Array.from(document.querySelectorAll(".block")); var card=blocks.filter(function(b){return b.textContent.indexOf("Model providers")===0;})[0]; return card?card.textContent.slice(0,400):"not found"; })()' 2>&1 | tail -1 | tee "$OUT/settings-provider-card.txt"
agent-browser screenshot "$OUT/settings-provider.png" 2>&1 | tail -1
