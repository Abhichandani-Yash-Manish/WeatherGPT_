#!/bin/sh
cd /Users/yashabhichandani/Desktop/WeatherGPT
export HOME=/tmp/ab-home AGENT_BROWSER_SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/implementation/product-review-20260915
mkdir -p "$OUT"
agent-browser open 'http://127.0.0.1:8790/#/assistant' >/dev/null 2>&1
agent-browser reload >/dev/null 2>&1
sleep 4
agent-browser eval '(function(){ return JSON.stringify({starters: Array.from(document.querySelectorAll(".starters button")).map(function(b){return b.textContent;}), placeholder: (document.querySelector("#question")||{}).placeholder, limits: Array.from(document.querySelectorAll(".welcome-limit")).map(function(n){return n.textContent.slice(0,80);})}); })()' 2>&1 | tail -1 | tee "$OUT/welcome-first-run.json"
agent-browser screenshot "$OUT/first-run-welcome.png" 2>&1 | tail -1
