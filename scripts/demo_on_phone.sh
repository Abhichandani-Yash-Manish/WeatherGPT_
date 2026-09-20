#!/usr/bin/env bash
# Put this workspace on a phone, over HTTPS, in about a minute.
#
# WHY A TUNNEL AND NOT THE LAN. The Web Push API, service worker registration and PWA install all
# require a secure context. A phone opening http://192.168.1.x:8765 gets none of them - the browser
# refuses before any of this product's code runs. localhost is also a secure context, which is why
# none of this shows up while developing on the laptop. So the phone needs HTTPS, and a tunnel is
# the shortest way to it. docs/118 covers the real deployment; this is for trying the journeys today.
#
# WHAT IT DOES. Starts a Cloudflare quick tunnel, reads the hostname it hands out, and starts the
# workspace bound to loopback with that hostname allowed and an access key required. The hostname
# must be passed to the server: the DNS-rebinding guard refuses a Host header it was not told about,
# which otherwise looks like a total outage rather than a configuration error.
#
#     ./scripts/demo_on_phone.sh
#
# Stop it with Ctrl-C; both processes are cleaned up.

set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-8765}"

if ! command -v cloudflared > /dev/null 2>&1; then
  cat <<'MISSING'
cloudflared is not installed, and it is what provides the HTTPS hostname.

  macOS:  brew install cloudflared
  Linux:  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

A quick tunnel needs no Cloudflare account and no sign-in. If you would rather not install it, the
alternative is the real deployment in docs/118 - there is no third option, because a plain LAN
address cannot carry web push no matter how the workspace is configured.
MISSING
  exit 1
fi

if [ ! -f web/dist/index.html ]; then
  echo "web/dist is not built. Run: (cd frontend && npm ci && npm run build)" >&2
  exit 1
fi
if [ ! -f web/dist/sw.js ] || [ ! -f web/dist/manifest.webmanifest ]; then
  echo "web/dist is missing sw.js or manifest.webmanifest - rebuild the frontend so the phone can" >&2
  echo "install the app and receive a push." >&2
  exit 1
fi

ACCESS_KEY="${WEATHERGPT_ACCESS_KEY:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(9))')}"
LOG="$(mktemp -t wgpt-tunnel)"
SERVER_PID=""
TUNNEL_PID=""

cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2> /dev/null || true
  [ -n "$TUNNEL_PID" ] && kill "$TUNNEL_PID" 2> /dev/null || true
  rm -f "$LOG"
}
trap cleanup EXIT INT TERM

echo "Opening a tunnel..."
cloudflared tunnel --url "http://127.0.0.1:${PORT}" --no-autoupdate > "$LOG" 2>&1 &
TUNNEL_PID=$!

HOST=""
for _ in $(seq 1 40); do
  HOST="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" 2> /dev/null | head -1 || true)"
  [ -n "$HOST" ] && break
  sleep 1
done

if [ -z "$HOST" ]; then
  echo "The tunnel did not report a hostname within 40 seconds. Its output:" >&2
  tail -20 "$LOG" >&2
  exit 1
fi

BARE_HOST="${HOST#https://}"

# The hostname is random per run, so the server has to be told it AFTER the tunnel exists. Bound to
# loopback: the tunnel is the only way in, and the access key is what keeps that way in closed.
WEATHERGPT_ACCESS_KEY="$ACCESS_KEY" python3 -m weathergpt_data.workspace \
  --port "$PORT" --public-host "$BARE_HOST" &
SERVER_PID=$!

sleep 6
cat <<BANNER

────────────────────────────────────────────────────────────────────
  Open this on the phone:

      ${HOST}/?k=${ACCESS_KEY}

  The key is remembered in a cookie after the first open, so later
  visits are just ${HOST}

  The tunnel hostname changes every run. Anyone with this link can
  use this workspace and spend its provider budget, so treat it as
  a door key and stop this script when you are done.
────────────────────────────────────────────────────────────────────

  What to try, in this order:

  1. INSTALL IT.  Chrome: menu, "Add to Home screen". Safari: share,
     "Add to Home Screen". It should install under its own icon and
     open without browser chrome.                             (M2)

  2. ASK SOMETHING with the keyboard closed as far as possible - a
     real question, in Hindi or Gujarati if you like.          (F8c)

  3. SAVE A WATCH on a district and allow notifications when the
     phone asks. Then, on the laptop:

         python3 scripts/check_watches.py

     It prints what it dispatched, by channel. "web_push=1" means it
     reached the phone; "local_inbox=1" means the subscription did
     not register and the phone will stay silent - tell me if you
     see that. The phone should buzz with the official wording, and
     acknowledging should land back in the ledger.      (F4a, X3, F4b)

  4. TURN OFF Wi-Fi AND MOBILE DATA mid-question, then turn them
     back on. The page should say what it could not reach, and
     recover - not sit silent or invent an answer.             (M1)

  Tell me what actually happened, including anything that did not
  work. A row on the scorecard is only met when a person has done
  the journey, not when the code that would support it exists.
────────────────────────────────────────────────────────────────────

BANNER

wait "$SERVER_PID"
