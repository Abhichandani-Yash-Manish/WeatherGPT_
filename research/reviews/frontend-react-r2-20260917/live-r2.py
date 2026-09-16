"""Live acceptance of the React build as the workspace server actually serves it.

The server is started in this process with frontend='react', so every byte below came over HTTP from the
loopback server a browser would talk to. Nothing here is a mock: the page, the hashed assets, the session
token contract and one real conversation turn are all read the way a client reads them.

    .venv/bin/python research/reviews/frontend-react-r2-20260917/live-r2.py
"""
import json, os, re, sys, threading, time, urllib.request, urllib.error, uuid
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from weathergpt_data.workspace import Workspace, make_server

record = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "checks": [], "basis": "live loopback HTTP, React build in web/dist"}

def check(name, ok, detail):
    record["checks"].append({"check": name, "ok": bool(ok), "detail": str(detail)[:400]})

workspace = Workspace(frontend="react")
server = make_server(workspace, 0)
port = server.server_port
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = "http://127.0.0.1:" + str(port)

def fetch(path, token=None, method="GET", body=None):
    request = urllib.request.Request(base + path, method=method)
    if token: request.add_header("X-WeatherGPT-Token", token)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, data=data, timeout=120) as answer:
            return answer.status, answer.read().decode("utf-8", "replace"), dict(answer.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace"), dict(error.headers)

try:
    status, page, headers = fetch("/")
    check("the page is served at the root", status == 200 and "<div id=\"root\" data-boot=\"react\">" in page, "HTTP " + str(status))
    check("the session token is injected into the built page", "__WORKSPACE_TOKEN__" not in page and re.search(r'name="workspace-token" content="[^"]+"', page) is not None, "token meta tag carries a per-process value")
    check("the page carries no inline script", re.search(r"<script(?![^>]*\\bsrc=)[^>]*>[^<]", page) is None, "every script tag carries a src")
    check("the page loads nothing off-origin", not re.findall(r"https?://[^\"'<> ]+", page), "no external URL in the served HTML")
    check("the strict page policy is sent", headers.get("Content-Security-Policy", "").startswith("default-src 'self'"), headers.get("Content-Security-Policy", "")[:120])

    entry = re.search(r'<script type="module"[^>]*src="([^"]+)"', page)
    entry_path = entry.group(1) if entry else ""
    status, script, assets = fetch(entry_path)
    check("the module entry is served", status == 200 and len(script) > 1000, entry_path + " HTTP " + str(status) + ", " + str(len(script)) + " bytes")
    check("a hashed asset is immutable-cached", "immutable" in assets.get("Cache-Control", ""), assets.get("Cache-Control", "no header"))

    token = re.search(r'name="workspace-token" content="([^"]+)"', page).group(1)
    status, body, _ = fetch("/api/health", token=token)
    check("an authorised read answers", status == 200 and json.loads(body).get("available") is True, "HTTP " + str(status) + " " + body[:120])
    status, body, _ = fetch("/api/health")
    check("an unauthorised read is refused", status in (401, 403), "HTTP " + str(status) + " for a request without the session token")
    status, body, _ = fetch("/api/health", token=token)
    project_page = fetch("/api/conversations", token=token)
    check("the stored conversation ledger answers", project_page[0] == 200 and "conversations" in project_page[1], "HTTP " + str(project_page[0]))

    question = "What is it like right now in Ahmedabad?"
    started = time.time()
    status, body, _ = fetch("/api/chat", token=token, method="POST", body={"question": question, "conversation_id": str(uuid.uuid4())})
    elapsed = round(time.time() - started, 2)
    if status == 400 and "not in the local store" in body:
        status, body, _ = fetch("/api/chat", token=token, method="POST", body={"question": question})
        elapsed = round(time.time() - started, 2)
    packet = json.loads(body) if status == 200 else {}
    check("a real turn answers through the served build's API", status == 200 and bool(packet.get("answer")), "HTTP " + str(status) + " in " + str(elapsed) + " s, status " + str(packet.get("status")))
    record["turn"] = {"question": question, "seconds": elapsed, "status": packet.get("status"),
                      "planner_policy": ((packet.get("trace") or {}).get("planning") or {}).get("planner_policy"),
                      "provider": (packet.get("trace") or {}).get("provider"),
                      "facts": len(packet.get("facts") or []), "answer_characters": len(packet.get("answer") or "")}
    check("the turn keeps a fact count, not a confidence", "confidence" not in json.dumps(packet).lower(), "no confidence field in the response")

    status, body, _ = fetch("/api/chat/progress", token=token)
    progress = json.loads(body) if status == 200 else {}
    check("progress names a stage and refuses to be a percentage", progress.get("schema_version") == "chat-progress-v1" and "stages_are_facts_not_progress" in progress, "state " + str(progress.get("state")))
    status, body, _ = fetch("/api/chat/preview", token=token, method="POST", body={"question": "Will it rain in Surat tomorrow morning?"})
    preview = json.loads(body) if status == 200 else {}
    check("the first reading is served and marks itself provisional", preview.get("provisional") is True and preview.get("reading_is_not_evidence") is True, str((preview.get("reading") or {}).get("line"))[:160])
finally:
    server.shutdown(); server.server_close()

failed = [entry for entry in record["checks"] if not entry["ok"]]
record["summary"] = {"checks": len(record["checks"]), "failed": len(failed), "port": port}
out = os.path.join(os.path.dirname(__file__), "live-r2.json")
with open(out, "w", encoding="utf-8") as handle:
    json.dump(record, handle, indent=1)
for entry in record["checks"]:
    print(("PASS " if entry["ok"] else "FAIL ") + entry["check"].ljust(52) + " " + entry["detail"])
print(str(len(record["checks"])) + " check(s), " + str(len(failed)) + " failed; written to " + os.path.relpath(out, ROOT))
