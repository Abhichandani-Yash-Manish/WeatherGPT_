#!/usr/bin/env bash
# Browser check on DeepSeek: the page, the engine and the paid endpoint end to end.
set -uo pipefail
export HOME=/tmp/wg-browser-home
cd /Users/yashabhichandani/Desktop/WeatherGPT
OUT=research/reviews/chat-overhaul-20260916
PORT=8796

.venv/bin/python -m weathergpt_data.workspace --port $PORT >/tmp/wg-serve-ds.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.5; done

export AGENT_BROWSER_SESSION=wgds
agent-browser connect 9222 >/dev/null
agent-browser open "http://127.0.0.1:$PORT/" >/dev/null
agent-browser set viewport 1280 900 >/dev/null

agent-browser fill '#question' "hello" >/dev/null
agent-browser click '#ask' >/dev/null
agent-browser wait --text "Conversational reply" >/dev/null 2>&1
echo "GREETING_STATUS=$(agent-browser get text '.turn .status-line')"
echo "GREETING_ANSWER=$(agent-browser get text '.turn .answer-copy')"

agent-browser fill '#question' "Will it rain in Surat tomorrow morning?" >/dev/null
agent-browser click '#ask' >/dev/null
agent-browser wait --text "Evidence retrieved" >/dev/null 2>&1
agent-browser wait 1500 >/dev/null
echo "WEATHER_ANSWER=$(agent-browser eval "Array.from(document.querySelectorAll('.turn .answer-copy')).pop().textContent")"
echo "WEATHER_TAGS=$(agent-browser eval "Array.from(document.querySelectorAll('.turn')).pop().querySelector('.status-line').textContent")"
echo "PROVIDER_IN_TRACE=$(agent-browser eval "Array.from(document.querySelectorAll('.turn')).pop().textContent.indexOf('deepseek') >= 0")"
agent-browser screenshot "$OUT/browser-deepseek.png" >/dev/null
agent-browser close >/dev/null
echo "BROWSER_DEEPSEEK_DONE"
