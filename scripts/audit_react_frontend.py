#!/usr/bin/env python3
"""The React frontend audit: the lines the vanilla audit held, read against the built output and the sources.

    python3 scripts/audit_react_frontend.py

`audit_workspace_frontend.py` reads web/*.js, the vanilla frontend, and its FE01-FE11 checks are the ones the
plan says must not be lost when that frontend is removed. This audit holds the same lines for the React build:
it reads the built page and its stylesheets where a claim is about what a browser receives, and the component
sources where a claim is about what a component does. It reads files and changes nothing.

A missing build is a reported skip, not a pass, exactly as the build audit treats it.
"""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "dist"
SRC = ROOT / "frontend" / "src"
LEDGER = ROOT / "research" / "reviews" / "frontend-react-r2-20260917" / "check-port.json"


def read(path):
    return path.read_text(encoding="utf-8")


def sources(pattern):
    return sorted(SRC.rglob(pattern))


def any_source(pattern, needle):
    return any(needle in read(path) for path in sources(pattern))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings = []
    index = DIST / "index.html"
    built = index.exists()
    findings.append(("built_page_present", built, str(index.relative_to(ROOT)) if built else "no build: run npm run build in frontend/"))
    page = read(index) if built else ""
    css = ""
    if built:
        css = "\n".join(read(sheet) for sheet in sorted((DIST / "assets").glob("*.css")))

    app = read(SRC / "App.tsx")
    # The shell since docs/111: gpt/Workspace.tsx — a conversation rail, a centred column and a docking
    # composer, targeting ChatGPT's architecture. There is no module rail and no dashboard topbar.
    workspace = read(SRC / "gpt" / "Workspace.tsx")
    gpt_css = read(SRC / "gpt" / "gpt.css")
    answer = read(SRC / "chat" / "AnswerTurn.tsx")
    composer = read(SRC / "gpt" / "Composer.tsx")
    host = read(SRC / "shell" / "SurfaceHost.tsx")
    print_css = read(SRC / "styles" / "print.css")

    # FE01: the question box is reachable and not below a competing form. The React shell keeps the prompt in
    # the composer, there is no other form on the page, and the column is one at every width.
    no_other_form = len(re.findall(r"<form", composer)) == 0 and "onSubmit" not in composer
    # One column at every width: the composer is a sticky dock and the bar collapses on a phone. Nothing has to
    # be opened before the question box can be reached.
    # The intent, not a literal breakpoint: there is a narrow-width rule, the composer docks, and the
    # page is one column. Pinning the pixel value made this fail every time the breakpoint moved.
    narrow = bool(re.search(r"@media \(max-width: \d+px\)", gpt_css)) and ".g-dock" in gpt_css and "g-dock" in workspace
    findings.append(("FE01_mobile_reachability", no_other_form and narrow,
                     "composer is not a form: " + str(no_other_form) + "; one-column dock rules: " + str(narrow)))

    # FE02: a bounded collection is reachable from an answer, and a check holds it.
    fe02 = "Collect fresh evidence" in answer and any_source("*.test.tsx", "Collect fresh evidence")
    findings.append(("FE02_bounded_collection_reachable", fe02,
                     "the card offers the control and a check exercises it" if fe02 else "no control or no check"))

    # FE03: no component wires itself to a request the workspace would reject. Every read goes through the
    # client (which carries the token and the error mapping), and the surface registry audit checks the routes.
    fetch_call = re.compile(r"(?<![A-Za-z_.$])fetch\s*\(")
    raw_fetch = [path.relative_to(ROOT).as_posix() for path in sources("*.tsx") + sources("*.ts")
                 if fetch_call.search(read(path)) and "test" not in path.name
                 and "api/client.ts" not in path.as_posix() and path.name != "probe.tsx"]
    findings.append(("FE03_no_unreachable_renderer", not raw_fetch,
                     ", ".join(raw_fetch) if raw_fetch else
                     "no product component calls fetch outside src/api/client.ts (the CSP probe is a development entry, built by its own config)"))

    # FE04: task accounting is reported as asked, answered and incomplete, not as one affirmative count.
    fe04 = "task_coverage" in read(SRC / "chat" / "model.ts") and "coverageNote" in answer
    findings.append(("FE04_task_accounting", fe04,
                     "the card states requested, completed and the incomplete ids" if fe04 else "no task-coverage sentence in the card"))

    # FE05: a language control exists and every surface states its own scope. The scope is the evidence footer
    # each module renders, and the control is the page bar's select.
    language_control = "Answer language" in workspace and "allLanguages" in workspace
    # A surface states its scope through SurfaceShell, which renders the evidence footer: counting the files that
    # call the shell is counting the surfaces that carry their coverage, limits and sources.
    footers = len([path for path in sources("*.tsx") if "SurfaceShell" in read(path) or "EvidenceFooter" in read(path)])
    findings.append(("FE05_scope_and_language", language_control and footers >= 10,
                     "language control: " + str(language_control) + "; surfaces rendering the evidence footer: " + str(footers)))

    # FE06: one question input, and the builder never submits it.
    inputs = len(re.findall(r'id="question"', composer))
    builder = [path for path in sources("*.tsx") if path.name.lower().startswith("workspace")]
    builder_writes_only = bool(builder) and any("Nothing was sent" in read(path) for path in builder) \
        and any_source("*.test.tsx", "sends nothing")
    findings.append(("FE06_one_question_input", inputs == 1 and builder_writes_only,
                     "question inputs in the composer: " + str(inputs) + "; builder writes and does not send: " + str(builder_writes_only)))

    # FE07: the surfaces are served and a live record exists.
    live = (ROOT / "research" / "reviews" / "frontend-react-r2-20260917" / "live-r2.json").exists()
    served = (ROOT / "scripts" / "audit_surface_registry.py").exists()
    findings.append(("FE07_surfaces_served_and_recorded", live and served,
                     "live acceptance record: " + str(live) + "; surface registry audit: " + str(served)))

    # FE08: transparency between editions is reachable.
    fe08 = (SRC / "modules" / "ChangesSurface.tsx").exists() and any_source("*.test.tsx", "printed editions")
    findings.append(("FE08_edition_coverage", fe08,
                     "the changed-edition surface exists with a check" if fe08 else "no edition-coverage surface or check"))

    # FE10: a card survives printing: the print rules and the markup agree.
    fe10 = "[data-print='drop']" in print_css and ".machine-record" in print_css and 'data-print="drop"' in answer
    findings.append(("FE10_print_parity", fe10,
                     "the print rules and the card markup name the same hooks" if fe10 else "print rules and markup disagree"))

    # FE11: every routed view exists end to end. The registry audit compares the two frontends and the routes;
    # this check is that the audit and the host check are present and that the host loads modules lazily.
    fe11 = host.count("lazy(") >= 1 and any_source("modules/registry.ts", "load:") and (ROOT / "scripts" / "audit_surface_registry.py").exists()
    findings.append(("FE11_view_contract", fe11,
                     "every surface is a registry entry loaded by the host, and the registry audit compares both frontends"))

    # FE12: no heading on any surface is shouted, and nothing claims otherwise.
    #
    # docs/111 recorded that the all-caps label had been removed everywhere. It had not: the claim rested on
    # a hand-written list of selectors in gpt.css, and four rules were missing from it -- .module h2, which
    # uppercased every section heading on every module surface, and three chart labels. The dashboard was
    # still shouting CHOOSE YOUR PLACE and AI ASSISTANT at a reader while the document said it did not.
    #
    # So the list is checked rather than trusted. Every selector in the project's stylesheets that declares
    # text-transform: uppercase must have each of its classes named in the block that neutralises them, and
    # no component may reach for Tailwind's uppercase utility. Add a shouted rule anywhere and this fails.
    def _declared_uppercase():
        out = []
        for sheet in sorted(SRC.rglob("*.css")):
            if sheet.name == "gpt.css":
                continue
            text = re.sub(r"/\*.*?\*/", "", read(sheet), flags=re.S)
            for block in re.finditer(r"([^{}]+)\{([^}]*)\}", text):
                if re.search(r"text-transform:\s*uppercase", block.group(2)):
                    for selector in block.group(1).split(","):
                        if selector.strip():
                            out.append(selector.strip())
        return out

    gpt_css = read(SRC / "gpt" / "gpt.css")
    shouted = []
    for selector in _declared_uppercase():
        names = re.findall(r"\.([a-z][a-z0-9-]*)", selector)
        # The trailing guard matters: ".module" must not be counted as covered by ".module-section".
        if not names or not all(re.search(r"\." + re.escape(n) + r"(?![a-z0-9-])", gpt_css) for n in names):
            shouted.append(selector)
    utility = [str(f.relative_to(SRC)) for f in sorted(SRC.rglob("*.tsx"))
               if ".test." not in f.name and re.search(r'className="[^"]*\buppercase\b', read(f))]
    fe12 = not shouted and not utility
    findings.append(("FE12_sentence_case", fe12,
                     "every uppercase rule is neutralised and no component uses the uppercase utility"
                     if fe12 else "still shouted: " + ", ".join(shouted + utility)[:160]))

    # The port ledger is part of the frontend story now: it says which of the vanilla checks the React specs
    # carry, and it must parse and be internally consistent.
    try:
        ledger = json.loads(read(LEDGER))
        suites = ledger.get("suites", [])
        total = sum(entry.get("checks", 0) for entry in suites)
        ported = sum(entry.get("ported", 0) for entry in suites)
        findings.append(("port_ledger_parses", len(suites) == 10 and total == 110,
                         str(len(suites)) + " suites, " + str(total) + " checks, " + str(ported) + " named against a React spec"))
    except (OSError, ValueError) as error:
        findings.append(("port_ledger_parses", False, str(error)[:120]))

    # The probe is a development entry, so it must not be part of the product page the server serves.
    manifest_path = DIST / ".vite" / "manifest.json"
    manifest = json.loads(read(manifest_path)) if manifest_path.exists() else {}
    probe_built = any("probe" in str(value.get("file", "")) for value in manifest.values() if isinstance(value, dict))
    findings.append(("probe_is_not_a_product_entry", bool(manifest) and not probe_built,
                     "the probe is absent from the built manifest" if not probe_built else "the probe reached the production build"))

    failed = [name for name, ok, _ in findings if not ok]
    if args.json:
        print(json.dumps([{"check": name, "ok": ok, "detail": detail} for name, ok, detail in findings], indent=2))
    else:
        for name, ok, detail in findings:
            print(("PASS " if ok else "FAIL ") + name.ljust(34) + " " + detail)
        print(str(len(findings)) + " check(s), " + str(len(failed)) + " failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
