#!/usr/bin/env bash
# One multilingual answer screenshot, retried across languages because the rendering gate can refuse a service.
set -uo pipefail
export HOME=/tmp/wg-browser-home
cd /Users/yashabhichandani/Desktop/WeatherGPT
PORT=8792
cp -f data/runtime/ingestion/ingestion.sqlite tmp/screenshots/ingestion.sqlite

.venv/bin/python -m weathergpt_data.workspace --port $PORT --database tmp/screenshots/ingestion.sqlite >/tmp/wg-serve-shots3.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.5; done

export AGENT_BROWSER_SESSION=wgshots3
agent-browser connect 9222 >/dev/null
agent-browser set viewport 1440 900 >/dev/null
agent-browser open "http://127.0.0.1:$PORT/" >/dev/null
agent-browser wait 1000 >/dev/null

for code in hi ta gu mr; do
  agent-browser select '#language' "$code" >/dev/null 2>&1
  agent-browser fill '#question' "Will it rain in Surat tomorrow morning?" >/dev/null
  agent-browser click '#ask' >/dev/null
  agent-browser wait 11000 >/dev/null
  TAG=$(agent-browser eval "(() => { const cards = document.querySelectorAll('.turn'); const last = cards[cards.length-1]; return (last.querySelector('.status-line')||{}).textContent || ''; })()")
  echo "LANG=$code STATUS=$TAG"
  if [ "${TAG#*Partly answered}" = "$TAG" ]; then
    agent-browser eval "(() => { const cards = document.querySelectorAll('.turn'); const last = cards[cards.length-1]; last.scrollIntoView({block:'start'}); return 'aligned'; })()" >/dev/null
    agent-browser wait 400 >/dev/null
    agent-browser screenshot docs/images/05-multilingual-answer.png >/dev/null
    echo "KEPT=$code"
    break
  fi
  agent-browser fill '#question' "hello" >/dev/null
  agent-browser click '#ask' >/dev/null
  agent-browser wait 6000 >/dev/null
done
agent-browser close >/dev/null
echo "LANG_SHOT_DONE"
