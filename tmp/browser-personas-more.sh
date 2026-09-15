#!/bin/sh
export HOME=/tmp/ab-home
export AGENT_BROWSER_SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/implementation/personas-briefcase-20260915
for who in district_officer traveller; do
  agent-browser open 'http://127.0.0.1:8790/#/assistant' >/dev/null 2>&1
  agent-browser select '#persona' $who >/dev/null 2>&1
  agent-browser reload >/dev/null 2>&1
  sleep 3
  agent-browser eval 'JSON.stringify({persona:document.querySelector("#persona").value,rail:Array.from(document.querySelectorAll(".rail [data-view]")).map(function(a){return a.getAttribute("data-view");}).slice(0,6),starters:Array.from(document.querySelectorAll(".starters button")).map(function(b){return b.textContent;}).slice(0,4)})' 2>&1 | tail -1 | tee "$OUT/browser/persona-$who.json"
done
