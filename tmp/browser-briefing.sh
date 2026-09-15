#!/bin/sh
export HOME=/tmp/ab-home
export AGENT_BROWSER_SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/implementation/briefing-20260915
agent-browser open 'http://127.0.0.1:8790/#/briefcase' >/dev/null 2>&1
agent-browser reload >/dev/null 2>&1
sleep 4
agent-browser eval 'JSON.stringify({title:Array.from(document.querySelectorAll(".block-title")).map(function(n){return n.textContent;}), briefing:(document.querySelectorAll(".block")[1]||{}).textContent})' 2>&1 | tail -1 | tee "$OUT/browser-briefing-block.json"
agent-browser screenshot "$OUT/browser-briefing.png" 2>&1 | tail -1
