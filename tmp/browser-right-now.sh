#!/bin/sh
export HOME=/tmp/ab-home
export AGENT_BROWSER_SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/implementation/right-now-20260915
agent-browser open 'http://127.0.0.1:8790/#/overview' >/dev/null 2>&1
agent-browser reload >/dev/null 2>&1
sleep 5
agent-browser eval 'JSON.stringify({titles:Array.from(document.querySelectorAll(".block-title")).map(function(n){return n.textContent;}), rightNow:(function(){var blocks=Array.from(document.querySelectorAll(".block"));var found=blocks.filter(function(b){return b.textContent.indexOf("Right now at this place")===0;});return found.length?found[0].textContent.slice(0,600):"not found";})()})' 2>&1 | tail -1 | tee "$OUT/browser-overview-right-now.json"
agent-browser screenshot "$OUT/browser-overview.png" 2>&1 | tail -1
