# The installable app: measured before the batch, 20 September 2026

Every line below was measured on this machine, not read off the source. It exists so the PWA lane starts
from a state rather than a guess, and so the "before" survives whatever the fixes turn out to be.

## The workspace was started and its own routes asked

    python3 -m weathergpt_data.workspace --port 8781 --no-warm --no-plan-watcher

| Route | Status | What a phone would do |
| --- | ---: | --- |
| `/` | 200 | the shell loads |
| `/sw.js` | 200 | the worker registers |
| `/manifest.webmanifest` | **404** | no manifest: the app is not installable, on any browser, over any transport |
| `/icon-192.png` | **404** | the icon `index.html` names and the manifest lists |
| `/icon-512.png` | **404** | as above |
| `/icon-maskable-512.png` | **404** | as above |

`index.html` asks for three of those by name — `<link rel="manifest" href="/manifest.webmanifest">` and
`<link rel="apple-touch-icon" href="/icon-192.png">` — so the page names four things the server does not
answer. The GET handler serves `/`, `/index.html`, `/probe.html`, `/assets/*`, `/viz.js` and `/sw.js`, and
everything else falls through to 404. The four files are tracked, and the build copies them into
`web/dist/`, which is not a directory the handler reads from.

**This is not the HTTPS gate.** docs/118 says F4a, X3, M1 and M2 are gated on a secure context because push
needs one. That is true of push. It is not true of M2: on loopback — which browsers already treat as a
secure context — the manifest is still a 404, so "the app installs as a PWA" cannot be demonstrated here
even before DNS exists. Two independent things were being carried as one.

## There are two service workers, and the server serves the older one

| File | Served? | What it is |
| --- | --- | --- |
| `web/sw.js` | **yes**, at `/sw.js` | the thin worker: `push`, `notificationclick`, `pushsubscriptionchange`, and a body that says the content is unavailable |
| `frontend/public/sw.js` | **no** | a fuller worker: `install` with `skipWaiting`, `activate` with `clients.claim`, an explicit unreadable-payload body, `requireInteraction`, an Acknowledge action, `postMessage` to the page, and a subscription-change event the page can record |

The build copies `frontend/public/sw.js` to `web/dist/sw.js`, and `web/dist/` is not tracked (0 files in
git) and is not served. So the fuller worker has never reached a browser. docs/92 §5 records the decision
that `web/sw.js` is served "from its one tracked copy, like `web/viz.js`", pinned by
`tests/test_react_vendor_assets.py` — which means the second copy is an edit that was written, built and
never served, and the check that pins the vendor assets does not know about it.

Worth keeping, because it bounds the risk: the served worker has **no fetch handler and neither copy caches
anything**. Offline stays what docs/92 says it is — the shell needs the local server, which owns the
evidence. So this is not a provenance defect and not a stale-answer defect; it is a delivery defect.

## What the shell says about itself is the retired language

- `index.html` prints `theme-color` `#ecf0ec` (light) and `#0b1216` (dark), and an inline favicon in a data
  teal `#0d6d77`.
- `frontend/public/manifest.webmanifest` prints `background_color` `#0b1216` and `theme_color` `#0d6d77`.

The ground the product actually draws is `#070b14` / `#0c1220` / `#131b2b` / `#1e2838` with one pale
instrument-blue accent `#a8c7fa`, and docs/111 moved the identity away from the teal mark. So the three
places the browser reads colour from — the theme colour in the page, the manifest's theme colour, and the
favicon — are the language docs/106 retired. A phone's title bar would be tinted by a palette the product
no longer uses, and this is exactly the class of untested surface the batch is for.

## What this baseline does not say

Nothing here was measured on a phone, and nothing here was measured over HTTPS — neither exists on this
machine. Installability, the install prompt, and a real push delivery remain unproven; what is proven is
that the four files a phone must fetch are 404 today, and that the worker reaching browsers is not the one
someone wrote.
---

## Which worker should live: decided from evidence, 20 September 2026

The obvious reading of the table above is "the fuller worker was written and never served, so serve it".
That reading is wrong, and the evidence is what says so.

| Question | Answer |
| --- | --- |
| Does the page consume the fuller worker's messages? | **No.** A grep of the whole frontend for a `message` listener from the worker, or for `weathergpt-sw`, returns nothing |
| Does the page read the `?ack=` query the fuller worker navigates to? | **No.** Nothing in `frontend/src` reads an `ack` parameter |
| How does the page acknowledge a notification today? | Over `POST /api/outbox/<id>/ack` from the panel's own row, asserted by `planwatch.parity.test.tsx` check 3 |
| Would serving the fuller worker break the vendor check? | No. Neither file contains the string `fetch`, and the vendor test's constraint is that this worker must not cache |

