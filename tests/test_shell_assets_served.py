"""Everything the shell names must be answered by the shell's own server.

Measured 20 September 2026, before this file existed: `index.html` named `/manifest.webmanifest` and
`/icon-192.png`, the manifest named three icons, and the server answered **404 for all four** while serving
`/` and `/sw.js`. The app was therefore not installable on any surface, over any transport - which is not the
HTTPS gate docs/118 described: on loopback, already a secure context, the manifest was still missing. Two
independent things had been carried as one.

The check reads the BUILT page, not the template: `frontend/index.html` names `/src/main.tsx`, a Vite
development path the build rewrites, so auditing the template would audit a URL no browser ever asks for. A
missing build is a reported skip here, exactly as the other audits treat it.

The worker check is the second half of the same defect. Two workers exist in this repository - `web/sw.js`,
which the server serves, and `frontend/public/sw.js`, which the build copies into an untracked, unserved
directory - so an edit to the wrong one looks live and is not. The invariant asserted here is the one both
resolutions satisfy: exactly one worker file exists, and the bytes served at `/sw.js` are that file.
"""
import json
import re
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from weathergpt_data.workspace import Workspace, make_server

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "dist"
INDEX = DIST / "index.html"

# The one worker file, whichever of the two the repository keeps. Both are named so that either resolution
# satisfies the check and a THIRD copy would still fail it.
WORKER_CANDIDATES = [ROOT / "web" / "sw.js", ROOT / "frontend" / "public" / "sw.js"]


@pytest.fixture(scope="module")
def served():
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


def built_or_skip():
    if not INDEX.exists():
        pytest.skip("the React frontend has not been built: run cd frontend && npm run build")


def page_urls():
    """Every URL the built page names with a leading slash, deduplicated in source order."""
    html = INDEX.read_text()
    found = re.findall(r'(?:href|src)="(/[^"]+)"', html)
    return list(dict.fromkeys(found))


def test_the_built_page_names_the_urls_this_check_is_about():
    built_or_skip()
    named = page_urls()
    assert named, "the built page names no absolute URL, so this check is reading nothing"
    assert "/manifest.webmanifest" in named, "the built page no longer names the manifest: " + str(named)


def test_every_url_the_built_page_names_is_answered(served):
    built_or_skip()
    missing = []
    for url in page_urls():
        status, body, _ = get(served + url)
        if status != 200:
            missing.append(str(status) + " " + url)
    assert not missing, "the page names what the server does not answer: " + ", ".join(missing)


def test_the_manifest_is_served_and_parses(served):
    status, body, headers = get(served + "/manifest.webmanifest")
    assert status == 200, "the manifest is not served: a browser cannot install this app"
    assert "json" in headers.get("Content-Type", "") or "manifest" in headers.get("Content-Type", ""), \
        "the manifest is served as " + headers.get("Content-Type", "nothing")
    document = json.loads(body)
    assert document.get("name"), "the manifest names no application"
    assert document.get("icons"), "the manifest lists no icon"


def test_every_icon_the_manifest_names_is_served(served):
    status, body, _ = get(served + "/manifest.webmanifest")
    assert status == 200, "no manifest to read the icons from"
    missing = []
    for icon in json.loads(body)["icons"]:
        code, _, headers = get(served + icon["src"])
        if code != 200 or not headers.get("Content-Type", "").startswith("image/png"):
            missing.append(str(code) + " " + icon["src"] + " as " + headers.get("Content-Type", "nothing"))
    assert not missing, "the manifest names icons the server does not serve: " + ", ".join(missing)


def test_the_served_worker_is_the_only_worker_the_repository_ships(served):
    present = [path for path in WORKER_CANDIDATES if path.exists()]
    assert len(present) == 1, (
        "the repository ships " + str(len(present)) + " workers (" + ", ".join(str(p.relative_to(ROOT)) for p in present)
        + "): an edit to the one that is not served looks live and is not")
    status, body, headers = get(served + "/sw.js")
    assert status == 200, "the worker the page registers is not served"
    assert body == present[0].read_bytes(), "the served worker is not the tracked file: " + str(present[0].relative_to(ROOT))
    assert "immutable" not in headers.get("Cache-Control", ""), "an unhashed worker must not be cached for a year"


def test_the_manifest_paints_the_browser_from_this_products_own_ground():
    """The colour the browser paints its chrome and splash with is a surface this product chooses.

    A fixed value cannot follow the hour, which is why the page updates its own theme-color meta beside
    whatever sets `data-hour`; what the manifest states must at least be a ground this product actually draws,
    read from tokens.css rather than from a design paragraph. On 20 September 2026 it was the retired data
    teal (#0d6d77) with the retired #0b1216 beside it, neither of which any part of the product paints."""
    tokens = (ROOT / "frontend" / "src" / "gpt" / "css" / "tokens.css").read_text()
    grounds = set(re.findall(r"--g-bg:\s*(#[0-9a-fA-F]{6})", tokens))
    assert len(grounds) >= 2, "tokens.css declares fewer than two grounds: " + str(sorted(grounds))
    manifest = json.loads((ROOT / "frontend" / "public" / "manifest.webmanifest").read_text())
    for key in ("theme_color", "background_color"):
        stated = str(manifest.get(key, "")).lower()
        assert stated in {value.lower() for value in grounds}, (
            "the manifest's " + key + " is " + stated + ", which is not a ground this product draws ("
            + ", ".join(sorted(grounds)) + ")")

