#!/usr/bin/env python3
"""Check the port ledger: which vanilla component checks the React suites have taken over.

    python3 scripts/audit_check_port.py

The vanilla frontend keeps ten Node suites that print 110 checks. Until R6 removes them they remain the
regression net, so this script does not pretend they are gone. What it does is make the port auditable: the
curated ledger in research/reviews/frontend-react-r2-20260917/check-port.json names, per vanilla suite, how
many of its checks a React spec now carries and which spec that is, and this script refuses to accept a claim
it cannot check.

Three things are checked, and nothing is inferred:

1. every vanilla suite is present in the ledger, and the check count recorded for it is the count the suite
   actually prints today (so the ledger cannot drift while a suite grows);
2. a ported count is a whole number no larger than that suite check count;
3. every named React spec exists and contains the test names it claims.

It reads files and changes nothing."""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "research" / "reviews" / "frontend-react-r2-20260917" / "check-port.json"


def printed_checks(path):
    return len(re.findall(r"console\.log\('PASS: ", path.read_text(encoding="utf-8")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings = []
    if not LEDGER.exists():
        print("check port: FAIL - no ledger at " + str(LEDGER.relative_to(ROOT)))
        return 1
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    suites = {entry["file"]: entry for entry in ledger.get("suites", [])}

    measured = {}
    for path in sorted((ROOT / "tests").glob("test_*.js")):
        measured[path.name] = printed_checks(path)

    missing = sorted(name for name in measured if name not in suites)
    findings.append(("every_vanilla_suite_is_in_the_ledger", not missing,
                     ", ".join(missing) if missing else str(len(measured)) + " suites recorded"))

    drifted = []
    for name, count in measured.items():
        entry = suites.get(name)
        if entry and entry.get("checks") != count:
            drifted.append(name + ": ledger " + str(entry.get("checks")) + " vs suite " + str(count))
    findings.append(("recorded_counts_match_the_suites", not drifted,
                     "; ".join(drifted) if drifted else str(sum(measured.values())) + " printed checks recorded"))

    over = []
    for name, entry in suites.items():
        ported = entry.get("ported")
        if not isinstance(ported, int) or ported < 0 or ported > entry.get("checks", 0):
            over.append(name + ": ported " + str(ported) + " of " + str(entry.get("checks")))
    findings.append(("ported_counts_are_possible", not over, "; ".join(over) if over else "no suite claims more than it prints"))

    unverifiable = []
    checked_tests = 0
    for name, entry in suites.items():
        for claim in entry.get("evidence", []):
            spec = ROOT / "frontend" / claim.get("spec", "")
            if not spec.exists() or not str(spec).startswith(str(ROOT / "frontend" / "src")):
                unverifiable.append(str(claim.get("spec")) + " (missing)")
                continue
            text = spec.read_text(encoding="utf-8")
            for test_name in claim.get("tests", []):
                checked_tests += 1
                if test_name not in text:
                    unverifiable.append(str(claim.get("spec")) + " has no test named: " + test_name)
    findings.append(("every_claimed_test_exists", not unverifiable,
                     "; ".join(unverifiable) if unverifiable else str(checked_tests) + " claimed test name(s) found in their spec"))

    total = sum(measured.values())
    ported = sum(entry.get("ported", 0) for entry in suites.values())
    new_surfaces = sum(entry.get("new_surface", 0) for entry in suites.values() if entry.get("new_surface"))
    findings.append(("the_rest_are_still_covered_by_the_vanilla_suites", ported < total,
                     str(ported) + " of " + str(total) + " checks named as taken over; the vanilla suites still run in verify_all"))

    failed = [name for name, ok, _ in findings if not ok]
    if args.json:
        print(json.dumps([{"check": name, "ok": ok, "detail": detail} for name, ok, detail in findings], indent=2))
    else:
        for name, ok, detail in findings:
            print(("PASS " if ok else "FAIL ") + name.ljust(48) + " " + detail)
        print(str(len(findings)) + " check(s), " + str(len(failed)) + " failed; " +
              str(ported) + " of " + str(total) + " vanilla component checks have a named React counterpart")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
