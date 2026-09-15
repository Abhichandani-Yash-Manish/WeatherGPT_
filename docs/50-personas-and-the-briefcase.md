# Personas and the briefcase: a reading position that changes no finding, and briefs you keep — 15 September 2026

This is the first half of WS7 in [docs/49](49-engine-architecture-and-gap-analysis.md): the product
surface the problem statement asks for (a farmer, a district officer and a traveller reaching the
same verified facts) and the briefcase that turns a composed brief into something a reader keeps.
The scheduled briefing half of WS7 is not in this batch and is not claimed.

## The gap this closes

docs/49 put it plainly: *no product surface beyond one page.* Thirteen surfaces read a product view,
and the same facts were presented to everyone in the same order. A farmer opening the workspace had
to know that the farm advisory surface existed; a district officer had to find the warnings surface;
a traveller had to think of aviation. Nothing was wrong with any of those surfaces. What was missing
was a position: a declared answer to *who is reading*, which decides where the page starts and which
questions it offers, and which is disclosed in the answer so the framing can never be mistaken for
the finding.

The second half of the gap was that a brief could be composed but not kept. The alert brief and the
advisory brief were already artefacts with content hashes; a reader who wanted one on disk had no
route to it from the page, and nothing local held what had been composed.

## What landed

| Landed | Where | Evidence |
|---|---|---|
| Three registered reading positions — farmer, district officer, traveller — each with its own surfaces, first-listed evidence classes, suggested questions and stated limits | weathergpt_data/personas.py | tests/test_personas_briefcase.py; /api/personas carries the catalogue |
| A persona is refused when unknown, never guessed, and is checked before any work is done | weathergpt_data/conversation.py | an unknown id is a 400 before planning, not a silent default |
| Every answer carries the position it was read under, and the disclosure states the rule | weathergpt_data/conversation.py, web/views.js | the answer receipt renders `Read as: …` with the no-finding rule |
| The page offers the position: a control in the masthead, surfaces reordered, persona questions offered first | web/index.html, web/shell.js, web/views.js | browser/persona-*.json, browser/welcome-as-farmer.png |
| The local briefcase: keep, list, reopen, export and delete composed briefs, each with its kind, place, window, named sources and content hash | weathergpt_data/briefcase.py, weathergpt_data/workspace.py | tests/test_personas_briefcase.py; /api/briefs, /api/briefs/get, /api/briefs/export, /api/briefs/save, /api/briefs/delete |
| A brief is composed by the server, never posted by the page: the client asks for a brief for a point and a day, and a payload with no provenance is refused | weathergpt_data/briefcase.py, web/panels.js | an empty payload raises; the page sends kind, lat, lon, day |
| The Briefcase surface: kept briefs with their provenance, open in the evidence drawer, export as Markdown, delete locally | web/panels.js, web/index.html, web/style.css | tests/test_briefcase_ui.js; browser/briefcase-drawer.png |
| The alert-brief drawer can keep what it just composed | web/panels.js | browser/brief-save-in-page.json, browser/brief-saved.png |

## The rules the tests pin

- **A position is not evidence.** `annotate()` returns framing keys only; the same question asked
  with a position and without one returns the same facts, source ids, units and windows.
- **No position chooses a language.** Language support is measured, not selected by who is reading.
- **An unknown position is refused** rather than quietly treated as the neutral reader.
- **A surface is never dropped** when the rail is reordered: the persona's surfaces move first and
  every other surface keeps its place after them.
- **A brief with no named source and no stated limit is not kept.** The store refuses it instead of
  accepting a claim nothing backs.
- **A not-available brief can be kept**, because *not issued* and *not carried by this edition* are
  answers: the entry records why, and its title says so.
- **Export is a file, not a delivery.** The export begins with a notice that nothing was delivered
  or published, and the store records `local_only_no_delivery`.
- **A payload this version cannot render is quoted, not paraphrased.** The entry is kept as stored.

## Measured on a live local server

Driver: `tmp/evidence-personas-briefcase.py` against `python3 -m weathergpt_data.workspace`.

- `/api/personas` returned three positions: `farmer`, `district_officer`, `traveller`
  (`personas-catalogue.json`).
- The same question — *Will it rain in Ahmedabad, Gujarat tomorrow morning?* — asked with
  `persona: farmer` and without a persona returned the same fact set: same parameter, value, unit
  and source (`chat-persona-farmer.json`, `chat-no-persona.json`). The answer carried
  `applied: emphasis_only` with the no-finding note.
- Two briefs were composed and kept in one run — an alert brief for Ahmedabad and an advisory brief
  for cotton at squaring — each with its own content hash and named sources (`briefs-list.json`).
- Reading one back returned the stored payload with its Markdown export (`brief-get.json`); the
  export route answered with `Content-Disposition: attachment; filename="advisory-brief-cotton-squaring-ahmedabad-236e9faa.md"`
  and 3131 characters of Markdown (`brief-export.md`, `brief-export-headers.txt`).
- Deleting the first entry left one in the store (`brief-delete.json`).

## In the page

A headless Chromium session at 1440x1200, recorded in `browser/`:

- the masthead control offers the neutral option plus the three positions;
- selecting one reorders the surfaces and the offered questions and changes nothing else —
  farmer: advisories, forecast, climate; district officer: warnings, map, observations, changes;
  traveller: forecast, aviation, marine, observations;
- the Briefcase lists kept briefs with their provenance; opening one shows the provenance table and
  the export text; the alert-brief drawer kept a brief with *"Kept as …"*; the Briefcase then listed
  two alert briefs;
- the page's own export wrote a real 3164-byte Markdown file through the browser download path.

## What this does and does not establish

- It establishes that a reading position exists as a declared, disclosed, server-checked choice; that
  it changes emphasis and never evidence; and that a composed brief can be kept, reopened, exported
  and deleted entirely on this machine.
- It does **not** establish any effect of a position on answer quality or usefulness: no usability
  study, no task-completion measurement, no native-speaker review.
- It does **not** establish delivery, scheduling, sharing or notification: nothing is pushed, and the
  export is a file the reader keeps. WS7's scheduled-briefing exit check is still open.
- The browser check is one desktop viewport, one browser and one session: no screen-reader, mobile,
  keyboard-only or cross-browser acceptance, and the download path was exercised once.
- No forecast skill, no accuracy and no operational clearance is claimed anywhere in this batch.
