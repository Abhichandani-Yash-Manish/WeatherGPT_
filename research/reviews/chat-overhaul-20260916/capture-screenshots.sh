#!/usr/bin/env bash
# README screenshots: the real workspace, a throwaway conversation store, one viewport.
# The conversation store is a copy of the ingestion store in tmp/, so the rail holds no reader data.
set -uo pipefail
export HOME=/tmp/wg-browser-home
cd /Users/yashabhichandani/Desktop/WeatherGPT
PORT=8794
mkdir -p tmp/screenshots docs/images
cp -f data/runtime/ingestion/ingestion.sqlite tmp/screenshots/ingestion.sqlite

.venv/bin/python -m weathergpt_data.workspace --port $PORT --database tmp/screenshots/ingestion.sqlite >/tmp/wg-serve-shots.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.5; done

export AGENT_BROWSER_SESSION=wgshots
agent-browser connect 9222 >/dev/null
agent-browser set viewport 1440 900 >/dev/null
agent-browser open "http://127.0.0.1:$PORT/" >/dev/null
agent-browser wait 1200 >/dev/null
agent-browser screenshot docs/images/01-ask-landing.png >/dev/null

# The first reading, observed by holding the answer in the page (no server behaviour is changed).
agent-browser eval "(() => { window.__wg = []; const orig = window.fetch; window.fetch = async function (url, options) { window.__wg.push(String(url)); const response = await orig(url, options); if (String(url) === '/api/chat') { await new Promise(r => setTimeout(r, 6000)); } return response; }; return 'hooked'; })()" >/dev/null
agent-browser fill '#question' "Will it rain in Surat tomorrow morning?" >/dev/null
agent-browser click '#ask' >/dev/null
agent-browser wait 1100 >/dev/null
agent-browser screenshot docs/images/02-first-reading.png >/dev/null
agent-browser wait --text "Source: GFS forecast" >/dev/null 2>&1
agent-browser wait 1500 >/dev/null
agent-browser screenshot docs/images/03-answer-written.png >/dev/null

agent-browser fill '#question' "hello" >/dev/null
agent-browser click '#ask' >/dev/null
agent-browser wait --text "Conversational reply" >/dev/null 2>&1
agent-browser screenshot docs/images/04-conversation.png >/dev/null

agent-browser select '#language' "hi" >/dev/null 2>&1
agent-browser fill '#question' "Will it rain in Surat tomorrow morning?" >/dev/null
agent-browser click '#ask' >/dev/null
agent-browser wait 9000 >/dev/null
agent-browser screenshot docs/images/05-hindi-answer.png >/dev/null

agent-browser open "http://127.0.0.1:$PORT/#/settings" >/dev/null
agent-browser wait --text "Model providers" >/dev/null 2>&1
agent-browser wait 800 >/dev/null
agent-browser screenshot docs/images/06-settings-providers.png >/dev/null

agent-browser open "http://127.0.0.1:$PORT/#/warnings" >/dev/null
agent-browser wait 3000 >/dev/null
agent-browser screenshot docs/images/07-warnings.png >/dev/null

agent-browser open "http://127.0.0.1:$PORT/#/overview" >/dev/null
agent-browser wait 3000 >/dev/null
agent-browser screenshot docs/images/08-today.png >/dev/null

agent-browser close >/dev/null
ls -la docs/images/
echo "SHOTS_DONE"
