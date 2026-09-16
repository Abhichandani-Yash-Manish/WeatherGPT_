#!/usr/bin/env bash
# Re-shoot the answer cards with their top aligned: header, status, lead, facts and ruler in frame.
set -uo pipefail
export HOME=/tmp/wg-browser-home
cd /Users/yashabhichandani/Desktop/WeatherGPT
PORT=8793
mkdir -p tmp/screenshots docs/images
cp -f data/runtime/ingestion/ingestion.sqlite tmp/screenshots/ingestion.sqlite

.venv/bin/python -m weathergpt_data.workspace --port $PORT --database tmp/screenshots/ingestion.sqlite >/tmp/wg-serve-shots2.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.5; done

export AGENT_BROWSER_SESSION=wgshots2
agent-browser connect 9222 >/dev/null
agent-browser set viewport 1440 900 >/dev/null
agent-browser open "http://127.0.0.1:$PORT/" >/dev/null
agent-browser wait 1000 >/dev/null

agent-browser fill '#question' "Will it rain in Surat tomorrow morning?" >/dev/null
agent-browser click '#ask' >/dev/null
agent-browser wait --text "Source: GFS forecast" >/dev/null 2>&1
agent-browser wait 1500 >/dev/null
agent-browser eval "(() => { const cards = document.querySelectorAll('.turn'); const last = cards[cards.length-1]; last.scrollIntoView({block:'start'}); return 'aligned'; })()" >/dev/null
agent-browser wait 400 >/dev/null
agent-browser screenshot docs/images/03-answer-written.png >/dev/null
echo "WEATHER_CARD=$(agent-browser eval "(() => { const cards = document.querySelectorAll('.turn'); const last = cards[cards.length-1]; return last.textContent.replace(/\s+/g,' ').slice(0,240); })()")"

agent-browser select '#language' "hi" >/dev/null 2>&1
agent-browser fill '#question' "Will it rain in Surat tomorrow morning?" >/dev/null
agent-browser click '#ask' >/dev/null
agent-browser wait 11000 >/dev/null
agent-browser eval "(() => { const cards = document.querySelectorAll('.turn'); const last = cards[cards.length-1]; last.scrollIntoView({block:'start'}); return 'aligned'; })()" >/dev/null
agent-browser wait 400 >/dev/null
agent-browser screenshot docs/images/05-hindi-answer.png >/dev/null
echo "HINDI_CARD=$(agent-browser eval "(() => { const cards = document.querySelectorAll('.turn'); const last = cards[cards.length-1]; return last.textContent.replace(/\s+/g,' ').slice(0,240); })()")"

agent-browser close >/dev/null
echo "RESHOOT_DONE"
