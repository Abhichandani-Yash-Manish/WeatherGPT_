#!/bin/sh
export HOME=/tmp/ab-home
export AGENT_BROWSER_SESSION=wg-frontend
echo served_briefcase_markers=$(curl -s http://127.0.0.1:8790/ | grep -c briefcase)
agent-browser reload 2>&1 | tail -1
sleep 2
agent-browser eval 'JSON.stringify({persona:Array.from(document.querySelectorAll("#persona option")).map(function(o){return o.value+"|"+o.textContent;}), hasBriefcase:!!document.querySelector("[data-view=briefcase]"), briefText:((document.querySelector("#briefcase-body")||{}).textContent||"").slice(0,300)})' 2>&1 | tail -3
