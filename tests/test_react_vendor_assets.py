"""The React frontend is served two vanilla files from their one tracked copy.

A React surface cannot import a file the server does not serve: under --frontend react the page is served from
web/dist and nothing else is reachable. This pins the seam — the engine is served verbatim from web/viz.js, the
content type is a script, it is not cached immutably because it is not content-hashed, and the vanilla frontend
keeps serving the same bytes. A missing file is a stated 404, never a blank script.
"""
import hashlib
import json
import threading
import urllib.error
import urllib.request

import pytest

from weathergpt_data.workspace import Workspace, make_server

ROOT_ENGINE = None
ROOT_WORKER = None


@pytest.fixture(scope="module")
def served():
    from pathlib import Path
    global ROOT_ENGINE, ROOT_WORKER
    web = Path(__file__).resolve().parents[1] / "web"
    ROOT_ENGINE = web / "viz.js"
    ROOT_WORKER = web / "sw.js"
    workspace = Workspace(frontend="react")
    server = make_server(workspace, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        server.server_close()


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as answer:
            return answer.status, answer.read(), dict(answer.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def test_the_chart_engine_is_served_verbatim_to_the_react_frontend(served):
    status, body, headers = get(served + "/viz.js")
    assert status == 200
    assert headers.get("Content-Type", "").startswith("text/javascript")
    assert body == ROOT_ENGINE.read_bytes(), "the served script is not the tracked file"
    assert "immutable" not in headers.get("Cache-Control", ""), "an unhashed script must not be cached for a year"


def test_the_served_engine_is_the_one_the_vanilla_checks_cover(served):
    status, body, _ = get(served + "/viz.js")
    assert status == 200
    digest = hashlib.sha256(body).hexdigest()
    assert digest == hashlib.sha256(ROOT_ENGINE.read_bytes()).hexdigest()
    assert b"Chart engine" in body[:400], "the script does not look like the chart engine"


def test_a_path_that_is_not_the_engine_is_not_a_script(served):
    status, body, headers = get(served + "/viz.js.map")
    assert status == 404
    assert "error" in json.loads(body)


def test_the_notification_worker_is_served_verbatim_to_the_react_frontend(served):
    """The plans panel registers /sw.js for push. It is a push worker, not an offline cache: it has no
    fetch handler, so serving it makes notifications possible and caches nothing."""
    status, body, headers = get(served + "/sw.js")
    assert status == 200
    assert headers.get("Content-Type", "").startswith("application/javascript")
    assert body == ROOT_WORKER.read_bytes(), "the served worker is not the tracked file"
    assert "immutable" not in headers.get("Cache-Control", "")
    assert b"addEventListener(" in body, "the served file does not register listeners"
    assert b"fetch" not in body, "this worker must not cache: it is a push worker"


def test_a_near_miss_on_the_worker_is_not_a_script(served):
    status, body, _ = get(served + "/sw.js.map")
    assert status == 404
