# 123 — The installable app: what the browser asked for, and what the server answered

20 September 2026. This lane started from a measurement rather than a plan, and the measurement held three
separate defects in one place: four files the page names that the server 404s, two service workers where one
is served, and a browser chrome painted from a palette this product retired.

## The four 404s

The workspace was started and asked for its own routes:

    python3 -m weathergpt_data.workspace --port 8781 --no-warm --no-plan-watcher

| Route | Status | What a phone would do |
| --- | ---: | --- |
| `/` | 200 | the shell loads |
| `/sw.js` | 200 | the worker registers |
| `/manifest.webmanifest` | **404** | no manifest: the app is not installable, on any browser, over any transport |
| `/icon-192.png` | **404** | the icon `index.html` names |
| `/icon-512.png` | **404** | the icon the manifest lists |
| `/icon-maskable-512.png` | **404** | the maskable icon the manifest lists |

**This was never the HTTPS gate.** docs/118 carried M1, M2, F4a and X3 as one thing gated on a secure context,
because Web Push needs one. That is true of push. It is not true of the manifest: on loopback - already a
secure context in every browser - the manifest was still a 404, so 'the app installs as a PWA' could not be
demonstrated here even before a hostname existed. Two independent defects had been wearing one sentence.

The GET branch serves `/`, `/index.html`, `/probe.html`, then `/viz.js` and `/sw.js` from their tracked copies,
then `/assets/<hash>` from `web/dist`, then 404s. The manifest and the icons are named by the page and copied
by the build into `web/dist`, and no branch read them.

## The two workers, and the one that was never served

| File | Served? | What it is |
| --- | --- | --- |
| `web/sw.js` | **yes**, at `/sw.js` | the worker the plans panel registers |
| `frontend/public/sw.js` | **no** | a fuller worker the build copied into `web/dist`, which is not a directory the server reads |

The obvious repair - serve the fuller one - is wrong, and the evidence says why. Its extra behaviour has **no
consumer in the page**: nothing in `frontend/src` listens for a `message` from the worker, nothing reads an
`ack` query parameter, and the page acknowledges over `POST /api/outbox/<id>/ack` from its own row
(`planwatch.parity.test.tsx` check 3). So its Acknowledge action would navigate to a parameter nothing reads
- a button that appears to acknowledge and leaves the ledger unchanged, which is precisely what F4b's own
criterion ('the acknowledgement returns to the ledger') forbids.

**What was done instead**: one worker, with the improvements that do not need a page consumer ported into it -
`install` with `skipWaiting`, `activate` with `clients.claim`, `requireInteraction` so an official warning does
not vanish unread, the more precise unreadable-payload sentence, and subscription-change handling. The
Acknowledge action, the `?ack=` navigation and the `postMessage` calls land only with the page features that
consume them, which is X3/F4a work. The unserved duplicate was deleted rather than left: an edit to the file
that is not served looks live and is not.

## The colour the browser paints

`theme-color` in `index.html`, the manifest's `theme_color` and `background_color`, and the favicon are the
places a browser reads colour from before a page has run. All three stated the retired language - the light
`#ecf0ec`, the old `#0b1216`, and the data teal `#0d6d77` - while the ground this product draws is chosen by
the HOUR, with four `--g-bg` values in tokens.css.

A static file cannot follow the hour, so what was fixed is the part that can be: the manifest states a ground
this product actually draws (`#0a0f1a`), the page's two metas state the daybreak ground for a light preference
and the night ground for a dark one, and the check derives the acceptable values from tokens.css rather than
from a design paragraph. The real fix - updating the `theme-color` meta at runtime beside whatever sets
`data-hour` - belongs to the lanes holding `Workspace.tsx` and `PlacePage.tsx`, and is recorded here rather
than half-done.

## The check

`tests/test_shell_assets_served.py` holds all of it, and it is deliberately written before the route exists so
that it can be watched failing:

| Test | What it catches |
| --- | --- |
| the built page names the URLs this is about | the check reading nothing (a template with `/src/main.tsx`, an empty list) |
| every URL the built page names is answered | any file the page asks for that the server does not have - the four 404s, and the next one |
| the manifest is served and parses | a manifest that is missing, wrongly typed, or not JSON |
| every icon the manifest names is served | a manifest listing an icon nobody serves (the manifest and the server drifting apart) |
| the served worker is the only worker | two workers, or a served worker that is not the tracked file, or an unhashed file cached for a year |
| the manifest paints this product's own ground | a browser chrome painted from a palette the product retired |

It reads the BUILT page rather than the template, because `frontend/index.html` names `/src/main.tsx` - a Vite
development path the build rewrites - and a missing build is a reported skip, as the other audits treat it.

## Evidence

| Command | Observed |
| --- | --- |
| `python3 -m pytest tests/test_shell_assets_served.py -q`, before any fix | **5 failed, 1 passed** - the four routes, the two workers, and the colour |
| the same, after the worker and colour repairs | **3 failed, 8 passed** with `tests/test_react_vendor_assets.py` - the three that need the route |
| the three that were still failing | `404 /manifest.webmanifest`, `no manifest to read the icons from`, `the page names what the server does not answer: 404 /manifest.webmanifest, 404 /icon-192.png, ...` |

## What is not covered

- ~~The route itself~~: **landed.** The GET branch in `weathergpt_data/workspace.py` now serves
  `/manifest.webmanifest` and `/icon-<name>.png` from `web/dist` - the directory the page comes from - with the
  manifest typed `application/manifest+json`, the icons `image/png`, no immutable caching (neither is
  content-hashed) and a `[A-Za-z0-9-]+` name pattern so an icon name cannot walk out of its directory. The check
  went from **5 failed, 1 passed** before any fix, to **3 failed, 8 passed** after the worker and colour repairs,
  to **11 passed** with it: `python3 -m pytest tests/test_shell_assets_served.py tests/test_react_vendor_assets.py -q`.
- **No HTTPS, no hostname, no phone.** Nothing here was measured over a secure context beyond loopback and
  nothing was installed. M2's 'behind a real URL' half is untouched by this lane.
- **No push delivery.** The worker was consolidated and its improvements ported, but no notification was
  delivered to any device; that needs push, which needs the secure context docs/118 describes.
- **No runtime theme update**, as above.
- **The icons themselves were not looked at.** They are served or not served; whether the mark on them is the
  mark the product draws now is a design question nobody has asked.
