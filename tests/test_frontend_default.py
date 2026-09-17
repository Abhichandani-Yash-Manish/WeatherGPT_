"""The React build is the surface this workspace serves by default.

R6 flips the default: a fresh checkout that runs the workspace gets the React page, and the vanilla frontend
is reachable only by asking for it by name until its tree is deleted. This check reads the constructor and the
command line rather than starting a server, and the live serving path is pinned by
research/reviews/frontend-react-r0-20260917/live-r0.json and the R6 acceptance run.
"""
import inspect
import re
from pathlib import Path

from weathergpt_data.workspace import Workspace

ROOT = Path(__file__).resolve().parents[1]


def test_the_workspace_serves_the_react_build_unless_asked_otherwise():
    default = inspect.signature(Workspace.__init__).parameters["frontend"].default
    assert default == "react", "the default frontend is " + repr(default)


def test_the_request_path_falls_through_to_the_react_branch_by_default():
    text = (ROOT / "weathergpt_data" / "workspace.py").read_text(encoding="utf-8")
    assert "getattr(workspace,'frontend','react')=='react'" in text, \
        "the serving branch still assumes the legacy default"
    assert re.search(r"add_argument\(" , text)
    flag = re.search(r"p\.add_argument\('--frontend'[^)]*\)", text, re.S)
    assert flag and "default='react'" in flag.group(0), "the command line default was not flipped"
    assert "choices=['legacy','react']" in flag.group(0), \
        "the legacy surface must stay selectable by name until its tree is deleted"


def test_a_missing_build_is_refused_in_words():
    text = (ROOT / "weathergpt_data" / "workspace.py").read_text(encoding="utf-8")
    assert "The React frontend has not been built" in text
    assert "npm run build" in text

