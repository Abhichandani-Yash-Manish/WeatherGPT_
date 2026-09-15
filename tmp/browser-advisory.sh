#!/bin/sh
cd /Users/yashabhichandani/Desktop/WeatherGPT
export HOME=/tmp/ab-home
export AGENT_BROWSER_SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/implementation/chat-surface-20260915
agent-browser open 'http://127.0.0.1:8790/#/assistant' >/dev/null 2>&1
agent-browser reload >/dev/null 2>&1
sleep 3
agent-browser fill '#question' 'What does the Ahmedabad district agromet advisory say for cotton?' >/dev/null 2>&1
agent-browser click '#ask' >/dev/null 2>&1
i=0; while [ $i -lt 30 ]; do n=$(agent-browser eval '(function(){ var t=document.querySelectorAll(".turn"); var last=t[t.length-1]; return String(t.length) + "|" + (last?String(last.textContent).indexOf("bulletin")>=0:"no"); })()' 2>/dev/null | tail -1); case "$n" in '"2|true"') break;; esac; sleep 3; i=$((i+1)); done
echo "waited=$((i*3))s state=$n"
agent-browser eval '(function(){ var t=document.querySelectorAll(".turn"); var last=t[t.length-1]; return JSON.stringify(Array.from(last.querySelectorAll(".actions button")).map(function(b){return b.textContent;})); })()' 2>&1 | tail -1 | tee "$OUT/actions-advisory.json"
agent-browser eval '(function(){ var bs=Array.from(document.querySelectorAll(".actions button")); var b=bs.filter(function(x){return x.textContent.indexOf("Write the advisory brief")===0;})[0]; if(!b){return "action not found";} b.click(); return "clicked"; })()' 2>&1 | tail -1
sleep 18
agent-browser eval '(function(){ var t=(document.querySelector("#drawer-title")||{}).textContent||""; var b=((document.querySelector("#drawer-body")||{}).textContent||"").slice(0,300); return t + " || " + b; })()' 2>&1 | tail -1 | tee "$OUT/drawer-advisory-brief.txt"
agent-browser screenshot "$OUT/chat-advisory-with-brief.png" 2>&1 | tail -1
