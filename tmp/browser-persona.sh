#!/bin/sh
export HOME=/tmp/ab-home
export AGENT_BROWSER_SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/implementation/personas-briefcase-20260915
agent-browser open 'http://127.0.0.1:8790/#/assistant' >/dev/null 2>&1
agent-browser select '#persona' farmer >/dev/null 2>&1
agent-browser reload >/dev/null 2>&1
sleep 3
agent-browser eval 'JSON.stringify({selected:document.querySelector("#persona").value,rail:Array.from(document.querySelectorAll(".rail [data-view]")).map(function(a){return a.getAttribute("data-view");}),starters:Array.from(document.querySelectorAll(".starters button")).map(function(b){return b.textContent;}),named:(document.querySelector(".welcome-limit")||{}).textContent})' 2>&1 | tail -1 | tee "$OUT/browser/persona-on-page.json"
agent-browser screenshot "$OUT/browser/welcome-as-farmer.png" 2>&1 | tail -1
