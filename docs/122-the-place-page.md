# 122 — The place's own page: a destination for the place an address names

20 September 2026, the batch that finishes the hole [docs/115](115-panel-and-claim-copy.md) ended with. The
panel states the place, the address names it and the panel is now also a link — but §7 of that document said
the last line plainly: *"A place's own page, with its own address, holding what the panel now shows plus its
conversations. The address names the place and the panel shows it; what is still missing is the page — the
panel is the glance, and the destination does not exist yet."* This document is that destination.

## 1. What was missing, and why this shape

Three facts already existed and none of them was a page. The place each conversation's own answers resolved is
carried by the ledger ([docs/114](114-places-and-search.md)); the address `#/assistant?place=…&plat=…&plon=…`
holds a place on arrival and opens the panel; and the panel states the place, its nearest station, what is
published for its district and the hours the model returned. A reader could not go to a place. They could only
be in a conversation that happened to be about one.

The destination is **`#/place?place=…&plat=…&plon=…`** — the same three names the panel already writes (`place`,
`plat`, `plon`), with one word different, so a link a reader already has is edited rather than replaced.

It is deliberately **not** a twentieth surface. The surface registry (`frontend/src/shell/views.ts`) is the
list of peer surfaces: each one is a rail entry, each one has a module renderer, and the two are held together
by checks this batch may not touch —

| Held by | What it requires |
| --- | --- |
| `scripts/audit_surface_registry.py` | the React registry and the frozen 19-entry expectation must agree exactly (measured: 10 checks, 0 failed with the registry unchanged) |
| `src/modules/surface.parity.test.tsx` | every `VIEWS` entry but `assistant` has a module renderer |
| `frontend/tests/ui/routes.spec.ts`, `a11y.spec.ts`, `visual.spec.ts` | each iterates `VIEWS` |

The place page is none of those things: it is rendered for one place rather than as a peer, it has no module
entry, and a rail row leading to it would offer a page whose only honest answer, without a place in the address,
is a refusal. So the route is declared where the shell's other non-surface routes are declared — `PLACE_ROUTE`
in `frontend/src/shell/views.ts`, beside the front door and the owner gate — and read from there by
`parseHash`, so the string has one home. What the surface audit would need instead is named in §6.

The other thing this page is not is a second dashboard. The station, the district days and the hours are the
panel's own blocks, exported and rendered here for this page rather than copied (`StationBlock`,
`DistrictBlock`, `HoursBlock` in `frontend/src/gpt/ReadingPanel.tsx`), so a fix to a read reaches both and the
glance and the destination cannot state the same read differently. The depth stays with the claim: the page is
the place, and the answers about it are still the conversation's.

## 2. The route, and the rule that refuses a half-written address

    #/place?place=Kochi%2C+Kerala&plat=9.93&plon=76.26

`readPlaceAddress` (`frontend/src/place/place.ts`) is the single place the address is read, and it is the rule
the assistant address already had: **a place is a name and a coordinate pair that parse as numbers and fall
inside the world, or it is nothing at all.** A refusal is stated on the page it names rather than redirected to
the conversation, because a redirect could not say what was wrong with the link.

| Address | Answer |
| --- | --- |
| `place=…, plat=9.93, plon=76.26` | the place, its blocks, and this browser holds it |
| no `place` | *"This address names no place…a name is never filled in from a pair of numbers."* |
| `place=…` and one coordinate | *"…it names “Kochi, Kerala” but gives no longitude (plon=…)."* |
| `plat=9.93N` | *"…states latitude “9.93N”, which is not a number."* |
| `plat=91` / `plon=180.01` | *"…which is outside the world (latitude ±90, longitude ±180)."* |
| `plat=0&plon=0` | accepted — on the equator, and `0` is read as a number rather than as absent |

A refused address makes **no read at all** (the spec counts the four routes at zero), and it does not overwrite
the place this browser holds with half of one. An accepted one holds the place, which is what the product
already does with a place named in an address ([docs/115](115-panel-and-claim-copy.md) §3), so a reader
arriving from somebody else's link holds the place that link names and the tab names it too
(`WeatherGPT — Kochi, Kerala`).

## 3. What is on the page, and the source line each block carries

| Block | What it states | Its source line |
| --- | --- | --- |
| The place | the name, and *"Latitude 9.93, longitude 76.26 — the coordinates this address names, in degrees"*, said as the address's own because that is the one fact on the page no source stated | the address itself, named as the address |
| The nearest station | the station's own wording and temperature, its distance from the point | station name · source id · read instant · *"4.2 km away"* · the payload's own "no unit in the source" when it printed none (the block also says *"The source marks this report stale."*) |
| Published for this district | the district and state, the issue instant, each published day in the colour the product printed, a day the product flagged nothing for as **nothing flagged**, and a read that published no day as *"published no day for this district, which is not the same as a quiet one"* | district, state and issue instant, then the registered source from the envelope |
| The next hours | the hours the read returned, each with the unit the payload stated | source id · model · the window the read returned |
| This machine's conversations about this place | the stored conversations whose **own answers** resolved this place, linked back to each, with the store's own turn count and stored instant | read from the store's ledger, and the block says the place is the one each conversation's own answers resolved, as this machine recorded it |
| In this browser | whether this place is pinned, through the product's own pin control | this browser's own local list, said as such: a pin states nothing about the place |

