# The place page, seen in a browser: 20 September 2026

docs/122 named three things it could not do - "no browser, no screenshot, no width/overflow measurement" - and
listed the checks to run next. This is those checks, run against a built frontend served by the local
workspace. It is the only part of this batch that a real browser has seen.

## How it was run

    cd frontend && npm run build
    python3 -m weathergpt_data.workspace --port 8781 --no-warm --no-plan-watcher
    cd frontend && UI_BASE_URL=http://127.0.0.1:8781 npx playwright test tests/ui/routes.spec.ts tests/ui/a11y.spec.ts --grep place
    cd frontend && UI_BASE_URL=http://127.0.0.1:8781 UI_EVIDENCE_DIR=../research/reviews/frontend-batch-20260920/shots node tools/capture.mjs --only place,place-refused

## What the checks found

| Check | Result |
| --- | --- |
| Place page in the route spec, both addresses, four widths | **16 passed (29.8s)** - 1440, 1024, 768, 390 |
| axe on the named place, four widths | **no violation** |
| axe on the refused address, four widths | **no violation** |
| horizontal overflow | **0 px at every width, both addresses** |
| failed requests, console errors | none, both addresses |
| captures | 16 (two addresses x four widths x two colour schemes), **0 with overflow or a failed request** |

Two of those assertions are the ones worth having:

- **A valid address reads the place; a refused address makes no read at all.** The spec counts requests to
  /api/ rather than counting errors, because "refused before any read" and "a read that failed" are different
  states and the product's rule is the first one. Asserted in a browser, not in jsdom.
- **The heading is the place.** The named address states the label it was given; the half-written one states
  its refusal. The spec fails if either heading is empty or wrong.

## What the page looks like, in its own words

Phone, 390 px, dark. Named place: eyebrow "Place", heading "Kochi, Kerala", then *"Latitude 9.93, longitude
76.26 - the coordinates this address names, in degrees. Every block below is a read for that point; the place
was not resolved from the wording of a question."* - which is the product's own rule about an address-supplied
place, said on the page rather than only in a document. Then the district block: "ERNAKULAM, KERALA - issued 20
Sep 2026, 11:30 IST", the days as "20 Sep 2026 (yellow) Thunderstorm/lightning - squall", "21 Sep 2026 nothing
flagged", "22 Sep 2026 nothing flagged", and the source line "S63 IMD district warnings_india". The yellow is
the colour the packet printed. The hours block says *"This read returned no hourly row for the point, so nothing
is drawn rather than a value being invented"* and offers the forecast surface as the way to more.

Refused address: eyebrow "Refused", heading "No place to show", then *"This address is half-written: it names
"Kochi, Kerala" but gives no longitude (plon=...). A place is either both coordinates or it is nothing, so
nothing is applied here."* - naming the actual missing parameter rather than saying the address is invalid.
Then the rule, then one action, "Back to the conversation".

Screenshots: `shots/{light,dark}-place@{390,768,1024,1440}.png` and the same for `place-refused`, with
`shots/capture-report.json` recording the heading, the section count and the overflow of each.

## The tool change this needed

`frontend/tools/capture.mjs` derived its list from the nineteen registered surfaces, so the place page was
invisible to it - a page the evidence tool cannot see is a page with no evidence. It now takes explicit
addresses as well as surface ids, each with the name its files take (an address carries a question mark and a
file name should not), and the place page in both states is in that list.

## What is still not verified

- **No engine run has been through the page.** The specs use fixtures and the capture ran against a workspace
  whose reads return what they return; the district block above is a real read, the station block was still
  showing its loading sentence when the shot was taken.
- **The rail still cannot send a reader here.** docs/122 records that `src/gpt/Rail.tsx` carries no anchor to
  the page, so "the place is a link somebody can send" is true from the panel and not yet from the rail.
- **No visual baseline.** `tests/ui/visual.spec.ts` iterates the registry, so the place page has no stored
  baseline image; a baseline has to be reviewed before it is committed, and nobody has reviewed one.
- **Nothing here says the numbers are correct.** They are drawn with their sources; whether the source is right
  is a different question this batch does not answer.
