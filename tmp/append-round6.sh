set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
cat > /tmp/round6.md <<'EOF'
## Round 6 — WS7 (part 1): the reading position, and a briefcase for what you keep

docs/49's structural finding 5 was that there is no product surface beyond one page: thirteen
surfaces read a product view, and every reader got the same order and the same questions. A farmer
had to know the farm advisory surface existed; a district officer had to think of the warnings
surface. The briefs the workspace could compose were artefacts with content hashes and no way to
keep one.

| Landed | Where | Evidence |
|---|---|---|
| Three registered reading positions with their own surfaces, first-listed evidence classes, suggested questions and stated limits | weathergpt_data/personas.py | tests/test_personas_briefcase.py; /api/personas catalogue |
| The position is validated before any work is done and refused when unknown | weathergpt_data/conversation.py | an unknown id is a 400 before planning; no silent default |
| Every answer carries the position it was read under, with the rule that it changes no finding | weathergpt_data/conversation.py, web/views.js | the receipt renders `Read as: …` and the no-finding note |
| The page offers the position and reorders what is offered, keeping every surface | web/index.html, web/shell.js, web/views.js | browser/persona-*.json for all three positions |
| A local briefcase: keep, list, reopen, export and delete briefs the server composed | weathergpt_data/briefcase.py, weathergpt_data/workspace.py | tests/test_personas_briefcase.py; /api/briefs and its get/export/save/delete routes |
| A brief is composed by the server, never posted by the page, and a payload with no provenance is refused | weathergpt_data/briefcase.py, web/panels.js | the page sends kind, lat, lon and day; an empty payload raises |
| The Briefcase surface and the keep action inside the alert-brief drawer | web/panels.js, web/index.html, web/style.css | tests/test_briefcase_ui.js; browser/briefcase-drawer.png, browser/brief-saved.png |

### The rules the tests pin

- **A position is not evidence.** The same question with and without a persona returns the same
  facts, units, windows and sources; the persona block carries framing keys only.
- **No position chooses a language**, because language support is measured rather than selected.
- **An unknown position is refused**, not treated as the neutral reader.
- **No surface is dropped** when the rail is reordered for a position.
- **A brief that names no source and states no limit is not kept**; a not-available brief is kept,
  because *not issued* is an answer, and its title says so.
- **Export is a file, not a delivery**: the export opens with the notice, and the entry records
  `local_only_no_delivery`. A payload this version cannot render is quoted, never paraphrased.

### Evidence

- `research/implementation/personas-briefcase-20260915/` — the live server run
  (`tmp/evidence-personas-briefcase.py`), the browser session, the exported Markdown and the
  `Content-Disposition` header.
- The same question asked with `persona: farmer` and without one returned the same fact set; the
  answer carried `applied: emphasis_only`.
- Two briefs kept in one run (alert and advisory), read back with their Markdown, exported as a 3131
  -character file, then one deleted.
- In the page: the position control, the reordered rail for each of the three positions, a kept brief
  reopened in the drawer, a brief saved from the warning journey, and a real 3164-byte download.

### What this does and does not establish

- It establishes the position as a declared, server-checked, disclosed choice, and the briefcase as a
  local store of composed briefs that can be reopened and exported.
- It does not establish any usability or quality effect of a position, and it does not deliver,
  schedule, push or share anything.
- WS7 is not finished by this round. Its exit check also asks for a scheduled briefing artefact, with
  a recorded run, and that is the next round.
- The page evidence is one desktop viewport, one browser and one session; no screen-reader, mobile,
  keyboard-only or cross-browser acceptance is claimed.

EOF
cat /tmp/round6.md >> docs/49-engine-architecture-and-gap-analysis.md
grep -c 'Round 6' docs/49-engine-architecture-and-gap-analysis.md