Three rules came with it, and they are the product's rules rather than this page's:

1. **A missing state is never a value.** The empty case is checked as a whole: no hazard chip is drawn, no
   number in the shape of a value (`°C`, `mm`, `%`, `km`, `turns`) appears anywhere, and every gap is a
   sentence — no station for the point, no day for the district, no hourly row, no stored conversation.
2. **Two different silences are said differently.** The station block used one sentence, *"No place is held, so
   no station was read"*, for both "no read was made" and "the read came back with no station". On a page that
   has just held the place, that sentence was false, so the block now distinguishes them.
3. **The district block gained the source line docs/115 said it kept.** It stated a colour and a hazard with
   the district name and issue instant and nothing else to check them against; it now prints the registered
   source the envelope named (`S15 imd:district_warnings_india`). The panel gained it with the page, because
   the block is one component.

## 4. How a reader reaches it, and how they get back

- **The panel** carries a real link — an `<a href>`, not a button that rewrites the address, because a page a
  reader can bookmark cannot be a button: *"The place's own page →"*, written from the place the panel holds.
  Choosing a place in the rail still writes `#/assistant?place=…` (docs/115 §3, checked in
  `src/gpt/shell.test.tsx`), and the panel's link is the step from that address to the page.
- **The page** carries *"Ask about this place"* — `#/assistant?place=…&plat=…&plon=…`, the link shape
  docs/115 recorded, unchanged — so arriving here is never a dead end, and *"Back to the conversation"*.
- The blocks keep their own ways in (*"Warnings in force →"*, *"The forecast surface →"*), which now work from
  the page as well as from the panel.

The batch's files, so the next reader knows what exists:

| File | What changed |
| --- | --- |
| `frontend/src/place/place.ts` | new — the address contract: `readPlaceAddress`, `placeHref`, `conversationHref`, `storedConversationHref` |
| `frontend/src/place/PlacePage.tsx` | new — the page, its frame, and its conversations block |
| `frontend/src/place/place.test.ts`, `frontend/src/place/PlacePage.test.tsx` | new — 18 checks, beside the code they hold |
| `frontend/src/shell/views.ts` | `PLACE_ROUTE`, declared with the reason it is not a `VIEWS` entry |
| `frontend/src/shell/useHashRoute.ts` | `ShellRoute` gains `'place'`, and `parseHash` reads `#/place` |
| `frontend/src/App.tsx` | the place shell renders `PlacePage`; the shell stops naming the tab "Ask" for it |
| `frontend/src/gpt/ReadingPanel.tsx` | `StationBlock` extracted, `StationBlock`/`DistrictBlock`/`HoursBlock` exported for the page, the panel's place block links to it, the district block gained its source line, and the station block's two silences are said differently |
| `docs/122-the-place-page.md` | this document |

## 5. Evidence

