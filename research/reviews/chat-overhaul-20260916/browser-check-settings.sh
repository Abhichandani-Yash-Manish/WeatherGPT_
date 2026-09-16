#!/usr/bin/env bash
# Browser check: the settings surface states the live provider state.
set -uo pipefail
export HOME=/tmp/wg-browser-home
cd /Users/yashabhichandani/Desktop/WeatherGPT
OUT=research/reviews/chat-overhaul-20260916
PORT=8795

.venv/bin/python -m weathergpt_data.workspace --port $PORT >/tmp/wg-serve-settings.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.5; done

export AGENT_BROWSER_SESSION=wgsettings
agent-browser connect 9222 >/dev/null
agent-browser open "http://127.0.0.1:$PORT/#/settings" >/dev/null
agent-browser wait --text "Model providers" >/dev/null 2>&1
echo "CARD=$(agent-browser eval "(() => { const node = [...document.querySelectorAll('.block')].find(b => b.textContent.indexOf('Model providers') >= 0); return node ? node.textContent.replace(/\s+/g, ' ').slice(0, 700) : 'not found'; })()")"
agent-browser screenshot "$OUT/browser-settings-providers.png" >/dev/null
agent-browser close >/dev/null
echo "BROWSER_SETTINGS_DONE"
