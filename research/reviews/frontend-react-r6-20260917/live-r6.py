"""Live acceptance that the default surface is the React build.

Starts the workspace with no frontend argument at all, over loopback, and reads what a browser would get: the
page, its module entry, the session token contract and one authorised read. A missing build would be answered
with words, so a blank page can never pass this check.
"""
import json, os, re, sys, threading, urllib.error, urllib.request
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from weathergpt_data.workspace import Workspace, make_server

record = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "checks": []}


def check(name, ok, detail):
    record["checks"].append({"check": name, "ok": bool(ok), "detail": str(detail)[:300]})


workspace = Workspace()  # no frontend argument: the default is under test
server = make_server(workspace, 0)
port = server.server_port
threading.Thread(target=server.serve_forever, daemon=True).start()
base = "http://127.0.0.1:" + str(port)


def fetch(path, token=None, method="GET", body=None):
    request = urllib.request.Request(base + path, method=method)
    if token:
        request.add_header("X-WeatherGPT-Token", token)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, data=data, timeout=60) as answer:
            return answer.status, answer.read().decode("utf-8", "replace"), dict(answer.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace"), dict(error.headers)


try:
    status, page, headers = fetch("/")
    check("the default surface is the React page", status == 200 and 'data-boot="react"' in page, "HTTP " + str(status))
    check("the vanilla page is not what a default start serves", "WeatherGPT — workspace" not in page and "/shell.js" not in page,
          "no legacy script in the served page")
    token = re.search(r'name="workspace-token" content="([^"]+)"', page)
    check("the session token is injected into the built page", "__WORKSPACE_TOKEN__" not in page and token is not None, "meta tag carries a per-process value")
    entry = re.search(r'<script type="module"[^>]*src="([^"]+)"', page)
    status, script, headers = fetch(entry.group(1) if entry else "/assets/missing.js")
    check("the built module entry is served", status == 200 and len(script) > 1000, (entry.group(1) if entry else "no entry") + " HTTP " + str(status))
    check("the strict page policy is sent", headers.get("Content-Security-Policy", "").startswith("default-src 'self'"), headers.get("Content-Security-Policy", "")[:80])
    status, body, _ = fetch("/api/health", token=token.group(1) if token else None)
    check("an authorised read answers", status == 200 and json.loads(body).get("available") is True, "HTTP " + str(status))
    status, body, _ = fetch("/viz.js")
    check("the chart engine the chart block draws with is still served", status == 200 and "Chart engine" in body[:400], "HTTP " + str(status))
    status, body, _ = fetch("/sw.js")
    check("the notification worker the plans panel registers is still served", status == 200 and "addEventListener" in body, "HTTP " + str(status))
finally:
    server.shutdown()
    server.server_close()

failed = [entry for entry in record["checks"] if not entry["ok"]]
record["summary"] = {"checks": len(record["checks"]), "failed": len(failed), "port": port}
out = os.path.join(os.path.dirname(__file__), "live-r6.json")
with open(out, "w", encoding="utf-8") as handle:
    json.dump(record, handle, indent=1)
for entry in record["checks"]:
    print(("PASS " if entry["ok"] else "FAIL ") + entry["check"].ljust(58) + " " + entry["detail"])
print(str(len(record["checks"])) + " check(s), " + str(len(failed)) + " failed; written to " + os.path.relpath(out, ROOT))
