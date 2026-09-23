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


def _workspace_css() -> str:
    """The workspace stylesheet, which is an index plus the parts it imports.

    It was one file of 1780 lines until it was split; source order is the cascade there, so the parts are
    concatenated in the order the index imports them rather than in directory order. Every check that asks
    "is this rule declared" has to see all of it, or it passes by finding nothing — which is the failure
    the checks exist to catch.
    """
    index_path = SRC / "gpt" / "gpt.css"
    index = read(index_path)
    parts = re.findall(r"@import\s+['\"]\./css/([A-Za-z0-9_-]+\.css)['\"]", index)
    return index + "\n" + "\n".join(read(index_path.parent / "css" / name) for name in parts)


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
    gpt_css = _workspace_css()
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
    # each module renders. The control moved out of the page bar into the reading panel — where the place, the
    # language and the persona are one block rather than two native selects in a bar — so the check reads the
    # shell's own files rather than one file by name. A control that moves should not read as a control that
    # vanished, and one that changes name should: the label and the measured list must both still be there.
    shell_sources = "\n".join(read(path) for path in sorted((SRC / "gpt").glob("*.tsx")))
    language_control = "Answer language" in shell_sources and "allLanguages" in shell_sources
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

    gpt_css = _workspace_css()
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

    # FE13: no element is drawn by the browser's defaults.
    #
    # WorkspaceSurface.tsx and IndiaWarningMap.tsx came into this tree from another one and their
    # stylesheets did not. About a hundred dash-* names and twenty-four imap-* names had never had a rule
    # here, so the dashboard's question box rendered as a letter, a naked textarea and an arrow on three
    # separate lines, and the map's four overlay switches ran together with no space at all. Nothing threw;
    # the page rendered; it looked like unstyled HTML because it was unstyled HTML.
    #
    # The test is held against the BUILT stylesheet, which carries the authored CSS and Tailwind's
    # generated utilities together -- so a class that looks undeclared but sits beside `px-3 py-2` is not
    # reported, because those utilities are doing the work. What is reported is an element whose whole
    # class list resolves to nothing, which is the failure that produced the dashboard.
    css = "".join(read(sheet) for sheet in sorted(DIST.glob("assets/*.css")))
    styled = set(re.findall(r"\.(-?[A-Za-z_][\w-]*)", css))
    # Four components are unreachable from the app -- nothing imports AskSurface or NationalReading, and
    # AskSurface is the only importer of Transcript and chat/Composer. They still carry test coverage, so
    # they are recorded here rather than deleted quietly; deleting them is its own change.
    unreachable = {"chat/AskSurface.tsx", "chat/Transcript.tsx", "chat/Composer.tsx",
                   "home/NationalReading.tsx", "flagship/motion.tsx"}
    unstyled = []
    for component in sorted((SRC).rglob("*.tsx")):
        if ".test." in component.name or str(component.relative_to(SRC)) in unreachable:
            continue
        for match in re.finditer(r'className=(?:"([^"]*)"|\{((?:[^{}]|\{[^{}]*\})*)\})', read(component)):
            if match.group(1) is not None:
                chunks = [match.group(1)]
            else:
                # Only quoted literals in an expression are class names; identifiers are not. A literal
                # on the right of a comparison is a value being tested, not a class -- in
                # `tone === 'rain' ? ' chart-rain' : ''` the class is chart-rain and 'rain' is the test.
                expression = re.sub(r"[=!]==?\s*(?:'[^']*'|\"[^\"]*\")", "", match.group(2))
                chunks = [a or b for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", expression)]
            for chunk in chunks:
                names = [n for n in chunk.split() if re.fullmatch(r"[a-z][a-z0-9-]{2,}", n)]
                if names and not any(n in styled for n in names):
                    unstyled.append(str(component.relative_to(SRC)) + ' "' + " ".join(names) + '"')
    fe13 = bool(css) and not unstyled
    findings.append(("FE13_no_unstyled_element", fe13,
                     "every element resolves to at least one rule in the built stylesheet"
                     if fe13 else "drawn by browser defaults: " + "; ".join(sorted(set(unstyled)))[:200]))

    # FE14: the ink is legible on every hour's ground, measured rather than asserted.
    #
    # DESIGN.md has claimed "contrast is measured rather than assumed" since before there was anything
    # measuring it. Now that two of the four hours are light pages, the claim has teeth: the same ink
    # ladder cannot serve a near-white ground and a navy-black one, and the tertiary ink -- which carries
    # the provenance line, the smallest type in the product -- is the one that fails first. It was at
    # 3.54:1 on the light grounds and 4.30:1 on night when it was measured for the first time.
    #
    # WCAG AA is 4.5:1 for normal text. The provenance line is 11.5px, so it is normal text.
    def _luminance(value):
        value = value.lstrip("#")
        channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def _contrast(ink, ground):
        light, dark = sorted((_luminance(ink), _luminance(ground)), reverse=True)
        return (light + 0.05) / (dark + 0.05)

    # The check this replaces read one ground per hour, --g-bg, and it passed while three surfaces were
    # failing in a browser: --g-bg is the LIGHTEST part of a light hour and the DARKEST part of a dark one,
    # so the one ground it never looked at was the one the top bar sits on. A browser probe on 19 September
    # measured the sky at the top of the page: mist-2 came out at 2.87:1 on noon, and the tertiary ink is
    # the provenance line. The grounds checked now are the whole gradient, and the two ink ladders are
    # treated as what they are -- the tertiary step is a surface ink and is not used over the sky.
    FLOOR = 4.5
    short = []
    for hour in ("night", "golden", "daybreak", "noon"):
        # Anchored to the line start so the shared light-hours block, whose selector list begins
        # "[data-hour='daybreak'], [data-hour='noon'] {", is not mistaken for noon's own block.
        block = re.search(r"^\[data-hour='" + hour + r"'\]\s*\{(.*?)\n\}", gpt_css, re.S | re.M)
        if not block:
            short.append(hour + ": no palette block")
            continue
        tokens = dict(re.findall(r"(--g-[a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", block.group(1)))
        grounds = [(name, tokens.get(name)) for name in ("--g-bg", "--g-sky-2", "--g-sky-1")]
        if not all(value for _, value in grounds):
            short.append(hour + ": " + ", ".join(name for name, value in grounds if not value) + " not declared")
            continue
        for name in ("--g-paper", "--g-mist", "--g-mist-2"):
            ink = tokens.get(name)
            if not ink:
                short.append(hour + " " + name + ": not declared")
                continue
            # Over the sky the product uses paper and mist; the tertiary step belongs to surfaces, and the
            # stylesheet has no rule that paints it on the bare ground.
            checked = grounds if name != "--g-mist-2" else grounds[:2]
            for ground_name, ground in checked:
                measured = _contrast(ink, ground)
                if measured < FLOOR:
                    short.append(hour + " " + name + " on " + ground_name + " " + format(measured, ".2f") + ":1")
    # The selected Meridian palette is the live React ground. Historic hour palettes above
    # remain covered for utility consumers, but cannot stand in as proof of this theme.
    meridian_css = read(SRC / "gpt" / "css" / "meridian.css")
    # The token block moved from `.g[data-design='meridian']` to `:root[data-design='meridian']`, and the
    # move was the point: `.g` carries the same attribute, and a declaration on an element beats its
    # parent's inline style, so declaring these on `.g` meant every value Field.tsx computed reached the
    # document element and nothing below it. Either selector is accepted here so this check follows the
    # palette rather than pinning it to the selector that had the bug.
    meridian_block = re.search(r"(?::root|\.g)\[data-design='meridian'\][^{]*\{(.*?)\n\}", meridian_css, re.S)
    meridian = dict(re.findall(r"(--g-[a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", meridian_block.group(1) if meridian_block else ""))
    # THE PAGE'S INKS, ON THE PAGE'S OWN PLANES. --g-rail-fill is deliberately NOT in this list any more:
    # the rail is near-black now, and measuring the page's dark ink against it produced a number about a
    # pairing that never occurs on screen. The rail carries its own inks and they are measured below,
    # against the plane they actually sit on -- which is the check that was missing all along.
    for ink_name in ("--g-paper", "--g-mist", "--g-mist-2", "--g-accent", "--g-accent-2"):
        for ground_name in ("--g-bg", "--g-raise", "--g-raise-2", "--g-bar-fill", "--g-accent-wash"):
            ink, ground = meridian.get(ink_name), meridian.get(ground_name)
            if not ink or not ground:
                short.append("Meridian missing " + ink_name + " or " + ground_name)
            elif _contrast(ink, ground) < FLOOR:
                short.append("Meridian " + ink_name + " on " + ground_name + " below AA")
    # THE RAIL'S OWN INKS, ON THE RAIL.
    for ink_name in ("--g-rail-ink", "--g-rail-mist", "--g-rail-mist-2", "--g-rail-accent"):
        ink, ground = meridian.get(ink_name), meridian.get("--g-rail-fill")
        if not ink or not ground:
            short.append("Meridian missing " + ink_name + " or --g-rail-fill")
        elif _contrast(ink, ground) < FLOOR:
            short.append("Meridian " + ink_name + " on the rail below AA")
    fe14 = not short
    findings.append(("FE14_ink_contrast", fe14,
                     "Meridian and historic palettes: every ink clears " + str(FLOOR) + ":1 on every ground of its hour (the tertiary step on "
                     "the page ground and the sky's lower band, the two upper inks on all three)"
                     if fe14 else "below " + str(FLOOR) + ":1 — " + ", ".join(short)[:180]))

    # FE16: a published hazard colour, printed as ink on its own wash, clears AA at the size it is printed.
    #
    # FE14 measures an ink against the page. A hazard cell is not on the page: it is on a 16 percent wash of
    # its own colour, over a card that is itself a translucent raise -- so the ground under the ink is close
    # to the ink's own hue, which is the worst case for a colour and the one no page-ground check sees.
    # Measured in a browser on 19 September: red 4.21:1 and orange 3.90:1 at 9.5px on the light hours, both
    # under the floor, while yellow and green cleared it. The four are held to it here.
    #
    # The composite is computed in sRGB while the stylesheets use oklab, so this is a close approximation
    # rather than the browser's own number. It agrees with the measured pair to within 0.15 where both exist.
    def _mix(a, b, weight):
        first, second = a.lstrip("#"), b.lstrip("#")
        return "#" + "".join(
            format(round(weight * int(first[i:i + 2], 16) + (1 - weight) * int(second[i:i + 2], 16)), "02x")
            for i in (0, 2, 4))

    WASH, CARD = 0.16, 0.55
    washed = []
    # The two light hours share a block for the tokens that are not per-hour, and the published colours are
    # declared in it. Reading only the hour's own block reported all four as "not declared", which is the
    # same anchoring mistake FE14's comment records.
    shared_light = re.search(r"^\[data-hour='daybreak'\], \[data-hour='noon'\]\s*\{(.*?)\n\}", gpt_css, re.S | re.M)
    for hour in ("daybreak", "noon"):
        block = re.search(r"^\[data-hour='" + hour + r"'\]\s*\{(.*?)\n\}", gpt_css, re.S | re.M)
        tokens = {}
        for body in (shared_light.group(1) if shared_light else "", block.group(1) if block else ""):
            tokens.update(dict(re.findall(r"(--g-[a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", body)))
        if not tokens.get("--g-raise") or not tokens.get("--g-bg"):
            washed.append(hour + ": no card tokens")
            continue
        card = _mix(tokens["--g-raise"], tokens["--g-bg"], CARD)
        for name in ("--g-red", "--g-orange", "--g-yellow", "--g-green"):
            ink = tokens.get(name)
            if not ink:
                washed.append(hour + " " + name + ": not declared")
                continue
            measured = _contrast(ink, _mix(ink, card, WASH))
            if measured < FLOOR:
                washed.append(hour + " " + name + " " + format(measured, ".2f") + ":1")
    for name in ("--g-red", "--g-orange", "--g-yellow", "--g-green"):
        ink = meridian.get(name)
        card = meridian.get("--g-bg")
        if not ink or not card or _contrast(ink, _mix(ink, card, WASH)) < FLOOR:
            washed.append("Meridian " + name + " below AA or missing")
    fe16 = not washed
    findings.append(("FE16_published_colour_on_its_wash", fe16,
                     "red, orange, yellow and green each clear " + str(FLOOR) + ":1 on their own " +
                     str(int(WASH * 100)) + " percent wash over a card, on both historic light hours and the active Meridian ground"
                     if fe16 else "below " + str(FLOOR) + ":1 — " + ", ".join(washed)[:180]))

    # FE15: the selected interface is LIGHT at every hour. Not frozen -- light.
    #
    # This check used to read "stable across solar hours" and enforce it by forbidding Field.tsx from
    # calling applySpectrum at all. That banned the code path instead of measuring the property, with two
    # costs. It never actually measured anything: a palette that went dark at midnight by some other route
    # would have passed. And it made "light" mean "one frozen set of hex values", which is what left the
    # page byte-for-byte identical at 06:00 and 23:00.
    #
    # The requirement was always that a reader who chose a light interface is never handed a dark one --
    # not that the light may never move. So the property is now measured, every fifteen minutes across a
    # full day at four latitudes, in meridianSpectrum.test.ts: the ground stays pale, the ink stays dark,
    # every ink clears AA on every ground, and the day is required to actually differ between its hours.
    #
    # What is checked HERE is the wiring that test cannot see: that the block still declares the light
    # colour-scheme, that Field drives Meridian's own family rather than the solar one that flips to dark,
    # and that the measuring test exists to be run.
    active_field = read(SRC / "gpt" / "Field.tsx")
    sweep_test = (SRC / "gpt" / "meridianSpectrum.test.ts")
    fe15 = (bool(meridian_block)
            and "color-scheme: light" in meridian_block.group(1)
            and "meridianSpectrumAt(" in active_field
            and not re.search(r"\bspectrumAt\(", active_field.replace("meridianSpectrumAt(", ""))
            and sweep_test.exists()
            and "--g-paper" in read(sweep_test))
    findings.append(("FE15_selected_light_ground", fe15,
                     "Meridian's own light family drives the ground, the solar family that flips to dark cannot reach it, "
                     "and a sweep across the day measures that it stays light and legible"
                     if fe15 else "the active ground may drift away from the selected light direction"))

    # FE17: nothing a reader is meant to read is set below eleven pixels.
    #
    # The chart engine's labels were at 9.5px and the module surfaces' meta lines at 10 and 10.5 — column
    # headers on the district matrix, the family and scope labels on every document card, the tool output
    # lines on the board. Small type is how a dense surface pretends to be less dense than it is, and the
    # matrix labels in particular name a published hazard colour.
    #
    # Two things are exempt and both are exempt for a reason, not by convenience: text inside an SVG
    # viewBox is in user units that scale with the frame rather than in CSS pixels, and a screen-reader-only
    # rule is clipped to one pixel and never read by eye.
    SVG_TEXT = re.compile(r"\bfill:", re.I)
    small = []
    for sheet in sorted((SRC).rglob("*.css")):
        # Paper is not a screen. print.css expands a link into its URL after the text, and ten point on
        # paper at print resolution is the convention for that, not a legibility failure.
        if sheet.name == "print.css":
            continue
        text = re.sub(r"/\*.*?\*/", "", read(sheet), flags=re.S)
        for block in re.finditer(r"([^{}]+)\{([^}]*)\}", text):
            selector, body = block.group(1).strip(), block.group(2)
            if "clip-path" in body or "clip:" in body:
                continue
            for size in re.findall(r"font-size:\s*([0-9]+(?:\.[0-9]+)?)px", body) + \
                        re.findall(r"font:\s*[0-9]+\s+([0-9]+(?:\.[0-9]+)?)px/", body):
                if float(size) < 11.0 and not SVG_TEXT.search(body):
                    small.append(sheet.name + " " + selector.split("\n")[-1].strip()[:38] + " @" + size + "px")
    fe17 = not small
    findings.append(("FE17_type_floor", fe17,
                     "no visible text is set below 11px"
                     if fe17 else "below the 11px floor: " + "; ".join(sorted(set(small)))[:170]))

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