| Command | Observed |
| --- | --- |
| `cd frontend && npx tsc --noEmit` | every file this batch touched is clean; the only errors are another lane's `src/flagship/provenance.surfaces.test.tsx` (two unused imports, mid-edit). Retried once as the batch requires, reported and not touched |
| `npx vitest run src/place/` | **2 files, 18 checks, 0 failed** (`place.test.ts` 9, `PlacePage.test.tsx` 9) |
| `npx vitest run` over the eight other specs this batch touches | **9 files, 77 checks, 0 failed** — `src/place/` (18), `src/gpt/shell.test.tsx` (26 — the panel's own spec), `src/App.test.tsx` (9), `src/shell/shell.test.ts` (2), `src/shell/homes.test.ts` (5), `src/shell/palette.gaps.test.tsx` (4), `src/modules/surface.parity.test.tsx` (10), `src/shell/keyboard.test.tsx` (3) |
| `python3 scripts/audit_surface_registry.py` | **10 checks, 0 failed** (the registry is unchanged: 19 entries, both frontends agree) |
| `python3 scripts/audit_react_frontend.py` | **19 checks, 0 failed**, FE13 (no unstyled element) included — every class the page uses already exists in the built stylesheet the audit reads (`web/dist`, built by another lane's batch and not rebuilt here; that is exactly what this pass proves — no new class name was needed). A re-run minutes later, while another lane was mid-edit, reported FE13 failing on `modules/DashboardCharts.tsx "dash-chart-bar"` — not a file or a class this batch touched |

Two checks were demonstrated failing rather than asserted to work:

| Check | What was broken | Observed |
| --- | --- | --- |
| *"refuses a point outside the world, either coordinate"* | the in-world guard in `readPlaceAddress` short-circuited to `false` | `Tests 1 failed \| 8 passed (9)` — `expected { label: 'Nowhere', … } to be null` |
| *"says what is missing in words when every read comes back empty, and never draws a zero"* | the empty-conversations sentence replaced with `Conversations about Kochi, Kerala: 0.` | `Tests 1 failed \| 8 passed (9)` — `Unable to find an element with the text: /holds no conversation whose own answers resolved/` |

Both files were restored byte-for-byte afterwards (`diff -q` against the saved copy: identical).

Two red things that belonged to other lanes were seen during the batch and are recorded rather than repaired;
both cleared before the final run, and neither touched a file this batch owns:

| Where | What was observed | Why it was not this batch's |
| --- | --- | --- |
| `npx tsc --noEmit` | `src/gpt/Workspace.tsx` and `src/flagship/provenance.surfaces.test.tsx` reporting unused imports | `Workspace.tsx` cleared on the lane's next save; `provenance.surfaces.test.tsx` is still mid-edit and read-only here. Retried once, as the batch requires |
| `npx vitest run src/gpt/shell.test.tsx` | one intermediate run: 25 of 26, *"offers a watch only when the answer named a place and something watchable, and sends the sentence"* failing | `src/chat/AnswerTurn.tsx`, `src/chat/model.ts`, `src/chat/useConversation.ts` and `src/gpt/Workspace.tsx` had all changed minutes before, and the chip that test reads is built there; the final run passes 26 of 26 |

## 6. What this does not cover

- **No browser and no screenshot has seen it.** This round forbade a build and a workspace server, so there is
  no rendered image of the page and no measurement of it at any width. The check I would run next is
  `npm run ui:routes` with `#/place?place=Kochi%2C+Kerala&plat=9.93&plon=76.26` added to the route list, which
  would catch a horizontal overflow, a failed request and a console error on the real surface; then
  `npm run ui:a11y` on the same address, for the landmark and heading structure, and `npm run ui:shots` for a
  visual record. The page's classes are all pre-existing, so the layout is predictable, but "predictable" is
  not "seen".
- **The registry and spec lines are not mine to write.** The route works without them, because the shell
  registry names it (`PLACE_ROUTE` in `frontend/src/shell/views.ts`). If the place page is to be covered by the
  audits and the Playwright specs, which all iterate `VIEWS`, the orchestrator adds exactly this:

  ```python
  # scripts/audit_surface_registry.py
  vanilla = [..., 'place']            # 20 entries: frozen_rail_expectation checks len(vanilla) == 20
  SURFACE_ROUTES = {..., 'place': None}   # it has no single product route: it reads
                                          # /api/now, /api/warnings/place, /api/forecast and /api/conversations
  ```
  and, because a `VIEWS` entry must have a module renderer and a home, the same batch then needs:
  `frontend/src/shell/views.ts` (a `VIEWS` entry — mine to add on request), `frontend/src/modules/registry.ts`
  (a `place` entry whose surface reads the address itself, since a module surface takes no props),
  `src/modules/surface.parity.test.tsx` (`['assistant']` → `['assistant', 'place']`) and
  `frontend/tests/ui/routes.spec.ts` (the place address added to `ROUTES`). Those four files belong to other lanes.
- **The rail does not link to it yet.** `src/gpt/Rail.tsx` is another lane's file this round. It needs the same
  one anchor the panel has — beside the pin control in the place section, and beside the row in "Places this
  machine knows" — written from `placeHref`, at which point "the rail and the panel can both send a reader here"
  is true rather than half true.
- **The shell's keys are not mounted here.** The place page carries no rail and no command palette, so ⌥K and
  ⌥/ do nothing on it — as they already do nothing on the front door and the owner gate, which mount neither.
  No shortcut is taken over and none is claimed; making the palette live on every shell route is a shell change
  of its own.
- **No real engine run went through this page.** Every read in the specs is an MSW fixture shaped like the
  payload the route returns. The page has never been rendered against the running workspace, so the payload's
  real shape is verified by the panel's own acceptance and not by this page.
- **X1 does not reach it.** `src/flagship/claims.audit.test.tsx` renders recorded `AnswerTurn` packets, so no
  number on the place page is audited by it. The page holds the invariant by construction — every block prints
  its own source line under its numbers, and the only numbers that are not a source's are the coordinates,
  which are labelled as the address's own — but "by construction" is not a check, and extending X1 to the place
  page is open work.
- **The hour is read once, at mount.** The page takes the reader's hour from the sun at the point for the ground's
  palette; it does not re-read it while a reader leaves the tab open, where the workspace does (every 120
  seconds). Nothing on the page states the hour, so nothing here can become stale as a fact — but the ground of
  a page left open overnight will not move.
