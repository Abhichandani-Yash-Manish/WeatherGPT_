# Personas and the briefcase - measured on a live local server

Driver: `tmp/evidence-personas-briefcase.py` against `python3 -m weathergpt_data.workspace --port 8796`,
in a browser-less loopback client. This is a desktop-web component check, not native-speaker, screen-reader,
mobile or cross-browser acceptance, and it measures no forecast skill.

## Measured

- Registered positions: Farmer or field adviser (`farmer`), District officer (`district_officer`), Traveller (`traveller`).
- The same question asked with a position and without one returned the same 1 facts: same parameters, values, units and sources.
- The answer carried the position it was read under: `Farmer or field adviser`, applied as `emphasis_only`.
- Kept briefs: 2 (advisory_brief, alert_brief), each with its content hash and named sources.
- Export: `attachment; filename="advisory-brief-cotton-squaring-ahmedabad-236e9faa.md"`, 41 lines of Markdown.
- After deleting the first entry, 1 remained in the local store.

## What this does not establish

- No delivery, push, scheduling or sharing: the store is local and the export is a file.
- No measured effect of a position on answer quality: the check pins that it changes no evidence.
- No browser layout, keyboard or screen-reader acceptance.

## In the page (headless Chromium session, 1440x1200)

- The reading position is a control in the masthead: the neutral option plus the three
  registered positions (browser/persona-on-page.json).
- Selecting a position reorders the surfaces offered first and the questions suggested and
  changes no evidence: farmer -> advisories, forecast, climate; district officer -> warnings,
  map, observations, changes; traveller -> forecast, aviation, marine, observations
  (browser/persona-district_officer.json, browser/persona-traveller.json).
- The Briefcase surface lists kept briefs with their kind, place, named sources, content hash
  and saved instant, and offers Open, Export Markdown and Delete per entry
  (browser/briefcase-drawer.png).
- Opening a kept brief reads it from the local store and shows the provenance table and the
  exact export text (browser/brief-drawer.json).
- Saving works from the Warnings surface end to end: Write the alert brief -> Save to briefcase
  -> "Kept as ..."; the Briefcase then lists two alert briefs
  (browser/brief-save-in-page.json, browser/brief-saved.png).
- The page's own export wrote a real file through the browser download path:
  browser/exported-brief.md, 3164 bytes, opening with the kept-notice, the saved instant, the
  entry id and the content hash.

## What this check does not establish

- One desktop viewport, one browser and one session. No screen-reader, mobile, keyboard-only or
  cross-browser acceptance, and no visual or layout measurement beyond the saved screenshots.
- The download path was exercised once; a repeated download, a blocked download or a different
  browser's download handling was not measured.
- No effect of a reading position on answer quality is claimed: the check pins that the same
  question returns the same facts with and without one.
