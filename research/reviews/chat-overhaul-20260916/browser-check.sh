#!/usr/bin/env bash
# Browser check for a conversational turn: the real page, the real engine, the real provider chain.
set -uo pipefail
export HOME=/tmp/wg-browser-home
cd /Users/yashabhichandani/Desktop/WeatherGPT
OUT=research/reviews/chat-overhaul-20260916
PORT=8797

.venv/bin/python -m weathergpt_data.workspace --port $PORT >/tmp/wg-serve-chat.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.5; done

export AGENT_BROWSER_SESSION=wgchat83
agent-browser connect 9222 >/dev/null
agent-browser open "http://127.0.0.1:$PORT/" >/dev/null
agent-browser set viewport 1280 900 >/dev/null
agent-browser fill '#question' "hello" >/dev/null
agent-browser click '#ask' >/dev/null
agent-browser wait --text "Conversational reply" >/dev/null 2>&1
echo "STATUS_LINE=$(agent-browser get text '.turn .status-line')"
echo "TITLE=$(agent-browser get text '.turn h2')"
echo "ANSWER=$(agent-browser get text '.turn .answer-copy')"
echo "FACTS=$(agent-browser get count '.turn .fact')"
echo "RECEIPT=$(agent-browser get count '.turn .receipt')"
echo "LEAD=$(agent-browser get count '.turn .lead')"
agent-browser screenshot "$OUT/browser-conversation.png" >/dev/null
agent-browser close >/dev/null
echo "BROWSER_CHAT_DONE"
