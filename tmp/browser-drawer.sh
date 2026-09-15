#!/bin/sh
export HOME=/tmp/ab-home
export AGENT_BROWSER_SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/implementation/personas-briefcase-20260915
agent-browser open 'http://127.0.0.1:8790/#/briefcase' >/dev/null 2>&1
sleep 3
agent-browser click '[data-brief-open]' 2>&1 | tail -1
sleep 3
agent-browser eval 'JSON.stringify({title:(document.querySelector("#drawer-title")||{}).textContent,hidden:(document.querySelector("#evidence-drawer")||{}).hidden,text:String((document.querySelector("#drawer-body")||{}).textContent).slice(0,420)})' 2>&1 | tail -1 | tee "$OUT/browser/brief-drawer.json"
agent-browser screenshot "$OUT/browser/briefcase-drawer.png" 2>&1 | tail -1
