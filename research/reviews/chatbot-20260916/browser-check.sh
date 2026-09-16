#!/usr/bin/env bash
# Browser acceptance for the conversational front door. Runs the real page against the real loopback
# workspace in Chrome via agent-browser. The only intervention is inside the page: the answer request is
# delayed in the page's own fetch so the placeholder can be observed, which is stated in the record.
set -uo pipefail
# Chrome is launched by the check's caller with CDP on 9222 and a workspace-writable HOME; the
# default socket directory under the real HOME is not writable in this sandbox.
export HOME=/tmp/wg-browser-home
cd /Users/yashabhichandani/Desktop/WeatherGPT
OUT=research/reviews/chatbot-20260916
PORT=8799

.venv/bin/python -m weathergpt_data.workspace --port $PORT >/tmp/wg-serve.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.5; done

export AGENT_BROWSER_SESSION=wgchat
agent-browser connect 9222 >/dev/null
agent-browser open "http://127.0.0.1:$PORT/" >/dev/null
agent-browser set viewport 1280 900 >/dev/null

echo "LANDING_SURFACE=$(agent-browser eval "document.querySelector('.surface:not([hidden])').getAttribute('data-surface')")"
echo "LANDING_HASH=$(agent-browser eval "window.location.hash")"
echo "REGISTER_OPTIONS=$(agent-browser get count '.register-option')"
echo "THREAD_REGISTER=$(agent-browser get attr '#thread' data-register)"
agent-browser screenshot "$OUT/browser-01-landing.png" >/dev/null

# The reader chooses the register, and the card text must not change with it.
agent-browser find text "Full evidence" click >/dev/null
echo "AFTER_FULL=$(agent-browser get attr '#thread' data-register)"
echo "STORED_REGISTER=$(agent-browser eval "window.localStorage.getItem('weathergpt.register')")"

# Instrument the page: record every request it makes, and delay the answer so the wait is observable.
agent-browser eval "window.__wg = []; const orig = window.fetch; window.fetch = async function (url, options) { window.__wg.push(String(url)); const response = await orig(url, options); if (String(url) === '/api/chat') { await new Promise(r => setTimeout(r, 5000)); } return response; }; 'hooked'" >/dev/null
agent-browser fill '#question' "Will it rain in Surat tomorrow morning?" >/dev/null
agent-browser click '#ask' >/dev/null
agent-browser wait 900 >/dev/null
echo "WORKING_TITLE=$(agent-browser get text '.working-title')"
echo "WORKING_READING=$(agent-browser get text '.working-reading')"
echo "STAGE_LINE=$(agent-browser get text '#stage')"
agent-browser screenshot "$OUT/browser-02-first-reading.png" >/dev/null
agent-browser wait --text "Forecast rainfall" >/dev/null 2>&1
echo "ANSWER_STATUS=$(agent-browser get text '.turn .status-line')"
echo "ANSWER_TEXT=$(agent-browser get text '.turn .answer-copy')"
echo "REQUESTS=$(agent-browser eval "JSON.stringify(window.__wg)")"
echo "QUICK_REPLIES=$(agent-browser eval "JSON.stringify(Array.from(document.querySelectorAll('.quick-reply')).map(b => b.textContent))")"
agent-browser screenshot "$OUT/browser-03-answer.png" >/dev/null

# The register decides what is shown, and the card keeps its text.
agent-browser find text "Brief" click >/dev/null
echo "BRIEF_RECEIPT_DISPLAY=$(agent-browser eval "getComputedStyle(document.querySelector('.turn .receipt')).display")"
echo "BRIEF_DISCLOSURE_DISPLAY=$(agent-browser eval "getComputedStyle(document.querySelector('.turn .disclosure')).display")"
echo "BRIEF_ANSWER_PRESENT=$(agent-browser eval "document.querySelector('.turn .answer-copy').textContent.length > 0")"
agent-browser screenshot "$OUT/browser-04-brief.png" >/dev/null
agent-browser find text "Conversational" click >/dev/null
echo "CONVERSATIONAL_RECEIPT_DISPLAY=$(agent-browser eval "getComputedStyle(document.querySelector('.turn .receipt')).display")"
agent-browser close >/dev/null
echo "BROWSER_CHECK_DONE"
