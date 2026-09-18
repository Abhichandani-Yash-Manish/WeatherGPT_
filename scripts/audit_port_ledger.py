#!/usr/bin/env python3
"""Verify the port ledger's claims: every named test must exist in the spec it names.

    python3 scripts/audit_port_ledger.py
    python3 scripts/audit_port_ledger.py --json

A ledger entry is a claim that a React spec carries a vanilla check. This re-reads
research/reviews/frontend-react-r2-20260917/check-port.json and refuses a claim whose spec is missing or
whose test name is not written in that spec. It reads the React sources only: the vanilla suites it once
counted were removed in R6, so the suite totals are the ledger's own record and the names are what is held
to account here. The parity spec for the chart engine reads the served web/viz.js from disk, so the nine
chart checks are claims about these bytes too.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "research" / "reviews" / "frontend-react-r2-20260917" / "check-port.json"


def flatten(text):
    return re.sub(r"\s+", " ", text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings = []
    try:
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        suites = ledger.get("suites", [])
    except (OSError, ValueError) as error:
        findings.append(("ledger parses", False, str(error)[:140]))
        suites = []
    else:
        total = sum(suite.get("checks", 0) for suite in suites)
        ported = sum(suite.get("ported", 0) for suite in suites)
        findings.append(("ledger totals", len(suites) == 10 and total == 110 and ported == total,
                         "%d suites, %d checks, %d named against a React spec" % (len(suites), total, ported)))

    named = 0
    missing = []
    specs = set()
    for suite in suites:
        for entry in suite.get("evidence", []):
            # A check retired by design names its reason and no spec: accounted for, not verified.
            if entry.get("retired"):
                continue
            spec = entry.get("spec", "")
            path = ROOT / "frontend" / spec
            if not path.exists():
                missing.append(spec + " (no such spec)")
                continue
            specs.add(spec)
            body = flatten(path.read_text(encoding="utf-8"))
            for name in entry.get("tests", []):
                named += 1
                if flatten(name) not in body:
                    missing.append(spec + ": " + name[:80])
    findings.append(("every named test exists in its spec", not missing,
                     "%d name(s) verified in %d spec file(s)" % (named, len(specs)) if not missing
                     else str(len(missing)) + " claim(s) without a test: " + "; ".join(missing[:4])))

    failed = [name for name, ok, _ in findings if not ok]
    if args.json:
        print(json.dumps([{"check": name, "ok": ok, "detail": detail} for name, ok, detail in findings], indent=2))
    else:
        for name, ok, detail in findings:
            print(("PASS " if ok else "FAIL ") + name.ljust(38) + " " + detail)
        print(str(len(findings)) + " check(s), " + str(len(failed)) + " failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
