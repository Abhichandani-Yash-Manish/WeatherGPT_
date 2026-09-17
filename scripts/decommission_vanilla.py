#!/usr/bin/env python3
"""The R6 deletion, in one reviewable step.

    python3 scripts/decommission_vanilla.py            # report what it would remove, change nothing
    python3 scripts/decommission_vanilla.py --apply    # perform it

The plan (docs/86) makes R6 the stage that deletes the vanilla frontend, and it sets the condition: the 110
component checks and the frontend audit ported first, with verify_all.py green on the React-only tree. This
script holds that condition rather than trusting whoever runs it: it refuses to apply while any vanilla check
is unclaimed in the port ledger, and it names the files it will remove, the files it will keep and why, in the
order it removes them.

Three web files stay, and the reason is in the ledger: web/tokens.css is imported by the React stylesheet,
web/viz.js is served to the React build at /viz.js so the nine viz checks keep covering the code a chart runs,
and web/sw.js is served at /sw.js because it is the notification worker the plans panel registers.
"""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "research" / "reviews" / "frontend-react-r2-20260917" / "check-port.json"

# Removed: the vanilla surfaces, their stylesheet and page, the component-check harness, and the two audits and
# scripts that only exist to read them.
REMOVE = [
    "web/app.js", "web/views.js", "web/panels.js", "web/shell.js", "web/home.js", "web/charts.js",
    "web/map.js", "web/voice.js", "web/index.html", "web/style.css",
    "tests/dom_shim.js", "tests/test_charts.js", "tests/test_viz.js", "tests/test_views.js",
    "tests/test_bulletin_ui.js", "tests/test_conversation_ui.js", "tests/test_suite_ui.js",
    "tests/test_voice_ui.js", "tests/test_briefcase_ui.js", "tests/test_workspace_ui.js",
    "tests/test_notify_ui.js",
    "scripts/audit_workspace_frontend.py", "scripts/audit_check_port.py",
]

# Kept, with the reason a reader can check.
KEEP = {
    "web/tokens.css": "imported by frontend/src/styles/app.css, so the design system stays single-sourced",
    "web/viz.js": "served to the React build at /viz.js; the nine test_viz.js checks cover these bytes",
    "web/sw.js": "served at /sw.js; the notification worker the plans panel registers for push",
    "research/reviews/frontend-react-r2-20260917/check-port.json": "the record of what was ported, kept as evidence",
}

# Edits that must accompany the deletion, named so the next step cannot forget one.
FOLLOW_UPS = [
    "scripts/verify_all.py: drop NODE_SUITES and the vanilla frontend audit step",
    "scripts/audit_surface_registry.py: compare the React registry with the served product paths only, keeping the vanilla rail list as a frozen expectation with the reason it was the second list until R6",
    "weathergpt_data/workspace.py: delete the legacy asset map and the frontend parameter, leaving the React branch unconditional",
    "docs/86 and docs/92: record R6 as delivered, with the evidence directory",
    "docs/images/: regenerate the gallery from the React build",
    "README: the frontend section, the check counts and the how-it-is-checked block",
]


def unclaimed(ledger):
    left = []
    for suite in ledger.get("suites", []):
        missing = suite.get("checks", 0) - suite.get("ported", 0)
        if missing > 0:
            left.append((suite["file"], missing))
    return left


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="actually remove the files")
    parser.add_argument("--force", action="store_true", help="apply even while checks are unclaimed (recorded, not recommended)")
    args = parser.parse_args()

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    left = unclaimed(ledger)
    total_left = sum(count for _, count in left)

    print("R6 decommission: " + ("apply" if args.apply else "dry run"))
    print("")
    print("port ledger: " + str(sum(suite.get("ported", 0) for suite in ledger["suites"])) + " of " +
          str(sum(suite.get("checks", 0) for suite in ledger["suites"])) + " checks named against a React spec")
    for name, count in left:
        print("  still unclaimed: " + name + " (" + str(count) + ")")
    if total_left and not args.force:
        print("")
        print("refused: " + str(total_left) + " checks are not named against a React spec yet. Port them, or run with")
        print("--force and say in the batch document which ones are being retired and why.")
        return 1

    print("")
    print("would remove:")
    for name in REMOVE:
        path = ROOT / name
        print("  " + ("remove " if path.exists() else "already gone ") + name)
    print("")
    print("keeps:")
    for name, reason in KEEP.items():
        print("  " + name + " - " + reason)
    print("")
    print("edits that must accompany it:")
    for line in FOLLOW_UPS:
        print("  - " + line)

    if not args.apply:
        print("")
        print("nothing was changed. Run with --apply to perform the removal.")
        return 0

    removed = []
    for name in REMOVE:
        path = ROOT / name
        if path.exists():
            path.unlink()
            removed.append(name)
    print("")
    print("removed " + str(len(removed)) + " file(s); the kept files are listed above.")
    print("the follow-up edits are NOT done by this script: do them, then run verify_all.py on the React-only tree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
