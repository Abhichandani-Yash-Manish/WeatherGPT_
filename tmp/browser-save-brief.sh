#!/bin/sh
export HOME=/tmp/ab-home
export AGENT_BROWSER_SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/implementation/personas-briefcase-20260915
agent-browser open 'http://127.0.0.1:8790/#/warnings' >/dev/null 2>&1
sleep 4
agent-browser find text 'Write the alert brief' click 2>&1 | tail -1
i=0
while [ $i -lt 40 ]; do
  state=$(agent-browser eval 'String(!!document.querySelector("[aria-label=\"Keep this brief in the local briefcase\"]"))' 2>&1 | tail -1)
  case "$state" in *true*) break;; esac
  sleep 5
  i=$((i+1))
done
echo "waited=$((i*5))s save_button=$state"
agent-browser eval 'String((document.querySelector("#drawer-body")||{}).textContent).slice(0,200)' 2>&1 | tail -1
agent-browser click '[aria-label="Keep this brief in the local briefcase"]' 2>&1 | tail -1
sleep 6
agent-browser eval 'JSON.stringify({note:Array.from(document.querySelectorAll("#drawer-body .block-note")).map(function(n){return n.textContent;}),save:(document.querySelector("[aria-label=\"Keep this brief in the local briefcase\"]")||{}).textContent})' 2>&1 | tail -1 | tee "$OUT/browser/brief-save-in-page.json"
agent-browser screenshot "$OUT/browser/brief-saved.png" 2>&1 | tail -1
agent-browser open 'http://127.0.0.1:8790/#/briefcase' >/dev/null 2>&1
sleep 3
agent-browser eval 'JSON.stringify({count:document.querySelectorAll(".brief-item").length,titles:Array.from(document.querySelectorAll(".brief-title")).map(function(n){return n.textContent;})})' 2>&1 | tail -1
