#!/usr/bin/env bash
# The multilingual screenshot: a rendered evidence answer if the gate passes, otherwise a Hindi conversation.
set -uo pipefail
export HOME=/tmp/wg-browser-home
cd /Users/yashabhichandani/Desktop/WeatherGPT
PORT=8791
cp -f data/runtime/ingestion/ingestion.sqlite tmp/screenshots/ingestion.sqlite

.venv/bin/python -m weathergpt_data.workspace --port $PORT --database tmp/screenshots/ingestion.sqlite >/tmp/wg-serve-shots4.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.5; done

export AGENT_BROWSER_SESSION=wgshots4
agent-browser connect 9222 >/dev/null
agent-browser set viewport 1440 900 >/dev/null
agent-browser open "http://127.0.0.1:$PORT/" >/dev/null
agent-browser wait 1000 >/dev/null
agent-browser select '#language' "hi" >/dev/null 2>&1

kept="none"
for attempt in 1 2 3; do
  agent-browser fill '#question' "Will it rain in Surat tomorrow morning?" >/dev/null
  agent-browser click '#ask' >/dev/null
  agent-browser wait 12000 >/dev/null
  TAG=$(agent-browser eval "(() => { const cards = document.querySelectorAll('.turn'); const last = cards[cards.length-1]; return (last.querySelector('.status-line')||{}).textContent || ''; })()")
  echo "ATTEMPT=$attempt STATUS=$TAG"
  case "$TAG" in
    *Partly*) continue ;;
    *) agent-browser eval "(() => { const cards = document.querySelectorAll('.turn'); const last = cards[cards.length-1]; last.scrollIntoView({block:'start'}); return 'aligned'; })()" >/dev/null
       agent-browser wait 400 >/dev/null
       agent-browser screenshot docs/images/05-multilingual-answer.png >/dev/null
       kept="rendered-answer"
       echo "KEPT=rendered-answer"
       break ;;
  esac
done

if [ "$kept" = "none" ]; then
  agent-browser select '#language' "" >/dev/null 2>&1
  agent-browser fill '#question' "नमस्ते, आप क्या-क्या कर सकते हैं?" >/dev/null
  agent-browser click '#ask' >/dev/null
  agent-browser wait 9000 >/dev/null
  agent-browser eval "(() => { const cards = document.querySelectorAll('.turn'); const last = cards[cards.length-1]; last.scrollIntoView({block:'start'}); return 'aligned'; })()" >/dev/null
  agent-browser wait 400 >/dev/null
  agent-browser screenshot docs/images/05-multilingual-answer.png >/dev/null
  kept="hindi-conversation"
  echo "KEPT=hindi-conversation"
fi
echo "MULTILINGUAL_KEPT=$kept"
agent-browser close >/dev/null
echo "LANG_SHOT_DONE"
