#!/bin/sh
export HOME=/tmp/ab-home
export AGENT_BROWSER_SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/implementation/personas-briefcase-20260915
mkdir -p "$OUT/browser"
echo '--- 1. the reading position is a control on the page'
agent-browser open 'http://127.0.0.1:8790/#/assistant' >/dev/null 2>&1
agent-browser select '#persona' farmer >/dev/null 2>&1
agent-browser reload >/dev/null 2>&1
sleep 3
agent-browser eval 'JSON.stringify({selected:document.querySelector("#persona").value,rail:Array.from(document.querySelectorAll(".rail [data-view]")).map(function(a){return a.getAttribute("data-view");}).slice(0,3),starters:Array.from(document.querySelectorAll(".starters button")).map(function(b){return b.textContent;}).slice(0,4),named:(document.querySelector(".welcome-limit")||{}).textContent})' 2>&1 | tail -1 | tee "$OUT/browser/persona-on-page.json"
agent-browser screenshot "$OUT/browser/welcome-as-farmer.png" 2>&1 | tail -1
echo '--- 2. open a kept brief from the briefcase'
agent-browser open 'http://127.0.0.1:8790/#/briefcase' >/dev/null 2>&1
sleep 3
agent-browser find text 'Open' click 2>&1 | tail -1
sleep 2
agent-browser eval 'String((document.querySelector("#drawer-body")||{}).textContent).slice(0,600)' 2>&1 | tail -1 | tee "$OUT/browser/brief-drawer.txt"
agent-browser screenshot "$OUT/browser/briefcase-drawer.png" 2>&1 | tail -1
echo '--- 3. export through the page download path'
agent-browser open 'http://127.0.0.1:8790/#/briefcase' >/dev/null 2>&1
sleep 3
agent-browser download '[data-brief-export]' "$OUT/browser/exported-brief.md" 2>&1 | tail -2
head -6 "$OUT/browser/exported-brief.md" 2>&1
echo '--- files'
ls -la "$OUT/browser" | tail -8