So the fuller worker's **Acknowledge** action would put a button on a notification that navigates to a query
parameter no page reads, and its `postMessage` events would land nowhere. A reader pressing Acknowledge would
believe the ledger had recorded it. **F4b's own criterion is "the acknowledgement returns to the ledger"** -
which makes the fuller-looking worker the *less* honest one to serve today, not the better one.

**Decision.** One worker file, and the bytes served at `/sw.js` are that file. The consumer-free improvements
are worth porting into it (`install` with `skipWaiting`, `activate` with `clients.claim`,
`requireInteraction` so an official warning does not disappear unread, the more precise unreadable-payload
sentence, and the subscription-change notice). The **Acknowledge action, the `?ack=` navigation and the
`postMessage` calls land only with the page features that consume them** - that is X3/F4a work, not this batch.

**The check that must hold it**, stated as the invariant rather than the fix, so either resolution satisfies it:
exactly one of `web/sw.js` and `frontend/public/sw.js` exists, and the body served at `/sw.js` is
byte-identical to it. `tests/test_react_vendor_assets.py` already pins the served bytes; what it cannot see is
that a second worker file exists at all.

## The four 404s: where the fix belongs

The GET branch serves `/`, `/index.html`, `/probe.html`, then `/viz.js` and `/sw.js` from `web/`, then
`/assets/<hash>` from `web/dist`, then 404s. The manifest and the three icons are copied by the build into
`web/dist` and named by the page, and no branch reads them. The fix belongs in that branch, reading
`web/dist` - the same place the page itself comes from - with content types for `.webmanifest` and `.png`,
and no immutable caching, because neither is content-hashed.

The check must read the **built** page, not the template: `frontend/index.html` names `/src/main.tsx`, which is
a Vite development path and is rewritten in the build. So the assertions are: every URL the built page names
with a leading slash answers 200; every icon the manifest names answers 200; and `/sw.js` is the one worker.

## The colour the browser reads, corrected after measuring the stylesheet

This section first read that "docs/111's ground is `#070b14` / `#0c1220`" - numbers taken from the standing
plan's summary of the palette. That was wrong twice over, and the stylesheet is what says so.

**First: the tokens are not those numbers.** `frontend/src/gpt/css/tokens.css` declares
`--g-void: #05080f`, `--g-bg: #0a0f1a`, `--g-raise: #111828`, `--g-raise-2: #172032`, `--g-line: #222d40`,
ink `#edf1f7` / `#96a3b8` / `#6b7890`, and the one accent `#a8c7fa`. So the plan's paragraph and the code
that paints the product disagree about the exact ground, and any change to a browser-visible colour must read
`tokens.css` rather than the paragraph. Recorded as a documentation-versus-code drift for the design owner -
not silently reconciled here, because the paragraph is somebody's summary and the tokens are the product.

**Second, and more important: the product is not dark-only, so a single theme colour cannot be right.**
`tokens.css` carries an hour-keyed ground, and `[data-hour='daybreak']` sets
`--g-void: #f0e9e1; --g-bg: #fdfaf6; --g-raise: #ffffff` - a light, warm-paper morning. At daybreak the
ground is nearly white; at night it is nearly black. A manifest carries one `theme_color` and one
`background_color` for all of it, and `index.html`'s two media-keyed metas answer the OS preference rather
than the hour the page actually resolved.

What is true today, and what a reader sees:

| Where the colour is stated | Stated as | The hour it is right for |
| --- | --- | --- |
| `index.html`, `prefers-color-scheme: light` | `#ecf0ec` | none - it is the retired light language; daybreak is `#fdfaf6` |
| `index.html`, `prefers-color-scheme: dark` | `#0b1216` | none - the night ground is `#0a0f1a` |
| `frontend/public/manifest.webmanifest` | `theme_color: #0d6d77`, `background_color: #0b1216` | none - the data teal is the retired mark |

So a reader on a phone gets a title bar and a splash painted from a palette this product retired, in both OS
preferences, at every hour. The honest fix is **not** a replacement value in three files: it is that the page
resolves its hour anyway, so the `theme-color` meta should be updated at runtime beside whatever sets
`data-hour`, and the manifest should carry the ground the product starts on before any hour is resolved.

**That sequencing matters, and it is why this was not done in the static files.** `data-hour` is set in
`frontend/src/gpt/Workspace.tsx` (another lane holds it) and `frontend/src/place/PlacePage.tsx` (another lane
holds that too). Writing a fixed colour now would lock in a value that is wrong for half the day and would have
to be undone by the lane that owns those two files. Recorded here as the requirement for that lane, with the
tokens it must read.
